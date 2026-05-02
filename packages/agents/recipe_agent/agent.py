from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from packages.agents.recipe_agent.prompts import RECIPE_GENERATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class RecipeAgent:
    """Two-phase recipe finder.

    Phase 1 — Vector search: embed the query with the injected embed_model and
    run a cosine-similarity RPC against the Supabase recipes table.  Returns
    immediately if any results clear the similarity threshold.

    Phase 2 — LLM generation: if Phase 1 yields nothing (or client / embed_model
    were not supplied), ask the LLM to synthesise a recipe as JSON.  The result is
    returned ephemerally — nothing is written to the database.

    If neither phase runs, returns a stub with an empty recipes list.
    """

    def __init__(self, client: Any = None, embed_model: Any = None) -> None:
        self._client = client
        self._embed_model = embed_model

    async def find(
        self,
        query: str,
        session_context: Optional[Dict[str, Any]] = None,
        llm: Any = None,
    ) -> Dict[str, Any]:
        ctx = session_context or {}

        # ------------------------------------------------------------------ #
        # Phase 1 — vector search (requires BOTH client and embed_model)      #
        # ------------------------------------------------------------------ #
        if self._client is not None and self._embed_model is not None:
            try:
                vector = await self._embed_model.aembed_query(query)
                result = self._client.rpc(
                    "match_recipes",
                    {
                        "query_embedding": vector,
                        "match_threshold": 0.72,
                        "match_count": 5,
                    },
                ).execute()
                if result.data:
                    return {
                        "query": query,
                        "recipes": result.data,
                        "source": "vector_search",
                        "session_context": ctx,
                    }
            except Exception:
                logger.warning("Recipe vector search failed", exc_info=True)

        # ------------------------------------------------------------------ #
        # Phase 2 — LLM generation                                            #
        # ------------------------------------------------------------------ #
        if llm is not None:
            try:
                response = await llm.ainvoke(
                    [
                        SystemMessage(content=RECIPE_GENERATION_SYSTEM_PROMPT),
                        HumanMessage(content=query),
                    ]
                )
                raw = getattr(response, "content", "") or ""
                # Strip optional markdown fence that local models sometimes add.
                raw = (
                    raw.strip()
                    .removeprefix("```json")
                    .removeprefix("```")
                    .removesuffix("```")
                    .strip()
                )
                recipe = json.loads(raw)
                return {
                    "query": query,
                    "recipes": [recipe],
                    "source": "generated",
                    "session_context": ctx,
                }
            except Exception:
                logger.warning("Recipe LLM generation failed", exc_info=True)
                return {
                    "query": query,
                    "recipes": [],
                    "source": "generated",
                    "session_context": ctx,
                }

        # ------------------------------------------------------------------ #
        # Stub fallback                                                        #
        # ------------------------------------------------------------------ #
        return {
            "query": query,
            "recipes": [],
            "source": "stub",
            "session_context": ctx,
        }
