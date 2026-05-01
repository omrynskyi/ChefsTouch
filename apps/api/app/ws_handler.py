from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from apps.api.app.canvas_state import apply_op
from apps.api.app.db import get_client
from apps.api.app.llm import get_llm
from apps.api.app.models import SessionContext
from apps.api.app.services.agent_runner import run_agent_turn
from apps.api.app.services.context_builder import build_context, humanize_action
from apps.api.app.session_loader import SessionLoader, SessionNotFoundError

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
    loader = SessionLoader(get_client())
    try:
        ctx = loader.load(session_id)
    except SessionNotFoundError:
        logger.warning("Session %s not found", session_id)
        return

    context = build_context(ctx)
    intent = humanize_action(action, ctx)

    async def _send_status(text: str) -> None:
        await websocket.send_text(json.dumps({"type": "agent_status", "text": text}))

    result = await run_agent_turn(intent, context, ctx, get_llm(), on_status=_send_status)

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
async def _resolve_session(session_id: Optional[str]) -> str:
    client = get_client()

    if session_id:
        result = client.table("sessions").select("session_id").eq("session_id", session_id).execute()
        if result.data:
            client.table("sessions").update({"last_active": "now()"}).eq("session_id", session_id).execute()
            return session_id

    result = client.table("sessions").insert({}).execute()
    return result.data[0]["session_id"]
