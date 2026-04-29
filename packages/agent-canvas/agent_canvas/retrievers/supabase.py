from __future__ import annotations

from typing import Any, List, Optional, Sequence

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


class SupabaseCSSRetriever:
    """
    Retrieves CSS class entries from a Supabase pgvector index.

    Requires the design_snippets table and match_design_snippets RPC
    from migrations/design_snippets.sql.

    Usage:
        from supabase import create_client
        from langchain_openai import OpenAIEmbeddings

        retriever = SupabaseCSSRetriever(
            client=create_client(url, key),
            embeddings=OpenAIEmbeddings(),
            k=10,
        )
        graph = build_canvas_render_graph(llm=llm, retriever=retriever)
    """

    def __init__(
        self,
        client: Any,
        embeddings: Embeddings,
        k: int = 10,
        match_threshold: float = 0.0,
    ) -> None:
        self._client = client
        self._embeddings = embeddings
        self._k = k
        self._match_threshold = match_threshold

    async def ainvoke(self, query: str, **kwargs: Any) -> Sequence[Document]:
        vector = await self._embeddings.aembed_query(query)
        vector_str = "[" + ",".join(str(v) for v in vector) + "]"
        result = self._client.rpc(
            "match_design_snippets",
            {"query_embedding": vector_str, "match_count": self._k},
        ).execute()

        if not result.data:
            return []

        return [
            Document(
                page_content=row["content"],
                metadata={"name": row["name"], "similarity": row["similarity"]},
            )
            for row in result.data
            if row["similarity"] >= self._match_threshold
        ]

    async def debug(self, query: str) -> None:
        """Print raw RPC response for a query — use to diagnose retrieval issues."""
        vector = await self._embeddings.aembed_query(query)
        vector_str = "[" + ",".join(str(v) for v in vector) + "]"
        print(f"  vector dims: {len(vector)}, first 3: {vector[:3]}")
        result = self._client.rpc(
            "match_design_snippets",
            {"query_embedding": vector_str, "match_count": self._k},
        ).execute()
        print(f"  result.data length: {len(result.data) if result.data else 'None'}")
        if result.data:
            for row in result.data[:3]:
                print(f"  {row['similarity']:.3f}  {row['name']}")

    # sync fallback for non-async callers
    def invoke(self, query: str, **kwargs: Any) -> Sequence[Document]:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.ainvoke(query))
