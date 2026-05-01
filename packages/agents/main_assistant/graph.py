from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langsmith.run_helpers import trace, tracing_context

from packages.agents.image_inference_agent import analyze_frames
from packages.agents.langsmith_utils import (
    get_langsmith_client,
    get_langsmith_project,
    langsmith_tracing_mode,
    summarize_canvas_state,
)
from packages.agents.main_assistant.prompts import INITIAL_REPLY_PROMPT, SYSTEM_PROMPT
from packages.agents.recipe_agent import find_recipes
from packages.agents.render_agent import astream_canvas_ops

logger = logging.getLogger(__name__)

ASSISTANT_MESSAGE_ID = "sys-assistant-message"
_DEFAULT_INITIAL_REPLY = "One sec, I'm on it."
_FALLBACK_FAILURE_REPLY = "Hmm, something went sideways. Let me try that another way."
_MAX_TOOL_ROUNDS = 4

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


class MainAssistantEvent(TypedDict, total=False):
    type: Literal["assistant_message", "canvas_op", "status", "turn_complete", "tool_call"]
    text: str
    op: dict
    tool_name: str
    tool_args: dict[str, Any]


class MainAssistantGraph:
    def __init__(self, llm: BaseChatModel) -> None:
        self._base_llm = llm
        self._tool_llm = llm.bind_tools(_TOOL_SCHEMAS)  # type: ignore[arg-type]

    async def astream(
        self,
        intent: str,
        context: str,
        canvas_state: Dict[str, Any],
    ) -> AsyncGenerator[MainAssistantEvent, None]:
        errors: List[str] = []
        initial_reply = await self._generate_initial_reply(intent, context)
        yield {"type": "assistant_message", "text": initial_reply}

        messages: List[Any] = [
            HumanMessage(content=intent),
            AIMessage(content=initial_reply),
        ]

        rounds = 0
        while rounds < _MAX_TOOL_ROUNDS:
            rounds += 1
            yield {"type": "status", "text": "Thinking…"}
            try:
                response = await self._plan_round(rounds, intent, context, messages)
            except Exception as exc:
                logger.warning("Main assistant planning failed: %s", exc)
                errors.append(f"planning failed: {exc}")
                break

            messages.append(response)
            if not isinstance(response, AIMessage) or not response.tool_calls:
                break

            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc.get("args", {})
                tool_id = tc.get("id", tool_name)
                yield {"type": "tool_call", "tool_name": tool_name, "tool_args": tool_args}
                yield {"type": "status", "text": _TOOL_STATUS.get(tool_name, f"Running {tool_name}…")}

                try:
                    result: dict[str, Any]
                    with trace(
                        f"main_assistant.tool.{tool_name}",
                        run_type="tool",
                        inputs={"args": tool_args, "context": context},
                        tags=["pair-cooking", "main-assistant", "tool", tool_name],
                        metadata={"round": rounds},
                    ) as tool_run:
                        if tool_name == "render_canvas":
                            streamed_ops = 0
                            async for op in astream_canvas_ops(
                                tool_args.get("intent", ""),
                                context,
                                canvas_state,
                                self._base_llm,
                            ):
                                streamed_ops += 1
                                yield {"type": "canvas_op", "op": op}
                            result = {"accepted": True, "streamed_ops": streamed_ops}
                        else:
                            result = await self._run_tool(tool_name, tool_args, context)
                        tool_run.end(outputs={"result": result})

                    messages.append(ToolMessage(content=str(result), tool_call_id=tool_id))
                except Exception as exc:
                    error_msg = f"{tool_name} failed: {exc}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    messages.append(ToolMessage(content=f"Error: {error_msg}", tool_call_id=tool_id))

        follow_up = self._collect_follow_up(messages, initial_reply, errors)
        if follow_up:
            yield {"type": "assistant_message", "text": follow_up}

        yield {"type": "turn_complete"}

    async def _generate_initial_reply(self, intent: str, context: str) -> str:
        prompt = "\n".join(
            part for part in [
                INITIAL_REPLY_PROMPT,
                f"User request: {intent}",
                f"Context: {context}" if context else "",
            ] if part
        )

        with trace(
            "main_assistant.initial_reply",
            run_type="llm",
            inputs={"intent": intent, "context": context},
            tags=["pair-cooking", "main-assistant", "initial-reply"],
        ) as reply_run:
            try:
                response = await self._base_llm.ainvoke([HumanMessage(content=prompt)])
            except Exception as exc:
                logger.warning("Initial reply generation failed: %s", exc)
                reply_run.end(outputs={"text": _DEFAULT_INITIAL_REPLY, "used_fallback": True}, error=str(exc))
                return _DEFAULT_INITIAL_REPLY

            text = self._message_text(response).strip() or _DEFAULT_INITIAL_REPLY
            reply_run.end(outputs={"text": text, "used_fallback": text == _DEFAULT_INITIAL_REPLY})
            return text

    async def _plan_round(
        self,
        round_number: int,
        intent: str,
        context: str,
        messages: List[Any],
    ) -> AIMessage:
        with trace(
            "main_assistant.plan_round",
            run_type="llm",
            inputs={
                "round": round_number,
                "intent": intent,
                "context": context,
                "message_count": len(messages),
            },
            tags=["pair-cooking", "main-assistant", "planning"],
            metadata={"round": round_number},
        ) as round_run:
            response = await self._tool_llm.ainvoke([SystemMessage(content=SYSTEM_PROMPT)] + messages)
            tool_calls = []
            if isinstance(response, AIMessage) and response.tool_calls:
                tool_calls = [
                    {"name": tc["name"], "args": tc.get("args", {})}
                    for tc in response.tool_calls
                ]
            round_run.end(
                outputs={
                    "assistant_text": self._message_text(response).strip() or None,
                    "tool_calls": tool_calls,
                }
            )
            return response

    async def _run_tool(self, name: str, args: dict, context: str) -> dict:
        if name == "find_recipes":
            return await find_recipes(args.get("query", ""), {"context": context})

        if name == "analyze_image":
            return await analyze_frames([], args.get("context", context), self._base_llm)

        return {"error": f"Unknown tool: {name}"}

    def _collect_follow_up(self, messages: List[Any], initial_reply: str, errors: List[str]) -> str:
        latest_text = ""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                latest_text = self._message_text(msg).strip()
                if latest_text:
                    break

        if latest_text and self._is_material_follow_up(initial_reply, latest_text):
            return latest_text

        if errors and self._is_material_follow_up(initial_reply, _FALLBACK_FAILURE_REPLY):
            return _FALLBACK_FAILURE_REPLY

        return ""

    @staticmethod
    def _is_material_follow_up(initial_reply: str, candidate: str) -> bool:
        normalized_initial = " ".join(initial_reply.lower().split())
        normalized_candidate = " ".join(candidate.lower().split())
        return bool(normalized_candidate) and normalized_candidate != normalized_initial

    @staticmethod
    def _message_text(message: Any) -> str:
        content = getattr(message, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        return str(content or "")


def build_main_assistant(llm: BaseChatModel) -> MainAssistantGraph:
    return MainAssistantGraph(llm)


async def stream_main_assistant(
    intent: str,
    context: str,
    canvas_state: Dict[str, Any],
    llm: BaseChatModel,
    tracking_context: Optional[dict[str, Any]] = None,
) -> AsyncGenerator[MainAssistantEvent, None]:
    graph = build_main_assistant(llm)
    client = get_langsmith_client()
    project_name = get_langsmith_project("agent-turns")
    tracing_mode = langsmith_tracing_mode()
    tracking_context = dict(tracking_context or {})
    trace_inputs = {
        "intent": intent,
        "context": context,
        "canvas_state": summarize_canvas_state(canvas_state),
    }
    trace_metadata = {
        **tracking_context,
        "canvas_state": summarize_canvas_state(canvas_state),
    }

    assistant_messages: List[str] = []
    canvas_ops: List[dict[str, Any]] = []
    tool_calls: List[dict[str, Any]] = []
    statuses: List[str] = []
    event_types: List[str] = []

    with tracing_context(
        project_name=project_name,
        metadata=trace_metadata,
        tags=["pair-cooking", "main-assistant", "streaming"],
        enabled=tracing_mode,
        client=client,
    ):
        with trace(
            "main_assistant.turn",
            run_type="chain",
            inputs=trace_inputs,
            project_name=project_name,
            metadata=trace_metadata,
            tags=["pair-cooking", "main-assistant", "streaming"],
            client=client,
        ) as turn_run:
            try:
                async for event in graph.astream(intent=intent, context=context, canvas_state=canvas_state):
                    event_types.append(event["type"])
                    if event["type"] == "assistant_message":
                        assistant_messages.append(event["text"])
                    elif event["type"] == "canvas_op":
                        canvas_ops.append(event["op"])
                    elif event["type"] == "tool_call":
                        tool_calls.append({
                            "name": event["tool_name"],
                            "args": event["tool_args"],
                        })
                    elif event["type"] == "status":
                        statuses.append(event["text"])
                    yield event
            except Exception as exc:
                turn_run.end(
                    outputs={
                        "assistant_messages": assistant_messages,
                        "tool_calls": tool_calls,
                        "canvas_ops": canvas_ops,
                        "statuses": statuses,
                        "event_types": event_types,
                    },
                    error=str(exc),
                )
                raise
            else:
                turn_run.end(
                    outputs={
                        "assistant_messages": assistant_messages,
                        "first_assistant_message": assistant_messages[0] if assistant_messages else None,
                        "final_assistant_message": assistant_messages[-1] if assistant_messages else None,
                        "tool_calls": tool_calls,
                        "tool_names": [tool["name"] for tool in tool_calls],
                        "canvas_ops": canvas_ops,
                        "canvas_op_count": len(canvas_ops),
                        "status_updates": statuses,
                        "event_types": event_types,
                        "follow_up_emitted": len(assistant_messages) > 1,
                    }
                )


async def run_main_assistant(
    intent: str,
    context: str,
    canvas_state: Dict[str, Any],
    llm: BaseChatModel,
    tracking_context: Optional[dict[str, Any]] = None,
) -> List[MainAssistantEvent]:
    events: List[MainAssistantEvent] = []
    async for event in stream_main_assistant(intent, context, canvas_state, llm, tracking_context=tracking_context):
        events.append(event)
    return events
