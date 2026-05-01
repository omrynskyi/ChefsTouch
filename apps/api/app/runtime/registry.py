from __future__ import annotations

from typing import Dict, Optional

from .state import LiveTurnState, SessionRuntimeState, ToolRunState, utc_now


class RuntimeRegistry:
    def __init__(self) -> None:
        self._sessions: Dict[str, SessionRuntimeState] = {}

    def get_or_create(self, session_id: str) -> SessionRuntimeState:
        state = self._sessions.get(session_id)
        if state is None:
            state = SessionRuntimeState(session_id=session_id)
            self._sessions[session_id] = state
        return state

    def begin_turn(self, session_id: str, turn_id: str, source: str) -> LiveTurnState:
        state = self.get_or_create(session_id)
        state.active_generation_id += 1
        turn = LiveTurnState(
            turn_id=turn_id,
            generation_id=state.active_generation_id,
            source=source,
        )
        state.active_turn_id = turn.turn_id
        state.current_turn = turn
        state.speech_state.cancelled = False
        state.speech_state.active = False
        state.speech_state.message_id = None
        state.active_tools.clear()
        return turn

    def is_active_generation(self, session_id: str, generation_id: int) -> bool:
        return self.get_or_create(session_id).active_generation_id == generation_id

    def mark_turn_running(self, session_id: str, generation_id: int) -> None:
        state = self.get_or_create(session_id)
        if state.current_turn and state.current_turn.generation_id == generation_id:
            state.current_turn.status = "running"

    def complete_turn(self, session_id: str, generation_id: int) -> None:
        state = self.get_or_create(session_id)
        if state.current_turn and state.current_turn.generation_id == generation_id:
            state.current_turn.status = "completed"
            state.speech_state.active = False

    def fail_turn(self, session_id: str, generation_id: int) -> None:
        state = self.get_or_create(session_id)
        if state.current_turn and state.current_turn.generation_id == generation_id:
            state.current_turn.status = "failed"
            state.speech_state.active = False

    def cancel_active_turn(self, session_id: str) -> Optional[LiveTurnState]:
        state = self.get_or_create(session_id)
        turn = state.current_turn
        if turn is None:
            return None
        cancelled_generation_id = turn.generation_id
        state.active_generation_id += 1
        turn.status = "cancelled"
        state.speech_state.active = False
        state.speech_state.cancelled = True
        state.active_tools.clear()
        return LiveTurnState(
            turn_id=turn.turn_id,
            generation_id=cancelled_generation_id,
            source=turn.source,
            status="cancelled",
            started_at=turn.started_at,
            final_transcript=turn.final_transcript,
            partial_transcript=turn.partial_transcript,
        )

    def set_speech_message(self, session_id: str, message_id: str, text: str) -> None:
        state = self.get_or_create(session_id)
        state.speech_state.message_id = message_id
        state.speech_state.active = True
        state.speech_state.cancelled = False
        state.speech_state.committed_text = text
        state.last_committed_assistant_text = text

    def cancel_speech(self, session_id: str) -> None:
        state = self.get_or_create(session_id)
        state.speech_state.active = False
        state.speech_state.cancelled = True

    def record_tool_started(
        self, session_id: str, tool_call_id: str, tool_name: str
    ) -> ToolRunState:
        state = self.get_or_create(session_id)
        tool = ToolRunState(tool_call_id=tool_call_id, tool_name=tool_name)
        state.active_tools[tool_call_id] = tool
        return tool

    def record_tool_finished(self, session_id: str, tool_call_id: str, failed: bool = False) -> None:
        state = self.get_or_create(session_id)
        tool = state.active_tools.get(tool_call_id)
        if tool is None:
            return
        tool.status = "failed" if failed else "finished"
        tool.finished_at = utc_now()
        state.active_tools.pop(tool_call_id, None)
