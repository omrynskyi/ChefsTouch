"""
Run behavioral evals for the render-agent.

Usage:
    python3 evals/run.py                     # run all 4 evals on all 10 cases
    python3 evals/run.py --eval class        # class_discipline only
    python3 evals/run.py --eval zone         # zone_correctness only
    python3 evals/run.py --eval tool         # tool_query_quality only
    python3 evals/run.py --eval html         # compelling_html only
    python3 evals/run.py --case 0            # single case by index
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

env_path = Path(__file__).resolve().parents[3] / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_openai import ChatOpenAI
from supabase import create_client

from render_agent import build_canvas_render_graph, SupabaseCSSRetriever
from render_agent.embeddings import LocalEmbeddings
from evals.dataset import DATASET
from evals.evaluators import (
    eval_class_discipline,
    eval_zone_correctness,
    eval_tool_query_quality,
    eval_compelling_html,
)

PASS_THRESHOLD = 0.75


def get_env(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        print(f"Error: {key} not set")
        sys.exit(1)
    return val


def build_graph():
    client = create_client(get_env("SUPABASE_URL"), get_env("SUPABASE_SERVICE_ROLE_KEY"))
    retriever = SupabaseCSSRetriever(
        client=client,
        embeddings=LocalEmbeddings(),
        k=10,
        match_threshold=0.0,
    )
    llm = ChatOpenAI(
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",
        model="google/gemma-4-26b-a4b",
        temperature=0,
    )
    return build_canvas_render_graph(llm=llm, retriever=retriever), llm


async def run_case(graph, case: dict) -> dict:
    return await graph.ainvoke({
        "intent": case["intent"],
        "canvas_state": case.get("canvas_state", {}),
        "context": case.get("context", ""),
    })


async def main(eval_filter: str | None, case_index: int | None) -> None:
    print("Loading model and building graph...")
    graph, llm = build_graph()

    cases = DATASET if case_index is None else [DATASET[case_index]]

    run_evals = {
        "class": eval_filter in (None, "class"),
        "zone":  eval_filter in (None, "zone"),
        "tool":  eval_filter in (None, "tool"),
        "html":  eval_filter in (None, "html"),
    }

    results = {k: [] for k in run_evals if run_evals[k]}

    for i, case in enumerate(cases):
        idx = case_index if case_index is not None else i
        print(f"\n[{idx+1}/{len(cases)}] {case['intent'][:60]}...")

        outputs = await run_case(graph, case)

        if run_evals["class"]:
            r = eval_class_discipline(outputs, case)
            results["class"].append(r["score"])
            print(f"  class_discipline    {r['score']:.2f}  {r['comment']}")

        if run_evals["zone"]:
            r = eval_zone_correctness(outputs, case)
            results["zone"].append(r["score"])
            print(f"  zone_correctness    {r['score']:.2f}  {r['comment']}")

        if run_evals["tool"]:
            r = await eval_tool_query_quality(outputs, case, llm)
            results["tool"].append(r["score"])
            print(f"  tool_query_quality  {r['score']:.2f}  queries: {r.get('queries', [])}")

        if run_evals["html"]:
            r = await eval_compelling_html(outputs, case, llm)
            results["html"].append(r["score"])
            print(f"  compelling_html     {r['score']:.2f}  {r['comment'][:80]}")

    # summary table
    NAMES = {
        "class": "class_discipline   ",
        "zone":  "zone_correctness   ",
        "tool":  "tool_query_quality ",
        "html":  "compelling_html    ",
    }
    print(f"\n{'─'*50}")
    print(f"{'eval':<24} {'score':>6}  {'pass':>5}")
    print(f"{'─'*50}")
    all_pass = True
    for key, scores in results.items():
        if not scores:
            continue
        avg = sum(scores) / len(scores)
        passed = avg >= PASS_THRESHOLD
        if not passed:
            all_pass = False
        mark = "✓" if passed else "✗"
        print(f"{NAMES[key]}  {avg:.2f}   {mark}")
    print(f"{'─'*50}")
    print(f"{'PASS' if all_pass else 'FAIL'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval", choices=["class", "zone", "tool", "html"], help="Run one eval only")
    parser.add_argument("--case", type=int, help="Run one case by index (0-9)")
    args = parser.parse_args()

    asyncio.run(main(eval_filter=args.eval, case_index=args.case))
