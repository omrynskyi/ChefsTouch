import uuid
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

FAKE_SESSION_ID = str(uuid.uuid4())


def _make_mock_client(existing_id: Optional[str] = None) -> MagicMock:
    """Return a Supabase client mock that simulates sessions table operations."""
    mock = MagicMock()

    def table_side_effect(name: str):
        tbl = MagicMock()

        # select().eq().execute() — return existing row when id matches
        def select_execute():
            result = MagicMock()
            result.data = [{"session_id": existing_id}] if existing_id else []
            return result

        select_chain = MagicMock()
        select_chain.execute = select_execute
        eq_chain = MagicMock(return_value=select_chain)
        select_mock = MagicMock()
        select_mock.eq = eq_chain
        tbl.select = MagicMock(return_value=select_mock)

        # update().eq().execute()
        update_eq = MagicMock()
        update_eq.execute = MagicMock(return_value=MagicMock(data=[]))
        tbl.update = MagicMock(return_value=MagicMock(eq=MagicMock(return_value=update_eq)))

        # insert().execute() — return new session
        insert_result = MagicMock()
        insert_result.data = [{"session_id": FAKE_SESSION_ID}]
        insert_mock = MagicMock()
        insert_mock.execute = MagicMock(return_value=insert_result)
        tbl.insert = MagicMock(return_value=insert_mock)

        return tbl

    mock.table = MagicMock(side_effect=table_side_effect)
    return mock


@pytest.fixture()
def new_session_client():
    """TestClient where no session exists yet — init must create one."""
    mock_db = _make_mock_client(existing_id=None)
    with patch("apps.api.app.ws_handler.get_client", return_value=mock_db):
        from apps.api.app.main import app
        with TestClient(app) as c:
            yield c


@pytest.fixture()
def resume_session_client():
    """TestClient where FAKE_SESSION_ID already exists in DB."""
    mock_db = _make_mock_client(existing_id=FAKE_SESSION_ID)
    with patch("apps.api.app.ws_handler.get_client", return_value=mock_db):
        from apps.api.app.main import app
        with TestClient(app) as c:
            yield c


@pytest.fixture()
def existing_session_id() -> str:
    return FAKE_SESSION_ID
