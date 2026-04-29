"""
Interactive demo for agent-canvas.

Uses:
  - LM Studio (local LLM, http://localhost:1234/v1) for generation
  - Supabase pgvector for CSS class retrieval
  - all-MiniLM-L6-v2 (local) for query embeddings

Usage:
    python3 demo.py
    python3 demo.py --verbose     # also print retrieved CSS classes
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

env_path = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

from langchain_openai import ChatOpenAI
from supabase import create_client

from agent_canvas import build_canvas_render_graph, SupabaseCSSRetriever
from agent_canvas.embeddings import LocalEmbeddings
from preview import render


def get_env(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        print(f"Error: {key} not set in .env")
        sys.exit(1)
    return val


def build_graph(verbose: bool):
    client = create_client(get_env("SUPABASE_URL"), get_env("SUPABASE_SERVICE_ROLE_KEY"))

    embeddings = LocalEmbeddings()
    retriever = SupabaseCSSRetriever(client=client, embeddings=embeddings, k=10, match_threshold=0.0)

    # LM Studio — OpenAI-compatible local server
    llm = ChatOpenAI(
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",           # LM Studio ignores the key
        model="google/gemma-4-26b-a4b",
        temperature=0,
    )

    if verbose:
        original = retriever.ainvoke
        async def verbose_retrieve(query, **kwargs):
            docs = await original(query, **kwargs)
            print(f"  \033[90m  search: \"{query}\" → {len(docs)} classes\033[0m")
            for d in docs[:5]:
                name = d.metadata.get("name", "?")
                sim = d.metadata.get("similarity", 0)
                print(f"  \033[90m    {sim:.2f}  {name}\033[0m")
            return docs
        retriever.ainvoke = verbose_retrieve

    return build_canvas_render_graph(llm=llm, retriever=retriever), retriever


async def run_repl(verbose: bool, debug: bool = False) -> None:
    print("Building graph...")
    graph, retriever = build_graph(verbose)

    if debug:
        print("\nDebug: testing retriever with 'timer countdown floating'...")
        await retriever.debug("timer countdown floating")
        print()

    canvas_state: dict = {}
    context = "demo session"


    print("\n\033[1magent-canvas demo\033[0m")
    print("Type an intent and press Enter. Type 'reset' to clear canvas, 'quit' to exit.\n")

    while True:
        try:
            intent = input("\033[32mintent>\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not intent:
            continue
        if intent.lower() == "quit":
            break
        if intent.lower() == "reset":
            canvas_state = {}
            render(canvas_state)
            print("Canvas cleared.")
            continue

        if verbose:
            print()
        result = await graph.ainvoke({
            "intent": intent,
            "canvas_state": canvas_state,
            "context": context,
        })

        ops = result["ops"]
        errors = result["errors"]

        if errors:
            print(f"\n\033[31mErrors:\033[0m")
            for e in errors:
                print(f"  {e}")

        if ops:
            print(f"\n\033[33mOps ({len(ops)}):\033[0m")
            print(json.dumps(ops, indent=2))

            for op in ops:
                oid = op.get("id")
                if op["op"] == "add":
                    canvas_state[oid] = {"id": oid, "html": op.get("html", ""), "zone": _extract_zone(op.get("html", ""))}
                elif op["op"] == "update":
                    if oid in canvas_state:
                        canvas_state[oid]["html"] = op.get("html", "")
                elif op["op"] == "remove":
                    canvas_state.pop(oid, None)
                elif op["op"] == "move":
                    if oid in canvas_state:
                        canvas_state[oid]["zone"] = op.get("zone")
        else:
            print("  (no ops returned)")

        render(canvas_state)
        print()


def _extract_zone(html: str) -> str:
    import re
    m = re.search(r'zone="([^"]+)"', html)
    return m.group(1) if m else "unknown"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true", help="Show retrieved CSS classes per turn")
    parser.add_argument("--debug", action="store_true", help="Run a test retrieval query on startup")
    args = parser.parse_args()

    asyncio.run(run_repl(verbose=args.verbose, debug=args.debug))
