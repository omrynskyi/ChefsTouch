import asyncio
import threading
import time
import uuid
from unittest.mock import patch

from apps.api.app.models import SessionContext


def test_new_session_creation(new_session_client):
    with new_session_client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "init", "session_id": None})
        msg = ws.receive_json()

    assert msg["type"] == "session_ready"
    assert isinstance(msg["session_id"], str)
    uuid.UUID(msg["session_id"])


def test_session_resumption(resume_session_client, existing_session_id):
    with resume_session_client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "init", "session_id": existing_session_id})
        msg = ws.receive_json()

    assert msg["type"] == "session_ready"
    assert msg["session_id"] == existing_session_id


def test_unknown_session_id_creates_new(new_session_client):
    with new_session_client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "init", "session_id": str(uuid.uuid4())})
        msg = ws.receive_json()

    assert msg["type"] == "session_ready"
    assert isinstance(msg["session_id"], str)


def test_malformed_json_does_not_crash(new_session_client):
    with new_session_client.websocket_connect("/ws") as ws:
        ws.send_text("not json at all")
        ws.send_json({"type": "init", "session_id": None})
        msg = ws.receive_json()

    assert msg["type"] == "session_ready"


def test_action_streams_assistant_message_before_canvas_ops(new_session_client, existing_session_id):
    ctx = SessionContext(
        session_id=existing_session_id,
        conversation=[],
        canvas_state={"active": {}, "staged": {}},
        preferences={},
    )

    class _LoaderStub:
        def __init__(self, client):
            self.saved_context = None

        def load(self, session_id: str) -> SessionContext:
            return ctx

        def save(self, context: SessionContext) -> None:
            self.saved_context = context

    async def _stream_turn(*args, **kwargs):
        yield {"type": "speech_commit", "turn_id": "turn-1", "generation_id": 1, "message_id": "msg-1", "text": "Pick a lane."}
        yield {"type": "canvas_op", "turn_id": "turn-1", "generation_id": 1, "op": {"op": "add", "id": "veg-grid", "type": "recipe-grid", "data": {}}}
        yield {
            "type": "canvas_op",
            "turn_id": "turn-1",
            "generation_id": 1,
            "op": {
                "op": "add",
                "id": "veg-opt-1",
                "type": "recipe-option",
                "parent": "veg-grid",
                "data": {"title": "Classic Vegetable Fried Rice", "action": "select_veg_opt_1"},
            },
        }
        yield {
            "type": "canvas_op",
            "turn_id": "turn-1",
            "generation_id": 1,
            "op": {
                "op": "add",
                "id": "veg-opt-2",
                "type": "recipe-option",
                "parent": "veg-grid",
                "data": {"title": "Rainbow Veggie Bowl", "action": "select_veg_opt_2"},
            },
        }
        yield {"type": "turn_completed", "turn_id": "turn-1", "generation_id": 1}

    with patch("apps.api.app.ws_handler.SessionLoader", _LoaderStub), \
         patch("apps.api.app.ws_handler.run_agent_turn", _stream_turn), \
         patch("apps.api.app.ws_handler.get_llm", return_value=object()):
        with new_session_client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "init", "session_id": existing_session_id})
            assert ws.receive_json()["type"] == "session_ready"

            ws.send_json({"type": "action", "action": "show recipes"})

            turn_started = ws.receive_json()
            speech_commit = ws.receive_json()
            assistant_canvas = ws.receive_json()
            assistant_tts = ws.receive_json()
            first_canvas = ws.receive_json()
            second_canvas = ws.receive_json()
            third_canvas = ws.receive_json()
            turn_completed = ws.receive_json()
            cleared_status = ws.receive_json()

    assert turn_started["type"] == "turn_started"
    assert speech_commit == {
        "type": "speech_commit",
        "turn_id": turn_started["turn_id"],
        "generation_id": turn_started["generation_id"],
        "message_id": "msg-1",
        "text": "Pick a lane.",
    }
    assert assistant_canvas == {
        "type": "canvas_ops",
        "operations": [{
            "op": "add",
            "id": "sys-assistant-message",
            "type": "assistant-message",
            "data": {"text": "Pick a lane."},
        }],
        "turn_id": turn_started["turn_id"],
        "generation_id": turn_started["generation_id"],
    }
    assert assistant_tts == {"type": "tts_text", "text": "Pick a lane."}
    assert first_canvas["operations"][0]["id"] == "veg-grid"
    assert second_canvas["operations"][0]["id"] == "veg-opt-1"
    assert third_canvas["operations"][0]["id"] == "veg-opt-2"
    assert turn_completed == {
        "type": "turn_completed",
        "turn_id": turn_started["turn_id"],
        "generation_id": turn_started["generation_id"],
    }
    assert cleared_status == {"type": "agent_status", "text": ""}


def test_second_action_waits_for_first_turn_to_finish(new_session_client, existing_session_id):
    ctx = SessionContext(
        session_id=existing_session_id,
        conversation=[],
        canvas_state={"active": {}, "staged": {}},
        preferences={},
    )
    started_actions: list[str] = []
    release_first_turn = threading.Event()

    class _LoaderStub:
        def __init__(self, client):
            self.saved_context = None

        def load(self, session_id: str) -> SessionContext:
            return ctx

        def save(self, context: SessionContext) -> None:
            self.saved_context = context

    async def _queued_turn(action: str, *args, **kwargs):
        started_actions.append(action)
        generation_id = kwargs["generation_id"]
        turn_id = kwargs["turn_id"]
        yield {
            "type": "speech_commit",
            "turn_id": turn_id,
            "generation_id": generation_id,
            "message_id": f"{turn_id}:msg",
            "text": f"Working on {action}",
        }
        if action == "first action":
            while not release_first_turn.is_set():
                await asyncio.sleep(0.01)
        yield {"type": "turn_completed", "turn_id": turn_id, "generation_id": generation_id}

    with patch("apps.api.app.ws_handler.SessionLoader", _LoaderStub), \
         patch("apps.api.app.ws_handler.run_agent_turn", _queued_turn), \
         patch("apps.api.app.ws_handler.get_llm", return_value=object()):
        with new_session_client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "init", "session_id": existing_session_id})
            assert ws.receive_json()["type"] == "session_ready"

            ws.send_json({"type": "action", "action": "first action"})
            ws.send_json({"type": "action", "action": "second action"})

            first_turn_started = ws.receive_json()
            second_turn_started = ws.receive_json()
            first_speech = ws.receive_json()
            first_canvas = ws.receive_json()
            first_tts = ws.receive_json()

            assert first_canvas["operations"][0]["data"]["text"] == "Working on first action"
            assert first_tts == {"type": "tts_text", "text": "Working on first action"}
            assert first_speech["type"] == "speech_commit"

            time.sleep(0.05)
            assert started_actions == ["first action"]

            release_first_turn.set()

            assert ws.receive_json() == {
                "type": "turn_completed",
                "turn_id": first_turn_started["turn_id"],
                "generation_id": first_turn_started["generation_id"],
            }
            assert ws.receive_json() == {"type": "agent_status", "text": ""}
            second_speech = ws.receive_json()
            second_canvas = ws.receive_json()
            second_tts = ws.receive_json()

    assert started_actions == ["first action", "second action"]
    assert first_turn_started["type"] == "turn_started"
    assert second_turn_started["type"] == "turn_started"
    assert second_speech["type"] == "speech_commit"
    assert second_canvas["operations"][0]["data"]["text"] == "Working on second action"
    assert second_tts == {"type": "tts_text", "text": "Working on second action"}


def test_interrupt_emits_cancel_and_ack(new_session_client, existing_session_id):
    ctx = SessionContext(
        session_id=existing_session_id,
        conversation=[],
        canvas_state={"active": {}, "staged": {}},
        preferences={},
    )

    class _LoaderStub:
        def __init__(self, client):
            self.saved_context = None

        def load(self, session_id: str) -> SessionContext:
            return ctx

        def save(self, context: SessionContext) -> None:
            self.saved_context = context

    async def _slow_turn(action: str, *args, **kwargs):
        await asyncio.sleep(0.05)
        yield {
            "type": "speech_commit",
            "turn_id": kwargs["turn_id"],
            "generation_id": kwargs["generation_id"],
            "message_id": "late-msg",
            "text": "Too late.",
        }
        yield {
            "type": "turn_completed",
            "turn_id": kwargs["turn_id"],
            "generation_id": kwargs["generation_id"],
        }

    with patch("apps.api.app.ws_handler.SessionLoader", _LoaderStub), \
         patch("apps.api.app.ws_handler.run_agent_turn", _slow_turn), \
         patch("apps.api.app.ws_handler.get_llm", return_value=object()):
        with new_session_client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "init", "session_id": existing_session_id})
            assert ws.receive_json()["type"] == "session_ready"

            ws.send_json({"type": "action", "action": "first action"})
            turn_started = ws.receive_json()

            ws.send_json({"type": "interrupt"})
            speech_cancel = ws.receive_json()
            interrupt_ack = ws.receive_json()
            cleared_status = ws.receive_json()

            assert speech_cancel["type"] == "speech_cancel"
            assert speech_cancel["reason"] == "interrupted"
            assert interrupt_ack == {
                "type": "interrupt_ack",
                "turn_id": turn_started["turn_id"],
                "generation_id": turn_started["generation_id"] + 1,
                "cancelled_generation_id": turn_started["generation_id"],
            }
            assert cleared_status == {"type": "agent_status", "text": ""}
