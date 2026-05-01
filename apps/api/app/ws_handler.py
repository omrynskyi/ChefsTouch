from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from apps.api.app.canvas_state import apply_op
from apps.api.app.db import get_client
from apps.api.app.llm import get_llm
from apps.api.app.models import ConversationTurn, SessionContext
from apps.api.app.services.agent_runner import run_agent_turn
from apps.api.app.services.context_builder import build_context, humanize_action
from apps.api.app.session_loader import SessionLoader, SessionNotFoundError
from packages.agents.main_assistant import ASSISTANT_MESSAGE_ID, MainAssistantEvent

logger = logging.getLogger(__name__)


async def handle_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    session_id: Optional[str] = None
    action_queue: asyncio.Queue[object] = asyncio.Queue()
    stop_sentinel = object()

    async def worker() -> None:
        while True:
            item = await action_queue.get()
            try:
                if item is stop_sentinel:
                    return
                if not session_id:
                    logger.warning("Received queued action before init, discarding")
                    continue
                await _handle_action(websocket, session_id, str(item))
            except WebSocketDisconnect:
                return
            except Exception:
                logger.exception("Unhandled error while processing websocket action")
            finally:
                action_queue.task_done()

    worker_task = asyncio.create_task(worker())

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
                await action_queue.put(msg.get("action", ""))

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Unhandled error in WebSocket handler")
    finally:
        await action_queue.put(stop_sentinel)
        await worker_task


async def _handle_action(websocket: WebSocket, session_id: str, action: str) -> None:
    loader = SessionLoader(get_client())
    try:
        ctx = loader.load(session_id)
    except SessionNotFoundError:
        logger.warning("Session %s not found", session_id)
        return

    _append_turn(ctx, "user", action)
    context = build_context(ctx)
    intent = humanize_action(action, ctx)
    turn_id = str(uuid.uuid4())

    try:
        async for event in run_agent_turn(
            intent,
            context,
            ctx,
            get_llm(),
            turn_id=turn_id,
            source="websocket",
        ):
            await _handle_turn_event(websocket, ctx, event)
    finally:
        await websocket.send_text(json.dumps({"type": "agent_status", "text": ""}))
        loader.save(ctx)


async def _handle_turn_event(
    websocket: WebSocket,
    ctx: SessionContext,
    event: MainAssistantEvent,
) -> None:
    event_type = event["type"]

    if event_type == "assistant_message":
        text = event["text"]
        op = _assistant_message_op(ctx.canvas_state, text)
        await _send_canvas_op(websocket, op)
        apply_op(ctx.canvas_state, op)
        _append_turn(ctx, "assistant", text)
        await websocket.send_text(json.dumps({"type": "tts_text", "text": text}))
        return

    if event_type == "canvas_op":
        op = event["op"]
        await _send_canvas_op(websocket, op)
        apply_op(ctx.canvas_state, op)
        return

    if event_type == "status":
        await websocket.send_text(json.dumps({"type": "agent_status", "text": event["text"]}))
        return

    if event_type == "tool_call":
        return

    if event_type == "turn_complete":
        return

    logger.warning("Unknown turn event: %s", event)


def _assistant_message_op(canvas_state: dict[str, Any], text: str) -> dict[str, Any]:
    if _has_component(canvas_state, ASSISTANT_MESSAGE_ID):
        return {"op": "update", "id": ASSISTANT_MESSAGE_ID, "data": {"text": text}}
    return {
        "op": "add",
        "id": ASSISTANT_MESSAGE_ID,
        "type": "assistant-message",
        "data": {"text": text},
    }


def _has_component(canvas_state: dict[str, Any], comp_id: str) -> bool:
    active = canvas_state.get("active", canvas_state)
    staged = canvas_state.get("staged", {})
    return comp_id in active or comp_id in staged


def _append_turn(ctx: SessionContext, role: str, content: str) -> None:
    text = content.strip()
    if not text:
        return
    ctx.conversation.append(
        ConversationTurn(role=role, content=text, timestamp=datetime.now(timezone.utc))
    )


async def _send_canvas_op(websocket: WebSocket, op: dict[str, Any]) -> None:
    await websocket.send_text(json.dumps({"type": "canvas_ops", "operations": [op]}))


async def _resolve_session(session_id: Optional[str]) -> str:
    client = get_client()

    if session_id:
        result = (
            client.table("sessions").select("session_id").eq("session_id", session_id).execute()
        )
        if result.data:
            client.table("sessions").update({"last_active": "now()"}).eq("session_id", session_id).execute()
            return session_id

    result = client.table("sessions").insert({}).execute()
    return result.data[0]["session_id"]
