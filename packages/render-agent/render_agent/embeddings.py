from __future__ import annotations

from typing import List


class LocalEmbeddings:
    """
    Wraps sentence-transformers for local CPU embeddings with no API key.

    Default model: all-MiniLM-L6-v2 (384 dims, ~80MB download on first use)

    Usage:
        from render_agent.embeddings import LocalEmbeddings
        embeddings = LocalEmbeddings()
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for LocalEmbeddings. "
                "Install it with: pip install sentence-transformers"
            )
        self._model = SentenceTransformer(model_name)

    async def aembed_query(self, text: str) -> List[float]:
        return self._model.encode(text, convert_to_numpy=True).tolist()

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._model.encode(texts, convert_to_numpy=True).tolist()

    # sync versions for non-async callers
    def embed_query(self, text: str) -> List[float]:
        return self._model.encode(text, convert_to_numpy=True).tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._model.encode(texts, convert_to_numpy=True).tolist()
