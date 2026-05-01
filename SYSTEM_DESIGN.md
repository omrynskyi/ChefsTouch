# AI Cooking Assistant — Product Requirements Document

**Version:** 0.2  
**Author:** Oleg Mrynskyi  
**Status:** Draft  
**Last Updated:** May 2026

---

## 1. Overview

### 1.1 Product Vision

An AI-powered web cooking assistant that feels like a knowledgeable friend guiding you through a cook in real time. The core thesis is a fundamentally different UI paradigm: instead of a static recipe page or a chatbot returning text, an AI agent dynamically controls a canvas, rendering and rearranging structured UI components in response to the conversation. The cooking domain is the proving ground; the agent-controlled canvas is the product.

### 1.2 Problem Statement

Existing cooking apps are static. You scroll through steps manually, set timers yourself, and get no awareness of where you are in the cook or what you could be doing in parallel. AI chat assistants respond in long text blocks that are impractical to read while your hands are covered in flour. Neither feels like having a knowledgeable friend in the kitchen.

### 1.3 Design North Star

> "It feels like a friend showing me how to cook — not software giving me instructions."

The assistant is proactive, anticipatory, and short. It speaks in brief quirky responses. It manages your time across a cook. It reacts to what you show it. It updates the screen without being asked.

### 1.4 Target Users

- Home cooks who want guidance without a cookbook
- College students cooking on a budget with limited experience
- The builder himself (dogfooding first)

---

## 2. Core Concepts

### 2.1 The Canvas

The entire UI is a single screen canvas. There is no navigation, no pages, no scrolling between sections. The agent controls what is rendered on this canvas at all times by emitting a stream of canvas operations over a WebSocket connection. The user never directly manipulates the canvas layout.

On first load the canvas is blank with a single centered mic icon, signaling this is a voice-first experience.

### 2.2 Agent-Controlled UI

The agent emits typed canvas operations streamed over WebSocket as **JSONL** (one JSON object per line). Each operation specifies a **component type** and a **data payload** — the agent never writes HTML, CSS, or JavaScript. The React canvas renderer maps each type to its designated React component and zone.

The system uses a **Double-Buffered UI Architecture**:
- **Active Canvas:** Visible components.
- **Staging Area:** Hidden in-memory cache where the agent pre-builds and holds components during idle time.

Operations may stream progressively. The backend can patch incomplete JSON chunks into valid partial objects so text and structured content can appear before the full component is finished generating.

The agent is constrained to a fixed catalog of named component types. It cannot introduce arbitrary markup.

### 2.3 Voice First

The primary input channel is voice. The long-term target is a **realtime voice loop**: the user speaks naturally, partial transcripts arrive continuously, and the assistant responds through streamed speech and independent canvas updates. Text input is not a priority for v1, but typed clarification UI is allowed when the agent explicitly requests it.

### 2.4 Camera as Input

The camera is an on-demand input channel, not a persistent feed. It is triggered when the user says something like "look at this" or "is this good." The agent renders a camera component, captures a few frames, analyzes them, dismisses the camera view, and responds verbally and visually based on what it saw.

---

## 3. Features

### 3.1 Voice Conversation Loop

The long-term system is **voice-first and realtime**. Audio is captured in the browser, streamed to the backend, and converted into partial and final transcript events. The Main Agent monitors these events continuously, decides when to acknowledge, when to wait, and when to launch background work.

The system is optimized for **perceived latency**:
- the assistant should sound responsive almost immediately
- the first spoken response does not need to wait for all blocking tools
- speech and canvas updates are independent channels

The assistant responds through two coordinated outputs:
- **Speech channel:** short conversational output, streamed and cancellable
- **Canvas channel:** structured UI updates rendered independently of speech timing

**Behavior:**
- Listening is active by default when no interruption or tool-specific capture is in progress
- The assistant may acknowledge before blocking tool work completes
- Spoken progress should be user-meaningful, not raw internal narration
- The assistant does not wait to be asked — it proactively speaks and updates the canvas when it determines something is useful

### 3.2 Proactive Parallel Task Suggestions

During a cook, the agent tracks the current step and estimates available time windows. When the user is waiting on a step (e.g. chicken searing for 6 minutes), the agent proactively suggests a parallel task and updates the canvas to show it without the user asking.

**Trigger:** Inferred from conversation context, not timers or computer vision.

### 3.3 Camera Analysis

When the user invokes a visual check ("look at this," "is this good," "what do I do with this"), the assistant should acknowledge quickly, render camera UI immediately if needed, and refine its spoken answer once analysis completes.

Long-term target flow:

1. User starts or finishes an utterance requesting a visual check
2. Main Agent emits a fast spoken acknowledgement
3. Render Agent emits a camera-related canvas update without blocking speech
4. Frontend captures a few frames automatically once the camera is active
5. Frames are sent to the Image Inference Agent
6. Main Agent receives analysis and either:
   - continues the same response with grounded detail, or
   - corrects or refines earlier speculative framing if needed
7. Camera is dismissed and canvas is updated as appropriate

**No persistent camera feed. No overlays. Frames only.**

### 3.4 Live Recipe Mutation

The recipe displayed on the canvas is a living document. The agent can insert, modify, or remove steps based on what it observes or decides during the cook. For example if the agent sees undercooked chicken via the camera it inserts a "cook chicken more" step immediately after the current one.

The user can reject mutations verbally ("remove that step, I like it") and the agent removes it.

### 3.5 Canvas Component Library (v1)

The agent uses a fixed catalog of named component types. Each type has a **defined data schema**, a **default canvas zone**, and a corresponding **React component**. The agent specifies content via data fields — it never specifies zone, size, layer, CSS classes, or HTML.

#### Component catalog

| Type | Default zone | Data fields |
|------|-------------|-------------|
| `step-view` | center | `step_number`, `total_steps`, `recipe`, `instruction`, `tip?`, `tags?`, `action?` |
| `progress-bar` | top | `current`, `total` |
| `timer` | corner-br | `duration_seconds`, `label`, `auto_start` |
| `suggestion` | bottom | `heading`, `body`, `action_label?` |
| `alert` | top | `text`, `urgent?` |
| `recipe-grid` | center | _(no data — children are `recipe-option` ops)_ |
| `recipe-option` | _(child of recipe-grid)_ | `title`, `description?`, `duration?`, `tags?`, `action` |
| `ingredient-list` | center | `items: [{name, qty}]` |
| `camera` | center | `prompt` |
| `text-card` | center | `body` (markdown) |

Full schema definitions and rendering details are in the Rendering Architecture Spec.

### 3.6 Canvas Operations

The agent emits operations as **JSONL** (one JSON object per line) streamed over WebSocket. Each line is independently parseable as it completes — the client does not wait for a complete array. The backend's `JSONStreamHealer` parses the stream and forwards each op to the client immediately via WebSocket.

| Operation | Payload | Description |
|-----------|---------|-------------|
| `add` | `id`, `type`, `data` | Insert a new component into the Active Canvas |
| `stage` | `id`, `type`, `data` | Build a component invisibly in the Staging Area |
| `commit` | `id` | Move a component from Staging to Active |
| `swap` | `out_id`, `in_id` | Atomic transition: remove `out_id` and commit `in_id` |
| `update` | `id`, `data` | Complete replacement of the component's data object |
| `remove` | `id` | Remove a component from canvas or staging memory |
| `clear_staged` | — | Wipe all components from the Staging Area |
| `focus` | `id` | Visually emphasize target; clear focus from others |
| `move` | `id`, `zone` | Relocate a component to a different grid zone |

**Predictive Staging:**  
When the system is idle, the Orchestrator predicts the most likely next user intent and prompts the Render Agent to build the corresponding UI into the **Staging Area** using `stage`. When the user performs that action, the system issues a `commit` or `swap`, delivering the UI in ~16ms.

**Streaming lifecycle per op:**
1. LLM starts streaming a new JSONL line
2. Backend healer continuously repairs the incomplete JSON string using stack-based patching
3. Healer emits partial events to the client
4. Client merges partial data into state and re-renders immediately
5. LLM completes the line and the final op is committed

**Topological ordering rule:** parents before children; most important content first; supplementary components last.

**Example JSONL stream (step view + progress + timer):**
```jsonl
{"op":"add","id":"step-1","type":"step-view","data":{"step_number":1,"total_steps":6,"recipe":"Pasta Carbonara","instruction":"Bring a large pot of salted water to a boil.","tags":["~10 min","stovetop"],"action":"next_step"}}
{"op":"add","id":"progress-1","type":"progress-bar","data":{"current":1,"total":6}}
{"op":"add","id":"timer-1","type":"timer","data":{"duration_seconds":600,"label":"Boiling","auto_start":true}}
```

**Update example (advancing to step 2):**
```jsonl
{"op":"update","id":"step-1","data":{"step_number":2,"instruction":"Add pasta to the boiling water."}}
{"op":"update","id":"progress-1","data":{"current":2}}
```

**WebSocket message format** (one per op, sent immediately as it completes):
```json
{ "type": "canvas_ops", "operations": [ { "op": "add", "id": "step-1", "type": "step-view", "data": { ... } } ] }
```

---

## 4. Agent Architecture

### 4.1 Architectural Goal: Perceived Latency Over Raw Completion Latency

The system uses a multi-agent architecture orchestrated by a Main Agent. The long-term target is not a turn-based assistant that waits for all tool work to finish before replying. It is a **realtime conversational controller** that optimizes for perceived responsiveness first, then grounds and refines as results arrive.

The design should make the system feel like:
- "I heard you instantly."
- "I'm already helping."
- "I refine naturally if I learn more."

It should not feel like:
- "I wait silently, then dump a final answer."

Implications:
- the assistant may begin speaking before blocking tools complete
- speech and canvas updates are decoupled
- the first response may be speculative, but only within explicit safety rules
- slower tool results may complete or refine an earlier spoken response rather than replace it wholesale

### 4.2 Two Loops: Conversation Loop vs Work Loop

The runtime is split into two coordinated but independent loops.

#### Conversation Loop

Responsible for:
- realtime audio intake
- partial transcript handling
- deciding when to respond
- generating immediate spoken acknowledgements
- interruption handling
- short user-facing conversational turns

This loop must be optimized for minimum perceived latency and must not be blocked by recipe retrieval, render completion, or image analysis.

#### Work Loop

Responsible for:
- recipe retrieval and generation
- image analysis
- render-agent requests
- speculative background staging
- state mutation planning
- lower-priority memory and summarization work

This loop may be slower, as long as it does not block the Conversation Loop from acknowledging the user and sounding responsive.

### 4.3 Realtime Main Agent

The Main Agent is the live controller of the session. It should not be modeled as "receive transcript, then return `tts_text` plus canvas ops" as a single synchronous artifact.

Instead, the Main Agent emits a stream of user-facing and system-facing events while maintaining the live state of the session.

Responsibilities:
- track live conversation state
- decide whether to speak now, wait, or stay silent
- classify the user request as:
  - conversational only
  - requiring blocking tool work
  - eligible for speculative-first speech
  - requiring visible UI change
- launch blocking and non-blocking work independently
- reconcile speculative speech with later grounded tool results
- cancel stale speech and ignore stale results when a newer turn supersedes the current one

### 4.4 Blocking and Non-Blocking Tools

The tool model is explicitly latency-aware.

#### Non-blocking tools

These must never block the first spoken response:
- Render Agent for supportive UI updates
- speculative pre-rendering and staging
- session summarization
- low-priority memory retrieval

#### Blocking tools

These may be required before a grounded answer is complete:
- Recipe Agent lookup and generation
- Image Inference Agent analysis
- future factual tool classes such as nutrition or inventory reasoning

#### Rule

The Conversation Loop may speak before blocking tools finish, but the first speech must obey speculative safety rules.

### 4.5 Speech Pipeline

Speech is a first-class realtime output stream.

Long-term sequence:

1. user starts speaking
2. partial transcript arrives continuously
3. Main Agent monitors the evolving utterance and intent confidence
4. once confidence is high enough, the assistant may pre-plan a short acknowledgement
5. after endpointing or sufficient confidence, speech output begins
6. blocking and non-blocking tool work runs in parallel
7. grounded tool results append to, refine, or complete the spoken response
8. if the user barges in, the current speech stream is cancelled immediately

Spoken progress should be **user-meaningful only**. The assistant should not narrate raw tool execution such as "calling recipe lookup" or "running render agent."

### 4.6 Interruptions, Corrections, and Barge-In

Interruptibility is part of the core architecture, not a later enhancement.

Rules:
- a newer user turn takes precedence over an older one
- user speech should cancel current assistant speech quickly
- tool work may continue in the background, but stale results must not surface as current truth
- canvas updates from stale generations must be discarded or treated as advisory only

If later tool output conflicts with earlier speculative speech:
- do not apologize mechanically unless the user-visible meaning changed
- continue naturally with the corrected grounded result
- only explicitly correct when the earlier framing would mislead the user

### 4.7 Canvas Update Pipeline

Canvas updates are independent from speech timing.

Rules:
- speech does not wait for render completion
- render requests may be launched in parallel with blocking recipe or image work
- the canvas may show placeholders, recipe options, camera UI, or input cards before the grounded spoken answer is complete
- speculative UI is allowed if it is low-risk, reversible, and visually stable
- the canvas must not flicker between contradictory states during refinement or interruption

The Render Agent remains the owner of typed canvas operations and progressive rendering strategy. That rendering-specific protocol is documented in the Rendering Architecture Spec.

### 4.8 Session and Working Memory

On every active interaction, the system maintains both persistent session state and live runtime state.

Persistent session state includes:
- conversation history (last N turns)
- active recipe (if any)
- current step index
- current canvas state
- user preferences

Live runtime state includes:
- current speech stream state
- current `turn_id`
- current `generation_id`
- active tool runs
- speculative claims not yet grounded
- pending canvas updates that belong to the live generation

This runtime state exists to:
- cancel outdated speech cleanly
- ignore stale tool results
- prevent old canvas commits from overwriting newer user context
- track what has been speculatively implied versus what has been grounded

### 4.9 Reliability Rules for Speculative Speech

The assistant is allowed to be speculative first, but only with safe non-factual phrasing.

#### Allowed before tool completion
- acknowledgements
- process framing
- lightweight next-step setup
- intent confirmation by implication
- soft planning language

Examples:
- "Yep, I'm pulling together something with chicken and rice."
- "Hang on, I'm narrowing this down."
- "I've got a couple directions for that."

#### Not allowed before tool completion
- specific recipe names unless already known
- claims that a recipe was found when retrieval has not confirmed it
- factual assertions about image contents before analysis returns
- precise timings, quantities, or step details unless grounded

#### Reliability constraints
- speculative speech cannot contain unverified specifics
- grounded tool results always outrank earlier speculation
- the assistant should rarely say "I'm doing X" unless that update is externally meaningful
- blocking tools may update or complete the answer, but should not restart the conversation from scratch

### 4.10 Latency Budgets

Recommended long-term design targets:

- First acknowledgement speech begins: `<300ms` perceived, `<700ms` hard upper target
- First visible progress signal: `<150ms`
- First meaningful canvas change: `<800ms` when applicable
- Interrupt reaction: `<150ms` from user speech start to assistant stop
- Tool-backed grounded follow-up after speculative opener:
  - recipe retrieval path: target `<1.5s`
  - image analysis path: target `<2.0s`

These are design targets, not guarantees, but they anchor architectural decisions.

Priority ordering when speed and completeness conflict:
1. stop listening ambiguity fast
2. acknowledge fast
3. start useful work in parallel
4. show or say grounded specifics as soon as available
5. refine continuously

### 4.11 Event Model

The long-term design moves from a synchronous `{ tts_text, canvas_ops }` contract toward an event stream model.

Recommended event classes:

#### Conversation events
- `speech_start`
- `speech_delta`
- `speech_commit`
- `speech_cancel`

#### Visual events
- `canvas_op`
- `canvas_stage_op`
- `canvas_commit`
- `canvas_swap`

#### Work/status events
- `tool_started`
- `tool_result`
- `tool_failed`

#### Input/control events
- `user_audio_start`
- `user_audio_end`
- `partial_transcript`
- `final_transcript`
- `interrupt`
- `barge_in`

This event model keeps the architecture compatible with realtime speech streaming, independent canvas timing, and cancellation when the user interrupts.

### 4.12 Agents

#### Main Agent (Realtime Orchestrator)
- Receives: partial or final transcripts, optional camera frames, session context, live runtime state
- Decides: whether to acknowledge immediately, whether a request requires blocking or non-blocking tool work, what to say now, what to defer, and what canvas operations to request
- Returns: a stream of conversation, canvas, and tool lifecycle events
- Personality: short, quirky, anticipatory, friend-like
- Constraint: optimize perceived responsiveness without making ungrounded factual claims

#### Recipe Agent
- Receives: user intent, dietary context, available ingredients if known
- Does:
  - Phase 1: retrieval-first lookup from VectorDB or another fast store
  - Phase 2: fallback synthesis if retrieval misses
  - Phase 3: optional grounding and normalization into canonical structured recipe output
- Returns: quick candidate availability plus finalized structured recipe data conforming to recipe and canvas schemas
- Constraint: should expose "quick candidate available" separately from "full recipe finalized" so the Main Agent does not wait unnecessarily to acknowledge the user

#### Image Inference Agent
- Receives: camera frames plus context prompt from Main Agent
- Does: passes frames to a vision-capable model and interprets the result in cooking context
- Returns: structured analysis (what it sees, assessment, suggested action)

#### Render Agent
- Receives: `{ intent: string, context: string, canvas_state: json }` — canvas state includes exact JSON of both **active** and **staged** components
- Does: decides which components to add, stage, commit, swap, update, or remove; emits JSONL ops; uses `update` for existing IDs; orders ops topologically
- Returns: JSONL stream of canvas operations — one typed op per line, with progressive partial updates
- Constraint: render work is explicitly decoupled from speech timing and must not block the first spoken acknowledgement

### 4.13 Invocation Pattern

The Main Agent uses tool calling via the OpenAI Responses API or an equivalent realtime-capable orchestration layer. Sub-agents are defined as tools. The orchestrator may call them sequentially or in parallel depending on the turn, but the long-term target is **tool concurrency by default** where latency allows.

All agent communication is structured JSON or typed events — no free text between agents.

### 4.14 Generation and Versioning Semantics

Every user turn and tool run should conceptually carry:
- `turn_id`
- `generation_id`

If a newer turn starts:
- older speech must stop
- stale tool results must be discarded or treated as advisory only
- stale canvas commits must not overwrite current user context

These semantics are required for responsiveness and interruption safety.

### 4.15 Current Runtime Reality vs Long-Term Target

The current codebase already supports part of this design, but not all of it.

#### Current runtime reality
- an immediate first reply exists
- status updates exist
- the Render Agent streams canvas ops
- the Recipe Agent is still effectively blocking for grounded recipe work
- true realtime audio streaming is not the current runtime
- true speculative staging and commit/swap are only partially realized

#### Long-term target
- continuous audio input and output
- event-stream orchestration
- cancellable speech
- tool concurrency as the default behavior
- speculative but safe conversation
- generation-aware stale-result handling

---

## 5. Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React (framework TBD) |
| Canvas renderer | React component tree; 9-zone CSS grid; typed components mapped by type; skeleton streaming |
| Backend | Python, FastAPI |
| Agent harness | LangChain / LangGraph |
| LLM | OpenAI Responses API (dev: Gemma 4 27B via LM Studio) |
| Real-time transport | WebSocket |
| STT | Realtime streaming STT preferred long-term; turn-based fallback acceptable during migration |
| TTS | Realtime streaming TTS preferred long-term; cancellable speech output required |
| Session store | Supabase Postgres (Upstash Redis if latency requires) |
| Vector DB | Supabase pgvector — recipes only |
| Render agent catalog | Inline typed component catalog in system prompt (no vector search) |
| JSONL streaming | Render agent streams one op per line; `JSONStreamHealer` parses partials in real time |
| Recipe data | LLM generated on demand + user-addable (scraped dataset TBD) |
| Auth | Anonymous sessions v1, accounts TBD |
| Deployment | TBD |

---

## 6. Data Models

### 6.1 Session
```
session_id        uuid (PK)
created_at        timestamp
last_active       timestamp
conversation      jsonb        -- array of {role, content, timestamp}
active_recipe_id  uuid | null
current_step      integer | null
canvas_state      jsonb        -- map of component_id -> component
preferences       jsonb        -- TBD
```

### 6.1a Long-Term Runtime State (Conceptual)
```
conversation_state      jsonb / in-memory   -- live dialogue controller state
live_turn_id            uuid | null         -- active user turn
generation_id           integer | null      -- monotonic turn generation for interruption safety
speech_state            jsonb               -- active speech stream metadata
active_tool_runs        jsonb               -- in-flight tool invocations keyed by turn/generation
speculative_claims      jsonb               -- user-visible claims not yet grounded
pending_canvas_actions  jsonb               -- not-yet-committed canvas work for current generation
interruption_generation integer | null      -- latest interrupt boundary
```

### 6.2 Recipe
```
recipe_id         uuid (PK)
title             text
description       text
duration_minutes  integer
servings          integer
tags              text[]
steps             jsonb        -- array of {step_number, instruction, tip}
embedding         vector(1536)
source            text         -- "generated" | "user" | "scraped"
created_at        timestamp
```

---

## 7. Key User Flows

### 7.1 Starting a Cook

1. User opens app, sees blank canvas with mic icon
2. User says "I want to make pasta"
3. Partial transcript streams to the backend
4. Main Agent decides this request can use speculative-first speech
5. TTS begins a short acknowledgement immediately
6. Main Agent launches Recipe Agent and Render Agent work in parallel
7. Recipe Agent returns quick candidates, then final structured options if needed
8. Render Agent emits `add` operations for recipe cards
9. TTS grounds and completes the response: "Here are a few options, which one?"
10. User picks one verbally
11. Canvas transitions to step-view for step 1
12. Cook begins

### 7.2 Camera Check

1. User says "is this good?"
2. Partial transcript or final transcript reaches the Main Agent
3. TTS acknowledges immediately: "Let me see"
4. Render Agent emits `add` for the camera component without blocking speech
5. Frontend captures frames and sends them to the backend
6. Image Inference Agent analyzes frames
7. Main Agent refines or completes the spoken answer with grounded assessment
8. Render Agent emits `remove` for camera and `update` on the current step-view if mutation is needed

### 7.3 Proactive Parallel Task

1. User confirms step 3 started (chicken searing)
2. Main Agent determines an available wait window from recipe context
3. Without being asked, it emits `add` for a suggestion component
4. TTS: "While that's going, chop your garlic — you've got time"
5. User completes task and says "done"
6. Suggestion is removed and step-view is focused

### 7.4 Recipe Mutation

1. Camera analysis returns "chicken appears undercooked"
2. Main Agent instructs Render Agent to insert a new step
3. Canvas step-view updates to show "cook chicken more, check again in 2 minutes"
4. Timer is added automatically
5. User says "remove that step, I like it pink"
6. Agent removes the inserted step and responds verbally

### 7.5 User Interrupts Assistant Mid-Reply

1. Assistant is in the middle of a spoken response
2. User starts speaking
3. Frontend emits interruption input immediately
4. Speech stream is cancelled within the interruption latency budget
5. A new `turn_id` and `generation_id` are created
6. Any stale tool results from the prior generation are ignored or treated as advisory only
7. Main Agent prioritizes the new utterance and responds accordingly

### 7.6 Retrieval Miss Without Fabricated Confidence

1. User asks for a recipe idea
2. Assistant acknowledges immediately without claiming a specific recipe was found
3. Recipe retrieval misses
4. Recipe Agent falls back to synthesis
5. Assistant continues naturally with generated options once grounded output is ready

---

## 8. Non-Goals (v1)

- Mobile app (web only)
- User accounts and persistent history across devices
- Social or sharing features
- Nutritional tracking
- Shopping list generation
- Multi-language support
- Offline mode
- Video or animated step instructions

---

## 9. Open Questions

| # | Question | Owner | Priority |
|---|----------|-------|----------|
| 1 | Assistant name and personality definition | Oleg | High |
| 2 | ~~Component visual design and layout system~~ — resolved by Rendering Architecture Spec | — | — |
| 3 | STT final choice: WASM Whisper vs Web Speech API vs hosted realtime STT | Oleg | Medium |
| 4 | Recipe data source: generate on demand vs seed dataset | Oleg | Medium |
| 5 | Production LLM: OpenAI GPT-4o vs other hosted model | Oleg | Medium |
| 6 | ~~Canvas position system: token-based vs coordinate-based~~ — resolved: 9-zone named CSS grid with per-type default positions; agent never specifies zone | — | — |
| 7 | Session persistence: how long before a session expires | Oleg | Low |
| 8 | Upstash Redis: add from day one or wait for latency issues | Oleg | Low |
| 9 | ~~Design snippet index: manual curation vs auto-generated~~ — resolved: inline typed component catalog in system prompt; no snippet index | — | — |
| 10 | Realtime transport evolution: raw WebSocket only vs dedicated realtime media channel later | Oleg | Medium |
| 11 | Endpointing and barge-in strategy for streaming speech input and output | Oleg | High |

---

## 10. Success Metrics (Personal / v1)

- Can complete a full cook from "I want to make X" to final step without touching a keyboard
- Camera check round trip feels under 3 seconds
- Proactive suggestions fire at least once per cook naturally
- Canvas transitions feel smooth and intentional, not jarring
- The assistant feels like a character, not a tool

---

## 11. Long-Term Responsiveness Acceptance Scenarios

### Conversation responsiveness
- User asks for a recipe idea; assistant acknowledges immediately and grounds the answer when recipe results arrive.
- User asks "is this done?"; assistant acknowledges immediately, opens camera, then refines after image analysis.
- User says something vague; assistant asks a short clarifying question without blocking on tools.
- User interrupts while the assistant is speaking; speech stops and the new turn takes precedence.

### Speculation safety
- Retrieval miss: assistant does not falsely claim it found a recipe before fallback generation completes.
- Vision lag: assistant does not describe the image before image analysis returns.
- Stale result: old tool response is ignored after a newer user turn starts.

### UI responsiveness
- Assistant can speak before a recipe grid fully renders.
- A text-card clarification prompt can appear independently of speech timing.
- Background staged UI does not leak visible junk.
- Canvas does not regress when the user barges in mid-render.

### Failure handling
- Recipe Agent timeout still yields a useful fallback response.
- Render Agent timeout does not block short spoken acknowledgement.
- WebSocket reconnect during an active turn does not surface stale generation output as current truth.
- TTS stream cancellation mid-utterance is treated as a normal control path, not an error.

---

*This PRD reflects decisions made through design conversation in April-May 2026. The long-term architecture is intentionally more ambitious than the current runtime. The "Current Runtime Reality vs Long-Term Target" section is the source of truth when distinguishing implemented behavior from target behavior.*
