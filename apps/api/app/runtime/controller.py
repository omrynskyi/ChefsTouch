from __future__ import annotations

from dataclasses import dataclass

from apps.api.app.runtime.registry import RuntimeRegistry


@dataclass(frozen=True)
class QueuedAction:
    action: str
    turn_id: str
    generation_id: int
    source: str = "websocket"


class TurnController:
    def __init__(self, registry: RuntimeRegistry) -> None:
        self._registry = registry

    def handle_action(self, session_id: str, action: str, turn_id: str, source: str = "websocket") -> QueuedAction:
        turn = self._registry.begin_turn(session_id, turn_id, source)
        return QueuedAction(
            action=action,
            turn_id=turn.turn_id,
            generation_id=turn.generation_id,
            source=source,
        )

    def handle_interrupt(self, session_id: str) -> tuple[str, int, int] | None:
        cancelled = self._registry.cancel_active_turn(session_id)
        if cancelled is None:
            return None
        active_state = self._registry.get_or_create(session_id)
        return (
            cancelled.turn_id,
            active_state.active_generation_id,
            cancelled.generation_id,
        )
