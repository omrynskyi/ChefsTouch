from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from .healer import ContentEvent, JSONStreamHealer, SkeletonEvent
from .prompts import AGENT_SYSTEM_PROMPT
from .schemas import CanvasOp, VALID_TYPES


def _canvas_summary(canvas_state: Dict[str, Any]) -> str:
    if not canvas_state:
        return "CURRENT CANVAS: empty"
    lines = ["CURRENT CANVAS:"]
    for comp_id, comp in canvas_state.items():
        comp_type = comp.get("type", "?")
        data = comp.get("data") or {}
        if comp_type == "step-view":
            desc = (
                f'step {data.get("step_number","?")}/{data.get("total_steps","?")} '
                f'"{data.get("instruction","")}"'
            )
        elif comp_type == "progress-bar":
            desc = f'{data.get("current","?")}/{data.get("total","?")}'
        elif comp_type == "timer":
            desc = (
                f'{data.get("duration_seconds","?")}s {data.get("label","?")} '
                f'[auto_start={data.get("auto_start","?")}]'
            )
        else:
            desc = ", ".join(f"{k}={v}" for k, v in list(data.items())[:2])
        lines.append(f"- {comp_id} ({comp_type}): {desc}")
    return "\n".join(lines)


def _validate_op(raw: dict) -> Optional[dict]:
    try:
        op = CanvasOp.model_validate(raw)
        return op.model_dump(exclude_none=True)
    except Exception:
        return None


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
        return {"ops": ops, "errors": []}


def build_canvas_render_graph(llm: BaseChatModel, retriever: Any = None) -> _RenderGraph:
    """
    Returns a graph-like object with ainvoke(state) -> {ops, errors}.
    The retriever arg is accepted but unused — CSS vector search is gone.
    """
    return _RenderGraph(llm)
