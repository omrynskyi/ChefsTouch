from __future__ import annotations

from typing import Any, Dict, Optional

from packages.agents.recipe_agent.agent import RecipeAgent

__all__ = ["find_recipes", "RecipeAgent"]


async def find_recipes(
    query: str,
    session_context: Optional[Dict[str, Any]] = None,
    llm: Any = None,
    *,
    client: Any = None,
    embed_model: Any = None,
) -> Dict[str, Any]:
    """Find recipes matching *query*.

    Parameters
    ----------
    query:
        Natural-language recipe search query.
    session_context:
        Optional dict of session state passed through to the returned payload.
    llm:
        LangChain chat model used for Phase 2 generation when vector search
        yields no results.
    client:
        Supabase client (keyword-only).  Required for Phase 1 vector search.
    embed_model:
        LangChain embeddings model (keyword-only).  Required for Phase 1.

    Returns
    -------
    dict with keys: ``query``, ``recipes``, ``source``, ``session_context``.
    ``source`` is one of ``"vector_search"``, ``"generated"``, or ``"stub"``.
    """
    return await RecipeAgent(client=client, embed_model=embed_model).find(
        query, session_context=session_context, llm=llm
    )
