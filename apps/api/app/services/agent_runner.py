from __future__ import annotations

from typing import AsyncGenerator

from langchain_core.language_models import BaseChatModel

from apps.api.app.db import get_client
from apps.api.app.llm import get_embed_model
from apps.api.app.models import SessionContext
from packages.agents.langsmith_utils import summarize_canvas_state
from packages.agents.main_assistant import MainAssistantEvent, stream_main_assistant


async def run_agent_turn(
    action: str,
    context: str,
    session: SessionContext,
    llm: BaseChatModel,
    *,
    turn_id: str,
    generation_id: int,
    source: str = "websocket",
) -> AsyncGenerator[MainAssistantEvent, None]:
    async for event in stream_main_assistant(
        intent=action,
        context=context,
        canvas_state=session.canvas_state,
        llm=llm,
        turn_id=turn_id,
        generation_id=generation_id,
        conversation=[
            {"role": turn.role, "content": turn.content}
            for turn in session.conversation
        ],
        tracking_context={
            "session_id": session.session_id,
            "turn_id": turn_id,
            "source": source,
            "active_recipe": session.active_recipe.title if session.active_recipe else None,
            "current_step": session.current_step,
            "canvas_state": summarize_canvas_state(session.canvas_state),
        },
        supabase_client=get_client(),
        embed_model=get_embed_model(),
    ):
        yield event
