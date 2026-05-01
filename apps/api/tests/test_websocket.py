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
        yield {"type": "assistant_message", "text": "Pick a lane."}
        yield {"type": "canvas_op", "op": {"op": "add", "id": "veg-grid", "type": "recipe-grid", "data": {}}}
        yield {
            "type": "canvas_op",
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
            "op": {
                "op": "add",
                "id": "veg-opt-2",
                "type": "recipe-option",
                "parent": "veg-grid",
                "data": {"title": "Rainbow Veggie Bowl", "action": "select_veg_opt_2"},
            },
        }
        yield {"type": "turn_complete"}

    with patch("apps.api.app.ws_handler.SessionLoader", _LoaderStub), \
         patch("apps.api.app.ws_handler.run_agent_turn", _stream_turn), \
         patch("apps.api.app.ws_handler.get_llm", return_value=object()):
        with new_session_client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "init", "session_id": existing_session_id})
            assert ws.receive_json()["type"] == "session_ready"

            ws.send_json({"type": "action", "action": "show recipes"})

            assistant_canvas = ws.receive_json()
            assistant_tts = ws.receive_json()
            first_canvas = ws.receive_json()
            second_canvas = ws.receive_json()
            third_canvas = ws.receive_json()
            cleared_status = ws.receive_json()

    assert assistant_canvas == {
        "type": "canvas_ops",
        "operations": [{
            "op": "add",
            "id": "sys-assistant-message",
            "type": "assistant-message",
            "data": {"text": "Pick a lane."},
        }],
    }
    assert assistant_tts == {"type": "tts_text", "text": "Pick a lane."}
    assert first_canvas["operations"][0]["id"] == "veg-grid"
    assert second_canvas["operations"][0]["id"] == "veg-opt-1"
    assert third_canvas["operations"][0]["id"] == "veg-opt-2"
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
        yield {"type": "assistant_message", "text": f"Working on {action}"}
        if action == "first action":
            while not release_first_turn.is_set():
                await asyncio.sleep(0.01)
        yield {"type": "turn_complete"}

    with patch("apps.api.app.ws_handler.SessionLoader", _LoaderStub), \
         patch("apps.api.app.ws_handler.run_agent_turn", _queued_turn), \
         patch("apps.api.app.ws_handler.get_llm", return_value=object()):
        with new_session_client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "init", "session_id": existing_session_id})
            assert ws.receive_json()["type"] == "session_ready"

            ws.send_json({"type": "action", "action": "first action"})
            ws.send_json({"type": "action", "action": "second action"})

            first_canvas = ws.receive_json()
            first_tts = ws.receive_json()

            assert first_canvas["operations"][0]["data"]["text"] == "Working on first action"
            assert first_tts == {"type": "tts_text", "text": "Working on first action"}

            time.sleep(0.05)
            assert started_actions == ["first action"]

            release_first_turn.set()

            assert ws.receive_json() == {"type": "agent_status", "text": ""}
            second_canvas = ws.receive_json()
            second_tts = ws.receive_json()

    assert started_actions == ["first action", "second action"]
    assert second_canvas["operations"][0]["data"]["text"] == "Working on second action"
    assert second_tts == {"type": "tts_text", "text": "Working on second action"}
