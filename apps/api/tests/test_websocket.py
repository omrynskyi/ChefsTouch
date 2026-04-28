import uuid


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
