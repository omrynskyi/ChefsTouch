from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket

from apps.api.app.canvas_state import apply_op
from apps.api.app.models import ConversationTurn, SessionContext
from packages.agents.main_assistant import ASSISTANT_MESSAGE_ID


class RuntimeEmitter:
    def __init__(self, websocket: WebSocket, ctx: SessionContext) -> None:
        self._websocket = websocket
        self._ctx = ctx

    async def emit(self, event: dict[str, Any]) -> None:
        event_type = event["type"]

        if event_type == "speech_commit":
            await self._send_json(event)
            text = event["text"]
            op = self._assistant_message_op(text)
            await self.emit_canvas_ops(
                [op],
                turn_id=event["turn_id"],
                generation_id=event["generation_id"],
            )
            self._append_turn("assistant", text)
            await self._send_json({"type": "tts_text", "text": text})
            return

        if event_type == "speech_cancel":
            await self._send_json(event)
            return

        if event_type == "status":
            await self._send_json(
                {
                    "type": "agent_status",
                    "text": event["text"],
                    "turn_id": event["turn_id"],
                    "generation_id": event["generation_id"],
                }
            )
            return

        if event_type == "canvas_op":
            await self.emit_canvas_ops(
                [event["op"]],
                turn_id=event["turn_id"],
                generation_id=event["generation_id"],
            )
            return

        await self._send_json(event)

    async def emit_canvas_ops(
        self,
        operations: list[dict[str, Any]],
        *,
        turn_id: str | None = None,
        generation_id: int | None = None,
    ) -> None:
        payload: dict[str, Any] = {"type": "canvas_ops", "operations": operations}
        if turn_id is not None:
            payload["turn_id"] = turn_id
        if generation_id is not None:
            payload["generation_id"] = generation_id
        await self._send_json(payload)
        for op in operations:
            apply_op(self._ctx.canvas_state, op)

    async def clear_status(self) -> None:
        await self._send_json({"type": "agent_status", "text": ""})

    def _assistant_message_op(self, text: str) -> dict[str, Any]:
        if self._has_component(ASSISTANT_MESSAGE_ID):
            return {"op": "update", "id": ASSISTANT_MESSAGE_ID, "data": {"text": text}}
        return {
            "op": "add",
            "id": ASSISTANT_MESSAGE_ID,
            "type": "assistant-message",
            "data": {"text": text},
        }

    def _has_component(self, comp_id: str) -> bool:
        active = self._ctx.canvas_state.get("active", self._ctx.canvas_state)
        staged = self._ctx.canvas_state.get("staged", {})
        return comp_id in active or comp_id in staged

    def _append_turn(self, role: str, content: str) -> None:
        text = content.strip()
        if not text:
            return
        from datetime import datetime, timezone

        self._ctx.conversation.append(
            ConversationTurn(role=role, content=text, timestamp=datetime.now(timezone.utc))
        )

    async def _send_json(self, payload: dict[str, Any]) -> None:
        await self._websocket.send_text(json.dumps(payload))
