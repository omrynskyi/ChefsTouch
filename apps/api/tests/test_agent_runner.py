from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from apps.api.app.models import ConversationTurn, SessionContext
from apps.api.app.services.agent_runner import run_agent_turn


@pytest.mark.asyncio
async def test_run_agent_turn_passes_session_conversation_to_main_assistant():
    session = SessionContext(
        session_id="session-123",
        conversation=[
            ConversationTurn(
                role="user",
                content="I don't eat mushrooms.",
                timestamp=datetime.now(timezone.utc),
            ),
            ConversationTurn(
                role="assistant",
                content="Got it, no mushrooms.",
                timestamp=datetime.now(timezone.utc),
            ),
        ],
        canvas_state={"active": {}, "staged": {}},
        preferences={},
    )

    captured = {}

    async def _fake_stream_main_assistant(**kwargs):
        captured.update(kwargs)
        yield {"type": "turn_completed", "turn_id": "turn-123", "generation_id": 1}

    with patch(
        "apps.api.app.services.agent_runner.stream_main_assistant",
        _fake_stream_main_assistant,
    ):
        events = [
            event
            async for event in run_agent_turn(
                action="show me dinner ideas",
                context="",
                session=session,
                llm=object(),  # type: ignore[arg-type]
                turn_id="turn-123",
                generation_id=1,
            )
        ]

    assert events == [{"type": "turn_completed", "turn_id": "turn-123", "generation_id": 1}]
    assert captured["conversation"] == [
        {"role": "user", "content": "I don't eat mushrooms."},
        {"role": "assistant", "content": "Got it, no mushrooms."},
    ]
