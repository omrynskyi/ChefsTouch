from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from db import get_client

logger = logging.getLogger(__name__)


async def handle_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
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

            # Future message types (audio_chunk, camera_frames, etc.) handled here

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Unhandled error in WebSocket handler")


async def _resolve_session(session_id: Optional[str]) -> str:
    client = get_client()

    if session_id:
        result = client.table("sessions").select("session_id").eq("session_id", session_id).execute()
        if result.data:
            client.table("sessions").update({"last_active": "now()"}).eq("session_id", session_id).execute()
            return session_id

    # Create a new session (all columns have DB defaults)
    result = client.table("sessions").insert({}).execute()
    return result.data[0]["session_id"]
