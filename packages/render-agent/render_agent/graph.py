from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Sequence

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from pydantic import ValidationError
from typing_extensions import TypedDict

from .prompts import AGENT_SYSTEM_PROMPT, format_classes
from .sanitizer import sanitize_html
from .schemas import CanvasOp, CanvasState


class _RenderState(TypedDict):
    intent: str
    canvas_state: Dict[str, Any]
    context: str
    messages: List[Any]
    retrieved_classes: List[Document]
    raw_output: str
    ops: List[Dict[str, Any]]
    errors: List[str]


def _extract_json(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        return fenced.group(1).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        return text[start : end + 1]
    return text.strip()


def build_canvas_render_graph(llm: BaseChatModel, retriever: Any) -> Any:
    """
    Returns a compiled LangGraph. The LLM calls search_css_classes as a tool
    to retrieve the CSS it needs, then generates canvas ops as a JSON array.

    Usage:
        graph = build_canvas_render_graph(llm, retriever)
        result = await graph.ainvoke({
            "intent": "show step 3 with a 6 minute timer",
            "canvas_state": {},
            "context": "Pasta Carbonara, step 3 of 6",
        })
        ops = result["ops"]
    """

    @tool
    async def search_css_classes(query: str) -> str:
        """
        Search for CSS classes and components by describing what you need.
        Call this before generating HTML to find the right class names.
        Example queries: "floating timer overlay", "list with text items", "fade-in animation"
        """
        docs: Sequence[Document] = await retriever.ainvoke(query)
        if not docs:
            return "No matching classes found."
        return format_classes(list(docs))

    llm_with_tools = llm.bind_tools([search_css_classes])

    def canvas_summary(canvas_state: Dict[str, Any]) -> str:
        if not canvas_state:
            return "empty"
        try:
            return CanvasState.model_validate({"components": canvas_state}).summary()
        except Exception:
            return ", ".join(f"{k}(zone={v.get('zone','?')})" for k, v in canvas_state.items())

    async def setup(state: _RenderState) -> _RenderState:
        system = AGENT_SYSTEM_PROMPT.format(canvas_state=canvas_summary(state["canvas_state"]))
        user = f"Intent: {state['intent']}\nContext: {state['context']}"
        return {
            **state,
            "messages": [SystemMessage(content=system), HumanMessage(content=user)],
            "retrieved_classes": [],
        }

    async def call_llm(state: _RenderState) -> _RenderState:
        response = await llm_with_tools.ainvoke(state["messages"])
        return {**state, "messages": state["messages"] + [response]}

    async def run_tools(state: _RenderState) -> _RenderState:
        last: AIMessage = state["messages"][-1]
        new_messages = []
        new_docs: List[Document] = []

        for tc in last.tool_calls:
            if tc["name"] == "search_css_classes":
                query = tc["args"].get("query", "")
                docs: Sequence[Document] = await retriever.ainvoke(query)
                new_docs.extend(docs)
                result_text = format_classes(list(docs)) if docs else "No matching classes found."
                new_messages.append(
                    ToolMessage(content=result_text, tool_call_id=tc["id"])
                )

        return {
            **state,
            "messages": state["messages"] + new_messages,
            "retrieved_classes": state["retrieved_classes"] + new_docs,
        }

    def should_continue(state: _RenderState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            return "tools"
        return "validate"

    async def validate_ops(state: _RenderState) -> _RenderState:
        last: AIMessage = state["messages"][-1]
        raw_text = last.content if isinstance(last.content, str) else ""
        errors: List[str] = []
        valid_ops: List[Dict[str, Any]] = []

        try:
            raw = json.loads(_extract_json(raw_text))
        except json.JSONDecodeError as e:
            return {**state, "raw_output": raw_text, "ops": [], "errors": [f"JSON parse failed: {e}"]}

        if not isinstance(raw, list):
            return {**state, "raw_output": raw_text, "ops": [], "errors": ["LLM output was not a JSON array"]}

        for item in raw:
            try:
                op = CanvasOp.model_validate(item)
                if op.html:
                    op = op.model_copy(update={"html": sanitize_html(op.html)})
                valid_ops.append(op.model_dump(exclude_none=True))
            except (ValidationError, Exception) as e:
                errors.append(f"dropped op {item.get('id', '?')}: {e}")

        return {**state, "raw_output": raw_text, "ops": valid_ops, "errors": errors}

    graph: StateGraph = StateGraph(_RenderState)
    graph.add_node("setup", setup)
    graph.add_node("llm", call_llm)
    graph.add_node("tools", run_tools)
    graph.add_node("validate", validate_ops)

    graph.set_entry_point("setup")
    graph.add_edge("setup", "llm")
    graph.add_conditional_edges("llm", should_continue, {"tools": "tools", "validate": "validate"})
    graph.add_edge("tools", "llm")
    graph.add_edge("validate", END)

    return graph.compile()
