from __future__ import annotations

import os
from langchain_openai import ChatOpenAI

_client: ChatOpenAI | None = None


def get_llm() -> ChatOpenAI:
    global _client
    if _client is None:
        _client = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "google/gemma-4-e4b"),
            temperature=0.3,
            base_url=os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234/v1"),
            api_key=os.getenv("OPENAI_API_KEY", "lm-studio"),
        )
    return _client
