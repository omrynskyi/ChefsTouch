# AI Cooking Assistant — Task Breakdown

**Version:** 0.1  
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

### T-001 — Monorepo and project scaffolding
**Priority:** P0  
**Estimate:** 0.5 day

Set up a monorepo with two workspaces: `apps/web` (React frontend) and `apps/api` (FastAPI backend). Add shared `packages/types` for shared TypeScript/Python type definitions including canvas operation schemas.

**Acceptance Criteria:**
- `apps/web` runs with `npm run dev` and renders a blank page
- `apps/api` runs with `uvicorn` and returns `{"status": "ok"}` from `GET /health`
- `packages/types` exports canvas operation types consumable by both workspaces
- Root `Makefile` has `make dev` that starts both services concurrently
- `.env.example` documents all required environment variables

**CI/CD:**
- GitHub Actions workflow triggers on all PRs to `main`
- Runs `npm install` and `pip install -r requirements.txt` to verify dependency resolution
- Health check smoke test: `curl /health` must return 200

---

### T-002 — Supabase schema and migrations
**Priority:** P0  
**Estimate:** 0.5 day  
**Depends on:** T-001

Create Supabase project. Write SQL migrations for `sessions` and `recipes` tables as defined in PRD section 6. Enable `pgvector` extension for recipe embeddings.

**Acceptance Criteria:**
- Migration runs cleanly against a fresh Supabase project via `supabase db push`
- `sessions` table has all fields from PRD 6.1 with correct types and constraints
- `recipes` table has all fields from PRD 6.2 including `embedding vector(1536)`
- Supabase client initialized in backend with typed models via SQLAlchemy or equivalent
- A seed script populates 5 sample recipes with embeddings for local dev

**CI/CD:**
- Migration lint runs on PR: check for destructive operations on `main` branch
- Seed script runs in test environment before integration tests

---

### T-003 — WebSocket connection foundation
**Priority:** P0  
**Estimate:** 1 day  
**Depends on:** T-001

Establish a persistent WebSocket connection between the React frontend and FastAPI backend. The connection should survive reconnects and carry a session ID from the first message.

**Acceptance Criteria:**
- Frontend connects on page load and reconnects automatically on disconnect (exponential backoff, max 5 retries)
- First message from client sends `{ "type": "init", "session_id": "<uuid or null>" }`
- Backend creates a new session in DB if `session_id` is null, otherwise loads existing
- Backend confirms with `{ "type": "session_ready", "session_id": "<uuid>" }`
- Session ID is persisted in `localStorage` on the client
- Connection status is exposed as a React context (connected / reconnecting / failed)

**CI/CD:**
- Integration test: WebSocket connect, send init, assert session_ready within 2s
- Test both new session creation and session resumption flows

---

## Epic 1 — Canvas Engine

### T-010 — Canvas state manager
**Priority:** P0  
**Estimate:** 1 day  
**Depends on:** T-003

Build the client-side canvas state manager. This is a React context that maintains a map of `component_id -> component` and exposes a `dispatch(operation)` function. The WebSocket listener feeds operations into this dispatcher.

**Acceptance Criteria:**
- Canvas state is a `Map<string, CanvasComponent>` maintained in a React context
- `dispatch` handles all five operation types: `add`, `update`, `remove`, `focus`, `move`
- `add` with a duplicate ID is a no-op and logs a warning
- `remove` on a non-existent ID is a no-op
- `update` deep-merges the incoming `data` with existing component data
- `focus` sets a `focused: true` flag on the target component and clears it on all others
- All operations are validated against the `CanvasOperation` type before dispatch
- Invalid operations are logged and discarded without crashing

**CI/CD:**
- Unit tests cover all five operation types including edge cases (duplicate add, remove missing, etc.)
- 100% branch coverage required on the dispatcher

---

### T-011 — Canvas renderer
**Priority:** P0  
**Estimate:** 1.5 days  
**Depends on:** T-010

Build the canvas renderer: a React component that reads canvas state and renders each component by type. The idle state (empty canvas with mic icon) is handled here.

**Acceptance Criteria:**
- Canvas renders all components currently in state
- Each component type renders its designated React component (stubs acceptable at this stage)
- Idle state (empty canvas state map) renders a centered mic icon
- Component mount/unmount is animated (fade in/out, 150ms)
- `focused` components receive a visual prominence treatment (exact styling TBD)
- Position tokens (`center`, `bottom-right`, etc.) map to CSS layout rules
- Canvas is responsive and works at viewport widths 375px and above

**CI/CD:**
- Snapshot tests for each component type rendered from a fixture
- Visual regression test on idle state using Playwright screenshot comparison

---

### T-012 — Canvas component: recipe-card
**Priority:** P1  
**Estimate:** 0.5 day  
**Depends on:** T-011

Implement the `recipe-card` React component. Renders title, description, duration, servings, and tags from schema.

**Acceptance Criteria:**
- Renders all fields from the `recipe-card` schema
- Missing optional fields render gracefully (no crashes, no empty boxes)
- Component is keyboard accessible
- Clicking/tapping a recipe card emits a `sendPrompt("I want to make {title}")` event (placeholder for voice — user might tap on mobile)

**CI/CD:**
- Unit test: renders with full data, renders with minimal data
- Accessibility audit: no critical axe violations

---

### T-013 — Canvas component: step-view
**Priority:** P1  
**Estimate:** 0.5 day  
**Depends on:** T-011

**Acceptance Criteria:**
- Renders step number, total steps, instruction, and optional tip
- Step progress indicator (e.g. "Step 2 of 7") is visually prominent
- Tip renders in a visually distinct secondary style when present
- Transitioning to a new step (update operation) animates the instruction text change

**CI/CD:**
- Unit test: renders with and without tip
- Snapshot test for step transition animation state

---

### T-014 — Canvas component: timer
**Priority:** P1  
**Estimate:** 1 day  
**Depends on:** T-011

**Acceptance Criteria:**
- Counts down from `duration_seconds` to zero
- Starts automatically if `auto_start` is true
- At zero, pulses visually and plays a soft audio cue
- Can be paused and resumed by tapping
- An `update` operation with a new `duration_seconds` resets the timer
- Timer state survives a WebSocket reconnect (timer continues counting in frontend state)

**CI/CD:**
- Unit test: countdown logic, auto-start behavior, zero-state behavior
- Test that timer does not reset on unrelated canvas operations

---

### T-015 — Canvas component: camera
**Priority:** P1  
**Estimate:** 1.5 days  
**Depends on:** T-011

**Acceptance Criteria:**
- Requests camera permission on first render; handles denied permission gracefully with a verbal TTS fallback message sent to backend
- Captures 3 frames at 500ms intervals automatically once rendered
- Frames are encoded as base64 JPEG at 720p max and sent to backend via WebSocket message `{ "type": "camera_frames", "frames": [...] }`
- After frames are sent, emits a local `remove` operation for itself (camera closes automatically)
- If capture fails for any reason, sends `{ "type": "camera_error" }` to backend

**CI/CD:**
- Unit test: frame capture logic mocked with a fake MediaStream
- Test denied permission flow
- Test that camera always removes itself after capture regardless of success/failure

---

### T-016 — Canvas component: suggestion
**Priority:** P1  
**Estimate:** 0.5 day  
**Depends on:** T-011

**Acceptance Criteria:**
- Renders heading, body, and optional action label
- Action label renders as a tappable button that sends the label text as a voice prompt
- Dismissable by swiping or tapping an X (sends `{ "type": "suggestion_dismissed" }` to backend)

**CI/CD:**
- Unit test: renders with and without action label
- Test dismiss interaction

---

### T-017 — Canvas component: text-card
**Priority:** P1  
**Estimate:** 0.25 day  
**Depends on:** T-011

**Acceptance Criteria:**
- Renders body text in a clean readable style
- Body text supports basic markdown (bold, italic) via a lightweight renderer
- Max 3 lines before truncating with a "tap to expand" affordance

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
- Microphone permission is requested once and its state is persisted
- Recording starts automatically when connection is established and no agent turn is in progress
- Audio is captured as WebM/Opus at 16kHz
- Chunks are sent every 250ms as `{ "type": "audio_chunk", "data": "<base64>" }`
- Recording pauses while the agent is speaking (TTS active) to prevent echo
- Visual mic indicator reflects state: listening, paused, processing

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
- `STTProvider` abstract class with a single `transcribe(audio_bytes) -> str` method
- `WhisperSTTProvider` implements it using OpenAI Whisper API
- Voice activity detection: only submit to Whisper when a pause is detected (300ms silence)
- Transcript is returned as `{ "type": "transcript", "text": "..." }` to the client for display
- Empty transcripts (silence) are discarded without triggering an agent turn
- Latency target: transcript available within 800ms of speech ending

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
- `TTSProvider` abstract class with `synthesize(text) -> audio_bytes` method
- `OpenAITTSProvider` implements it using OpenAI TTS via Responses API
- Audio is sent as `{ "type": "tts_audio", "data": "<base64 mp3>" }`
- Frontend plays audio immediately on receipt using Web Audio API
- Frontend sets recording state to `paused` while TTS audio is playing
- Recording resumes 300ms after audio playback ends

**CI/CD:**
- Unit test: TTS provider interface contract
- Integration test: send a short text, assert audio bytes returned within 1.5s

---

## Epic 3 — Agent Harness

### T-030 — Session context loader
**Priority:** P0  
**Estimate:** 0.5 day  
**Depends on:** T-002, T-003

On every agent turn, load the full session context from Supabase and inject it into the agent request.

**Acceptance Criteria:**
- `SessionLoader` reads session by ID from Supabase
- Returns typed `SessionContext` object with conversation history, active recipe, current step, canvas state, and preferences
- Conversation history is trimmed to last 20 turns to manage context window
- After each agent turn, session is written back to Supabase with updated state
- Write is atomic: if the agent turn fails, session state is not updated

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
- Main Assistant is a LangGraph `StateGraph` node
- System prompt enforces short, quirky, friend-like responses (max 2 sentences for TTS)
- Sub-agents (Recipe, Image Inference, Render) are registered as tools
- Main Assistant decides which tools to call based on user intent
- All tool calls use structured JSON input/output — no free text between agents
- Agent turn completes within 4 seconds for text-only turns
- Graceful degradation: if a sub-agent fails, Main Assistant responds with a fallback message rather than crashing

**CI/CD:**
- Unit test: mock tool calls, assert correct tools invoked for 5 canonical intents (recipe request, camera check, step navigation, mutation rejection, parallel task)
- Eval: see Eval section E-001

---

### T-032 — Recipe Agent
**Priority:** P1  
**Estimate:** 1.5 days  
**Depends on:** T-031, T-002

**Acceptance Criteria:**
- Accepts `{ intent: string, tags: string[], max_results: number }` as input
- Queries Supabase pgvector using cosine similarity on intent embedding
- Returns up to `max_results` recipes conforming to the `recipe-card` schema
- Falls back to LLM generation if vector search returns fewer than 2 results with similarity > 0.75
- Generated recipes are saved to the `recipes` table with `source: "generated"`
- Returns structured JSON only — no prose

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
- Accepts `{ frames: string[], context: string }` where `context` is the current recipe step
- Passes frames to vision-capable model (GPT-4o vision) alongside a structured analysis prompt
- Returns `{ observation: string, assessment: "ok" | "warning" | "error", suggested_action: string | null }`
- `suggested_action` is a short imperative string suitable for a new step-view ("Cook for 2 more minutes")
- If frames are unusable (blurry, dark), returns `assessment: "error"` with a descriptive observation
- Latency target: response within 2.5 seconds

**CI/CD:**
- Unit test: output schema validation, error handling for bad frames
- Integration test with 3 fixture images (correctly cooked, undercooked, unrecognizable): assert correct assessment for each
- Eval: see Eval section E-003

---

### T-034 — Render Agent
**Priority:** P0  
**Estimate:** 1.5 days  
**Depends on:** T-031

**Acceptance Criteria:**
- Accepts `{ intent: string, current_canvas: CanvasState, data: any }` as input
- Returns an ordered array of canvas operations conforming to the `CanvasOperation` schema
- Each operation is validated against the schema before being returned
- Invalid operations are dropped and logged — never returned to client
- Agent never returns more than 5 operations per turn
- Position tokens are chosen contextually: timers go `bottom-right`, suggestions go `bottom`, recipe cards go `center`

**CI/CD:**
- Unit test: output schema validation, operation count limit, position token assignment for each component type
- Eval: see Eval section E-004

---

### T-035 — Proactive suggestion engine
**Priority:** P1  
**Estimate:** 1 day  
**Depends on:** T-034

**Acceptance Criteria:**
- After each step confirmation, Main Assistant evaluates whether the current step has a wait window
- Wait window is inferred from step instruction text (keywords: "simmer", "bake", "sear", "rest", "wait", time mentions)
- If a wait window is detected, a parallel task suggestion is generated from remaining recipe steps
- Suggestion is emitted as a canvas operation without a user prompt triggering it
- Suggestion fires at most once per step
- If the user is already engaged in conversation, suggestion is suppressed

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
- Pipeline triggers on all PRs to `main` and on direct pushes to `main`
- Jobs: `lint`, `type-check`, `unit-test`, `integration-test`, `eval` (E-001 and E-004 on PR, all evals on merge)
- All jobs must pass before a PR can merge (branch protection rule)
- Pipeline completes in under 8 minutes for PR runs

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
- Merge to `main` triggers automatic deployment to staging environment
- Frontend deployed to Vercel (or equivalent) preview URL
- Backend deployed to Railway / Render / Fly.io (TBD)
- Staging uses a separate Supabase project with its own seed data
- Deployment completes within 5 minutes of merge
- Smoke test runs post-deploy: WebSocket connect, send "hello", assert `session_ready` within 3s

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
- All agent turns are logged with: session ID, turn ID, input tokens, output tokens, latency, tools invoked, eval scores if available
- Logs are structured JSON written to stdout and ingested by a log aggregator (TBD: Axiom or Supabase logs)
- Three alerts configured: agent turn latency p95 > 5s, eval score below threshold on nightly run, WebSocket error rate > 5%
- A simple `/metrics` endpoint on the backend returns current session count and turn count

---

### T-053 — Eval result tracking
**Priority:** P2  
**Estimate:** 0.5 day  
**Depends on:** T-050

**Acceptance Criteria:**
- Each eval run writes results to `evals/results/{eval-id}-{timestamp}.json`
- Results are committed to the repo via a bot commit after each CI run
- A `evals/summary.md` is auto-generated showing the last 10 runs per eval with pass/fail
- Regressions (score drops by more than 5% from previous run) trigger a Slack alert

---

## Implementation Order

The recommended build sequence respects dependencies and gets a working demo loop as fast as possible.

**Week 1** — Foundation. Complete T-001, T-002, T-003, T-010, T-011. Goal: blank canvas receiving and rendering a hardcoded canvas operation from the backend over WebSocket.

**Week 2** — Canvas and Voice. Complete T-012 through T-017, T-020, T-021, T-022. Goal: all six components rendering, voice captured and transcribed, TTS playing back.

**Week 3** — Agent harness. Complete T-030, T-031, T-034. Goal: voice in, canvas ops out, full loop working end to end with stub Recipe and Image agents.

**Week 4** — Full agents and evals. Complete T-032, T-033, T-035, E-001 through E-004. Goal: all agents functional, eval suite passing, proactive suggestions firing.

**Week 5** — CI/CD and polish. Complete T-050 through T-053. Goal: full pipeline running, staging deployed, nightly E-005 eval green.

---

## Open Tasks (Unscheduled)

These tasks are acknowledged but not yet estimated or scheduled. They correspond to open questions from the PRD.

- `T-OQ-1` Define assistant personality and write system prompt
- `T-OQ-2` Design and implement component visual styles
- `T-OQ-3` Finalize STT provider (WASM Whisper vs Web Speech API)
- `T-OQ-4` Recipe seed dataset sourcing and embedding pipeline
- `T-OQ-5` Canvas position system design (token-based vs coordinate grid)
- `T-OQ-6` Session expiry policy and cleanup job

---

*Tasks.md is a living document. Update estimates and acceptance criteria as implementation reveals new constraints.*
