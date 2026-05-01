from __future__ import annotations

import asyncio
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.agents.main_assistant import AgentState, run_main_assistant


# ─── Mock LLM helpers ─────────────────────────────────────────────────────────

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
    """Mock LLM that returns a predefined sequence of responses."""
    def __init__(self, responses: list) -> None:
        self._responses = list(responses)
        self._idx = 0

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages) -> Any:
        if self._idx >= len(self._responses):
            from langchain_core.messages import AIMessage
            return AIMessage(content="Done.")
        resp = self._responses[self._idx]
        self._idx += 1
        return resp


class _ToolThenStreamLLM(_SequenceLLM):
    def __init__(self, responses: list, stream_text: str) -> None:
        super().__init__(responses)
        self._stream_text = stream_text

    async def astream(self, messages, **kwargs):
        chunk = MagicMock()
        chunk.content = self._stream_text
        yield chunk


# ─── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_plain_text_response_sets_tts_text():
    llm = _SequenceLLM([_make_text_msg("Looks perfect, let's go!")])
    result = await run_main_assistant("how am I doing?", "Step 3", {}, llm)  # type: ignore[arg-type]

    assert result["tts_text"] == "Looks perfect, let's go!"
    assert result["canvas_ops"] == []


@pytest.mark.asyncio
async def test_render_canvas_tool_call_populates_ops():
    fake_ops = [{"op": "add", "id": "s1", "type": "step-view", "data": {
        "step_number": 1, "total_steps": 3, "recipe": "Test", "instruction": "Boil water"
    }}]

    render_result = {"ops": fake_ops, "errors": []}

    llm = _SequenceLLM([
        _make_tool_call_msg("render_canvas", {"intent": "show step 1"}),
        _make_text_msg("Step one, here we go!"),
    ])

    with patch("packages.agents.main_assistant.graph.MainAssistantGraph._run_render_agent", new=AsyncMock(return_value=render_result)):
        result = await run_main_assistant("next step", "Recipe: Pasta", {}, llm)  # type: ignore[arg-type]

    assert result["canvas_ops"] == fake_ops
    assert result["tts_text"] == "Step one, here we go!"


@pytest.mark.asyncio
async def test_graceful_degradation_when_render_fails():
    llm = _SequenceLLM([
        _make_tool_call_msg("render_canvas", {"intent": "show step"}),
        _make_text_msg("Oops, let me try again."),
    ])

    async def _fail(*args, **kwargs):
        raise RuntimeError("LLM timeout")

    with patch("packages.agents.main_assistant.graph.MainAssistantGraph._run_render_agent", new=_fail):
        result = await run_main_assistant("next step", "", {}, llm)  # type: ignore[arg-type]

    assert result["canvas_ops"] == []
    assert result["tts_text"] == "Oops, let me try again."


@pytest.mark.asyncio
async def test_fallback_tts_when_all_messages_fail():
    llm = _SequenceLLM([
        _make_tool_call_msg("render_canvas", {"intent": "show step"}),
        _make_text_msg(""),  # empty content — should trigger fallback
    ])

    async def _fail(*args, **kwargs):
        raise RuntimeError("error")

    with patch("packages.agents.main_assistant.graph.MainAssistantGraph._run_render_agent", new=_fail):
        result = await run_main_assistant("next step", "", {}, llm)  # type: ignore[arg-type]

    assert "try" in result["tts_text"].lower() or result["tts_text"] != ""


@pytest.mark.asyncio
async def test_find_recipes_stub_returns_empty():
    llm = _SequenceLLM([
        _make_tool_call_msg("find_recipes", {"query": "pasta"}),
        _make_text_msg("Here are some pasta recipes!"),
    ])
    result = await run_main_assistant("show me pasta recipes", "", {}, llm)  # type: ignore[arg-type]

    assert result["canvas_ops"] == []
    assert result["tts_text"] == "Here are some pasta recipes!"


@pytest.mark.asyncio
async def test_completes_within_latency_budget():
    """Tool calls with mocks should finish well under 4 seconds."""
    llm = _SequenceLLM([_make_text_msg("Done!")])
    result = await asyncio.wait_for(
        run_main_assistant("hello", "", {}, llm),  # type: ignore[arg-type]
        timeout=4.0,
    )
    assert result["tts_text"] == "Done!"


@pytest.mark.asyncio
async def test_canvas_state_passed_to_render_agent():
    canvas = {"active": {"s1": {"type": "step-view", "data": {}}}, "staged": {}}
    captured: list = []

    async def _capture(self, intent: str, state: AgentState):
        captured.append(state["canvas_state"])
        return {"ops": [], "errors": []}

    llm = _SequenceLLM([
        _make_tool_call_msg("render_canvas", {"intent": "update step"}),
        _make_text_msg("Updated!"),
    ])

    with patch("packages.agents.main_assistant.graph.MainAssistantGraph._run_render_agent", new=_capture):
        await run_main_assistant("update", "context", canvas, llm)  # type: ignore[arg-type]

    assert captured[0] == canvas


@pytest.mark.asyncio
async def test_render_canvas_repairs_orphaned_recipe_options():
    llm = _ToolThenStreamLLM(
        [
            _make_tool_call_msg("render_canvas", {"intent": "show recipe suggestions"}),
            _make_text_msg("Pick one and let's get cooking."),
        ],
        (
            '{"op":"add","id":"veg-opt-1","type":"recipe-option","parent":"veg-grid","data":{"title":"Classic Vegetable Fried Rice","action":"select_veg_opt_1"}}\n'
            '{"op":"add","id":"veg-opt-2","type":"recipe-option","parent":"veg-grid","data":{"title":"Rainbow Veggie Bowl","action":"select_veg_opt_2"}}\n'
        ),
    )

    result = await run_main_assistant("show recipes", "", {}, llm)  # type: ignore[arg-type]

    assert result["canvas_ops"][0] == {"op": "add", "id": "veg-grid", "type": "recipe-grid", "data": {}}
    assert [op["id"] for op in result["canvas_ops"][1:]] == ["veg-opt-1", "veg-opt-2"]
    assert result["tts_text"] == "Pick one and let's get cooking."
