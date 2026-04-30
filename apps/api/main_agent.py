from __future__ import annotations

import logging
import os
import sys
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langsmith import traceable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../packages/render-agent"))

logger = logging.getLogger(__name__)

StatusCallback = Optional[Callable[[str], Awaitable[None]]]

SYSTEM_PROMPT = """\
You're Pip, a sharp and playful cooking sidekick. Keep every reply to two sentences max — you're talking, not typing. Be direct and a bit cheeky.

You have three tools:
- render_canvas: Call this when the screen needs updating (showing steps, recipes, timers, etc.)
- find_recipes: Call this when the user wants to find or start a recipe.
- analyze_image: Call this when the user sends camera frames to check their cooking.

Always call render_canvas when the screen should change. Always keep tts_text short and conversational.\
If you need clarification from the user, render it on-screen. Use a text-card for short questions, and use a text-card with an input field when you want the user to type an answer.\
"""

_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "render_canvas",
            "description": "Update the canvas UI. Call this to render cooking steps, recipe options, timers, or any screen content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "description": "What to render — a natural-language description of what should appear on screen.",
                    }
                },
                "required": ["intent"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_recipes",
            "description": "Search for recipes matching a query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Recipe search query."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_image",
            "description": "Analyze camera frames to assess cooking state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "context": {"type": "string", "description": "Current step context for image analysis."}
                },
                "required": ["context"],
            },
        },
    },
]

_TOOL_STATUS: Dict[str, str] = {
    "render_canvas": "Updating canvas…",
    "find_recipes": "Searching for recipes…",
    "analyze_image": "Analyzing your photo…",
}


class AgentState(TypedDict):
    messages: List[Any]
    canvas_ops: List[dict]
    tts_text: str
    context: str
    canvas_state: Dict[str, Any]
    errors: List[str]


class MainAssistantGraph:
    def __init__(self, llm: BaseChatModel, on_status: StatusCallback = None) -> None:
        self._llm = llm.bind_tools(_TOOL_SCHEMAS)  # type: ignore[arg-type]
        self._on_status = on_status

    async def _emit(self, text: str) -> None:
        if self._on_status:
            await self._on_status(text)

    async def ainvoke(self, state: AgentState) -> AgentState:
        from langgraph.graph import StateGraph, END

        graph = StateGraph(AgentState)
        graph.add_node("call_llm", self._call_llm_node)
        graph.add_node("execute_tools", self._execute_tools_node)
        graph.add_node("collect_response", self._collect_response_node)
        graph.set_entry_point("call_llm")
        graph.add_conditional_edges("call_llm", self._router)
        graph.add_edge("execute_tools", "call_llm")
        graph.add_edge("collect_response", END)
        compiled = graph.compile()
        return await compiled.ainvoke(state)  # type: ignore[return-value]

    async def _call_llm_node(self, state: AgentState) -> AgentState:
        await self._emit("Thinking…")
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = await self._llm.ainvoke(messages)
        return {**state, "messages": state["messages"] + [response]}

    async def _execute_tools_node(self, state: AgentState) -> AgentState:
        last_msg = state["messages"][-1]
        if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
            return state

        new_messages = list(state["messages"])
        canvas_ops = list(state["canvas_ops"])
        errors = list(state["errors"])

        for tc in last_msg.tool_calls:
            tool_name = tc["name"]
            tool_args = tc.get("args", {})
            tool_id = tc.get("id", tool_name)
            await self._emit(_TOOL_STATUS.get(tool_name, f"Running {tool_name}…"))
            try:
                result = await self._dispatch_tool(tool_name, tool_args, state)
                if tool_name == "render_canvas":
                    canvas_ops.extend(result.get("ops", []))
                new_messages.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tool_id,
                ))
            except Exception as exc:
                error_msg = f"{tool_name} failed: {exc}"
                logger.warning(error_msg)
                errors.append(error_msg)
                new_messages.append(ToolMessage(
                    content=f"Error: {error_msg}",
                    tool_call_id=tool_id,
                ))

        return {**state, "messages": new_messages, "canvas_ops": canvas_ops, "errors": errors}

    def _collect_response_node(self, state: AgentState) -> AgentState:
        tts_text = ""
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage) and isinstance(msg.content, str) and msg.content.strip():
                tts_text = msg.content.strip()
                break

        if not tts_text and state["errors"]:
            tts_text = "Hmm, something went sideways. Let's try that again."

        return {**state, "tts_text": tts_text}

    def _router(self, state: AgentState) -> str:
        last_msg = state["messages"][-1]
        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            return "execute_tools"
        return "collect_response"

    async def _dispatch_tool(
        self, name: str, args: dict, state: AgentState
    ) -> dict:
        if name == "render_canvas":
            return await self._run_render_agent(args.get("intent", ""), state)
        if name == "find_recipes":
            return {"recipes": [], "note": "Recipe search not yet implemented"}
        if name == "analyze_image":
            return {
                "observation": "No frames available",
                "assessment": "ok",
                "suggested_action": None,
            }
        return {"error": f"Unknown tool: {name}"}

    async def _run_render_agent(self, intent: str, state: AgentState) -> dict:
        from render_agent import build_canvas_render_graph
        graph = build_canvas_render_graph(self._llm)  # type: ignore[arg-type]
        result = await graph.ainvoke({
            "intent": intent,
            "context": state["context"],
            "canvas_state": state["canvas_state"],
        })
        return result


def build_main_agent_graph(llm: BaseChatModel, on_status: StatusCallback = None) -> MainAssistantGraph:
    return MainAssistantGraph(llm, on_status=on_status)


@traceable(name="main-agent", project_name="main-agent")
async def run_main_agent(
    intent: str,
    context: str,
    canvas_state: Dict[str, Any],
    llm: BaseChatModel,
    on_status: StatusCallback = None,
) -> Dict[str, Any]:
    """Run the Main Assistant and return {"tts_text": str, "canvas_ops": list}."""
    graph = build_main_agent_graph(llm, on_status=on_status)
    initial_state: AgentState = {
        "messages": [HumanMessage(content=intent)],
        "canvas_ops": [],
        "tts_text": "",
        "context": context,
        "canvas_state": canvas_state,
        "errors": [],
    }
    result = await graph.ainvoke(initial_state)
    return {
        "tts_text": result["tts_text"],
        "canvas_ops": result["canvas_ops"],
    }
