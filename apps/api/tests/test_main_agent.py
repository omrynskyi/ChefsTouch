from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from packages.agents.main_assistant import stream_main_assistant


def _make_tool_call_msg(tool_name: str, args: dict, call_id: str = "tc1"):
    from langchain_core.messages import AIMessage
    return AIMessage(
        content="",
        tool_calls=[{"name": tool_name, "args": args, "id": call_id, "type": "tool_call"}],
    )


def _make_text_msg(text: str):
    from langchain_core.messages import AIMessage
    return AIMessage(content=text)


class _SequenceLLM:
    def __init__(self, responses: list, stream_text: str = "") -> None:
        self._responses = list(responses)
        self._idx = 0
        self._stream_text = stream_text

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages) -> Any:
        if self._idx >= len(self._responses):
            from langchain_core.messages import AIMessage
            return AIMessage(content="")
        resp = self._responses[self._idx]
        self._idx += 1
        return resp

    async def astream(self, messages, **kwargs):
        chunk = MagicMock()
        chunk.content = self._stream_text
        yield chunk


@pytest.mark.asyncio
async def test_initial_reply_emits_before_streamed_canvas_ops():
    llm = _SequenceLLM(
        [
            _make_text_msg("On it."),
            _make_tool_call_msg("render_canvas", {"intent": "show step 1"}),
            _make_text_msg("Step one, here we go!"),
        ],
        (
            '{"op":"add","id":"step-1","type":"step-view","data":{"step_number":1,"total_steps":3,"recipe":"Test","instruction":"Boil water"}}\n'
        ),
    )

    events = [e async for e in stream_main_assistant("next step", "Recipe: Pasta", {}, llm)]  # type: ignore[arg-type]

    assistant_events = [e for e in events if e["type"] == "assistant_message"]
    canvas_events = [e for e in events if e["type"] == "canvas_op"]

    assert assistant_events[0]["text"] == "On it."
    assert canvas_events[0]["op"]["id"] == "step-1"
    assert events.index(assistant_events[0]) < events.index(canvas_events[0])
    assert assistant_events[-1]["text"] == "Step one, here we go!"


@pytest.mark.asyncio
async def test_empty_initial_reply_uses_default_message():
    llm = _SequenceLLM([
        _make_text_msg(""),
        _make_text_msg(""),
    ])

    events = [e async for e in stream_main_assistant("how am I doing?", "Step 3", {}, llm)]  # type: ignore[arg-type]

    first_reply = next(e for e in events if e["type"] == "assistant_message")
    assert first_reply["text"] == "One sec, I'm on it."


@pytest.mark.asyncio
async def test_render_canvas_streams_repaired_recipe_grid_before_options():
    llm = _SequenceLLM(
        [
            _make_text_msg("Let's pick something good."),
            _make_tool_call_msg("render_canvas", {"intent": "show recipe suggestions"}),
            _make_text_msg(""),
        ],
        (
            '{"op":"add","id":"veg-opt-1","type":"recipe-option","parent":"veg-grid","data":{"title":"Classic Vegetable Fried Rice","action":"select_veg_opt_1"}}\n'
            '{"op":"add","id":"veg-opt-2","type":"recipe-option","parent":"veg-grid","data":{"title":"Rainbow Veggie Bowl","action":"select_veg_opt_2"}}\n'
        ),
    )

    events = [e async for e in stream_main_assistant("show recipes", "", {}, llm)]  # type: ignore[arg-type]
    canvas_ids = [e["op"]["id"] for e in events if e["type"] == "canvas_op" and e["op"]["op"] != "skeleton"]

    assert canvas_ids == ["veg-grid", "veg-opt-1", "veg-opt-2"]


@pytest.mark.asyncio
async def test_find_recipes_can_emit_material_follow_up():
    llm = _SequenceLLM([
        _make_text_msg("On it."),
        _make_tool_call_msg("find_recipes", {"query": "pasta"}),
        _make_text_msg("Here are some pasta ideas."),
    ])

    events = [e async for e in stream_main_assistant("show me pasta recipes", "", {}, llm)]  # type: ignore[arg-type]
    assistant_texts = [e["text"] for e in events if e["type"] == "assistant_message"]

    assert assistant_texts == ["On it.", "Here are some pasta ideas."]


@pytest.mark.asyncio
async def test_render_failures_emit_fallback_follow_up():
    llm = _SequenceLLM([
        _make_text_msg("On it."),
        _make_tool_call_msg("render_canvas", {"intent": "show step"}),
        _make_text_msg(""),
    ])

    async def _fail(*args, **kwargs):
        raise RuntimeError("LLM timeout")
        yield  # pragma: no cover

    with patch("packages.agents.main_assistant.graph.astream_canvas_ops", _fail):
        events = [e async for e in stream_main_assistant("next step", "", {}, llm)]  # type: ignore[arg-type]

    assistant_texts = [e["text"] for e in events if e["type"] == "assistant_message"]
    assert assistant_texts[-1] == "Hmm, something went sideways. Let me try that another way."


@pytest.mark.asyncio
async def test_completes_within_latency_budget():
    llm = _SequenceLLM([
        _make_text_msg("Done!"),
        _make_text_msg(""),
    ])

    events = await asyncio.wait_for(
        asyncio.create_task(_collect_events("hello", "", {}, llm)),
        timeout=4.0,
    )

    assert any(event["type"] == "turn_complete" for event in events)


async def _collect_events(intent: str, context: str, canvas_state: dict, llm: Any):
    return [e async for e in stream_main_assistant(intent, context, canvas_state, llm)]  # type: ignore[arg-type]
