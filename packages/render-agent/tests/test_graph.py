from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from render_agent import (
    ContentEvent,
    JSONStreamHealer,
    SkeletonEvent,
    astream_events,
    build_canvas_render_graph,
)
from render_agent.schemas import CanvasOp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_llm(response: str) -> Any:
    """LLM mock that yields response as a single chunk via astream()."""
    llm = MagicMock()

    async def _astream(messages, **kwargs):
        chunk = MagicMock()
        chunk.content = response
        yield chunk

    llm.astream = _astream
    return llm


def make_chunked_llm(chunks: list) -> Any:
    """LLM mock that yields multiple chunks in order."""
    llm = MagicMock()

    async def _astream(messages, **kwargs):
        for text in chunks:
            chunk = MagicMock()
            chunk.content = text
            yield chunk

    llm.astream = _astream
    return llm


# ---------------------------------------------------------------------------
# JSONStreamHealer unit tests
# ---------------------------------------------------------------------------

class TestJSONStreamHealer:
    def test_complete_object_emits_content_event(self):
        healer = JSONStreamHealer()
        obj = '{"op":"remove","id":"x"}'
        events = healer.feed(obj)
        assert len(events) == 1
        assert isinstance(events[0], ContentEvent)
        assert events[0].op == {"op": "remove", "id": "x"}

    def test_skeleton_fires_before_object_closes(self):
        healer = JSONStreamHealer()
        partial = '{"op":"add","id":"step-1","type":"step-view","data":{"step_number":1'
        events = healer.feed(partial)
        skeleton_events = [e for e in events if isinstance(e, SkeletonEvent)]
        assert len(skeleton_events) == 1
        assert skeleton_events[0].id == "step-1"
        assert skeleton_events[0].component_type == "step-view"

    def test_skeleton_emitted_only_once_per_id(self):
        healer = JSONStreamHealer()
        # Feed in chunks — skeleton should fire exactly once
        full = '{"op":"add","id":"step-1","type":"step-view","data":{"step_number":1,"total_steps":3,"recipe":"Test","instruction":"Boil water"}}'
        events = []
        for char in full:
            events.extend(healer.feed(char))
        skeleton_events = [e for e in events if isinstance(e, SkeletonEvent)]
        assert len(skeleton_events) == 1

    def test_multiple_objects_in_stream(self):
        healer = JSONStreamHealer()
        stream = '{"op":"remove","id":"a"}\n{"op":"remove","id":"b"}\n'
        events = healer.feed(stream)
        content_events = [e for e in events if isinstance(e, ContentEvent)]
        assert len(content_events) == 2
        ids = [e.op["id"] for e in content_events]
        assert ids == ["a", "b"]

    def test_finalize_parses_remaining_buffer(self):
        healer = JSONStreamHealer()
        # Partial object without trailing newline
        healer.feed('{"op":"remove","id":"x"}')
        # Simulate that content was already emitted by feed
        # Let's test finalize with a partial
        healer2 = JSONStreamHealer()
        healer2.line_buffer = '{"op":"remove","id":"y"}'
        healer2.depth = 0
        events = healer2.finalize()
        assert len(events) == 1
        assert isinstance(events[0], ContentEvent)

    def test_malformed_json_produces_no_content_event(self):
        healer = JSONStreamHealer()
        events = healer.feed('{"op":"add","id":broken}')
        content_events = [e for e in events if isinstance(e, ContentEvent)]
        assert len(content_events) == 0

    def test_nested_objects_emit_correctly(self):
        healer = JSONStreamHealer()
        obj = '{"op":"add","id":"il-1","type":"ingredient-list","data":{"items":[{"name":"pasta","qty":"200g"}]}}'
        events = healer.feed(obj)
        content_events = [e for e in events if isinstance(e, ContentEvent)]
        assert len(content_events) == 1
        assert content_events[0].op["id"] == "il-1"


# ---------------------------------------------------------------------------
# CanvasOp schema unit tests
# ---------------------------------------------------------------------------

class TestCanvasOpSchema:
    def test_add_requires_type(self):
        with pytest.raises(Exception):
            CanvasOp(op="add", id="x", data={"body": "hi"})

    def test_add_requires_data(self):
        with pytest.raises(Exception):
            CanvasOp(op="add", id="x", type="text-card")

    def test_add_rejects_unknown_type(self):
        with pytest.raises(Exception):
            CanvasOp(op="add", id="x", type="recipe-card", data={"title": "Pasta"})

    def test_add_validates_required_data_keys(self):
        with pytest.raises(Exception):
            # step-view requires step_number, total_steps, recipe, instruction
            CanvasOp(op="add", id="x", type="step-view", data={"instruction": "Boil water"})

    def test_add_valid_step_view(self):
        op = CanvasOp(
            op="add", id="s1", type="step-view",
            data={"step_number": 1, "total_steps": 6, "recipe": "Pasta", "instruction": "Boil water"},
        )
        assert op.type == "step-view"

    def test_add_valid_recipe_grid_empty_data(self):
        op = CanvasOp(op="add", id="rg", type="recipe-grid", data={})
        assert op.type == "recipe-grid"

    def test_move_requires_position(self):
        with pytest.raises(Exception):
            CanvasOp(op="move", id="x")

    def test_move_rejects_invalid_position(self):
        with pytest.raises(Exception):
            CanvasOp(op="move", id="x", position="bottom-right")

    def test_move_accepts_valid_position(self):
        op = CanvasOp(op="move", id="x", position="corner-br")
        assert op.position == "corner-br"

    def test_remove_needs_only_id(self):
        op = CanvasOp(op="remove", id="step-1")
        assert op.type is None
        assert op.data is None

    def test_update_needs_only_id_and_data(self):
        op = CanvasOp(op="update", id="step-1", data={"instruction": "Updated"})
        assert op.op == "update"


# ---------------------------------------------------------------------------
# astream_events integration tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_astream_events_yields_content_events():
    stream = (
        '{"op":"add","id":"step-1","type":"step-view",'
        '"data":{"step_number":1,"total_steps":6,"recipe":"Pasta","instruction":"Boil water"}}\n'
        '{"op":"add","id":"pb-1","type":"progress-bar","data":{"current":1,"total":6}}\n'
    )
    llm = make_llm(stream)
    events = [e async for e in astream_events("show step 1", "Pasta", {}, llm)]
    content = [e for e in events if isinstance(e, ContentEvent)]
    assert len(content) == 2
    assert content[0].op["id"] == "step-1"
    assert content[1].op["id"] == "pb-1"


@pytest.mark.asyncio
async def test_astream_events_yields_skeleton_before_content():
    stream = (
        '{"op":"add","id":"step-1","type":"step-view",'
        '"data":{"step_number":1,"total_steps":3,"recipe":"Test","instruction":"Boil water"}}\n'
    )
    # Feed char by char so skeleton fires mid-stream
    chars = list(stream)
    llm = make_chunked_llm(chars)
    events = [e async for e in astream_events("show step", "Test", {}, llm)]
    skeleton_idx = next(i for i, e in enumerate(events) if isinstance(e, SkeletonEvent))
    content_idx = next(i for i, e in enumerate(events) if isinstance(e, ContentEvent))
    assert skeleton_idx < content_idx


@pytest.mark.asyncio
async def test_astream_events_drops_invalid_ops():
    stream = (
        '{"op":"add","id":"ok-1","type":"text-card","data":{"body":"Hello"}}\n'
        '{"op":"add","id":"bad-1","type":"unknown-type","data":{"foo":"bar"}}\n'
        '{"op":"add","id":"bad-2"}\n'  # missing type
    )
    llm = make_llm(stream)
    events = [e async for e in astream_events("test", "", {}, llm)]
    content = [e for e in events if isinstance(e, ContentEvent)]
    ids = [e.op["id"] for e in content]
    assert "ok-1" in ids
    assert "bad-1" not in ids
    assert "bad-2" not in ids


@pytest.mark.asyncio
async def test_astream_events_update_and_remove():
    stream = (
        '{"op":"update","id":"step-1","data":{"instruction":"Updated"}}\n'
        '{"op":"remove","id":"timer-1"}\n'
    )
    llm = make_llm(stream)
    events = [e async for e in astream_events("advance step", "", {}, llm)]
    content = [e for e in events if isinstance(e, ContentEvent)]
    assert content[0].op == {"op": "update", "id": "step-1", "data": {"instruction": "Updated"}}
    assert content[1].op == {"op": "remove", "id": "timer-1"}


# ---------------------------------------------------------------------------
# build_canvas_render_graph (batch wrapper)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_graph_ainvoke_returns_ops():
    stream = (
        '{"op":"add","id":"step-1","type":"step-view",'
        '"data":{"step_number":1,"total_steps":3,"recipe":"Test","instruction":"Boil water"}}\n'
    )
    graph = build_canvas_render_graph(make_llm(stream))
    result = await graph.ainvoke({"intent": "show step 1", "canvas_state": {}, "context": "Test"})
    assert len(result["ops"]) == 1
    assert result["ops"][0]["op"] == "add"
    assert result["ops"][0]["id"] == "step-1"


@pytest.mark.asyncio
async def test_graph_ainvoke_with_canvas_state():
    existing = {
        "step-1": {"type": "step-view", "data": {"step_number": 1, "total_steps": 3, "recipe": "Test", "instruction": "Boil water"}},
    }
    stream = '{"op":"update","id":"step-1","data":{"step_number":2,"instruction":"Add pasta"}}\n'
    graph = build_canvas_render_graph(make_llm(stream))
    result = await graph.ainvoke({"intent": "next step", "canvas_state": existing, "context": ""})
    assert result["ops"][0]["op"] == "update"
