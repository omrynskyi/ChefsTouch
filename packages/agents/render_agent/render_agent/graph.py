from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langsmith.run_helpers import trace

from packages.agents.langsmith_utils import summarize_canvas_state
from .healer import ContentEvent, JSONStreamHealer, SkeletonEvent
from .prompts import AGENT_SYSTEM_PROMPT
from .schemas import CanvasOp, VALID_TYPES

_RESERVED_POSITION = "corner-tl"
_SUPPRESSED_SKELETON_TYPES = {"recipe-option"}


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


def _known_component_types(canvas_state: Dict[str, Any]) -> Dict[str, Optional[str]]:
    active, staged = _canvas_layers(canvas_state)
    known: Dict[str, Optional[str]] = {}
    for layer in (active, staged):
        if isinstance(layer, dict):
            for comp_id, entry in layer.items():
                known[comp_id] = _component_type(entry)
    return known


def _uses_reserved_surface(op: dict) -> bool:
    if op.get("type") == "assistant-message":
        return True
    if op.get("position") == _RESERVED_POSITION:
        return True
    return False


def _repair_recipe_option_ops(ops: List[dict], canvas_state: Dict[str, Any]) -> tuple[List[dict], List[str]]:
    existing_types = _known_component_types(canvas_state)
    repaired: List[dict] = []
    errors: List[str] = []

    for op in ops:
        for streamed_op in _stream_repaired_ops(op, existing_types):
            if streamed_op.get("_dropped"):
                errors.append(streamed_op["_dropped"])
                continue
            repaired.append(streamed_op)

    return repaired, errors


def _stream_repaired_ops(op: dict, known_types: Dict[str, Optional[str]]) -> List[dict]:
    if _uses_reserved_surface(op):
        return []

    op_type = op.get("op")
    comp_id = op.get("id")
    comp_type = op.get("type")

    if op_type in {"add", "stage"} and comp_type == "recipe-option":
        parent_id = op.get("parent")
        if not isinstance(parent_id, str):
            return [op]

        parent_type = known_types.get(parent_id)
        if parent_type and parent_type != "recipe-grid":
            return [{
                "_dropped": (
                    f"Dropped recipe-option '{comp_id}' because parent "
                    f"'{parent_id}' exists as '{parent_type}'."
                )
            }]

        emitted: List[dict] = []
        if parent_type != "recipe-grid":
            parent_op = {"op": "add", "id": parent_id, "type": "recipe-grid", "data": {}}
            emitted.append(parent_op)
            known_types[parent_id] = "recipe-grid"

        emitted.append(op)
        if isinstance(comp_id, str):
            known_types[comp_id] = "recipe-option"
        return emitted

    if op_type in {"add", "stage"} and isinstance(comp_id, str) and isinstance(comp_type, str):
        known_types[comp_id] = comp_type
    elif op_type == "remove" and isinstance(comp_id, str):
        known_types.pop(comp_id, None)

    return [op]


async def astream_events(
    intent: str,
    context: str,
    canvas_state: Dict[str, Any],
    llm: BaseChatModel,
) -> AsyncGenerator[Union[SkeletonEvent, ContentEvent], None]:
    """
    Stream SkeletonEvent and ContentEvent as the LLM generates JSONL ops.

    SkeletonEvents fire as soon as "type" and "id" are visible in the partial
    buffer, before the full op object closes. ContentEvents carry a validated
    CanvasOp dict and fire when the object closes. Invalid ops are dropped
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


async def astream_canvas_ops(
    intent: str,
    context: str,
    canvas_state: Dict[str, Any],
    llm: BaseChatModel,
) -> AsyncGenerator[dict, None]:
    known_types = _known_component_types(canvas_state)
    skeleton_count = 0
    content_count = 0
    reserved_surface_drops = 0
    recipe_grid_repairs = 0

    with trace(
        "render_agent.stream",
        run_type="chain",
        inputs={
            "intent": intent,
            "context": context,
            "canvas_state": summarize_canvas_state(canvas_state),
        },
        tags=["pair-cooking", "render-agent", "streaming"],
    ) as render_run:
        async for event in astream_events(intent, context, canvas_state, llm):
            if isinstance(event, SkeletonEvent):
                if event.component_type in _SUPPRESSED_SKELETON_TYPES:
                    continue
                skeleton_count += 1
                yield {"op": "skeleton", "id": event.id, "type": event.component_type}
                continue

            for op in _stream_repaired_ops(event.op, known_types):
                if "_dropped" in op:
                    reserved_surface_drops += 1
                    continue
                if op.get("type") == "recipe-grid" and op.get("op") == "add" and op.get("data") == {}:
                    recipe_grid_repairs += 1
                content_count += 1
                yield op

        render_run.end(
            outputs={
                "skeleton_count": skeleton_count,
                "content_count": content_count,
                "reserved_surface_drops": reserved_surface_drops,
                "recipe_grid_repairs": recipe_grid_repairs,
            }
        )


class _RenderGraph:
    """Non-streaming wrapper around astream_canvas_ops for batch invocation."""

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
