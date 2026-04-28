from __future__ import annotations

from typing import Literal, Union
from pydantic import BaseModel


# ─── Position tokens ──────────────────────────────────────────────────────────

PositionToken = Literal[
    "top", "bottom", "left", "right", "center",
    "bottom-right", "bottom-left", "top-right", "top-left",
]

# ─── Component data schemas ───────────────────────────────────────────────────

class RecipeCardData(BaseModel):
    title: str
    description: str
    duration_minutes: int
    servings: int
    tags: list[str]


class StepViewData(BaseModel):
    step_number: int
    total_steps: int
    instruction: str
    tip: str | None = None


class TimerData(BaseModel):
    duration_seconds: int
    label: str
    auto_start: bool


class CameraData(BaseModel):
    prompt: str


class SuggestionData(BaseModel):
    heading: str
    body: str
    action_label: str | None = None


class TextCardData(BaseModel):
    body: str


ComponentData = Union[
    RecipeCardData, StepViewData, TimerData,
    CameraData, SuggestionData, TextCardData,
]

ComponentType = Literal[
    "recipe-card", "step-view", "timer", "camera", "suggestion", "text-card"
]

# ─── Canvas component ─────────────────────────────────────────────────────────

class CanvasComponent(BaseModel):
    id: str
    type: ComponentType
    data: ComponentData
    position: PositionToken | None = None
    focused: bool = False

# ─── Canvas operations ────────────────────────────────────────────────────────

class AddOperation(BaseModel):
    op: Literal["add"] = "add"
    id: str
    type: ComponentType
    data: ComponentData
    position: PositionToken | None = None


class UpdateOperation(BaseModel):
    op: Literal["update"] = "update"
    id: str
    data: dict  # Partial component data — validated by the dispatcher


class RemoveOperation(BaseModel):
    op: Literal["remove"] = "remove"
    id: str


class FocusOperation(BaseModel):
    op: Literal["focus"] = "focus"
    id: str


class MoveOperation(BaseModel):
    op: Literal["move"] = "move"
    id: str
    position: PositionToken


CanvasOperation = Union[
    AddOperation, UpdateOperation, RemoveOperation, FocusOperation, MoveOperation
]

# ─── WebSocket message types ──────────────────────────────────────────────────

class InitMessage(BaseModel):
    type: Literal["init"] = "init"
    session_id: str | None = None


class SessionReadyMessage(BaseModel):
    type: Literal["session_ready"] = "session_ready"
    session_id: str


class AudioChunkMessage(BaseModel):
    type: Literal["audio_chunk"] = "audio_chunk"
    data: str  # base64


class TranscriptMessage(BaseModel):
    type: Literal["transcript"] = "transcript"
    text: str


class CameraFramesMessage(BaseModel):
    type: Literal["camera_frames"] = "camera_frames"
    frames: list[str]  # base64 JPEG


class CameraErrorMessage(BaseModel):
    type: Literal["camera_error"] = "camera_error"


class TtsAudioMessage(BaseModel):
    type: Literal["tts_audio"] = "tts_audio"
    data: str  # base64 mp3


class CanvasOpsMessage(BaseModel):
    type: Literal["canvas_ops"] = "canvas_ops"
    operations: list[CanvasOperation]


class SuggestionDismissedMessage(BaseModel):
    type: Literal["suggestion_dismissed"] = "suggestion_dismissed"
