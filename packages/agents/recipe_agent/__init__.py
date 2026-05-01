from __future__ import annotations

from typing import Any, Dict, List, Optional


async def find_recipes(query: str, session_context: Optional[Dict[str, Any]] = None, llm: Any = None) -> Dict[str, Any]:
    return {
        "query": query,
        "recipes": [],
        "source": "stub",
        "session_context": session_context or {},
    }
