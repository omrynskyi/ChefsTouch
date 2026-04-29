"""
Seed script: embeds all CSS class entries and upserts them into design_snippets.

Uses all-MiniLM-L6-v2 (local, no API key). Model downloads ~80MB on first run.

Reads SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from .env at the repo root.

Usage:
    python3 seed_css.py              # seed default entries
    python3 seed_css.py --clear      # wipe table first, then seed
    python3 seed_css.py --count      # print current row count and exit
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

env_path = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

from supabase import create_client

from agent_canvas import DEFAULT_CSS_ENTRIES, seed_design_snippets
from agent_canvas.embeddings import LocalEmbeddings


def get_env(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        print(f"Error: {key} is not set. Add it to .env or export it.")
        sys.exit(1)
    return val


async def main(clear: bool = False, count_only: bool = False) -> None:
    client = create_client(
        get_env("SUPABASE_URL"),
        get_env("SUPABASE_SERVICE_ROLE_KEY"),
    )

    if count_only:
        result = client.table("design_snippets").select("id", count="exact").execute()
        print(f"design_snippets: {result.count} rows")
        return

    print("Loading all-MiniLM-L6-v2 (downloads ~80MB on first run)...")
    embeddings = LocalEmbeddings()

    print(f"Seeding {len(DEFAULT_CSS_ENTRIES)} CSS entries...")
    if clear:
        print("  --clear: deleting existing rows first")

    n = await seed_design_snippets(
        client=client,
        embeddings=embeddings,
        entries=DEFAULT_CSS_ENTRIES,
        clear=clear,
    )
    print(f"Done. {n} rows upserted.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true", help="Delete all rows before seeding")
    parser.add_argument("--count", action="store_true", help="Print row count and exit")
    args = parser.parse_args()

    asyncio.run(main(clear=args.clear, count_only=args.count))
