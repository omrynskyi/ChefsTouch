from __future__ import annotations

import asyncio
from typing import Any, List, Optional

from langchain_core.embeddings import Embeddings

from .schemas import CSSEntry
from .snippets.default import DEFAULT_CSS_ENTRIES


async def seed_design_snippets(
    client: Any,
    embeddings: Embeddings,
    entries: Optional[List[CSSEntry]] = None,
    clear: bool = False,
) -> int:
    """
    Embed CSS entries and upsert them into the design_snippets table.

    Args:
        client:     Supabase client (supabase.create_client(...))
        embeddings: LangChain Embeddings (e.g. OpenAIEmbeddings())
        entries:    CSS entries to seed. Defaults to DEFAULT_CSS_ENTRIES.
        clear:      If True, delete all existing rows before inserting.

    Returns:
        Number of rows upserted.

    Usage:
        from supabase import create_client
        from langchain_openai import OpenAIEmbeddings
        from agent_canvas.seeder import seed_design_snippets
        from agent_canvas import DEFAULT_CSS_ENTRIES

        await seed_design_snippets(
            client=create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY),
            embeddings=OpenAIEmbeddings(),
            entries=DEFAULT_CSS_ENTRIES,   # or your own app-specific entries
        )
    """
    if entries is None:
        entries = DEFAULT_CSS_ENTRIES

    if clear:
        client.table("design_snippets").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    contents = [entry.to_document().page_content for entry in entries]
    vectors = await embeddings.aembed_documents(contents)

    rows = [
        {
            "name": entry.name,
            "description": entry.description,
            "tags": entry.tags,
            "example": entry.example,
            "content": contents[i],
            "embedding": vectors[i],
        }
        for i, entry in enumerate(entries)
    ]

    # upsert on name — safe to re-run; updates embeddings if content changes
    client.table("design_snippets").upsert(rows, on_conflict="name").execute()
    return len(rows)


def seed_sync(
    client: Any,
    embeddings: Embeddings,
    entries: Optional[List[CSSEntry]] = None,
    clear: bool = False,
) -> int:
    """Synchronous wrapper around seed_design_snippets for use in scripts."""
    return asyncio.run(seed_design_snippets(client, embeddings, entries, clear))
