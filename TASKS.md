# AI Cooking Assistant — Task Breakdown

**Version:** 0.2  
**Author:** Oleg Mrynskyi  
**Status:** Active  
**Last Updated:** April 2026

---

## How to Read This Document

Tasks are organized into epics. Each epic maps to a PRD section. Tasks within an epic are sequenced — later tasks depend on earlier ones within the same epic. Cross-epic dependencies are called out explicitly.

Priority levels: `P0` (blocks everything), `P1` (core v1 feature), `P2` (important but not blocking), `P3` (nice to have).

Each task includes acceptance criteria, eval requirements where applicable, and CI/CD hooks.

---

## Epic 0 — Project Foundation

### T-001 — Monorepo and project scaffolding ✅
**Priority:** P0  
**Estimate:** 0.5 day

Set up a monorepo with two workspaces: `apps/web` (React frontend) and `apps/api` (FastAPI backend). Add shared `packages/types` for shared TypeScript/Python type definitions including canvas operation schemas.

**Acceptance Criteria:**
- [x] `apps/web` runs with `npm run dev` and renders a blank page
- [x] `apps/api` runs with `uvicorn` and returns `{"status": "ok"}` from `GET /health`
- [x] `packages/types` exports canvas operation types consumable by both workspaces
- [x] Root `Makefile` has `make dev` that starts both services concurrently
- [x] `.env.example` documents all required environment variables

**CI/CD:**
- GitHub Actions workflow triggers on all PRs to `main`
- Runs `npm install` and `pip install -r requirements.txt` to verify dependency resolution
- Health check smoke test: `curl /health` must return 200

---

### T-002 — Supabase schema and migrations ✅
**Priority:** P0  
**Estimate:** 0.5 day  
**Depends on:** T-001

Create Supabase project. Write SQL migrations for `sessions` and `recipes` tables as defined in PRD section 6. Enable `pgvector` extension for recipe embeddings.

**Acceptance Criteria:**
- [x] Migration runs cleanly against a fresh Supabase project via `supabase db push`
- [x] `sessions` table has all fields from PRD 6.1 with correct types and constraints
- [x] `recipes` table has all fields from PRD 6.2 including `embedding vector(1536)`
- [x] Supabase client initialized in backend with typed models via SQLAlchemy or equivalent
- [x] A seed script populates 5 sample recipes with embeddings for local dev

**CI/CD:**
- Migration lint runs on PR: check for destructive operations on `main` branch
- Seed script runs in test environment before integration tests

---

### T-003 — WebSocket connection foundation ✅
**Priority:** P0  
**Estimate:** 1 day  
**Depends on:** T-001

Establish a persistent WebSocket connection between the React frontend and FastAPI backend. The connection should survive reconnects and carry a session ID from the first message.

**Acceptance Criteria:**
- [x] Frontend connects on page load and reconnects automatically on disconnect (exponential backoff, max 5 retries)
- [x] First message from client sends `{ "type": "init", "session_id": "<uuid or null>" }`
- [x] Backend creates a new session in DB if `session_id` is null, otherwise loads existing
- [x] Backend confirms with `{ "type": "session_ready", "session_id": "<uuid>" }`
- [x] Session ID is persisted in `localStorage` on the client
- [x] Connection status is exposed as a React context (connected / reconnecting / failed)

**CI/CD:**
- Integration test: WebSocket connect, send init, assert session_ready within 2s
- Test both new session creation and session resumption flows

---

## Epic 1 — Canvas Engine

### T-010a — Update shared types package ✅
**Priority:** P0  
**Estimate:** 0.5 day  
**Depends on:** T-001

Update `packages/types/src/index.ts` to reflect the new typed component catalog.

**Acceptance Criteria:**
- [x] `PositionToken` updated to match design-system.css zone names: `center | top | bottom | left | right | corner-tl | corner-tr | corner-bl | corner-br`
- [x] `StepViewData` extended with `recipe: string`, `tags?: string[]`, `action?: string`
- [x] New interfaces added: `ProgressBarData`, `AlertData`, `RecipeGridData`, `RecipeOptionData`, `IngredientListData`
- [x] `ComponentType` union updated to include all 10 catalog types
- [x] `ComponentDataMap` updated to map new types to their data interfaces
- [x] `CanvasComponent` extended with `data: ... | null`, `skeleton?: boolean`, `parent?: string`
- [x] `SkeletonOperation { op: "skeleton"; id: string; type: ComponentType }` added to `CanvasOperation` union
- [x] `ActionMessage { type: "action"; action: string }` added to `ClientMessage` union
- [x] `npm run build --workspace=packages/types` passes
- [x] `npm run type-check --workspace=apps/web` passes

**CI/CD:**
- Type check runs on every PR

---

### T-010 — Canvas state manager ✅
**Priority:** P0  
**Estimate:** 1 day  
**Depends on:** T-003, T-010a

Build the client-side canvas state manager. This is a React context that maintains a map of `component_id -> component` and exposes a `dispatch(operation)` function. The WebSocket listener feeds operations into this dispatcher.

**Acceptance Criteria:**
- [x] Canvas state is a `Map<string, CanvasComponent>` maintained in a React context
- [x] `dispatch` handles all six operation types: `add`, `update`, `remove`, `focus`, `move`, `skeleton`
- [x] `add` with a duplicate ID **upserts** (shallow-merge update) — agent may safely re-add without tracking state perfectly
- [x] `skeleton` op type: stores `{ id, type, data: null, skeleton: true }` in state; subsequent `add` for same id replaces it with real data and sets `skeleton: false`
- [x] `remove` on a non-existent ID is a no-op
- [x] `update` shallow-merges the incoming `data` with existing component data
- [x] `focus` sets a `focused: true` flag on the target component and clears it on all others
- [x] All operations are validated against the `CanvasOperation` type before dispatch
- [x] Invalid operations are logged and discarded without crashing
- [x] `CanvasContext` batches ops arriving within 16ms into a single `requestAnimationFrame` flush — prevents intermediate re-renders during rapid streaming

**CI/CD:**
- [x] 25 unit tests covering all six operation types including skeleton, upsert, and batching
- 100% branch coverage required on the dispatcher

---

### T-010b — Double-buffered canvas state
**Priority:** P0  
**Estimate:** 0.5 day  
**Depends on:** T-010

Update `CanvasContext` and `reducer.ts` to support predictive staging.

**Acceptance Criteria:**
- [ ] State maintains two maps: `active` and `staged`
- [ ] New operation handlers: `stage` (adds to staged map), `commit` (moves from staged to active), `swap` (atomic remove + commit), `clear_staged` (wipes staged map)
- [ ] `update` and `remove` target both maps
- [ ] `Canvas.tsx` only renders components from the `active` map

---

### T-011 — Canvas renderer ✅
**Priority:** P0  
**Estimate:** 1.5 days  
**Depends on:** T-010, T-010a

Build `apps/web/src/canvas/Canvas.tsx` — a React component that reads canvas state and renders each component in its designated zone using the 9-zone CSS grid from `design-system.css`. No iframe. Components are typed React components, not raw HTML.

**Acceptance Criteria:**
- [x] Canvas is a CSS grid matching the 9-zone layout: `corner-tl / top / corner-tr / left / center / right / corner-bl / bottom / corner-br`
- [x] Each `CanvasComponent` in state renders its typed React component in its default zone (zone is determined by component type, not stored in state)
- [x] Default zone mapping: `step-view → center`, `progress-bar → top`, `timer → corner-br`, `suggestion → bottom`, `alert → top`, `recipe-grid → center`, `ingredient-list → center`, `camera → center`, `text-card → center`
- [x] `skeleton` components render `<Skeleton>` placeholder with shimmer animation in the correct zone
- [x] Idle state (empty canvas state map) renders a centered mic icon
- [x] Component mount/unmount animated via Framer Motion (opacity + y translate, 200ms)
- [x] `focused` components receive elevated visual treatment (stronger shadow or border)
- [x] Canvas is responsive and works at viewport widths 375px and above

**CI/CD:**
- Snapshot tests for each component type rendered from a fixture
- Visual regression test on idle state using Playwright screenshot comparison

---

### T-012 — Canvas component: recipe-grid + recipe-option ✅
**Priority:** P1  
**Estimate:** 0.75 day  
**Depends on:** T-011

Implement `RecipeGrid.tsx` and `RecipeOption.tsx`. `RecipeGrid` renders in the center zone; `RecipeOption` children are inserted into it as they stream in (via `parent` field in their canvas state entry).

**Data schema:** `RecipeOptionData { title: string; description?: string; duration?: string; tags?: string[]; action: string }`

**Acceptance Criteria:**
- [x] `RecipeGrid` renders children in center zone; options appear progressively as added with `parent` field
- [x] `RecipeOption` cards appear progressively as they are added to canvas state with `parent: "recipe-grid-id"`
- [x] Each option renders title, optional description, optional duration, optional tags
- [x] Tapping an option sends `{ type: "action", action: option.data.action }` over WebSocket
- [x] Missing optional fields render gracefully (no crashes, no empty space)
- [x] Component is keyboard accessible (button element)

**CI/CD:**
- Unit test: renders with 0, 1, and 3 options; renders with minimal data per option
- Accessibility audit: no critical axe violations

---

### T-013 — Canvas component: step-view ✅
**Priority:** P1  
**Estimate:** 0.5 day  
**Depends on:** T-011

**Data schema:** `StepViewData { step_number: number; total_steps: number; recipe: string; instruction: string; tip?: string; tags?: string[]; action?: string }`

**Acceptance Criteria:**
- [x] Renders `recipe · Step N of M` as a muted eyebrow label
- [x] Renders `instruction` as the primary large text
- [x] Renders `tip` in a visually distinct secondary style when present
- [x] Renders `tags` as pill badges when present
- [x] Renders a "Next step →" button when `action` is present; tapping sends `{ type: "action", action }` over WebSocket
- [x] Mini variant (`StepMini`) used as camera companion above center zone

**CI/CD:**
- Unit test: renders with full data, renders with minimal data (step_number, total_steps, instruction only)
- Snapshot test for step transition animation state

---

### T-013a — Canvas component: progress-bar ✅
**Priority:** P1  
**Estimate:** 0.25 day  
**Depends on:** T-011

**Data schema:** `ProgressBarData { current: number; total: number }`

**Acceptance Criteria:**
- [x] Renders in top zone as a compact card
- [x] Shows "Step N of M" label above a filled track
- [x] Fill width is `(current / total) * 100%` with terracotta accent color
- [x] Animates fill width transition on `update` op (400ms ease)

**CI/CD:**
- Unit test: renders at 0%, 50%, 100% fill; label text is correct

---

### T-013b — Canvas component: alert ✅
**Priority:** P1  
**Estimate:** 0.25 day  
**Depends on:** T-011

**Data schema:** `AlertData { text: string; urgent?: boolean }`

**Acceptance Criteria:**
- [x] Renders in top zone as a warning strip (companion below progress-bar, or standalone)
- [x] `urgent: true` uses terracotta-tinted background and accent text color
- [x] `urgent: false` (default) uses warm amber background
- [x] Dismissable via X button; dispatches `remove` op

**CI/CD:**
- Unit test: renders standard and urgent variants

---

### T-013c — Canvas component: ingredient-list ✅
**Priority:** P1  
**Estimate:** 0.25 day  
**Depends on:** T-011

**Data schema:** `IngredientListData { items: { name: string; qty: string }[] }`

**Acceptance Criteria:**
- [x] Renders in left zone as a scrollable card
- [x] Each row shows `name` left-aligned and `qty` right-aligned
- [x] Max-height 340px with visible scrollbar on overflow

**CI/CD:**
- Unit test: renders with 3 items, renders with 15 items (scroll case)

---

### T-014 — Canvas component: timer ✅
**Priority:** P1  
**Estimate:** 1 day  
**Depends on:** T-011

**Acceptance Criteria:**
- [x] Counts down from `duration_seconds` to zero
- [x] Starts automatically if `auto_start` is true
- [x] At zero, pulses visually and plays a soft audio cue
- [x] Can be paused and resumed by tapping
- [x] An `update` operation with a new `duration_seconds` resets the timer
- [x] Timer state survives a WebSocket reconnect (timer continues counting in frontend state)

**CI/CD:**
- Unit test: countdown logic, auto-start behavior, zero-state behavior
- Test that timer does not reset on unrelated canvas operations

---

### T-015 — Canvas component: camera ✅
**Priority:** P1  
**Estimate:** 1.5 days  
**Depends on:** T-011

**Acceptance Criteria:**
- [x] Requests camera permission on first render; handles denied permission gracefully with `camera_error` message to backend
- [x] Captures 3 frames at 500ms intervals automatically once rendered
- [x] Frames are encoded as base64 JPEG at 720p max and sent to backend via WebSocket message `{ "type": "camera_frames", "frames": [...] }`
- [x] After frames are sent, emits a local `remove` operation for itself (camera closes automatically)
- [x] If capture fails for any reason, sends `{ "type": "camera_error" }` to backend

**CI/CD:**
- Unit test: frame capture logic mocked with a fake MediaStream
- Test denied permission flow
- Test that camera always removes itself after capture regardless of success/failure

---

### T-016 — Canvas component: suggestion ✅
**Priority:** P1  
**Estimate:** 0.5 day  
**Depends on:** T-011

**Acceptance Criteria:**
- [x] Renders heading, body, and optional action label
- [x] Action label renders as a tappable button that sends `{ "type": "suggestion_dismissed" }` to backend
- [x] Dismissable by tapping the action label button

**CI/CD:**
- Unit test: renders with and without action label
- Test dismiss interaction

---

### T-017 — Canvas component: text-card ✅
**Priority:** P1  
**Estimate:** 0.25 day  
**Depends on:** T-011

**Acceptance Criteria:**
- [x] Renders body text in a clean readable style
- [x] Body text supports basic markdown (bold, italic) via a lightweight renderer
- [ ] Max 3 lines before truncating with a "tap to expand" affordance

**CI/CD:**
- Unit test: renders short text, long text, markdown formatting

---

## Epic 2 — Voice Pipeline

### T-020 — Audio capture in browser
**Priority:** P0  
**Estimate:** 1 day  
**Depends on:** T-003

Capture microphone audio in the browser using the MediaRecorder API. Stream audio chunks to the backend over WebSocket.

**Acceptance Criteria:**
- [ ] Microphone permission is requested once and its state is persisted
- [ ] Recording starts automatically when connection is established and no agent turn is in progress
- [ ] Audio is captured as WebM/Opus at 16kHz
- [ ] Chunks are sent every 250ms as `{ "type": "audio_chunk", "data": "<base64>" }`
- [ ] Recording pauses while the agent is speaking (TTS active) to prevent echo
- [ ] Visual mic indicator reflects state: listening, paused, processing

**CI/CD:**
- Unit test: audio state machine (listening, paused, processing) transitions
- Mock MediaRecorder in test environment

---

### T-021 — STT integration (backend)
**Priority:** P0  
**Estimate:** 1 day  
**Depends on:** T-020

Receive audio chunks on the backend, run STT, and produce a transcript. Initial implementation uses OpenAI Whisper API. The STT provider is abstracted behind an interface for future swapping.

**Acceptance Criteria:**
- [ ] `STTProvider` abstract class with a single `transcribe(audio_bytes) -> str` method
- [ ] `WhisperSTTProvider` implements it using OpenAI Whisper API
- [ ] Voice activity detection: only submit to Whisper when a pause is detected (300ms silence)
- [ ] Transcript is returned as `{ "type": "transcript", "text": "..." }` to the client for display
- [ ] Empty transcripts (silence) are discarded without triggering an agent turn
- [ ] Latency target: transcript available within 800ms of speech ending

**CI/CD:**
- Unit test: VAD logic, empty transcript discard
- Integration test with a pre-recorded audio fixture: transcript must match expected text with >90% word accuracy

---

### T-022 — TTS integration (backend)
**Priority:** P0  
**Estimate:** 0.5 day  
**Depends on:** T-021

Convert the agent's verbal response to audio and stream it to the frontend.

**Acceptance Criteria:**
- [ ] `TTSProvider` abstract class with `synthesize(text) -> audio_bytes` method
- [ ] `OpenAITTSProvider` implements it using OpenAI TTS via Responses API
- [ ] Audio is sent as `{ "type": "tts_audio", "data": "<base64 mp3>" }`
- [ ] Frontend plays audio immediately on receipt using Web Audio API
- [ ] Frontend sets recording state to `paused` while TTS audio is playing
- [ ] Recording resumes 300ms after audio playback ends

**CI/CD:**
- Unit test: TTS provider interface contract
- Integration test: send a short text, assert audio bytes returned within 1.5s

---

## Epic 3 — Agent Harness

### T-030 — Session context loader ✅
**Priority:** P0  
**Estimate:** 0.5 day  
**Depends on:** T-002, T-003

On every agent turn, load the full session context from Supabase and inject it into the agent request.

**Acceptance Criteria:**
- [x] `SessionLoader` reads session by ID from Supabase
- [x] Returns typed `SessionContext` object with conversation history, active recipe, current step, canvas state, and preferences
- [x] Conversation history is trimmed to last 20 turns to manage context window
- [x] After each agent turn, session is written back to Supabase with updated state
- [x] Write is atomic: if the agent turn fails, session state is not updated

**CI/CD:**
- Unit test: load, trim history, write back
- Integration test: session state persists correctly across two sequential turns

---

### T-031 — Main Assistant agent
**Priority:** P0  
**Estimate:** 2 days  
**Depends on:** T-030

Implement the Main Assistant as a LangGraph node. It receives session context and user input, calls sub-agents as tools via the OpenAI Responses API, and returns a `{ tts_text, canvas_ops }` response.

**Acceptance Criteria:**
- [ ] Main Assistant is a LangGraph `StateGraph` node
- [ ] System prompt enforces short, quirky, friend-like responses (max 2 sentences for TTS)
- [ ] Sub-agents (Recipe, Image Inference, Render) are registered as tools
- [ ] Main Assistant decides which tools to call based on user intent
- [ ] All tool calls use structured JSON input/output — no free text between agents
- [ ] Agent turn completes within 4 seconds for text-only turns
- [ ] Graceful degradation: if a sub-agent fails, Main Assistant responds with a fallback message rather than crashing

**CI/CD:**
- Unit test: mock tool calls, assert correct tools invoked for 5 canonical intents (recipe request, camera check, step navigation, mutation rejection, parallel task)
- Eval: see Eval section E-001

---

### T-032 — Recipe Agent
**Priority:** P1  
**Estimate:** 1.5 days  
**Depends on:** T-031, T-002

**Acceptance Criteria:**
- [ ] Accepts `{ intent: string, tags: string[], max_results: number }` as input
- [ ] Queries Supabase pgvector using cosine similarity on intent embedding
- [ ] Returns up to `max_results` recipes conforming to the `recipe-card` schema
- [ ] Falls back to LLM generation if vector search returns fewer than 2 results with similarity > 0.75
- [ ] Generated recipes are saved to the `recipes` table with `source: "generated"`
- [ ] Returns structured JSON only — no prose

**CI/CD:**
- Unit test: vector search mock, fallback trigger condition, output schema validation
- Integration test: query with "pasta" intent returns at least 1 result from seed data
- Eval: see Eval section E-002

---

### T-033 — Image Inference Agent
**Priority:** P1  
**Estimate:** 1 day  
**Depends on:** T-031

**Acceptance Criteria:**
- [ ] Accepts `{ frames: string[], context: string }` where `context` is the current recipe step
- [ ] Passes frames to vision-capable model (GPT-4o vision) alongside a structured analysis prompt
- [ ] Returns `{ observation: string, assessment: "ok" | "warning" | "error", suggested_action: string | null }`
- [ ] `suggested_action` is a short imperative string suitable for a new step-view ("Cook for 2 more minutes")
- [ ] If frames are unusable (blurry, dark), returns `assessment: "error"` with a descriptive observation
- [ ] Latency target: response within 2.5 seconds

**CI/CD:**
- Unit test: output schema validation, error handling for bad frames
- Integration test with 3 fixture images (correctly cooked, undercooked, unrecognizable): assert correct assessment for each
- Eval: see Eval section E-003

---

### T-034 — Render Agent ✅
**Priority:** P0  
**Estimate:** 1.5 days  
**Depends on:** T-010a

Rewrite render-agent to use the A2UI-style typed component catalog with JSONL streaming. No raw HTML, no vector search, no iframe.

**Acceptance Criteria:**
- [x] Accepts `{ intent: string, context: string, canvas_state: dict }` as input via `astream_events()`
- [x] LLM outputs **JSONL** (one JSON object per line) — no array brackets
- [x] Each line is a valid canvas op: `{ op, id, type, data }` for add; `{ op, id, data }` for update; `{ op, id }` for remove/focus
- [x] Agent only uses component types from the catalog: `step-view`, `progress-bar`, `timer`, `suggestion`, `alert`, `recipe-grid`, `recipe-option`, `ingredient-list`, `camera`, `text-card`
- [x] Agent receives a compact canvas state summary (`CURRENT CANVAS: - id (type): ...`) and emits `update` ops for existing IDs
- [x] System prompt encodes topological ordering rule: parents before children, most important first
- [x] `CanvasOp` schema validation: unknown `type` values and missing required `data` keys are caught and dropped
- [x] `recipe-option` ops include `parent` field referencing their `recipe-grid` id
- [x] `build_canvas_render_graph(llm)` provides a non-streaming `ainvoke()` wrapper for batch use and tests
- [x] Dropped LangGraph `StateGraph`, CSS vector search tool, bleach sanitizer, retriever arg

**CI/CD:**
- [x] 24 unit tests: healer, schema validation, astream_events integration, batch wrapper
- Eval: see Eval section E-004

---

### T-034a — JSONL Stream Healer ✅
**Priority:** P0  
**Estimate:** 1 day  
**Depends on:** T-034

Implement `render_agent/healer.py` — the streaming JSON parser that makes progressive rendering possible.

**Acceptance Criteria:**
- [x] `JSONStreamHealer.feed(chunk: str) → list[SkeletonEvent | ContentEvent]` processes token chunks as they arrive
- [x] `SkeletonEvent(id, component_type)` is emitted once per op when `"type":` and `"id":` are both visible in the partial buffer via regex — before the object is complete
- [x] `ContentEvent(op: dict)` is emitted when brace depth returns to 0 and `json.loads` succeeds
- [x] State machine correctly handles JSON strings containing `{`, `}`, `"`, and `\` escape sequences
- [x] Handles nested objects within `data` (e.g. `ingredient-list` items array with inner `{}`) correctly via depth tracking
- [x] `finalize() → list[ContentEvent]` attempts to parse remaining buffer at stream end as fallback
- [x] Duplicate `SkeletonEvent` for same id is suppressed (idempotent guard via `skeleton_emitted` set)
- [x] `line_buffer` resets after each `ContentEvent`; `\n` between objects at depth 0 also resets buffer

**CI/CD:**
- [x] 7 unit tests: complete object, skeleton timing, single-emit guard, multi-op JSONL, finalize fallback, malformed JSON, nested objects

---

### T-034b — Progressive JSON Parsing fix
**Priority:** P0  
**Estimate:** 0.5 day  
**Depends on:** T-034a

Upgrade `JSONStreamHealer` to emit partial content events as tokens arrive.

**Acceptance Criteria:**
- [ ] `JSONStreamHealer` uses a stack-based parser to repair incomplete JSON strings on every chunk
- [ ] Emits `PartialContentEvent(data: dict)` as fields arrive (e.g., partial `instruction` text)
- [ ] `ws_handler.py` sends `partial_update` messages to frontend
- [ ] Frontend `reducer.ts` merges partial data into state, triggering real-time re-renders

---

### T-034c — Predictive Staging Loop
**Priority:** P1  
**Estimate:** 1 day  
**Depends on:** T-031, T-034

Implement the background precomputation loop in the Orchestrator.

**Acceptance Criteria:**
- [ ] Orchestrator triggers an async task after each user-facing turn finishes
- [ ] Predictor (heuristic or LLM) identifies most likely next intent
- [ ] Render Agent receives a hidden prompt to generate UI into the staging area
- [ ] Agent emits `stage` operations; results are held in frontend `staged` map
- [ ] If user intent matches prediction, Orchestrator issues `commit` or `swap` instead of a full render turn

---

### T-034d — Render Agent context upgrade
**Priority:** P0  
**Estimate:** 0.25 day  
**Depends on:** T-034

Update Render Agent system prompt to handle exact JSON state and new operations.

**Acceptance Criteria:**
- [ ] System prompt receives exact JSON of `active` and `staged` canvas
- [ ] Prompt explicitly defines `update` as total replacement of nested objects
- [ ] Prompt includes documentation for `stage`, `commit`, `swap`, and `clear_staged`

---

### T-034e — FastAPI streaming wiring ✅
**Priority:** P0  
**Estimate:** 0.75 day  
**Depends on:** T-034, T-034a

Wire the streaming render agent into the FastAPI WebSocket handler so canvas ops reach the React app component-by-component as the LLM streams.

**Acceptance Criteria:**
- [x] `ws_handler.py` handles `{ "type": "action", "action": "..." }` client messages
- [x] On action: loads session via `SessionLoader`, builds context string from active recipe + step
- [x] Calls `astream_events(action, context, canvas_state, llm)` — `AsyncGenerator[SkeletonEvent | ContentEvent]`
- [x] Each `SkeletonEvent` immediately sends `{ "type": "canvas_ops", "operations": [{ "op": "skeleton", "id": ..., "type": ... }] }` over WebSocket
- [x] Each `ContentEvent` immediately sends `{ "type": "canvas_ops", "operations": [op] }` over WebSocket
- [x] `canvas_state.apply_op()` mutates session canvas state for each ContentEvent
- [x] After streaming completes, updated session (including new canvas_state) is persisted via `SessionLoader.save()`
- [x] LLM is a module-level lazy singleton (`ChatOpenAI(model="gpt-4o-mini")`) initialized on first action
- [x] `langchain-core` and `langchain-openai` added to `apps/api/requirements.txt`
- [ ] Wire to Main Assistant tool call once T-031 is implemented (currently called directly from action handler as dev shortcut)

**CI/CD:**
- Existing 11 API tests pass unmodified
- Integration test (future): mock LLM that streams 3 JSONL lines; assert 6 WS messages sent (3 skeleton + 3 content) in correct order

---

### T-035 — Proactive suggestion engine
**Priority:** P1  
**Estimate:** 1 day  
**Depends on:** T-034

**Acceptance Criteria:**
- [ ] After each step confirmation, Main Assistant evaluates whether the current step has a wait window
- [ ] Wait window is inferred from step instruction text (keywords: "simmer", "bake", "sear", "rest", "wait", time mentions)
- [ ] If a wait window is detected, a parallel task suggestion is generated from remaining recipe steps
- [ ] Suggestion is emitted as a canvas operation without a user prompt triggering it
- [ ] Suggestion fires at most once per step
- [ ] If the user is already engaged in conversation, suggestion is suppressed

**CI/CD:**
- Unit test: wait window detection for 10 sample step instructions
- Test suppression logic when conversation is active

---

## Epic 4 — Evals

Evals run as a dedicated test suite in CI on every merge to `main`. They use a fixed dataset of golden test cases. Each eval produces a score that must exceed the minimum threshold or the build fails.

---

### E-001 — Main Assistant intent routing eval
**Priority:** P0

**What it tests:** Given a user message and session context, does the Main Assistant invoke the correct sub-agents and produce a structurally valid response?

**Dataset:** 30 golden test cases covering recipe request, step navigation, camera trigger, mutation rejection, proactive suggestion window, unrelated question (graceful decline), and multi-intent turns.

**Scoring:**
- Correct tool invocation: 1 point per case
- Valid `tts_text` length (under 40 words): 1 point per case
- Valid canvas ops array returned: 1 point per case
- Maximum score: 90

**Pass threshold:** 80/90 (88%)

**Runner:** Python pytest suite using mocked sub-agents. Results logged to `evals/results/E-001-{timestamp}.json`.

**CI/CD:** Runs on every merge to `main`. Blocks merge if below threshold.

---

### E-002 — Recipe Agent retrieval eval
**Priority:** P1

**What it tests:** Does the Recipe Agent return relevant recipes for a given intent? Does the fallback trigger correctly?

**Dataset:** 20 intent queries with labeled relevant recipes from seed data. 5 out-of-distribution queries that should trigger LLM fallback.

**Scoring:**
- Retrieval: NDCG@3 on returned recipes vs labeled relevant set
- Fallback trigger: correct trigger on 5/5 OOD queries
- Output schema validity: 1 point per valid response

**Pass threshold:** NDCG@3 > 0.70, fallback trigger 5/5, schema validity 25/25

**CI/CD:** Runs on merge to `main`. Results logged to `evals/results/E-002-{timestamp}.json`.

---

### E-003 — Image Inference Agent eval
**Priority:** P1

**What it tests:** Does the Image Inference Agent correctly assess cooking state from images?

**Dataset:** 15 fixture images across 3 categories: correctly cooked (5), undercooked (5), unrecognizable/dark (5). Each labeled with expected `assessment` and whether `suggested_action` should be non-null.

**Scoring:**
- Correct `assessment` label: 2 points per image (max 30)
- `suggested_action` non-null when expected: 1 point per image (max 10)
- Output schema validity: 1 point per image (max 15)

**Pass threshold:** 48/55 (87%)

**CI/CD:** Runs on merge to `main`. Fixture images stored in `evals/fixtures/images/`.

---

### E-004 — Render Agent output eval
**Priority:** P0

**What it tests:** Does the Render Agent produce valid, contextually appropriate canvas operations for a given intent and canvas state?

**Dataset:** 25 scenarios: recipe selection (5), step transition (5), camera trigger (5), timer placement (5), suggestion placement (5).

**Scoring:**
- Schema validity: 1 point per operation in output (all ops must be valid)
- Operation count within limit: 1 point per scenario
- Position token appropriateness: 1 point per scenario (judged by rule: timers must be `bottom-right`, suggestions must be `bottom`)
- Component type correctness: 1 point per scenario

**Pass threshold:** 90% of available points

**CI/CD:** Runs on merge to `main`.

---

### E-005 — End-to-end cook flow eval
**Priority:** P1

**What it tests:** Can the system complete a full cook session from first message to final step without a failure?

**Dataset:** 5 scripted cook sessions as conversation transcripts. Each session simulates 8-12 turns including a recipe selection, step progressions, one camera check, and one proactive suggestion.

**Scoring:**
- Session completion (reaches final step): 4 points per session (max 20)
- No crashes or fallback errors during session: 3 points per session (max 15)
- Canvas state is coherent at each turn (no orphaned components): 3 points per session (max 15)

**Pass threshold:** 42/50 (84%)

**CI/CD:** Runs nightly against staging environment (not on every PR due to cost). Failures page Slack.

---

## Epic 5 — CI/CD Pipeline

### T-050 — GitHub Actions base pipeline
**Priority:** P0  
**Estimate:** 0.5 day  
**Depends on:** T-001

**Acceptance Criteria:**
- [ ] Pipeline triggers on all PRs to `main` and on direct pushes to `main`
- [ ] Jobs: `lint`, `type-check`, `unit-test`, `integration-test`, `eval` (E-001 and E-004 on PR, all evals on merge)
- [ ] All jobs must pass before a PR can merge (branch protection rule)
- [ ] Pipeline completes in under 8 minutes for PR runs

**Pipeline definition (`github/workflows/ci.yml`):**

```
lint         → eslint (frontend) + ruff (backend)
type-check   → tsc --noEmit (frontend) + mypy (backend)
unit-test    → vitest (frontend) + pytest (backend, unit only)
integration  → pytest (backend, integration) against test Supabase instance
eval-fast    → E-001, E-004 (runs on every PR)
eval-full    → E-001 through E-004 (runs on merge to main only)
e2e-nightly  → E-005 (runs nightly via cron, not on PR)
```

---

### T-051 — Staging deployment
**Priority:** P1  
**Estimate:** 1 day  
**Depends on:** T-050

**Acceptance Criteria:**
- [ ] Merge to `main` triggers automatic deployment to staging environment
- [ ] Frontend deployed to Vercel (or equivalent) preview URL
- [ ] Backend deployed to Railway / Render / Fly.io (TBD)
- [ ] Staging uses a separate Supabase project with its own seed data
- [ ] Deployment completes within 5 minutes of merge
- [ ] Smoke test runs post-deploy: WebSocket connect, send "hello", assert `session_ready` within 3s

**CI/CD:**
- Deployment step runs after all eval jobs pass
- Slack notification on successful deploy with staging URL
- Slack alert on deploy failure

---

### T-052 — Observability
**Priority:** P1  
**Estimate:** 1 day  
**Depends on:** T-051

**Acceptance Criteria:**
- [ ] All agent turns are logged with: session ID, turn ID, input tokens, output tokens, latency, tools invoked, eval scores if available
- [ ] Logs are structured JSON written to stdout and ingested by a log aggregator (TBD: Axiom or Supabase logs)
- [ ] Three alerts configured: agent turn latency p95 > 5s, eval score below threshold on nightly run, WebSocket error rate > 5%
- [ ] A simple `/metrics` endpoint on the backend returns current session count and turn count

---

### T-053 — Eval result tracking
**Priority:** P2  
**Estimate:** 0.5 day  
**Depends on:** T-050

**Acceptance Criteria:**
- [ ] Each eval run writes results to `evals/results/{eval-id}-{timestamp}.json`
- [ ] Results are committed to the repo via a bot commit after each CI run
- [ ] A `evals/summary.md` is auto-generated showing the last 10 runs per eval with pass/fail
- [ ] Regressions (score drops by more than 5% from previous run) trigger a Slack alert

---

## Implementation Order

The recommended build sequence respects dependencies and gets a working demo loop as fast as possible.

**Week 1** — Foundation + types. Complete T-001, T-002, T-003, T-010a, T-010. Goal: shared types up to date, canvas state manager handling skeleton + upsert + batching.

**Week 2** — Canvas renderer + render agent. Complete T-011, T-012 through T-013c, T-034, T-034a, T-034b. Goal: React canvas renders all component types from streamed JSONL ops; skeleton placeholders appear immediately; full streaming loop from LLM to browser working.

**Week 3** — Remaining components + voice. Complete T-014, T-015, T-016, T-017, T-020, T-021, T-022. Goal: timer, camera, suggestion, text-card components; voice pipeline capturing, transcribing, and playing TTS.

**Week 4** — Agent harness + recipe + image. Complete T-030, T-031, T-032, T-033, T-035, E-001 through E-004. Goal: full multi-agent loop, all evals passing, proactive suggestions firing.

**Week 5** — CI/CD and polish. Complete T-050 through T-053. Goal: full pipeline running, staging deployed, nightly E-005 eval green.

---

## Open Tasks (Unscheduled)

- `T-OQ-1` Define assistant personality and write system prompt
- ~~`T-OQ-2` Design and implement component visual styles~~ ✅ Resolved — design-system.css + 9-zone grid defined; React component library in T-011 through T-013c
- `T-OQ-3` Finalize STT provider (WASM Whisper vs Web Speech API)
- `T-OQ-4` Recipe seed dataset sourcing and embedding pipeline
- ~~`T-OQ-5` Canvas position system design (token-based vs coordinate grid)~~ ✅ Resolved — 9-zone named CSS grid with per-type default positions; agent never emits zone
- `T-OQ-6` Session expiry policy and cleanup job
- ~~`T-OQ-9` Design snippet index: manual curation vs auto-generated~~ ✅ Resolved — inline typed component catalog in system prompt; no snippet index needed

---

*Tasks.md is a living document. Update estimates and acceptance criteria as implementation reveals new constraints.*
