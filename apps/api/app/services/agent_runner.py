from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Optional

from langchain_core.language_models import BaseChatModel

from apps.api.app.models import SessionContext
from packages.agents.main_assistant import run_main_assistant

StatusCallback = Optional[Callable[[str], Awaitable[None]]]


async def run_agent_turn(
    action: str,
    context: str,
    session: SessionContext,
    llm: BaseChatModel,
    on_status: StatusCallback = None,
) -> Dict[str, Any]:
    return await run_main_assistant(
        intent=action,
        context=context,
        canvas_state=session.canvas_state,
        llm=llm,
        on_status=on_status,
    )
