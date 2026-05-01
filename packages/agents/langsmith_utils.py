from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Literal, Optional

from langsmith import Client

TracingMode = Literal[False, True, "local"]


def _env_flag(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def langsmith_tracing_mode() -> TracingMode:
    configured = _env_flag("LANGSMITH_TRACING") or _env_flag("LANGCHAIN_TRACING_V2")
    if configured == "local":
        return "local"
    if configured in {"1", "true", "yes", "on"}:
        return True if has_langsmith_api_key() else False
    if configured in {"0", "false", "no", "off"}:
        return False
    return has_langsmith_api_key()


def has_langsmith_api_key() -> bool:
    return bool(os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"))


def should_upload_eval_results() -> bool:
    configured = _env_flag("LANGSMITH_EVAL_UPLOAD_RESULTS")
    if configured in {"1", "true", "yes", "on"}:
        return has_langsmith_api_key()
    if configured in {"0", "false", "no", "off"}:
        return False
    return False


@lru_cache(maxsize=1)
def get_langsmith_client() -> Optional[Client]:
    if not has_langsmith_api_key():
        return None
    return Client()


def get_langsmith_project(suffix: str = "") -> str:
    base = (
        os.getenv("LANGSMITH_PROJECT")
        or os.getenv("LANGCHAIN_PROJECT")
        or "pair-cooking"
    )
    return f"{base}-{suffix}" if suffix else base


def summarize_canvas_state(canvas_state: dict[str, Any]) -> dict[str, Any]:
    active = canvas_state.get("active", canvas_state)
    staged = canvas_state.get("staged", {})
    active_ids = sorted(active.keys()) if isinstance(active, dict) else []
    staged_ids = sorted(staged.keys()) if isinstance(staged, dict) else []
    return {
        "active_count": len(active_ids),
        "staged_count": len(staged_ids),
        "active_ids": active_ids[:10],
        "staged_ids": staged_ids[:10],
    }
