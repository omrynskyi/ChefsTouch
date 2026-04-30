from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from canvas_state import apply_op
from db import get_client
from llm import get_llm
from models import SessionContext
from session_loader import SessionLoader, SessionNotFoundError

logger = logging.getLogger(__name__)


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
    from main_agent import run_main_agent

    loader = SessionLoader(get_client())
    try:
        ctx = loader.load(session_id)
    except SessionNotFoundError:
        logger.warning("Session %s not found", session_id)
        return

    context = _build_context(ctx)
    intent = _humanize_action(action, ctx)

    async def _send_status(text: str) -> None:
        await websocket.send_text(json.dumps({"type": "agent_status", "text": text}))

    result = await run_main_agent(intent, context, ctx.canvas_state, get_llm(), on_status=_send_status)

    await _send_status("")  # clear the status bar

    if result.get("tts_text"):
        await websocket.send_text(json.dumps({
            "type": "tts_text",
            "text": result["tts_text"],
        }))

    for op in result.get("canvas_ops", []):
        await websocket.send_text(json.dumps({
            "type": "canvas_ops",
            "operations": [op],
        }))
        apply_op(ctx.canvas_state, op)

    loader.save(ctx)


def _build_context(ctx: SessionContext) -> str:
    parts = []
    if ctx.active_recipe:
        parts.append(f"Recipe: {ctx.active_recipe.title}")
        if ctx.current_step is not None:
            total = len(ctx.active_recipe.steps)
            parts.append(f"Step {ctx.current_step + 1} of {total}")
    return ". ".join(parts) if parts else ""


def _humanize_action(action: str, ctx: SessionContext) -> str:
    """Convert machine action IDs into natural-language intents for the LLM."""
    if action == "next_step":
        if ctx.active_recipe and ctx.current_step is not None:
            next_n = ctx.current_step + 2  # 1-based
            total = len(ctx.active_recipe.steps)
            return f"Go to step {next_n} of {total} in {ctx.active_recipe.title}"
        return "Advance to the next cooking step"

    if action.startswith("select_"):
        name = action[len("select_"):].replace("_", " ").title()
        return f'User selected recipe: "{name}"'

    # Fall back to the raw string — may be a free-text intent from the debug panel
    return action


async def _resolve_session(session_id: Optional[str]) -> str:
    client = get_client()

    if session_id:
        result = client.table("sessions").select("session_id").eq("session_id", session_id).execute()
        if result.data:
            client.table("sessions").update({"last_active": "now()"}).eq("session_id", session_id).execute()
            return session_id

    result = client.table("sessions").insert({}).execute()
    return result.data[0]["session_id"]
