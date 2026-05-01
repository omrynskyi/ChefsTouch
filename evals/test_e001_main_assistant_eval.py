from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from langsmith.run_helpers import tracing_context

from evals.common import load_json_fixture, run_async_eval
from packages.agents.main_assistant import stream_main_assistant
from packages.types.python.canvas_types import CanvasOpsMessage

EVAL_ID = "E-001"
THRESHOLD = 80 / 90


def _make_tool_call_msg(tool_name: str, args: dict[str, Any], call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": tool_name, "args": args, "id": call_id, "type": "tool_call"}],
    )


def _make_text_msg(text: str) -> AIMessage:
    return AIMessage(content=text)


class _ScriptedSequenceLLM:
    def __init__(self, responses: list[AIMessage]) -> None:
        self._responses = list(responses)
        self._idx = 0

    def bind_tools(self, tools: Any) -> "_ScriptedSequenceLLM":
        return self

    async def ainvoke(self, messages: Any) -> AIMessage:
        if self._idx >= len(self._responses):
            return AIMessage(content="")
        response = self._responses[self._idx]
        self._idx += 1
        return response

    async def astream(self, messages: Any, **kwargs: Any):
        chunk = MagicMock()
        chunk.content = ""
        yield chunk


def _build_llm(script: dict[str, Any]) -> _ScriptedSequenceLLM:
    responses: list[AIMessage] = [_make_text_msg(script["initial_reply"])]
    for idx, round_spec in enumerate(script["rounds"], start=1):
        if round_spec["type"] == "tool":
            responses.append(
                _make_tool_call_msg(
                    round_spec["tool_name"],
                    round_spec.get("args", {}),
                    call_id=f"tc{idx}",
                )
            )
        else:
            responses.append(_make_text_msg(round_spec.get("text", "")))
    return _ScriptedSequenceLLM(responses)


async def _run_case(inputs: dict[str, Any]) -> dict[str, Any]:
    script = inputs["script"]
    llm = _build_llm(script)

    async def _fake_render_stream(*args: Any, **kwargs: Any):
        for op in script.get("render_stream", []):
            yield op

    async def _fake_find_recipes(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return script.get("find_recipes_result", {"recipes": []})

    async def _fake_analyze_frames(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return script.get("analyze_result", {"assessment": "unknown", "suggested_action": None})

    with tracing_context(enabled=False):
        with patch("packages.agents.main_assistant.graph.astream_canvas_ops", _fake_render_stream), patch(
            "packages.agents.main_assistant.graph.find_recipes", _fake_find_recipes
        ), patch(
            "packages.agents.main_assistant.graph.analyze_frames", _fake_analyze_frames
        ):
            events = [
                event
                async for event in stream_main_assistant(
                    inputs["intent"],
                    inputs["context"],
                    inputs["canvas_state"],
                    llm,  # type: ignore[arg-type]
                    turn_id="eval-turn",
                    generation_id=1,
                )
            ]

    assistant_messages = [event["text"] for event in events if event["type"] == "speech_commit"]
    canvas_ops = [event["op"] for event in events if event["type"] == "canvas_op"]
    tool_names = [event["tool_name"] for event in events if event["type"] == "tool_call"]

    return {
        "assistant_messages": assistant_messages,
        "tool_names": tool_names,
        "canvas_ops": canvas_ops,
        "event_types": [event["type"] for event in events],
    }


def _tool_invocation_evaluator(run: Any, example: Any) -> dict[str, Any]:
    actual = run.outputs["tool_names"]
    expected = example.outputs["tool_names"]
    score = 1 if actual == expected else 0
    return {
        "key": "tool_invocation",
        "score": score,
        "value": {"available": 1, "actual": actual, "expected": expected},
        "comment": "Tool routing matched expected sequence." if score else "Tool routing diverged.",
    }


def _tts_length_evaluator(run: Any, example: Any) -> dict[str, Any]:
    assistant_messages = run.outputs["assistant_messages"]
    limit = example.outputs["max_tts_words"]
    valid = bool(assistant_messages) and all(len(message.split()) <= limit for message in assistant_messages)
    score = 1 if valid else 0
    return {
        "key": "tts_length",
        "score": score,
        "value": {"available": 1, "word_limit": limit},
        "comment": "All assistant messages stayed within the TTS limit." if score else "A TTS message exceeded the limit.",
    }


def _canvas_ops_evaluator(run: Any, example: Any) -> dict[str, Any]:
    canvas_ops = run.outputs["canvas_ops"]
    requires_canvas = bool(example.outputs["requires_canvas"])
    valid = True
    try:
        CanvasOpsMessage(type="canvas_ops", operations=canvas_ops)
    except Exception:
        valid = False
    if requires_canvas and not canvas_ops:
        valid = False
    score = 1 if valid else 0
    return {
        "key": "canvas_ops",
        "score": score,
        "value": {"available": 1, "requires_canvas": requires_canvas, "canvas_op_count": len(canvas_ops)},
        "comment": "Canvas ops were structurally valid." if score else "Canvas ops were missing or invalid.",
    }


@pytest.mark.asyncio
async def test_e001_main_assistant_routing_eval() -> None:
    cases = load_json_fixture("main_assistant_cases.json")
    summary, result_path = await run_async_eval(
        eval_id=EVAL_ID,
        cases=cases,
        target=_run_case,
        evaluators=[
            _tool_invocation_evaluator,
            _tts_length_evaluator,
            _canvas_ops_evaluator,
        ],
        threshold=THRESHOLD,
        description="Main Assistant routing and response-structure regression suite.",
    )

    assert summary["case_count"] == 30
    assert summary["available"] == 90
    assert summary["passed"], f"{EVAL_ID} failed: see {result_path}"
