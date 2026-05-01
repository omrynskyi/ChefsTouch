from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from apps.api.app.db import get_client
from apps.api.app.llm import get_llm
from apps.api.app.runtime import RuntimeEmitter, RuntimeRegistry, TurnController
from apps.api.app.services.agent_runner import run_agent_turn
from apps.api.app.services.context_builder import build_context, humanize_action
from apps.api.app.session_loader import SessionLoader, SessionNotFoundError

logger = logging.getLogger(__name__)

_RUNTIME_REGISTRY = RuntimeRegistry()


async def handle_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    session_id: Optional[str] = None
    action_queue: asyncio.Queue[object] = asyncio.Queue()
    stop_sentinel = object()
    controller = TurnController(_RUNTIME_REGISTRY)

    async def worker() -> None:
        while True:
            item = await action_queue.get()
            try:
                if item is stop_sentinel:
                    return
                if not session_id:
                    logger.warning("Received queued action before init, discarding")
                    continue
                await _handle_action(websocket, session_id, item)  # type: ignore[arg-type]
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
                turn_id = str(uuid.uuid4())
                queued = controller.handle_action(
                    session_id,
                    str(msg.get("action", "")),
                    turn_id,
                    source="websocket",
                )
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "turn_started",
                            "turn_id": queued.turn_id,
                            "generation_id": queued.generation_id,
                            "source": queued.source,
                        }
                    )
                )
                await action_queue.put(queued)
            elif msg_type == "interrupt":
                if not session_id:
                    logger.warning("Received interrupt before init, ignoring")
                    continue
                cancelled = controller.handle_interrupt(session_id)
                if cancelled is not None:
                    turn_id, generation_id, cancelled_generation_id = cancelled
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "speech_cancel",
                                "turn_id": turn_id,
                                "generation_id": generation_id,
                                "message_id": f"{turn_id}:cancelled",
                                "reason": "interrupted",
                            }
                        )
                    )
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "interrupt_ack",
                                "turn_id": turn_id,
                                "generation_id": generation_id,
                                "cancelled_generation_id": cancelled_generation_id,
                            }
                        )
                    )
                    await websocket.send_text(json.dumps({"type": "agent_status", "text": ""}))

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Unhandled error in WebSocket handler")
    finally:
        await action_queue.put(stop_sentinel)
        await worker_task


async def _handle_action(websocket: WebSocket, session_id: str, queued) -> None:
    runtime = _RUNTIME_REGISTRY.get_or_create(session_id)
    if runtime.active_generation_id != queued.generation_id:
        return

    loader = SessionLoader(get_client())
    try:
        ctx = loader.load(session_id)
    except SessionNotFoundError:
        logger.warning("Session %s not found", session_id)
        return

    emitter = RuntimeEmitter(websocket, ctx)
    _append_user_turn(ctx, queued.action)
    context = build_context(ctx)
    intent = humanize_action(queued.action, ctx)
    _RUNTIME_REGISTRY.mark_turn_running(session_id, queued.generation_id)

    try:
        async for event in run_agent_turn(
            intent,
            context,
            ctx,
            get_llm(),
            turn_id=queued.turn_id,
            generation_id=queued.generation_id,
            source=queued.source,
        ):
            if not _RUNTIME_REGISTRY.is_active_generation(session_id, queued.generation_id):
                continue
            await _handle_turn_event(emitter, session_id, event)
    finally:
        if _RUNTIME_REGISTRY.is_active_generation(session_id, queued.generation_id):
            _RUNTIME_REGISTRY.complete_turn(session_id, queued.generation_id)
            await emitter.clear_status()
        loader.save(ctx)


async def _handle_turn_event(
    emitter: RuntimeEmitter,
    session_id: str,
    event: dict,
) -> None:
    event_type = event["type"]

    if event_type == "speech_commit":
        _RUNTIME_REGISTRY.set_speech_message(session_id, event["message_id"], event["text"])
    elif event_type == "tool_started":
        _RUNTIME_REGISTRY.record_tool_started(
            session_id,
            event["tool_call_id"],
            event["tool_name"],
        )
    elif event_type == "tool_result":
        _RUNTIME_REGISTRY.record_tool_finished(session_id, event["tool_call_id"])
    elif event_type == "tool_failed":
        _RUNTIME_REGISTRY.record_tool_finished(
            session_id,
            event["tool_call_id"],
            failed=True,
        )
    elif event_type == "turn_completed":
        _RUNTIME_REGISTRY.complete_turn(session_id, event["generation_id"])

    if event_type == "tool_call":
        return

    await emitter.emit(event)


def _append_user_turn(ctx, content: str) -> None:
    text = content.strip()
    if not text:
        return
    from datetime import datetime, timezone
    from apps.api.app.models import ConversationTurn

    ctx.conversation.append(
        ConversationTurn(role="user", content=text, timestamp=datetime.now(timezone.utc))
    )


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
