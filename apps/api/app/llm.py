from __future__ import annotations

import os
from typing import Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

_client: Optional[ChatOpenAI] = None
_embed_model: Optional[OpenAIEmbeddings] = None


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


def get_embed_model() -> OpenAIEmbeddings:
    """Return a singleton OpenAIEmbeddings client pointed at the local LM Studio
    server running nomic-embed-text-v1 (768-dimensional output).

    LM Studio exposes an OpenAI-compatible /v1/embeddings endpoint, so we reuse
    the same base_url and api_key as the LLM client.
    """
    global _embed_model
    if _embed_model is None:
        _embed_model = OpenAIEmbeddings(
            model="nomic-embed-text-v1",
            base_url=os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234/v1"),
            api_key=os.getenv("OPENAI_API_KEY", "lm-studio"),
            check_embedding_ctx_length=False,  # local models don't expose this metadata
        )
    return _embed_model
