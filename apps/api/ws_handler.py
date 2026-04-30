from __future__ import annotations

import json
import logging
import os
import sys
from typing import Optional

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from canvas_state import apply_op
from db import get_client
from models import SessionContext
from session_loader import SessionLoader, SessionNotFoundError

# Make render-agent importable from the monorepo without installing it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../packages/render-agent"))

logger = logging.getLogger(__name__)

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_openai import ChatOpenAI
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    return _llm


async def handle_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    session_id: Optional[str] = None

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Received malformed JSON, ignoring")
                continue

            msg_type = msg.get("type")

            if msg_type == "init":
                session_id = await _resolve_session(msg.get("session_id"))
                await websocket.send_text(
                    json.dumps({"type": "session_ready", "session_id": session_id})
                )

            elif msg_type == "action":
                if not session_id:
                    logger.warning("Received action before init, ignoring")
                    continue
                action = msg.get("action", "")
                await _handle_action(websocket, session_id, action)

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Unhandled error in WebSocket handler")


async def _handle_action(websocket: WebSocket, session_id: str, action: str) -> None:
    from render_agent import ContentEvent, SkeletonEvent, astream_events

    loader = SessionLoader(get_client())
    try:
        ctx = loader.load(session_id)
    except SessionNotFoundError:
        logger.warning("Session %s not found", session_id)
        return

    context = _build_context(ctx)

    async for event in astream_events(action, context, ctx.canvas_state, _get_llm()):
        if isinstance(event, SkeletonEvent):
            await websocket.send_text(json.dumps({
                "type": "canvas_ops",
                "operations": [{"op": "skeleton", "id": event.id, "type": event.component_type}],
            }))
        elif isinstance(event, ContentEvent):
            await websocket.send_text(json.dumps({
                "type": "canvas_ops",
                "operations": [event.op],
            }))
            apply_op(ctx.canvas_state, event.op)

    loader.save(ctx)


def _build_context(ctx: SessionContext) -> str:
    parts = []
    if ctx.active_recipe:
        parts.append(f"Recipe: {ctx.active_recipe.title}")
        if ctx.current_step is not None:
            total = len(ctx.active_recipe.steps)
            parts.append(f"Step {ctx.current_step + 1} of {total}")
    return ". ".join(parts) if parts else ""


async def _resolve_session(session_id: Optional[str]) -> str:
    client = get_client()

    if session_id:
        result = client.table("sessions").select("session_id").eq("session_id", session_id).execute()
        if result.data:
            client.table("sessions").update({"last_active": "now()"}).eq("session_id", session_id).execute()
            return session_id

    result = client.table("sessions").insert({}).execute()
    return result.data[0]["session_id"]
