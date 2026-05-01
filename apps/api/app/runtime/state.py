from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Literal, Optional


TurnStatus = Literal["pending", "running", "completed", "cancelled", "failed"]
ToolStatus = Literal["started", "finished", "failed"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class LiveTurnState:
    turn_id: str
    generation_id: int
    source: str
    status: TurnStatus = "pending"
    started_at: datetime = field(default_factory=utc_now)
    final_transcript: Optional[str] = None
    partial_transcript: Optional[str] = None


@dataclass
class SpeechState:
    message_id: Optional[str] = None
    active: bool = False
    committed_text: str = ""
    cancelled: bool = False


@dataclass
class ToolRunState:
    tool_call_id: str
    tool_name: str
    status: ToolStatus = "started"
    started_at: datetime = field(default_factory=utc_now)
    finished_at: Optional[datetime] = None


@dataclass
class SessionRuntimeState:
    session_id: str
    active_generation_id: int = 0
    active_turn_id: Optional[str] = None
    current_turn: Optional[LiveTurnState] = None
    speech_state: SpeechState = field(default_factory=SpeechState)
    active_tools: Dict[str, ToolRunState] = field(default_factory=dict)
    last_committed_assistant_text: Optional[str] = None
