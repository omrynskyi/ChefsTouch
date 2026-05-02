# AI Cooking Assistant — Execution Backlog

**Version:** 1.0  
**Owner:** Oleg Mrynskyi  
**Status:** Active  
**Last Updated:** May 1, 2026

---

## Purpose

This document is the implementation backlog for the full product described in [SYSTEM_DESIGN.md](/Users/oleg/Documents/Coding/PairCooking/SYSTEM_DESIGN.md). The goal is simple: **if every task in this file is completed in order, the result should be a working v1 app**.

This backlog is written for agent execution, not just planning. Every task includes:
- a clear dependency list
- the concrete outcome it must produce
- acceptance criteria that define done
- enough scope boundaries that a worker can pick it up without re-planning the architecture

---

## How To Use This Backlog

### Status values

- `DONE` — implemented and verified enough to depend on
- `READY` — unblocked and ready to start
- `BLOCKED` — waiting on listed dependencies
- `LATER` — intentionally deferred until earlier phases land

### Execution rules

1. Do tasks in dependency order.
2. Do not start a task unless every dependency is `DONE`.
3. If a task needs follow-up work that is not already listed, add a new task below the current phase before implementation continues.
4. A task is only complete when its acceptance criteria and verification requirements are met.

### Definition of a working app

At the end of this backlog, the app should support:
- session-based websocket connection
- a voice-first loop with transcript input and spoken output
- a responsive top-left assistant message surface
- canvas-driven recipe discovery and recipe selection
- step-by-step guided cooking UI
- timers and progress
- camera-based visual checks
- recipe mutation during a cook
- interruption-safe orchestration
- evaluation and deployment basics needed to run it reliably

---

## Delivery Order

The work is intentionally sequenced in these phases:

1. Foundation and protocol
2. Canvas runtime and rendering
3. Voice transport and speech loop
4. Realtime orchestration runtime
5. Domain agents and structured outputs
6. End-to-end cooking flows
7. Proactivity and mutation
8. Reliability, evals, and release readiness

---

## Phase 0 — Foundation And Shared Contracts

### T-000 — Lock shared protocol and runtime ownership
**Status:** DONE  
**Priority:** P0  
**Depends on:** None

Create the canonical event-driven runtime contract shared by backend and frontend, and define runtime ownership boundaries.

**Scope**
- Shared wire types for conversation, tool, canvas, and control events
- Python equivalents for backend typing
- Runtime state separated from durable session state
- Generation-aware turn metadata

**Acceptance Criteria**
- `packages/types` defines canonical server/client message unions including `speech_commit`, `speech_cancel`, `turn_started`, `turn_completed`, `tool_started`, `tool_result`, `tool_failed`, and `interrupt_ack`
- Backend has typed runtime state for active turn, generation, speech, and in-flight tools
- Durable session state does not own live speech/tool lifecycle fields
- `turn_id` and `generation_id` exist as first-class runtime identifiers

**Verification**
- TypeScript types build cleanly
- Python runtime files compile cleanly

---

### T-001 — Session bootstrap and reconnectable websocket base
**Status:** DONE  
**Priority:** P0  
**Depends on:** T-000

Provide the persistent client-server session channel the rest of the app depends on.

**Acceptance Criteria**
- Browser opens websocket on load and reconnects automatically
- Client sends `init` with existing or null session ID
- Backend creates or restores session and returns `session_ready`
- Session ID persists client-side
- Connection state is exposed to the frontend

**Verification**
- Integration coverage for new session and resumed session flows

---

### T-002 — Supabase schema and durable session persistence
**Status:** DONE  
**Priority:** P0  
**Depends on:** T-001

Persist app state required across turns and reconnects.

**Acceptance Criteria**
- Supabase schema exists for sessions and recipes
- Recipe storage supports embeddings
- Backend can load and persist session state atomically
- Seed data exists for local development

**Verification**
- Migration push works on a clean database
- Seed script produces usable sample recipe data

---

## Phase 1 — Canvas Runtime And Structured UI

### T-010 — Finish active/staged canvas runtime
**Status:** DONE  
**Priority:** P0  
**Depends on:** T-000, T-001

Complete the double-buffered canvas model described in the system design so the UI can support predictive staging and atomic swaps.

**Scope**
- Add explicit `active` and `staged` canvas maps
- Support `stage`, `commit`, `swap`, and `clear_staged`
- Keep current component rendering stable while staged state remains hidden

**Acceptance Criteria**
- Canvas state stores separate `active` and `staged` maps
- `stage` writes only to the staged map
- `commit` moves a staged component into active state without re-creating unrelated active components
- `swap` atomically removes `out_id` and promotes `in_id`
- `clear_staged` removes only staged components
- `update` and `remove` behave correctly for active and staged components
- The visible canvas renders from `active` state only

**Verification**
- Reducer tests cover all staged-state transitions
- UI test proves staged components never appear before commit/swap

---

### T-011 — Finish component library parity with the PRD
**Status:** DONE  
**Priority:** P0  
**Depends on:** T-010

Bring every v1 canvas component to the spec required by the PRD, including missing behaviors and consistency fixes.

**Scope**
- Review all current components against the PRD catalog
- Close remaining gaps such as text-card expansion, recipe-grid progressive behavior, camera lifecycle polish, and consistent zone behavior
- Standardize loading, empty, and focused states

**Acceptance Criteria**
- All PRD v1 components exist and match their documented schemas
- `text-card` supports truncation plus expand behavior
- `recipe-grid` and `recipe-option` support progressive child insertion
- `camera` handles denied permission, capture failure, and auto-dismiss consistently
- Timers survive reconnect and component rerenders
- Each component has a documented default zone and renders correctly on mobile and desktop

**Verification**
- Unit tests exist for every component
- Basic visual regression coverage exists for idle state, recipe selection, active step, and camera view

---

### T-012 — Harden canvas operation validation and renderer behavior
**Status:** DONE  
**Priority:** P0  
**Depends on:** T-010

Make canvas updates safe enough that malformed or stale render output cannot crash or visually corrupt the app.

**Scope**
- Validate all incoming canvas operations before state mutation
- Drop invalid ops safely
- Add generation-awareness to canvas application
- Make parent-child ordering failures survivable

**Acceptance Criteria**
- Invalid canvas operations are rejected with logs instead of crashing the UI
- Canvas ops carrying stale `generation_id` are ignored
- `recipe-option` ops without valid parent handling do not break rendering
- Duplicate `add` operations remain safe upserts
- Canvas update batching prevents janky rerenders during streamed render output

**Verification**
- Reducer and integration tests cover invalid ops, stale ops, and parent-child edge cases

---

## Phase 2 — Voice Input And Speech Output

### T-020 — Implement browser audio capture and input state machine
**Status:** READY  
**Priority:** P0  
**Depends on:** T-001

Build the browser-side listening loop that captures microphone audio and streams it to the backend.

**Scope**
- Microphone permissions
- Listening, paused, and processing states
- Chunked audio transport
- Client-side guardrails so capture and playback do not fight

**Acceptance Criteria**
- Browser requests microphone permission once and stores the result
- Audio capture starts automatically when the app is idle and connected
- Audio chunks are streamed over websocket on a fixed cadence
- Recording pauses when assistant speech is actively playing
- Recording resumes automatically after playback ends
- The UI exposes at least three states: listening, paused, processing

**Verification**
- Unit tests cover state transitions
- Browser tests mock microphone capture and verify websocket sends

---

### T-021 — Implement backend transcript pipeline
**Status:** READY  
**Priority:** P0  
**Depends on:** T-020

Convert streamed audio into partial and final transcript events suitable for the realtime conversation loop.

**Scope**
- STT provider abstraction
- VAD or endpointing
- Partial transcript event support
- Final transcript emission into runtime flow

**Acceptance Criteria**
- Backend accepts streamed audio input messages
- STT is hidden behind a provider interface
- Silence or empty transcript segments do not trigger turns
- Backend can emit partial transcript events before final transcript completion
- Final transcript events feed the runtime controller in the canonical event model
- Transcript latency is fast enough to support conversational use

**Verification**
- Tests cover empty transcript discard and endpointing behavior
- Integration test with recorded fixture audio produces stable transcript output

---

### T-022 — Implement cancellable speech output pipeline
**Status:** READY  
**Priority:** P0  
**Depends on:** T-020, T-021

Add the speech side of the voice-first loop so assistant output is heard immediately and can later be interrupted cleanly.

**Scope**
- TTS provider abstraction
- Speech playback transport
- Frontend playback controller
- Cancel path for superseded speech

**Acceptance Criteria**
- Backend can emit spoken assistant output through a TTS provider
- Frontend starts playback immediately when assistant speech arrives
- A new speech unit cancels any superseded playback cleanly
- `speech_cancel` messages are understood client-side even before full barge-in UX is complete
- The top-left assistant message stays in sync with the most recently committed spoken text

**Verification**
- Unit tests cover provider contract and playback state transitions
- Integration test proves speech resumes listening after playback completes or is cancelled

---

## Phase 3 — Realtime Runtime Controller

### T-030 — Convert websocket handling to full event routing
**Status:** DONE  
**Priority:** P0  
**Depends on:** T-000, T-001

Move websocket transport from a simple action queue to a true runtime event router.

**Scope**
- Route canonical runtime events through a dedicated emitter
- Preserve compatibility projections for current UI surfaces
- Accept future-ready client messages without redesigning the transport later

**Acceptance Criteria**
- Backend websocket handler routes `action`, transcript, camera, and interrupt-class messages through a single controller path
- Outgoing server events are emitted through a runtime emitter instead of ad hoc branching
- Compatibility outputs still exist for `tts_text`, `canvas_ops`, and `agent_status`
- Transport code is separated from orchestration code enough that future transports can reuse the runtime controller

**Verification**
- Websocket integration tests cover init, action, transcript, and interrupt message handling

---

### T-031 — Implement generation filtering and interruption semantics end to end
**Status:** DONE  
**Priority:** P0  
**Depends on:** T-030

Make the runtime safe under interruptions, back-to-back turns, and late tool results.

**Scope**
- Active generation ownership in runtime registry
- Superseding turns
- Interrupt acknowledgements
- Dropping stale speech, tool, and canvas events

**Acceptance Criteria**
- Every turn has a new `turn_id` and `generation_id`
- A newer turn supersedes older in-flight work
- `interrupt` bumps generation and emits `interrupt_ack`
- Speech, tool, and canvas events from superseded generations are dropped before reaching the UI
- Stale tool completion cannot overwrite the current assistant message or canvas

**Verification**
- Integration tests simulate back-to-back turns and explicit interrupts
- Tests prove stale results are filtered across all event classes

---

### T-032 — Implement realtime conversation loop behavior
**Status:** READY  
**Priority:** P0  
**Depends on:** T-021, T-022, T-031

Add the control logic that makes the assistant feel responsive instead of turn-batch driven.

**Scope**
- Partial transcript observation
- Fast acknowledgement decisions
- Separation of conversation loop from slower work loop
- Speech-first behavior within speculative safety limits

**Acceptance Criteria**
- Runtime can receive partial transcripts without forcing a final turn immediately
- Assistant can emit a fast acknowledgement before slower tool work completes
- Conversation loop decisions are modeled separately from background work execution
- User-meaningful progress messages are supported without narrating raw tool calls
- The system can stay silent when appropriate instead of always speaking

**Verification**
- Runtime tests cover quick acknowledgement, wait, and no-speech branches
- Latency instrumentation exists for first acknowledgement timing

---

## Phase 4 — Main Agent And Tooling

### T-040 — Complete realtime Main Agent orchestration
**Status:** DONE  
**Priority:** P0  
**Depends on:** T-031

Turn the Main Agent into the realtime session controller described in the system design.

**Scope**
- Tool selection
- speculative-first spoken acknowledgements
- structured event emission
- follow-up grounding after tool completion

**Acceptance Criteria**
- Main Agent emits canonical speech, tool, and canvas events instead of a single synchronous response shape
- Initial assistant speech is short and safe under speculative rules
- Main Agent can continue or refine its response after tool completion without restarting the turn
- Tool failures degrade into useful fallback speech instead of dead air or crashes
- System prompt and control logic enforce short, friend-like conversational output

**Verification**
- Unit tests cover recipe request, camera request, clarification, next-step navigation, and fallback behavior
- Evals include response brevity and speculative-safety checks

---

### T-041 — Finish Render Agent integration with staged UI semantics
**Status:** DONE  
**Priority:** P0  
**Depends on:** T-010, T-040

Align the render pipeline with the double-buffered canvas model and the responsive orchestration flow.

**Scope**
- Render Agent support for `stage`, `commit`, `swap`, and `clear_staged`
- Independent render execution from speech
- Clear render-intent handling for placeholders and speculative UI

**Acceptance Criteria**
- Render Agent can emit staged ops as well as active canvas ops
- Main Agent can launch render work without delaying first assistant speech
- Placeholder UI, recipe options, and clarification cards can appear before final grounded answers when low-risk
- Conversational misuse of render intents still gets promoted to spoken assistant output instead of canvas junk

**Verification**
- Render-agent tests cover staged op schemas and progressive rendering order
- Integration test proves speech can arrive before a completed render batch

---

### T-042 — Build two-phase Recipe Agent
**Status:** READY  
**Priority:** P0  
**Depends on:** T-002, T-040

Implement the recipe resolver described in the system design: fast retrieval first, synthesis second, normalized structured output always.

**Scope**
- Retrieval-first candidate lookup
- Fallback recipe synthesis
- Structured recipe normalization
- Quick candidate vs finalized recipe distinction

**Acceptance Criteria**
- Recipe Agent first queries fast stored recipes before invoking full synthesis
- If retrieval misses, fallback generation produces a structured recipe instead of prose
- Agent output distinguishes between quick candidate availability and finalized recipe data
- Generated recipes can be persisted for later reuse if that path is enabled
- Output schema is stable enough to drive recipe-grid and step-view rendering directly

**Verification**
- Tests cover retrieval hit, retrieval miss, and normalization
- Eval checks quality and schema validity for multiple ingredient-based prompts

---

### T-043 — Build Image Inference Agent for cooking checks
**Status:** READY  
**Priority:** P0  
**Depends on:** T-040

Implement the structured vision tool for "look at this" and "is this done?" flows.

**Scope**
- Frame ingestion
- vision model analysis
- structured cooking assessment
- unusable-image fallback

**Acceptance Criteria**
- Image Inference Agent accepts captured frames plus context
- Output includes structured observation, assessment, and suggested next action
- Bad frames produce a recoverable error state instead of misleading analysis
- Response shape is directly consumable by the Main Agent for speech and canvas mutation

**Verification**
- Tests cover valid frames, unusable frames, and schema correctness
- Eval set covers at least undercooked, okay, and unreadable cases

---

## Phase 5 — End-To-End Cooking Experience

### T-050 — Recipe discovery flow
**Status:** READY  
**Priority:** P0  
**Depends on:** T-041, T-042

Deliver the initial product loop where a user asks what to cook and sees useful options quickly.

**Scope**
- Ingredient or intent-based recipe request
- fast spoken acknowledgement
- recipe-grid rendering
- selection action handling

**Acceptance Criteria**
- User can ask for a recipe by ingredients or general intent
- Assistant acknowledges quickly before full recipe work completes
- Canvas shows a recipe-grid with actionable options
- Selecting a recipe triggers the next turn with the selected recipe intent
- If no strong match exists, the app still produces viable options or a clarifying choice instead of a dead end

**Verification**
- Integration test covers ask -> options -> select flow
- Eval checks usefulness and diversity of returned options

---

### T-051 — Guided step-by-step cook flow
**Status:** READY  
**Priority:** P0  
**Depends on:** T-050

Deliver the core cooking experience after recipe selection.

**Scope**
- active recipe session state
- step-view rendering
- progress-bar updates
- next-step actions
- timer support when required by a step

**Acceptance Criteria**
- Selecting a recipe starts an active cook session
- Canvas shows current step, progress, and relevant timer or supporting UI
- User can advance steps by action button or voice intent
- Step advancement updates both spoken guidance and canvas state
- Active recipe and current step persist across reconnect

**Verification**
- Integration test covers recipe selection through recipe completion
- Session persistence test proves reconnect resumes the cook correctly

---

### T-052 — Camera analysis flow
**Status:** READY  
**Priority:** P0  
**Depends on:** T-043, T-051

Deliver the visual check flow during a cook.

**Scope**
- camera component invocation
- frame capture
- analysis result handling
- dismissal and follow-up guidance

**Acceptance Criteria**
- User can request a visual check during a cook
- Assistant acknowledges immediately and opens camera UI without blocking speech
- Frontend captures frames and sends them automatically
- Main Agent refines or completes its response after image analysis returns
- Camera dismisses cleanly and canvas returns to a stable cooking state

**Verification**
- Integration test covers request -> camera -> analysis -> updated guidance flow

---

### T-053 — Clarification and typed input card flow
**Status:** READY  
**Priority:** P1  
**Depends on:** T-041, T-050

Support short clarifying questions when voice intent is too ambiguous or when typed input is the cleanest UX.

**Scope**
- text-card based clarifications
- optional text input card support if needed
- backend handling of typed replies through the same runtime path

**Acceptance Criteria**
- Assistant can ask a short clarifying question without blocking on slow tools
- Clarification appears both as spoken assistant output and structured canvas UI when appropriate
- User can answer by follow-up voice turn
- If typed input is introduced, it feeds the same action/runtime path without special-case orchestration

**Verification**
- Integration tests cover an ambiguous recipe request and successful clarification

---

## Phase 6 — Proactivity And Live Mutation

### T-060 — Proactive parallel-task suggestion system
**Status:** READY  
**Priority:** P1  
**Depends on:** T-051

Teach the assistant to suggest useful parallel work during natural waiting windows.

**Scope**
- track current recipe step semantics
- infer waiting windows
- suggestion component rendering
- conversational framing that feels helpful, not chatty

**Acceptance Criteria**
- During eligible waiting steps, the assistant can proactively surface a parallel task suggestion
- Suggestions are grounded in the current recipe state, not generic filler
- Suggestion UI is actionable and dismissible
- Suggestions do not interrupt urgent cooking guidance or timer-related alerts

**Verification**
- Tests cover waiting-step detection and suppression in non-waiting steps
- Eval checks suggestion usefulness on representative recipes

---

### T-061 — Live recipe mutation engine
**Status:** READY  
**Priority:** P1  
**Depends on:** T-052, T-060

Allow the app to modify the active cook plan when new information arrives.

**Scope**
- insert, update, and remove active steps
- mutation provenance in session state
- user rejection path

**Acceptance Criteria**
- Main Agent can insert or modify steps in the active recipe during a cook
- Mutations can be triggered by image analysis or other grounded runtime decisions
- User can reject a mutation and the recipe state reverts appropriately
- Mutations update step-view, progress, and spoken guidance consistently

**Verification**
- Integration tests cover insert-step, update-step, and reject-mutation flows

---

## Phase 7 — Reliability, Evals, And Product Hardening

### T-070 — Observability and latency instrumentation
**Status:** READY  
**Priority:** P0  
**Depends on:** T-032, T-040

Add the measurements needed to know whether the realtime design is actually working.

**Scope**
- timing spans for transcript, acknowledgement, tool latency, render latency, and speech latency
- structured logs for generation and stale-event drops
- per-turn traceability

**Acceptance Criteria**
- First acknowledgement latency is measured
- Tool runtimes are recorded per turn
- Speech cancellation and stale-generation drops are observable in logs
- A developer can inspect one turn and understand transcript, tool, speech, and canvas timing

**Verification**
- Tests cover metric/log emission on success, failure, and interruption paths

---

### T-071 — End-to-end evaluation suite
**Status:** READY  
**Priority:** P0  
**Depends on:** T-050, T-051, T-052, T-060, T-061

Build the evaluation harness that protects the product behavior defined in the PRD and system design.

**Scope**
- conversation responsiveness evals
- speculative safety evals
- recipe quality evals
- vision evals
- interruption and stale-result evals

**Acceptance Criteria**
- Evals exist for at least:
  - recipe request responsiveness
  - clarification behavior
  - camera analysis follow-up
  - interruption handling
  - mutation acceptance/rejection
- Evals assert both UX quality and structured output correctness where possible
- CI can run the deterministic subset on every PR

**Verification**
- Eval harness documented and runnable locally

---

### T-072 — Failure handling and degraded-mode UX
**Status:** READY  
**Priority:** P0  
**Depends on:** T-052, T-070

Make the app behave like a product instead of a prototype when tools or network conditions go bad.

**Scope**
- recipe tool failure fallback
- vision failure fallback
- websocket reconnect during active turn
- speech cancellation edge cases

**Acceptance Criteria**
- Recipe lookup failure still yields a useful conversational fallback
- Vision failure asks for a retry or alternate user action instead of guessing
- Reconnect during a cook restores a stable session state
- Tool failures do not leave orphaned canvas UI behind
- Assistant never exposes raw exception text to the user

**Verification**
- Integration tests inject failures into recipe, vision, render, and websocket paths

---

### T-073 — Release-ready local and deployed environments
**Status:** READY  
**Priority:** P1  
**Depends on:** T-071, T-072

Make the project straightforward to run, test, and deploy for daily use.

**Scope**
- environment documentation
- one-command local startup
- production env var docs
- deployment target wiring

**Acceptance Criteria**
- A fresh developer can run the full stack locally from documented steps
- Required env vars are documented and validated at startup
- Production deployment path is documented for frontend, backend, and database
- Smoke checks exist for health, websocket session bootstrap, and a basic assistant turn

**Verification**
- Manual fresh-start verification from a clean environment

---

## Final Acceptance Gate

Do not mark the app complete until all tasks from `T-010` through `T-073` are `DONE` and the following product-level checks pass:

- A user can open the app and establish a session automatically.
- A user can speak a recipe request and receive a fast spoken acknowledgement.
- The canvas can show recipe options and let the user choose one.
- The user can move through a cook with step guidance, progress, and timers.
- The user can ask for a visual check and receive grounded follow-up after camera analysis.
- The assistant can handle interrupts without surfacing stale speech or stale UI.
- The assistant can proactively suggest parallel work during a waiting period.
- The active recipe can be mutated and corrected during the cook.
- The app remains usable when recipe lookup, rendering, camera, or network flows partially fail.

---

## Suggested Next Task

If work starts from the current repository state, the next task to pick up is:

**T-011 — Finish component library parity with the PRD**

The staged canvas runtime and event-driven websocket foundation are already in place. The next gap is bringing the visible component library up to PRD parity before adding the full voice and cooking flows on top.
