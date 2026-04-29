from __future__ import annotations

import json
from typing import Any, List, Sequence
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage

from render_agent import build_canvas_render_graph
from render_agent.sanitizer import sanitize_html
from render_agent.schemas import CanvasOp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_llm(response: str) -> Any:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content=response))
    return llm


def make_retriever(docs: List[Document]) -> Any:
    retriever = MagicMock()
    retriever.ainvoke = AsyncMock(return_value=docs)
    return retriever


STEP_SNIPPET = Document(
    page_content='card elevated: Card with drop shadow. Use for primary focus components. | tags: card, shadow, primary',
    metadata={"name": "card elevated"},
)

TIMER_SNIPPET = Document(
    page_content='data-component="timer": Initializes a countdown timer. Required: data-duration, data-autostart, data-label. | tags: timer, countdown, component | example: <div class="card compact glass" data-component="timer" data-duration="6m" data-autostart="true" data-label="Chicken">',
    metadata={"name": 'data-component="timer"'},
)


# ---------------------------------------------------------------------------
# Graph integration tests
# ---------------------------------------------------------------------------

async def test_graph_returns_add_ops():
    llm_response = json.dumps([
        {
            "op": "add",
            "id": "step-1",
            "html": '<div zone="center" size="large" layer="base" class="card elevated animate-in"><p class="text-primary size-lg">Boil water</p></div>',
        }
    ])
    graph = build_canvas_render_graph(make_llm(llm_response), make_retriever([STEP_SNIPPET]))
    result = await graph.ainvoke({"intent": "show step 1", "canvas_state": {}, "context": "Pasta"})

    assert len(result["ops"]) == 1
    assert result["ops"][0]["op"] == "add"
    assert result["ops"][0]["id"] == "step-1"
    assert result["errors"] == []


async def test_graph_returns_multiple_ops():
    llm_response = json.dumps([
        {
            "op": "add",
            "id": "step-3",
            "html": '<div zone="center" size="large" layer="base" class="card elevated"><p class="text-primary size-lg">Sear chicken</p></div>',
        },
        {
            "op": "add",
            "id": "timer-1",
            "html": '<div zone="corner-br" size="small" layer="float" class="card compact glass" data-component="timer" data-duration="6m" data-autostart="true" data-label="Chicken"></div>',
        },
        {"op": "remove", "id": "step-2"},
    ])
    graph = build_canvas_render_graph(make_llm(llm_response), make_retriever([STEP_SNIPPET, TIMER_SNIPPET]))
    result = await graph.ainvoke({"intent": "next step with timer", "canvas_state": {}, "context": "step 3"})

    assert len(result["ops"]) == 3
    ops_by_id = {op["id"]: op for op in result["ops"]}
    assert ops_by_id["step-3"]["op"] == "add"
    assert ops_by_id["timer-1"]["op"] == "add"
    assert ops_by_id["step-2"]["op"] == "remove"


async def test_graph_strips_markdown_fences():
    llm_response = '```json\n[{"op": "remove", "id": "step-1"}]\n```'
    graph = build_canvas_render_graph(make_llm(llm_response), make_retriever([]))
    result = await graph.ainvoke({"intent": "remove step", "canvas_state": {}, "context": ""})

    assert len(result["ops"]) == 1
    assert result["ops"][0]["op"] == "remove"


async def test_graph_drops_invalid_ops_and_records_errors():
    llm_response = json.dumps([
        {"op": "add", "id": "ok-1", "html": '<div zone="center" size="large" layer="base" class="card">ok</div>'},
        {"op": "add", "id": "bad-1"},          # missing html
        {"op": "move", "id": "bad-2"},          # missing zone
        {"op": "focus", "id": "ok-2"},
    ])
    graph = build_canvas_render_graph(make_llm(llm_response), make_retriever([]))
    result = await graph.ainvoke({"intent": "test", "canvas_state": {}, "context": ""})

    valid_ids = [op["id"] for op in result["ops"]]
    assert "ok-1" in valid_ids
    assert "ok-2" in valid_ids
    assert "bad-1" not in valid_ids
    assert "bad-2" not in valid_ids
    assert len(result["errors"]) == 2


async def test_graph_handles_malformed_json():
    graph = build_canvas_render_graph(make_llm("not json at all"), make_retriever([]))
    result = await graph.ainvoke({"intent": "test", "canvas_state": {}, "context": ""})

    assert result["ops"] == []
    assert len(result["errors"]) == 1
    assert "JSON parse failed" in result["errors"][0]


async def test_graph_handles_non_array_json():
    graph = build_canvas_render_graph(make_llm('{"op": "add"}'), make_retriever([]))
    result = await graph.ainvoke({"intent": "test", "canvas_state": {}, "context": ""})

    assert result["ops"] == []
    assert "not a JSON array" in result["errors"][0]


# ---------------------------------------------------------------------------
# Sanitizer unit tests
# ---------------------------------------------------------------------------

def test_sanitizer_strips_script_tags():
    html = '<div class="card"><script>alert(1)</script>content</div>'
    result = sanitize_html(html)
    assert "<script>" not in result
    assert "content" in result


def test_sanitizer_strips_disallowed_attributes():
    html = '<div class="card" onclick="evil()" style="color:red">text</div>'
    result = sanitize_html(html)
    assert "onclick" not in result
    assert "style=" not in result
    assert 'class="card"' in result


def test_sanitizer_allows_data_component_attributes():
    html = '<div class="card" data-component="timer" data-duration="6m" data-autostart="true"></div>'
    result = sanitize_html(html)
    assert 'data-component="timer"' in result
    assert 'data-duration="6m"' in result


def test_sanitizer_preserves_zone_size_layer():
    html = '<div zone="center" size="large" layer="base" class="card">content</div>'
    result = sanitize_html(html)
    assert 'zone="center"' in result
    assert 'size="large"' in result
    assert 'layer="base"' in result


def test_sanitizer_strips_external_src():
    html = '<img src="https://evil.com/track.png">'
    result = sanitize_html(html)
    assert "evil.com" not in result


# ---------------------------------------------------------------------------
# Schema unit tests
# ---------------------------------------------------------------------------

def test_canvas_op_add_requires_html():
    with pytest.raises(Exception):
        CanvasOp(op="add", id="x")


def test_canvas_op_move_requires_zone():
    with pytest.raises(Exception):
        CanvasOp(op="move", id="x")


def test_canvas_op_move_rejects_invalid_zone():
    with pytest.raises(Exception):
        CanvasOp(op="move", id="x", zone="floating-nowhere")


def test_canvas_op_remove_needs_only_id():
    op = CanvasOp(op="remove", id="step-1")
    assert op.html is None
    assert op.zone is None


def test_canvas_op_focus_needs_only_id():
    op = CanvasOp(op="focus", id="step-1")
    assert op.html is None
