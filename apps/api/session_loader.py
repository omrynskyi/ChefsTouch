from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from supabase import Client

from models import ConversationTurn, Recipe, RecipeStep, SessionContext

CONVERSATION_MAX_TURNS = 20


class SessionNotFoundError(Exception):
    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session not found: {session_id}")
        self.session_id = session_id


class SessionLoader:
    def __init__(self, client: Client) -> None:
        self._client = client

    def load(self, session_id: str) -> SessionContext:
        result = (
            self._client.table("sessions")
            .select("*")
            .eq("session_id", session_id)
            .execute()
        )

        if not result.data:
            raise SessionNotFoundError(session_id)

        row: dict[str, Any] = result.data[0]

        conversation = _parse_conversation(row.get("conversation") or [])
        conversation = conversation[-CONVERSATION_MAX_TURNS:]

        active_recipe = _fetch_recipe(self._client, row.get("active_recipe_id"))

        return SessionContext(
            session_id=session_id,
            conversation=conversation,
            active_recipe=active_recipe,
            current_step=row.get("current_step"),
            canvas_state=row.get("canvas_state") or {},
            preferences=row.get("preferences") or {},
        )

    def save(self, context: SessionContext) -> None:
        trimmed = context.conversation[-CONVERSATION_MAX_TURNS:]

        payload: dict[str, Any] = {
            "last_active": datetime.now(timezone.utc).isoformat(),
            "conversation": [_turn_to_dict(t) for t in trimmed],
            "active_recipe_id": (
                str(context.active_recipe.recipe_id) if context.active_recipe else None
            ),
            "current_step": context.current_step,
            "canvas_state": context.canvas_state,
            "preferences": context.preferences,
        }

        self._client.table("sessions").update(payload).eq(
            "session_id", context.session_id
        ).execute()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_conversation(raw: list[Any]) -> list[ConversationTurn]:
    turns = []
    for item in raw:
        if isinstance(item, str):
            item = json.loads(item)
        turns.append(ConversationTurn(**item))
    return turns


def _fetch_recipe(client: Client, recipe_id: Optional[str]) -> Optional[Recipe]:
    if not recipe_id:
        return None
    result = (
        client.table("recipes")
        .select("*")
        .eq("recipe_id", recipe_id)
        .execute()
    )
    if not result.data:
        return None
    row = result.data[0]
    steps = [RecipeStep(**s) for s in (row.get("steps") or [])]
    return Recipe(
        recipe_id=row["recipe_id"],
        title=row["title"],
        description=row["description"],
        duration_minutes=row["duration_minutes"],
        servings=row["servings"],
        tags=row.get("tags") or [],
        steps=steps,
        source=row.get("source", "generated"),
        created_at=row.get("created_at", datetime.now(timezone.utc)),
    )


def _turn_to_dict(turn: ConversationTurn) -> dict[str, Any]:
    return {
        "role": turn.role,
        "content": turn.content,
        "timestamp": turn.timestamp.isoformat(),
    }
