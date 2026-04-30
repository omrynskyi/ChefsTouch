from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from .healer import ContentEvent, JSONStreamHealer, SkeletonEvent
from .prompts import AGENT_SYSTEM_PROMPT
from .schemas import CanvasOp, VALID_TYPES


def _canvas_summary(canvas_state: Dict[str, Any]) -> str:
    import json
    if "active" in canvas_state or "staged" in canvas_state:
        active = canvas_state.get("active", {})
        staged = canvas_state.get("staged", {})
    else:
        active = canvas_state
        staged = {}
    return "CANVAS STATE:\n" + json.dumps({"active": active, "staged": staged}, indent=2)


def _validate_op(raw: dict) -> Optional[dict]:
    try:
        op = CanvasOp.model_validate(raw)
        return op.model_dump(exclude_none=True)
    except Exception:
        return None


def _canvas_layers(canvas_state: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    if "active" in canvas_state or "staged" in canvas_state:
        return canvas_state.get("active", {}), canvas_state.get("staged", {})
    return canvas_state, {}


def _component_type(entry: Any) -> Optional[str]:
    if isinstance(entry, dict):
        comp_type = entry.get("type")
        if isinstance(comp_type, str):
            return comp_type
    return None


def _repair_recipe_option_ops(ops: List[dict], canvas_state: Dict[str, Any]) -> tuple[List[dict], List[str]]:
    active, staged = _canvas_layers(canvas_state)

    existing_types: Dict[str, Optional[str]] = {}
    for layer in (active, staged):
        if isinstance(layer, dict):
            for comp_id, entry in layer.items():
                existing_types[comp_id] = _component_type(entry)

    batch_types = {
        op["id"]: op["type"]
        for op in ops
        if op.get("op") in {"add", "stage"} and isinstance(op.get("id"), str) and isinstance(op.get("type"), str)
    }

    repaired: List[dict] = []
    errors: List[str] = []
    synthesized_parents: set[str] = set()

    for op in ops:
        if op.get("op") not in {"add", "stage"} or op.get("type") != "recipe-option":
            repaired.append(op)
            continue

        parent_id = op.get("parent")
        if not isinstance(parent_id, str):
            repaired.append(op)
            continue

        existing_parent_type = existing_types.get(parent_id)
        batch_parent_type = batch_types.get(parent_id)

        if existing_parent_type and existing_parent_type != "recipe-grid":
            errors.append(
                f"Dropped recipe-option '{op['id']}' because parent '{parent_id}' exists as '{existing_parent_type}'."
            )
            continue

        if batch_parent_type and batch_parent_type != "recipe-grid":
            errors.append(
                f"Dropped recipe-option '{op['id']}' because parent '{parent_id}' is emitted as '{batch_parent_type}' in the same batch."
            )
            continue

        parent_exists = existing_parent_type == "recipe-grid" or batch_parent_type == "recipe-grid"
        if not parent_exists and parent_id not in synthesized_parents:
            repaired.append({"op": "add", "id": parent_id, "type": "recipe-grid", "data": {}})
            synthesized_parents.add(parent_id)

        repaired.append(op)

    return repaired, errors


async def astream_events(
    intent: str,
    context: str,
    canvas_state: Dict[str, Any],
    llm: BaseChatModel,
) -> AsyncGenerator[Union[SkeletonEvent, ContentEvent], None]:
    """
    Stream SkeletonEvent and ContentEvent as the LLM generates JSONL ops.

    SkeletonEvents fire as soon as "type" and "id" are visible in the partial
    buffer, before the full op object closes.  ContentEvents carry a validated
    CanvasOp dict and fire when the object closes.  Invalid ops are dropped
    silently.
    """
    system = AGENT_SYSTEM_PROMPT.format(canvas_state=_canvas_summary(canvas_state))
    messages = [SystemMessage(content=system), HumanMessage(content=f"Intent: {intent}\nContext: {context}")]
    healer = JSONStreamHealer()

    async for chunk in llm.astream(messages):
        text = chunk.content if isinstance(chunk.content, str) else ""
        for event in healer.feed(text):
            if isinstance(event, SkeletonEvent):
                if event.component_type in VALID_TYPES:
                    yield event
            else:
                validated = _validate_op(event.op)
                if validated is not None:
                    yield ContentEvent(op=validated)

    for event in healer.finalize():
        if isinstance(event, SkeletonEvent):
            if event.component_type in VALID_TYPES:
                yield event
        else:
            validated = _validate_op(event.op)
            if validated is not None:
                yield ContentEvent(op=validated)


class _RenderGraph:
    """Non-streaming wrapper around astream_events for batch invocation."""

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    async def ainvoke(self, state: dict) -> dict:
        intent = state.get("intent", "")
        context = state.get("context", "")
        canvas_state = state.get("canvas_state", {})
        ops: List[dict] = []
        async for event in astream_events(intent, context, canvas_state, self._llm):
            if isinstance(event, ContentEvent):
                ops.append(event.op)
        repaired_ops, errors = _repair_recipe_option_ops(ops, canvas_state)
        return {"ops": repaired_ops, "errors": errors}


def build_canvas_render_graph(llm: BaseChatModel, retriever: Any = None) -> _RenderGraph:
    """
    Returns a graph-like object with ainvoke(state) -> {ops, errors}.
    The retriever arg is accepted but unused — CSS vector search is gone.
    """
    return _RenderGraph(llm)
