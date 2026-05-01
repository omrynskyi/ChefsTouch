from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from langsmith.run_helpers import tracing_context

from evals.common import load_json_fixture, run_async_eval
from packages.agents.render_agent import astream_canvas_ops
from packages.types.python.canvas_types import CanvasOpsMessage

EVAL_ID = "E-004"
THRESHOLD = 0.90

DEFAULT_POSITIONS = {
    "step-view": "center",
    "progress-bar": "top",
    "timer": "corner-br",
    "alert": "top",
    "recipe-grid": "center",
    "recipe-option": "center",
    "ingredient-list": "left",
    "camera": "center",
    "suggestion": "bottom",
    "text-card": "center",
    "assistant-message": "corner-tl",
}


class _ChunkedLLM:
    def __init__(self, chunks: list[str]) -> None:
        self._chunks = list(chunks)

    async def astream(self, messages: Any, **kwargs: Any):
        for text in self._chunks:
            chunk = MagicMock()
            chunk.content = text
            yield chunk


async def _run_case(inputs: dict[str, Any]) -> dict[str, Any]:
    llm = _ChunkedLLM(inputs["chunks"])
    with tracing_context(enabled=False):
        stream_ops = [
            op
            async for op in astream_canvas_ops(
                inputs["intent"],
                inputs["context"],
                inputs["canvas_state"],
                llm,  # type: ignore[arg-type]
            )
        ]
    ops = [op for op in stream_ops if op.get("op") != "skeleton"]
    return {
        "canvas_ops": ops,
        "stream_op_count": len(stream_ops),
        "component_types": sorted({op["type"] for op in ops if isinstance(op.get("type"), str)}),
    }


def _effective_position(op: dict[str, Any]) -> str | None:
    explicit = op.get("position")
    if isinstance(explicit, str):
        return explicit
    comp_type = op.get("type")
    if isinstance(comp_type, str):
        return DEFAULT_POSITIONS.get(comp_type)
    return None


def _schema_validity_evaluator(run: Any, example: Any) -> dict[str, Any]:
    ops = run.outputs["canvas_ops"]
    valid_count = 0
    for op in ops:
        try:
            CanvasOpsMessage(type="canvas_ops", operations=[op])
        except Exception:
            continue
        valid_count += 1
    return {
        "key": "schema_validity",
        "score": valid_count,
        "value": {"available": len(ops), "valid_count": valid_count},
        "comment": "All render ops were schema-valid." if valid_count == len(ops) else "Some render ops failed schema validation.",
    }


def _count_limit_evaluator(run: Any, example: Any) -> dict[str, Any]:
    ops = run.outputs["canvas_ops"]
    max_ops = example.outputs["max_ops"]
    score = 1 if len(ops) <= max_ops else 0
    return {
        "key": "operation_count_limit",
        "score": score,
        "value": {"available": 1, "max_ops": max_ops, "actual_ops": len(ops)},
        "comment": "Operation count stayed within the limit." if score else "Operation count exceeded the limit.",
    }


def _position_evaluator(run: Any, example: Any) -> dict[str, Any]:
    ops = run.outputs["canvas_ops"]
    required_positions = example.outputs["required_positions"]
    valid = True
    for comp_type, expected_position in required_positions.items():
        type_ops = [op for op in ops if op.get("type") == comp_type]
        if not type_ops:
            valid = False
            break
        if any(_effective_position(op) != expected_position for op in type_ops):
            valid = False
            break
    score = 1 if valid else 0
    return {
        "key": "position_appropriateness",
        "score": score,
        "value": {"available": 1, "required_positions": required_positions},
        "comment": "Effective positions matched expected zones." if score else "A component landed in the wrong zone.",
    }


def _component_type_evaluator(run: Any, example: Any) -> dict[str, Any]:
    actual_types = set(run.outputs["component_types"])
    required_types = set(example.outputs["required_types"])
    valid = required_types.issubset(actual_types) and "assistant-message" not in actual_types
    score = 1 if valid else 0
    return {
        "key": "component_type_correctness",
        "score": score,
        "value": {"available": 1, "required_types": sorted(required_types), "actual_types": sorted(actual_types)},
        "comment": "Component types matched expectations." if score else "Rendered component types were wrong.",
    }


@pytest.mark.asyncio
async def test_e004_render_agent_output_eval() -> None:
    cases = load_json_fixture("render_agent_cases.json")
    summary, result_path = await run_async_eval(
        eval_id=EVAL_ID,
        cases=cases,
        target=_run_case,
        evaluators=[
            _schema_validity_evaluator,
            _count_limit_evaluator,
            _position_evaluator,
            _component_type_evaluator,
        ],
        threshold=THRESHOLD,
        description="Render Agent streaming output regression suite.",
    )

    assert summary["case_count"] == 25
    assert summary["available"] == 114
    assert summary["passed"], f"{EVAL_ID} failed: see {result_path}"
