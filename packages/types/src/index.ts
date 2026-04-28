// ─── Position tokens ────────────────────────────────────────────────────────

export type PositionToken =
  | "top"
  | "bottom"
  | "left"
  | "right"
  | "center"
  | "bottom-right"
  | "bottom-left"
  | "top-right"
  | "top-left";

// ─── Component data schemas ──────────────────────────────────────────────────

export interface RecipeCardData {
  title: string;
  description: string;
  duration_minutes: number;
  servings: number;
  tags: string[];
}

export interface StepViewData {
  step_number: number;
  total_steps: number;
  instruction: string;
  tip: string | null;
}

export interface TimerData {
  duration_seconds: number;
  label: string;
  auto_start: boolean;
}

export interface CameraData {
  prompt: string;
}

export interface SuggestionData {
  heading: string;
  body: string;
  action_label: string | null;
}

export interface TextCardData {
  body: string;
}

// ─── Component types ─────────────────────────────────────────────────────────

export type ComponentType =
  | "recipe-card"
  | "step-view"
  | "timer"
  | "camera"
  | "suggestion"
  | "text-card";

export type ComponentDataMap = {
  "recipe-card": RecipeCardData;
  "step-view": StepViewData;
  timer: TimerData;
  camera: CameraData;
  suggestion: SuggestionData;
  "text-card": TextCardData;
};

export type ComponentData = ComponentDataMap[ComponentType];

export interface CanvasComponent<T extends ComponentType = ComponentType> {
  id: string;
  type: T;
  data: ComponentDataMap[T];
  position?: PositionToken;
  focused?: boolean;
}

export type CanvasState = Map<string, CanvasComponent>;

// ─── Canvas operations ───────────────────────────────────────────────────────

export interface AddOperation<T extends ComponentType = ComponentType> {
  op: "add";
  id: string;
  type: T;
  data: ComponentDataMap[T];
  position?: PositionToken;
}

export interface UpdateOperation {
  op: "update";
  id: string;
  data: Partial<ComponentData>;
}

export interface RemoveOperation {
  op: "remove";
  id: string;
}

export interface FocusOperation {
  op: "focus";
  id: string;
}

export interface MoveOperation {
  op: "move";
  id: string;
  position: PositionToken;
}

export type CanvasOperation =
  | AddOperation
  | UpdateOperation
  | RemoveOperation
  | FocusOperation
  | MoveOperation;

export type OperationType = CanvasOperation["op"];

// ─── WebSocket message types ─────────────────────────────────────────────────

export interface InitMessage {
  type: "init";
  session_id: string | null;
}

export interface SessionReadyMessage {
  type: "session_ready";
  session_id: string;
}

export interface AudioChunkMessage {
  type: "audio_chunk";
  data: string; // base64
}

export interface TranscriptMessage {
  type: "transcript";
  text: string;
}

export interface CameraFramesMessage {
  type: "camera_frames";
  frames: string[]; // base64 JPEG
}

export interface CameraErrorMessage {
  type: "camera_error";
}

export interface TtsAudioMessage {
  type: "tts_audio";
  data: string; // base64 mp3
}

export interface CanvasOpsMessage {
  type: "canvas_ops";
  operations: CanvasOperation[];
}

export interface SuggestionDismissedMessage {
  type: "suggestion_dismissed";
}

export type ClientMessage =
  | InitMessage
  | AudioChunkMessage
  | CameraFramesMessage
  | CameraErrorMessage
  | SuggestionDismissedMessage;

export type ServerMessage =
  | SessionReadyMessage
  | TranscriptMessage
  | TtsAudioMessage
  | CanvasOpsMessage;
