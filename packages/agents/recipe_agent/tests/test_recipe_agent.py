from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.agents.recipe_agent import find_recipes
from packages.agents.recipe_agent.agent import RecipeAgent


# --------------------------------------------------------------------------- #
# Helpers                                                                       #
# --------------------------------------------------------------------------- #

def make_embed(vector=None):
    """Mock embed_model whose aembed_query returns *vector* (default 768-dim)."""
    m = MagicMock()
    m.aembed_query = AsyncMock(return_value=vector or [0.1] * 768)
    return m


def make_client(rows=None):
    """Mock Supabase client whose match_recipes RPC returns *rows*."""
    client = MagicMock()
    result = MagicMock()
    result.data = rows if rows is not None else []
    client.rpc.return_value.execute.return_value = result
    return client


def make_llm(content=""):
    """Mock LLM whose ainvoke returns a message with *content*."""
    m = MagicMock()
    response = MagicMock()
    response.content = content
    m.ainvoke = AsyncMock(return_value=response)
    return m


# --------------------------------------------------------------------------- #
# Phase 1 tests                                                                 #
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_phase1_hit_returns_vector_search_source():
    rows = [{"title": "Pasta", "description": "Simple pasta", "similarity": 0.85}]
    agent = RecipeAgent(client=make_client(rows), embed_model=make_embed())

    result = await agent.find("pasta dish")

    assert result["source"] == "vector_search"
    assert result["recipes"] == rows
    assert result["query"] == "pasta dish"


@pytest.mark.asyncio
async def test_phase1_hit_calls_rpc_with_correct_args():
    rows = [{"title": "Pasta"}]
    client = make_client(rows)
    embed = make_embed()

    await RecipeAgent(client=client, embed_model=embed).find("pasta")

    client.rpc.assert_called_once_with(
        "match_recipes",
        {
            "query_embedding": [0.1] * 768,
            "match_threshold": 0.72,
            "match_count": 5,
        },
    )


@pytest.mark.asyncio
async def test_phase1_miss_falls_through_to_phase2():
    """Empty RPC result should fall through to LLM generation."""
    recipe_json = json.dumps({
        "title": "Shakshuka",
        "description": "Eggs in tomato sauce",
        "duration_minutes": 25,
        "servings": 2,
        "tags": ["middle-eastern"],
        "steps": [{"step_number": 1, "instruction": "Cook eggs."}],
    })
    agent = RecipeAgent(
        client=make_client([]),          # empty — Phase 1 miss
        embed_model=make_embed(),
    )

    result = await agent.find("shakshuka", llm=make_llm(recipe_json))

    assert result["source"] == "generated"
    assert result["recipes"][0]["title"] == "Shakshuka"


# --------------------------------------------------------------------------- #
# Phase 2 tests                                                                 #
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_phase2_valid_json_no_client():
    recipe_json = json.dumps({
        "title": "Shakshuka",
        "description": "Eggs poached in spiced tomato sauce.",
        "duration_minutes": 25,
        "servings": 2,
        "tags": ["vegetarian", "middle-eastern"],
        "steps": [{"step_number": 1, "instruction": "Heat oil in a skillet."}],
    })

    result = await find_recipes("shakshuka", llm=make_llm(recipe_json))

    assert result["source"] == "generated"
    assert result["recipes"][0]["title"] == "Shakshuka"


@pytest.mark.asyncio
async def test_phase2_markdown_fenced_json_is_parsed():
    recipe = {
        "title": "Tacos",
        "description": "Street-style tacos.",
        "duration_minutes": 20,
        "servings": 4,
        "tags": ["mexican"],
        "steps": [{"step_number": 1, "instruction": "Season meat."}],
    }
    fenced = f"```json\n{json.dumps(recipe)}\n```"

    result = await find_recipes("tacos", llm=make_llm(fenced))

    assert result["source"] == "generated"
    assert result["recipes"][0]["title"] == "Tacos"


@pytest.mark.asyncio
async def test_phase2_bad_json_returns_empty_recipes_no_exception():
    result = await find_recipes("something weird", llm=make_llm("this is not json at all"))

    assert result["source"] == "generated"
    assert result["recipes"] == []


# --------------------------------------------------------------------------- #
# Stub / guard tests                                                            #
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_stub_mode_no_dependencies():
    result = await find_recipes("chicken soup")

    assert result["source"] == "stub"
    assert result["recipes"] == []


@pytest.mark.asyncio
async def test_phase1_requires_both_client_and_embed_model__only_embed():
    """If only embed_model is supplied (no client), Phase 1 must be skipped."""
    embed = make_embed()
    result = await find_recipes("pasta", embed_model=embed)

    # embed.aembed_query should NOT have been called
    embed.aembed_query.assert_not_called()
    assert result["source"] == "stub"


@pytest.mark.asyncio
async def test_phase1_requires_both_client_and_embed_model__only_client():
    """If only client is supplied (no embed_model), Phase 1 must be skipped."""
    client = make_client([{"title": "Pasta"}])
    result = await find_recipes("pasta", client=client)

    # client.rpc should NOT have been called
    client.rpc.assert_not_called()
    assert result["source"] == "stub"


@pytest.mark.asyncio
async def test_session_context_is_passed_through():
    ctx = {"current_step": 3, "active_recipe": "Ramen"}
    result = await find_recipes("noodles", session_context=ctx)

    assert result["session_context"] == ctx
