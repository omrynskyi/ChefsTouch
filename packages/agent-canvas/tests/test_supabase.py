from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_canvas.retrievers.supabase import SupabaseCSSRetriever
from agent_canvas.seeder import seed_design_snippets
from agent_canvas.schemas import CSSEntry


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_embeddings(vector: list = None) -> MagicMock:
    emb = MagicMock()
    emb.aembed_query = AsyncMock(return_value=vector or [0.1] * 1536)
    emb.aembed_documents = AsyncMock(side_effect=lambda texts: [[0.1] * 1536] * len(texts))
    return emb


def make_supabase_client(rpc_rows: list = None) -> MagicMock:
    client = MagicMock()
    rpc_result = MagicMock()
    rpc_result.data = rpc_rows or []
    client.rpc.return_value.execute.return_value = rpc_result
    return client


# ── Retriever tests ───────────────────────────────────────────────────────────

async def test_retriever_returns_documents():
    rows = [
        {"name": "card elevated", "content": "card elevated: Card with drop shadow.", "similarity": 0.92},
        {"name": "animate-in",    "content": "animate-in: Fade and slide in on mount.", "similarity": 0.85},
    ]
    retriever = SupabaseCSSRetriever(
        client=make_supabase_client(rows),
        embeddings=make_embeddings(),
    )
    docs = await retriever.ainvoke("primary card with shadow")

    assert len(docs) == 2
    assert docs[0].metadata["name"] == "card elevated"
    assert docs[1].metadata["name"] == "animate-in"


async def test_retriever_filters_by_threshold():
    rows = [
        {"name": "card",       "content": "card: base container.", "similarity": 0.80},
        {"name": "font-mono",  "content": "font-mono: monospace.", "similarity": 0.15},  # below threshold
    ]
    retriever = SupabaseCSSRetriever(
        client=make_supabase_client(rows),
        embeddings=make_embeddings(),
        match_threshold=0.3,
    )
    docs = await retriever.ainvoke("card layout")

    assert len(docs) == 1
    assert docs[0].metadata["name"] == "card"


async def test_retriever_calls_rpc_with_correct_args():
    client = make_supabase_client([])
    embeddings = make_embeddings([0.5] * 1536)
    retriever = SupabaseCSSRetriever(client=client, embeddings=embeddings, k=7)

    await retriever.ainvoke("timer countdown")

    client.rpc.assert_called_once_with(
        "match_design_snippets",
        {"query_embedding": [0.5] * 1536, "match_count": 7},
    )


async def test_retriever_returns_empty_on_no_results():
    retriever = SupabaseCSSRetriever(
        client=make_supabase_client([]),
        embeddings=make_embeddings(),
    )
    docs = await retriever.ainvoke("something obscure")
    assert docs == []


# ── Seeder tests ──────────────────────────────────────────────────────────────

async def test_seeder_upserts_all_entries():
    client = make_supabase_client()
    client.table.return_value.upsert.return_value.execute.return_value = MagicMock()

    entries = [
        CSSEntry(name="card", description="Base card", tags=["card"]),
        CSSEntry(name="card elevated", description="Card with shadow", tags=["card", "shadow"]),
    ]
    count = await seed_design_snippets(client, make_embeddings(), entries)

    assert count == 2
    client.table.assert_called_with("design_snippets")
    upsert_call = client.table.return_value.upsert.call_args
    rows = upsert_call[0][0]
    assert len(rows) == 2
    assert rows[0]["name"] == "card"
    assert rows[1]["name"] == "card elevated"
    assert len(rows[0]["embedding"]) == 1536


async def test_seeder_clears_before_insert_when_requested():
    client = make_supabase_client()
    delete_chain = MagicMock()
    client.table.return_value.delete.return_value.neq.return_value.execute = MagicMock()
    client.table.return_value.upsert.return_value.execute.return_value = MagicMock()

    entries = [CSSEntry(name="card", description="Base card", tags=[])]
    await seed_design_snippets(client, make_embeddings(), entries, clear=True)

    client.table.return_value.delete.assert_called_once()


async def test_seeder_defaults_to_builtin_entries():
    from agent_canvas.snippets.default import DEFAULT_CSS_ENTRIES

    client = make_supabase_client()
    client.table.return_value.upsert.return_value.execute.return_value = MagicMock()

    count = await seed_design_snippets(client, make_embeddings())

    assert count == len(DEFAULT_CSS_ENTRIES)


async def test_seeder_content_matches_css_entry_document():
    client = make_supabase_client()
    client.table.return_value.upsert.return_value.execute.return_value = MagicMock()

    entry = CSSEntry(
        name="timer-display",
        description="Large countdown number display",
        tags=["timer", "number"],
        example='<span class="timer-display font-mono">6:00</span>',
    )
    await seed_design_snippets(client, make_embeddings(), [entry])

    upsert_rows = client.table.return_value.upsert.call_args[0][0]
    assert upsert_rows[0]["content"] == entry.to_document().page_content
