from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── Constants ─────────────────────────────────────────────────────────────────

# Classes always valid — structural HTML attributes, not in the CSS DB
STRUCTURAL_ATTRS = {
    "animate-in", "animate-out", "hover-lift", "pulse-on-end",
    "muted", "size-sm", "size-md", "size-lg", "size-xl",
}

ZONE_DEFAULTS = {
    "timer":      "corner-br",
    "suggestion": "bottom",
    "alert":      "top",
    "progress":   "top",
}

EvalResult = Dict[str, Any]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _all_html(ops: List[Dict[str, Any]]) -> str:
    return " ".join(op.get("html", "") for op in ops if op.get("html"))

def _used_classes(html: str) -> set:
    return {c for m in re.findall(r'class="([^"]+)"', html) for c in m.split()}

def _zone_of(html: str) -> Optional[str]:
    m = re.search(r'zone="([^"]+)"', html)
    return m.group(1) if m else None

def _parse_llm_score(text: str) -> Optional[float]:
    try:
        data = json.loads(re.search(r'\{.*\}', text, re.DOTALL).group())
        return min(max(int(data["score"]), 1), 5) / 5.0
    except Exception:
        # fallback: find first digit 1-5
        m = re.search(r'\b([1-5])\b', text)
        return int(m.group(1)) / 5.0 if m else None


# ── Evaluator 1: Class discipline ─────────────────────────────────────────────

def eval_class_discipline(run_outputs: Dict[str, Any], example: Dict[str, Any]) -> EvalResult:
    """Did the agent only use CSS classes it actually retrieved?"""
    retrieved = {d.metadata.get("name", "") for d in run_outputs.get("retrieved_classes", [])}
    html = _all_html(run_outputs.get("ops", []))
    used = _used_classes(html)

    if not used:
        return {"score": 1.0, "comment": "no classes used"}

    checkable = used - STRUCTURAL_ATTRS
    invented = checkable - retrieved

    score = 1.0 if not invented else round(1 - len(invented) / max(len(checkable), 1), 2)
    comment = f"invented: {invented}" if invented else "all classes retrieved"
    return {"score": score, "comment": comment}


# ── Evaluator 2: Zone correctness ─────────────────────────────────────────────

def eval_zone_correctness(run_outputs: Dict[str, Any], example: Dict[str, Any]) -> EvalResult:
    """Do component types land in their expected default zones?"""
    ops = [op for op in run_outputs.get("ops", []) if op.get("html")]

    if not ops:
        return {"score": 1.0, "comment": "no ops to check"}

    checked, correct = 0, 0
    notes = []

    for op in ops:
        component_id = op.get("id", "")
        zone = _zone_of(op["html"])

        for keyword, expected_zone in ZONE_DEFAULTS.items():
            if keyword in component_id.lower():
                checked += 1
                if zone == expected_zone:
                    correct += 1
                else:
                    notes.append(f"{component_id}: expected {expected_zone}, got {zone}")

    if checked == 0:
        return {"score": 1.0, "comment": "no zone-typed components to check"}

    score = round(correct / checked, 2)
    return {"score": score, "comment": "; ".join(notes) if notes else "all zones correct"}


# ── Evaluator 3: Tool query quality (LLM-as-judge) ───────────────────────────

TOOL_QUERY_PROMPT = """\
A canvas render agent was given this intent:
"{intent}"

It searched for CSS classes using these queries:
{queries}

Score the quality of these search queries from 1 to 5:
5 = queries clearly describe CSS/layout needs in CSS vocabulary (e.g. "floating card overlay", "monospace countdown display")
3 = queries are vague, partially describe CSS, or mix UI concepts with content
1 = queries just rephrase the user intent with no CSS thinking (e.g. "ingredients list for pasta")

Return only valid JSON: {{"score": <1-5>, "reason": "<one sentence>"}}"""


async def eval_tool_query_quality(
    run_outputs: Dict[str, Any],
    example: Dict[str, Any],
    judge_llm: Any,
) -> EvalResult:
    """Were the CSS search queries written in CSS vocabulary?"""
    from langchain_core.messages import HumanMessage

    messages = run_outputs.get("messages", [])
    queries = []
    for msg in messages:
        if hasattr(msg, "tool_calls"):
            for tc in (msg.tool_calls or []):
                if tc.get("name") == "search_css_classes":
                    queries.append(tc["args"].get("query", ""))

    if not queries:
        return {"score": 0.0, "comment": "agent made no tool calls"}

    prompt = TOOL_QUERY_PROMPT.format(
        intent=example.get("intent", ""),
        queries="\n".join(f"  - {q}" for q in queries),
    )
    response = await judge_llm.ainvoke([HumanMessage(content=prompt)])
    score = _parse_llm_score(response.content)

    return {
        "score": score if score is not None else 0.5,
        "comment": response.content[:200],
        "queries": queries,
    }


# ── Evaluator 4: Compelling HTML (LLM-as-judge) ───────────────────────────────

COMPELLING_HTML_PROMPT = """\
A canvas render agent was given this intent:
"{intent}"

Expected behavior:
"{rubric}"

It generated this HTML:
{html}

Score the quality of the HTML from 1 to 5:
5 = well-structured, semantic hierarchy, right components for the job, would render as a compelling UI that matches the intent
3 = functional but generic, missing detail, or only partially matches the intent
1 = wrong component choice, broken structure, ignores the intent, or too minimal to be useful

Return only valid JSON: {{"score": <1-5>, "reason": "<one sentence>"}}"""


async def eval_compelling_html(
    run_outputs: Dict[str, Any],
    example: Dict[str, Any],
    judge_llm: Any,
) -> EvalResult:
    """Is the generated HTML well-structured and compelling for the given intent?"""
    from langchain_core.messages import HumanMessage

    ops = run_outputs.get("ops", [])
    html = _all_html(ops)

    if not html:
        return {"score": 0.0, "comment": "no HTML generated"}

    prompt = COMPELLING_HTML_PROMPT.format(
        intent=example.get("intent", ""),
        rubric=example.get("rubric", ""),
        html=html[:2000],  # cap to avoid token blowout
    )
    response = await judge_llm.ainvoke([HumanMessage(content=prompt)])
    score = _parse_llm_score(response.content)

    return {
        "score": score if score is not None else 0.5,
        "comment": response.content[:200],
    }
