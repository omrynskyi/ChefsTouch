# AI Cooking Assistant — Product Requirements Document

**Version:** 0.1  
**Author:** Oleg Mrynskyi  
**Status:** Draft  
**Last Updated:** April 2026

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

The agent does not return text responses. It emits structured canvas operations that the frontend applies to maintain canvas state. This means the agent can add components, update their content, move them, focus them, or remove them at any point during a conversation turn, not just in response to a user message.

### 2.3 Voice First

The primary input channel is voice. The user speaks naturally and the assistant responds both verbally via TTS and visually via canvas operations. Text input is not a priority for v1.

### 2.4 Camera as Input

The camera is an on-demand input channel, not a persistent feed. It is triggered when the user says something like "look at this" or "is this good." The agent renders a camera component, captures a few frames, analyzes them, dismisses the camera view, and responds verbally and visually based on what it saw.

---

## 3. Features

### 3.1 Voice Conversation Loop

The user speaks. Audio is captured in the browser and sent to an STT service. The transcript is passed to the Main Assistant along with session context. The Main Assistant responds with a verbal reply (passed to TTS) and a sequence of canvas operations.

**Behavior:**
- Listening is always active when no other input is in progress
- Responses are short, conversational, and occasionally quirky
- The assistant does not wait to be asked — it proactively speaks and updates the canvas when it determines something is useful

### 3.2 Proactive Parallel Task Suggestions

During a cook, the agent tracks the current step and estimates available time windows. When the user is waiting on a step (e.g. chicken searing for 6 minutes), the agent proactively suggests a parallel task and updates the canvas to show it without the user asking.

**Trigger:** Inferred from conversation context, not timers or computer vision.

### 3.3 Camera Analysis

When the user invokes a visual check ("look at this," "is this good," "what do I do with this"), the agent:

1. Responds verbally to acknowledge
2. Emits a canvas operation to render the Camera component
3. Frontend captures a few frames automatically once the camera is active
4. Frames are sent to the vision model
5. Agent receives analysis, dismisses camera, responds verbally and updates canvas

**No persistent camera feed. No overlays. Frames only.**

### 3.4 Live Recipe Mutation

The recipe displayed on the canvas is a living document. The agent can insert, modify, or remove steps based on what it observes or decides during the cook. For example if the agent sees undercooked chicken via the camera it inserts a "cook chicken more" step immediately after the current one.

The user can reject mutations verbally ("remove that step, I like it") and the agent removes it.

### 3.5 Canvas Component Library (v1)

The agent picks from a fixed set of components. Each component has a defined JSON schema. The frontend has a renderer for each type. Visual design is TBD — schemas are defined here, not layouts.

#### Component Schemas

**recipe-card**
```json
{
  "type": "recipe-card",
  "id": "string",
  "data": {
    "title": "string",
    "description": "string",
    "duration_minutes": "number",
    "servings": "number",
    "tags": ["string"]
  }
}
```

**step-view**
```json
{
  "type": "step-view",
  "id": "string",
  "data": {
    "step_number": "number",
    "total_steps": "number",
    "instruction": "string",
    "tip": "string | null"
  }
}
```

**timer**
```json
{
  "type": "timer",
  "id": "string",
  "data": {
    "duration_seconds": "number",
    "label": "string",
    "auto_start": "boolean"
  }
}
```

**camera**
```json
{
  "type": "camera",
  "id": "string",
  "data": {
    "prompt": "string"
  }
}
```

**suggestion**
```json
{
  "type": "suggestion",
  "id": "string",
  "data": {
    "heading": "string",
    "body": "string",
    "action_label": "string | null"
  }
}
```

**text-card**
```json
{
  "type": "text-card",
  "id": "string",
  "data": {
    "body": "string"
  }
}
```

### 3.6 Canvas Operations

The agent emits a stream of operations over WebSocket. The frontend maintains a canvas state map keyed by component ID and applies each operation as it arrives.

| Operation | Description |
|-----------|-------------|
| `add` | Render a new component |
| `update` | Update data on an existing component |
| `remove` | Remove a component from the canvas |
| `focus` | Bring a component to visual prominence |
| `move` | Reposition a component (position tokens: `top`, `bottom`, `left`, `right`, `center`, `bottom-right`, etc.) |

**Example operation stream:**
```json
{ "op": "add", "id": "step-3", "type": "step-view", "data": { ... }, "position": "center" }
{ "op": "add", "id": "timer-1", "type": "timer", "data": { "duration_seconds": 360, "label": "Chicken", "auto_start": true }, "position": "bottom-right" }
{ "op": "remove", "id": "recipe-card-1" }
```

---

## 4. Agent Architecture

### 4.1 Overview

The system uses a multi-agent architecture orchestrated by a Main Assistant. The Main Assistant handles conversation, decides which sub-agents to invoke, and composes the final canvas operation stream and TTS response.

### 4.2 Agents

#### Main Assistant (Orchestrator)
- Receives: STT transcript, optional camera frames, session context from DB
- Decides: which sub-agents to call, what to say, what canvas operations to emit
- Returns: TTS text + ordered list of canvas operations
- Personality: TBD — short, quirky, anticipatory, friend-like

#### Recipe Agent
- Receives: user intent, dietary context, available ingredients if known
- Does: queries VectorDB for matching recipes, falls back to LLM generation if no match
- Returns: structured recipe data conforming to recipe-card and step-view schemas

#### Image Inference Agent
- Receives: camera frames + context prompt from Main Assistant
- Does: passes frames to vision-capable model, interprets result in cooking context
- Returns: structured analysis (what it sees, assessment, suggested action)

#### Render Agent
- Receives: conversation state, current canvas state, Main Assistant intent
- Does: decides which components to add/update/remove/move
- Returns: ordered list of canvas operations

### 4.3 Invocation Pattern

The Main Assistant uses tool calling via the OpenAI Responses API. Sub-agents are defined as tools. The orchestrator calls them sequentially or in parallel depending on the turn, then composes the final response. All agent communication is structured JSON — no free text between agents.

### 4.4 Session Context

On every turn the API layer reads the current session from the database and injects it into the Main Assistant context. After the turn completes the updated session is written back. Session state includes:

- Conversation history (last N turns)
- Active recipe (if any)
- Current step index
- Current canvas state (component ID map)
- User preferences (TBD)

---

## 5. Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React (framework TBD) |
| Backend | Python, FastAPI |
| Agent harness | LangChain / LangGraph |
| LLM | OpenAI Responses API (dev: Gemma 4 27B via LM Studio) |
| Real-time transport | WebSocket |
| STT | Browser-based Whisper (whisper.cpp WASM) or Web Speech API — TBD |
| TTS | OpenAI TTS via Responses API |
| Session store | Supabase Postgres (Upstash Redis if latency requires) |
| Vector DB | Supabase pgvector |
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
3. STT transcribes, sends to backend
4. Main Assistant calls Recipe Agent
5. Recipe Agent returns 2-3 matching recipes
6. Render Agent emits `add` operations for recipe cards
7. TTS: "Here are a few options, which one?"
8. User picks one verbally
9. Canvas transitions to step-view for step 1
10. Cook begins

### 7.2 Camera Check

1. User says "is this good?"
2. TTS: "Let me see"
3. Render Agent emits `add` for camera component
4. Frontend captures frames, sends to backend
5. Image Inference Agent analyzes frames
6. Main Assistant composes response
7. Render Agent emits `remove` for camera, `update` on current step-view if mutation needed
8. TTS delivers assessment

### 7.3 Proactive Parallel Task

1. User confirms step 3 started (chicken searing)
2. Main Assistant determines ~6 minute wait window from recipe context
3. Without being asked, emits `add` for suggestion component
4. TTS: "While that's going, chop your garlic — you've got time"
5. User completes task, says "done"
6. Suggestion removed, step-view focused

### 7.4 Recipe Mutation

1. Camera analysis returns "chicken appears undercooked"
2. Main Assistant instructs Render Agent to insert a new step
3. Canvas step-view updates to show "cook chicken more, check again in 2 minutes"
4. Timer added automatically
5. User says "remove that step, I like it pink"
6. Agent removes the inserted step, responds verbally

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
| 2 | Component visual design and layout system | Oleg | High |
| 3 | STT final choice: WASM Whisper vs Web Speech API | Oleg | Medium |
| 4 | Recipe data source: generate on demand vs seed dataset | Oleg | Medium |
| 5 | Production LLM: OpenAI GPT-4o vs other hosted model | Oleg | Medium |
| 6 | Canvas position system: token-based vs coordinate-based | Oleg | Medium |
| 7 | Session persistence: how long before a session expires | Oleg | Low |
| 8 | Upstash Redis: add from day one or wait for latency issues | Oleg | Low |

---

## 10. Success Metrics (Personal / v1)

- Can complete a full cook from "I want to make X" to final step without touching a keyboard
- Camera check round trip feels under 3 seconds
- Proactive suggestions fire at least once per cook naturally
- Canvas transitions feel smooth and intentional, not jarring
- The assistant feels like a character, not a tool

---

*This PRD reflects decisions made through design conversation in April 2026. All open questions should be resolved before v1 development begins in earnest.*
