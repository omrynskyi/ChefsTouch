import uuid
from unittest.mock import AsyncMock, patch

from models import SessionContext


def test_new_session_creation(new_session_client):
    with new_session_client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "init", "session_id": None})
        msg = ws.receive_json()

    assert msg["type"] == "session_ready"
    assert isinstance(msg["session_id"], str)
    uuid.UUID(msg["session_id"])  # raises if not a valid UUID


def test_session_resumption(resume_session_client, existing_session_id):
    with resume_session_client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "init", "session_id": existing_session_id})
        msg = ws.receive_json()

    assert msg["type"] == "session_ready"
    assert msg["session_id"] == existing_session_id


def test_unknown_session_id_creates_new(new_session_client):
    """A session_id that doesn't exist in DB should result in a new session."""
    with new_session_client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "init", "session_id": str(uuid.uuid4())})
        msg = ws.receive_json()

    assert msg["type"] == "session_ready"
    assert isinstance(msg["session_id"], str)


def test_malformed_json_does_not_crash(new_session_client):
    """Sending garbage should not close the connection — server ignores it."""
    with new_session_client.websocket_connect("/ws") as ws:
        ws.send_text("not json at all")
        # Follow with a valid init to confirm the connection is still alive
        ws.send_json({"type": "init", "session_id": None})
        msg = ws.receive_json()

    assert msg["type"] == "session_ready"


def test_recipe_selection_action_sends_recipe_grid_before_options(new_session_client, existing_session_id):
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

    result = {
        "tts_text": "Pick a lane.",
        "canvas_ops": [
            {"op": "add", "id": "veg-grid", "type": "recipe-grid", "data": {}},
            {
                "op": "add",
                "id": "veg-opt-1",
                "type": "recipe-option",
                "parent": "veg-grid",
                "data": {"title": "Classic Vegetable Fried Rice", "action": "select_veg_opt_1"},
            },
            {
                "op": "add",
                "id": "veg-opt-2",
                "type": "recipe-option",
                "parent": "veg-grid",
                "data": {"title": "Rainbow Veggie Bowl", "action": "select_veg_opt_2"},
            },
        ],
    }

    with patch("ws_handler.SessionLoader", _LoaderStub), \
         patch("main_agent.run_main_agent", new=AsyncMock(return_value=result)), \
         patch("ws_handler._get_llm", return_value=object()):
        with new_session_client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "init", "session_id": existing_session_id})
            assert ws.receive_json()["type"] == "session_ready"

            ws.send_json({"type": "action", "action": "show recipes"})

            assert ws.receive_json() == {"type": "agent_status", "text": ""}
            assert ws.receive_json() == {"type": "tts_text", "text": "Pick a lane."}
            first_canvas = ws.receive_json()
            second_canvas = ws.receive_json()
            third_canvas = ws.receive_json()

    assert first_canvas["type"] == "canvas_ops"
    assert first_canvas["operations"][0]["id"] == "veg-grid"
    assert second_canvas["operations"][0]["id"] == "veg-opt-1"
    assert third_canvas["operations"][0]["id"] == "veg-opt-2"
