from __future__ import annotations

from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel


PositionToken = Literal[
    "center",
    "top",
    "bottom",
    "left",
    "right",
    "corner-tl",
    "corner-tr",
    "corner-bl",
    "corner-br",
]


class StepViewData(BaseModel):
    step_number: int
    total_steps: int
    recipe: str
    instruction: str
    tip: Optional[str] = None
    tags: Optional[List[str]] = None
    action: Optional[str] = None


class ProgressBarData(BaseModel):
    current: int
    total: int


class TimerData(BaseModel):
    duration_seconds: int
    label: str
    auto_start: bool


class AlertData(BaseModel):
    text: str
    urgent: Optional[bool] = None


class RecipeGridData(BaseModel):
    pass


class RecipeOptionData(BaseModel):
    title: str
    description: Optional[str] = None
    duration: Optional[str] = None
    tags: Optional[List[str]] = None
    action: str


class IngredientItem(BaseModel):
    name: str
    qty: str


class IngredientListData(BaseModel):
    items: List[IngredientItem]


class CameraData(BaseModel):
    prompt: str


class SuggestionData(BaseModel):
    heading: str
    body: str
    action_label: Optional[str] = None


class TextCardData(BaseModel):
    body: str
    input_placeholder: Optional[str] = None
    submit_label: Optional[str] = None
    input_action_prefix: Optional[str] = None


ComponentType = Literal[
    "step-view",
    "progress-bar",
    "timer",
    "alert",
    "recipe-grid",
    "recipe-option",
    "ingredient-list",
    "camera",
    "suggestion",
    "text-card",
]


ComponentData = Union[
    StepViewData,
    ProgressBarData,
    TimerData,
    AlertData,
    RecipeGridData,
    RecipeOptionData,
    IngredientListData,
    CameraData,
    SuggestionData,
    TextCardData,
]


class CanvasComponent(BaseModel):
    id: str
    type: ComponentType
    data: Optional[ComponentData] = None
    position: Optional[PositionToken] = None
    focused: bool = False
    skeleton: bool = False
    parent: Optional[str] = None


class AddOperation(BaseModel):
    op: Literal["add"] = "add"
    id: str
    type: ComponentType
    data: ComponentData
    position: Optional[PositionToken] = None
    parent: Optional[str] = None


class UpdateOperation(BaseModel):
    op: Literal["update"] = "update"
    id: str
    data: Dict[str, object]


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


class SkeletonOperation(BaseModel):
    op: Literal["skeleton"] = "skeleton"
    id: str
    type: ComponentType


class StageOperation(BaseModel):
    op: Literal["stage"] = "stage"
    id: str
    type: ComponentType
    data: ComponentData
    position: Optional[PositionToken] = None
    parent: Optional[str] = None


class CommitOperation(BaseModel):
    op: Literal["commit"] = "commit"
    id: str


class SwapOperation(BaseModel):
    op: Literal["swap"] = "swap"
    id: str
    out_id: str


class ClearStagedOperation(BaseModel):
    op: Literal["clear_staged"] = "clear_staged"


CanvasOperation = Union[
    AddOperation,
    UpdateOperation,
    RemoveOperation,
    FocusOperation,
    MoveOperation,
    SkeletonOperation,
    StageOperation,
    CommitOperation,
    SwapOperation,
    ClearStagedOperation,
]


class InitMessage(BaseModel):
    type: Literal["init"] = "init"
    session_id: Optional[str] = None


class SessionReadyMessage(BaseModel):
    type: Literal["session_ready"] = "session_ready"
    session_id: str


class AudioChunkMessage(BaseModel):
    type: Literal["audio_chunk"] = "audio_chunk"
    data: str


class TranscriptMessage(BaseModel):
    type: Literal["transcript"] = "transcript"
    text: str


class CameraFramesMessage(BaseModel):
    type: Literal["camera_frames"] = "camera_frames"
    frames: List[str]


class CameraErrorMessage(BaseModel):
    type: Literal["camera_error"] = "camera_error"


class TtsAudioMessage(BaseModel):
    type: Literal["tts_audio"] = "tts_audio"
    data: str


class CanvasOpsMessage(BaseModel):
    type: Literal["canvas_ops"] = "canvas_ops"
    operations: List[CanvasOperation]


class ActionMessage(BaseModel):
    type: Literal["action"] = "action"
    action: str


class SuggestionDismissedMessage(BaseModel):
    type: Literal["suggestion_dismissed"] = "suggestion_dismissed"


class TtsTextMessage(BaseModel):
    type: Literal["tts_text"] = "tts_text"
    text: str


class AgentStatusMessage(BaseModel):
    type: Literal["agent_status"] = "agent_status"
    text: str
