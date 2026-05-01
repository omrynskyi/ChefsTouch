// ─── Position tokens ────────────────────────────────────────────────────────

export type PositionToken =
  | "center"
  | "top"
  | "bottom"
  | "left"
  | "right"
  | "corner-tl"
  | "corner-tr"
  | "corner-bl"
  | "corner-br";

// ─── Component data schemas ──────────────────────────────────────────────────

export interface StepViewData {
  step_number: number;
  total_steps: number;
  recipe: string;
  instruction: string;
  tip?: string | null;
  tags?: string[];
  action?: string;
}

export interface ProgressBarData {
  current: number;
  total: number;
}

export interface TimerData {
  duration_seconds: number;
  label: string;
  auto_start: boolean;
}

export interface AlertData {
  text: string;
  urgent?: boolean;
}

export interface RecipeGridData {
  // no fields — children are recipe-option ops with parent referencing this id
}

export interface RecipeOptionData {
  title: string;
  description?: string;
  duration?: string;
  tags?: string[];
  action: string;
}

export interface IngredientListData {
  items: { name: string; qty: string }[];
}

export interface CameraData {
  prompt: string;
}

export interface SuggestionData {
  heading: string;
  body: string;
  action_label?: string | null;
}

export interface TextCardData {
  body: string;
  input_placeholder?: string;
  submit_label?: string;
  input_action_prefix?: string;
}

export interface AssistantMessageData {
  text: string;
}

// ─── Component types ─────────────────────────────────────────────────────────

export type ComponentType =
  | "step-view"
  | "progress-bar"
  | "timer"
  | "alert"
  | "recipe-grid"
  | "recipe-option"
  | "ingredient-list"
  | "camera"
  | "suggestion"
  | "text-card"
  | "assistant-message";

export type ComponentDataMap = {
  "step-view": StepViewData;
  "progress-bar": ProgressBarData;
  timer: TimerData;
  alert: AlertData;
  "recipe-grid": RecipeGridData;
  "recipe-option": RecipeOptionData;
  "ingredient-list": IngredientListData;
  camera: CameraData;
  suggestion: SuggestionData;
  "text-card": TextCardData;
  "assistant-message": AssistantMessageData;
};

export type ComponentData = ComponentDataMap[ComponentType];

export interface CanvasComponent<T extends ComponentType = ComponentType> {
  id: string;
  type: T;
  data: ComponentDataMap[T] | null; // null when skeleton: true
  position?: PositionToken;
  focused?: boolean;
  skeleton?: boolean;
  /** only set for recipe-option — references the parent recipe-grid id */
  parent?: string;
}

export type CanvasMap = Map<string, CanvasComponent>;

export interface CanvasState {
  active: CanvasMap;
  staged: CanvasMap;
}

// ─── Canvas operations ───────────────────────────────────────────────────────

export interface AddOperation<T extends ComponentType = ComponentType> {
  op: "add";
  id: string;
  type: T;
  data: ComponentDataMap[T];
  position?: PositionToken;
  parent?: string;
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

/** Sent by the backend as soon as type+id are parsed from the LLM stream.
 *  The client renders a skeleton placeholder immediately, before data arrives. */
export interface SkeletonOperation {
  op: "skeleton";
  id: string;
  type: ComponentType;
}

export interface StageOperation<T extends ComponentType = ComponentType> {
  op: "stage";
  id: string;
  type: T;
  data: ComponentDataMap[T];
  position?: PositionToken;
  parent?: string;
}

export interface CommitOperation {
  op: "commit";
  id: string;
}

export interface SwapOperation {
  op: "swap";
  id: string;
  out_id: string;
}

export interface ClearStagedOperation {
  op: "clear_staged";
}

export type CanvasOperation =
  | AddOperation
  | UpdateOperation
  | RemoveOperation
  | FocusOperation
  | MoveOperation
  | SkeletonOperation
  | StageOperation
  | CommitOperation
  | SwapOperation
  | ClearStagedOperation;

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

export interface ActionMessage {
  type: "action";
  action: string;
}

export interface SuggestionDismissedMessage {
  type: "suggestion_dismissed";
}

export type ClientMessage =
  | InitMessage
  | AudioChunkMessage
  | CameraFramesMessage
  | CameraErrorMessage
  | ActionMessage
  | SuggestionDismissedMessage;

export interface TtsTextMessage {
  type: "tts_text";
  text: string;
}

/** Streamed status updates from the main orchestrator. Empty text = clear. */
export interface AgentStatusMessage {
  type: "agent_status";
  text: string;
}

export type ServerMessage =
  | SessionReadyMessage
  | TranscriptMessage
  | TtsAudioMessage
  | CanvasOpsMessage
  | TtsTextMessage
  | AgentStatusMessage;
