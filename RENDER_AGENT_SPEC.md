# AI Cooking Assistant — Rendering Architecture Spec

**Version:** 0.3
**Author:** Oleg Mrynskyi
**Status:** Active
**Last Updated:** April 2026

---

## Overview

This document specifies the rendering architecture for the agent-controlled canvas. The system uses a **Double-Buffered, Predictive Architecture** to eliminate LLM latency for common user transitions and **Progressive JSON Parsing** to achieve instantaneous, token-by-token UI updates.

The agent emits typed canvas operations as JSONL. The React canvas renderer maps each operation to a React component placed in a named CSS grid zone.

---

## Core Principles

1. **Double-Buffering:** The UI maintains an **Active Canvas** (visible) and a **Staging Area** (in-memory cache).
2. **Speculative Execution:** During idle time, the Orchestrator predicts next user actions and prompts the Agent to pre-generate UI into the Staging Area.
3. **Progressive Streaming:** The backend continuously patches incomplete JSON chunks into valid partial objects, allowing text to "type out" on the screen before the LLM finishes a turn.
4. **Topological Ordering:** Parents arrive before children; critical data arrives before supplementary data.

---

## Canvas Environments

The frontend maintains two logical environments for components:

| Environment | Visible? | Description |
| :--- | :--- | :--- |
| **Active Canvas** | Yes | Components currently visible to the user. |
| **Staging Area** | No | In-memory React state where components are pre-assembled and held. |

---

## Enhanced Operations Protocol

The agent emits one JSON object per line. The backend healer transforms raw LLM tokens into a stream of valid operations.

| Operation | Target | Description |
| :--- | :--- | :--- |
| `add` | Active | Immediately renders a new component on the visible canvas. |
| `stage` | Staging | Renders a component invisibly in memory for future use. |
| `commit` | Active | Instantly moves a component from Staging to Active. |
| `swap` | Both | Atomic switch: removes `out_id` from Active and commits `in_id` in its place. |
| `update` | Both | Replaces a component's data object (total replacement, not shallow merge). |
| `remove` | Both | Deletes a component from the canvas or memory. |
| `clear_staged`| Staging | Wipes all staged components from the cache. |
| `focus` | Active | Visually emphasizes target; clears focus from others. |
| `move` | Active | Relocates a component to a different grid zone. |

---

## Component Catalog & Default Zones

| Type | Default zone | Layer |
|------|-------------|-------|
| `step-view` | center | base |
| `progress-bar` | top | base |
| `timer` | corner-br | float |
| `suggestion` | bottom | float |
| `alert` | top | float |
| `recipe-grid` | center | base |
| `recipe-option` | _(child of recipe-grid)_ | — |
| `ingredient-list` | center | base |
| `camera` | center | base |
| `text-card` | center | base |

### Data schemas (Summary)
See `packages/types/src/index.ts` for full TypeScript interfaces. Components must be generated with enough data to populate their primary fields (e.g., `instruction` for `step-view`).

---

## Background Precomputation Loop

To achieve zero-latency for expected actions (e.g., "Next step"), the Orchestrator follows this speculative loop:

1. **Idle Detection:** The system waits for the Render Agent to finish an active turn.
2. **Action Prediction:** The Orchestrator predicts the most likely next user intent (e.g., "Advance to step 2").
3. **Pre-render Prompt:** The Orchestrator secretly sends a prompt to the Render Agent: *"Assume the user just said 'Next step'. Generate step 2 into the staging area."*
4. **Silent Staging:** The Agent emits `stage` operations. The user sees nothing, but the components are parsed and ready in the browser.
5. **Intent Match:** If the user performs the predicted action, the Orchestrator issues a `commit` or `swap` command. The UI updates in ~16ms.

---

## Streaming & Partial Updates

### JSONStreamHealer (Progressive Patching)
The backend does not wait for a JSON line to close (`\n`) before sending it to the client.

1. **Token Patching:** As tokens arrive (e.g., `{"op":"add","data":{"text":"Hell`), the healer uses a stack-based parser to append the necessary closing braces (`"}}`) to make it valid.
2. **Partial Events:** The healer emits `partial_update` messages to the frontend.
3. **Frontend Typing:** The React `reducer` merges these partial chunks into the state. Components (like `StepView`) re-render immediately, making text appear to stream or "type out" in real-time.

---

## Canvas State Summary (Agent Input)

The Agent receives the **exact JSON state** of both Active and Staged environments in its system prompt to ensure precise `update` operations.

```json
CANVAS STATE:
{
  "active": {
    "step-1": { "type": "step-view", "data": { "step_number": 1, "instruction": "Boil water" } }
  },
  "staged": {
    "step-2": { "type": "step-view", "data": { "step_number": 2, "instruction": "Add pasta" } }
  }
}
```

**Rule for Agent Updates:** If an ID exists in `active` or `staged`, use `update`. An `update` operation on a data object (e.g., `data: { items: [...] }`) replaces the entire nested object/array.

---

## Topological Ordering Rule

1. **Parents before children** — `recipe-grid` before `recipe-option`.
2. **Most important first** — `step-view` before `timer`.
3. **Within data — critical keys first** — `instruction` before `tags` before `action`.

---

## Open Questions

| # | Question | Priority |
|---|----------|----------|
| 1 | **Staging Invalidation:** How long do staged components live before being cleared? | Medium |
| 2 | **Conflict Resolution:** What happens if a background pre-render turn overlaps with a sudden user voice input? | High |
| 3 | **Partial State Flickering:** How to prevent React from flickering when a partial JSON string is momentarily invalid during patching? | Medium |
