import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, call

import pytest

from models import ConversationTurn, SessionContext
from session_loader import CONVERSATION_MAX_TURNS, SessionLoader, SessionNotFoundError

# ─── Fixtures ─────────────────────────────────────────────────────────────────

SESSION_ID = str(uuid.uuid4())
RECIPE_ID = str(uuid.uuid4())

def _turn(i: int) -> dict:
    return {"role": "user", "content": f"msg {i}", "timestamp": "2026-01-01T00:00:00"}

def _make_session_row(*, turns: int = 3, with_recipe: bool = False) -> dict:
    return {
        "session_id": SESSION_ID,
        "conversation": [_turn(i) for i in range(turns)],
        "active_recipe_id": RECIPE_ID if with_recipe else None,
        "current_step": 2 if with_recipe else None,
        "canvas_state": {"comp-1": {"id": "comp-1", "type": "timer"}},
        "preferences": {"dietary": "vegan"},
    }

def _make_recipe_row() -> dict:
    return {
        "recipe_id": RECIPE_ID,
        "title": "Pasta",
        "description": "Nice pasta",
        "duration_minutes": 20,
        "servings": 2,
        "tags": ["italian"],
        "steps": [{"step_number": 1, "instruction": "Boil water", "tip": None}],
        "source": "generated",
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def _make_client(*, session_row=None, recipe_row=None) -> MagicMock:
    client = MagicMock()
    _table_cache: dict = {}

    def _make_table(name: str) -> MagicMock:
        tbl = MagicMock()

        def make_chain(data):
            chain = MagicMock()
            chain.execute = MagicMock(return_value=MagicMock(data=data))
            return chain

        select_mock = MagicMock()
        eq_mock = MagicMock()

        if name == "sessions":
            rows = [session_row] if session_row else []
            eq_mock.return_value = make_chain(rows)
        elif name == "recipes":
            rows = [recipe_row] if recipe_row else []
            eq_mock.return_value = make_chain(rows)

        select_mock.eq = eq_mock
        tbl.select = MagicMock(return_value=select_mock)

        update_chain = MagicMock()
        update_eq = MagicMock()
        update_eq.execute = MagicMock(return_value=MagicMock(data=[]))
        update_chain.eq = MagicMock(return_value=update_eq)
        tbl.update = MagicMock(return_value=update_chain)

        return tbl

    def table_side_effect(name: str):
        if name not in _table_cache:
            _table_cache[name] = _make_table(name)
        return _table_cache[name]

    client.table = MagicMock(side_effect=table_side_effect)
    return client


# ─── load tests ───────────────────────────────────────────────────────────────

def test_load_returns_session_context():
    client = _make_client(session_row=_make_session_row(turns=3))
    ctx = SessionLoader(client).load(SESSION_ID)

    assert isinstance(ctx, SessionContext)
    assert ctx.session_id == SESSION_ID
    assert len(ctx.conversation) == 3
    assert ctx.canvas_state == {"comp-1": {"id": "comp-1", "type": "timer"}}
    assert ctx.preferences == {"dietary": "vegan"}
    assert ctx.active_recipe is None
    assert ctx.current_step is None


def test_load_trims_conversation_to_20():
    client = _make_client(session_row=_make_session_row(turns=25))
    ctx = SessionLoader(client).load(SESSION_ID)

    assert len(ctx.conversation) == CONVERSATION_MAX_TURNS
    # Keeps the LAST 20 — content should be msg 5 through msg 24
    assert ctx.conversation[0].content == "msg 5"
    assert ctx.conversation[-1].content == "msg 24"


def test_load_fetches_active_recipe():
    client = _make_client(
        session_row=_make_session_row(with_recipe=True),
        recipe_row=_make_recipe_row(),
    )
    ctx = SessionLoader(client).load(SESSION_ID)

    assert ctx.active_recipe is not None
    assert ctx.active_recipe.title == "Pasta"
    assert len(ctx.active_recipe.steps) == 1
    assert ctx.current_step == 2


def test_load_no_active_recipe():
    client = _make_client(session_row=_make_session_row(with_recipe=False))
    ctx = SessionLoader(client).load(SESSION_ID)

    assert ctx.active_recipe is None


def test_load_raises_for_unknown_session():
    client = _make_client(session_row=None)
    with pytest.raises(SessionNotFoundError) as exc_info:
        SessionLoader(client).load("nonexistent-id")
    assert "nonexistent-id" in str(exc_info.value)


# ─── save tests ───────────────────────────────────────────────────────────────

def test_save_writes_correct_fields():
    client = _make_client()
    turns = [
        ConversationTurn(role="user", content="hi", timestamp=datetime.now(timezone.utc))
    ]
    ctx = SessionContext(
        session_id=SESSION_ID,
        conversation=turns,
        current_step=3,
        canvas_state={"t1": {}},
        preferences={"x": 1},
    )

    SessionLoader(client).save(ctx)

    # Verify update was called on sessions table
    client.table.assert_any_call("sessions")
    sessions_tbl = client.table("sessions")
    sessions_tbl.update.assert_called_once()

    payload = sessions_tbl.update.call_args[0][0]
    assert payload["current_step"] == 3
    assert payload["canvas_state"] == {"t1": {}}
    assert payload["preferences"] == {"x": 1}
    assert payload["active_recipe_id"] is None
    assert len(payload["conversation"]) == 1
    assert payload["conversation"][0]["role"] == "user"


def test_save_trims_conversation_on_write():
    client = _make_client()
    turns = [
        ConversationTurn(role="user", content=f"msg {i}", timestamp=datetime.now(timezone.utc))
        for i in range(25)
    ]
    ctx = SessionContext(session_id=SESSION_ID, conversation=turns)

    SessionLoader(client).save(ctx)

    sessions_tbl = client.table("sessions")
    payload = sessions_tbl.update.call_args[0][0]
    assert len(payload["conversation"]) == CONVERSATION_MAX_TURNS
    assert payload["conversation"][0]["content"] == "msg 5"
    assert payload["conversation"][-1]["content"] == "msg 24"
