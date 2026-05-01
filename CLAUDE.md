# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Start everything
```bash
make dev          # starts both services via concurrently (web on :5173, api on :8000)
make install      # npm install + pip install -r apps/api/requirements.txt
```

### Frontend (`apps/web`)
```bash
npm run dev --workspace=apps/web           # Vite dev server
npm run type-check --workspace=apps/web    # tsc --noEmit
npm run test --workspace=apps/web          # vitest run (no watch)
npm run test:coverage --workspace=apps/web # vitest with v8 coverage
npm run build --workspace=apps/web         # type-check + vite build
```

Run a single test file:
```bash
npm run test --workspace=apps/web -- src/canvas/reducer.test.ts
```

### Backend (`apps/api`)
```bash
uvicorn apps.api.app.main:app --reload --port 8000           # dev server
python3 -m pytest apps/api/tests -v                          # full suite
python3 -m pytest apps/api/tests/test_session_loader.py -v   # single file
```

### Shared types (`packages/types`)
```bash
npm run build --workspace=packages/types   # compile TS → dist/
```
Must be rebuilt after changes to `packages/types/src/index.ts` before the frontend picks them up.

### Agent packages (`packages/agents`)
```bash
python3 -m pytest packages/agents/render_agent/tests -v   # render-agent tests
```

---

## Architecture

### Monorepo layout
- `apps/web` — React + Vite frontend (TypeScript)
- `apps/api/app` — FastAPI backend app package (Python 3.9+)
- `packages/agents` — decision-agent packages kept in one place:
  - `main_assistant` — orchestrator
  - `render_agent` — typed canvas rendering agent
  - `recipe_agent` — recipe lookup/generation interface
  - `image_inference_agent` — vision analysis interface
- `packages/types` — canonical schemas shared across both, with two mirrors:
  - `packages/types/src/index.ts` — TypeScript (consumed by `apps/web`)
  - `packages/types/python/canvas_types.py` — Pydantic mirror for Python consumers

### Real-time transport
All meaningful communication goes over a single persistent WebSocket at `ws://localhost:8000/ws`, not REST. The frontend never calls HTTP endpoints beyond the initial health check.

Connection lifecycle:
1. Client opens WS, sends `{ type: "init", session_id: "<uuid or null>" }`
2. Backend creates or resumes a Supabase session row, replies `{ type: "session_ready", session_id: "..." }`
3. Client persists `session_id` in `localStorage` and sets status to `connected`
4. Subsequent messages flow in both directions over the same socket

Frontend reconnects with exponential backoff (max 5 retries, cap 30s).

### Frontend state model
Two React contexts wrap the app in `main.tsx` (outer → inner):
- `WebSocketProvider` — owns the socket, exposes `status`, `sessionId`, `send`, and `subscribe(handler) → unsubscribe`
- `CanvasProvider` — owns canvas state as `Map<id, CanvasComponent>`, subscribes to WS `canvas_ops` messages and applies them via `canvasReducer`

The reducer (`src/canvas/reducer.ts`) is a pure function — testable without React. It handles five operation types: `add`, `update` (shallow-merge data), `remove`, `focus` (clears others), `move`.

### Backend session flow
Every agent turn will follow the pattern:
1. `SessionLoader(get_client()).load(session_id)` → returns `SessionContext` (conversation trimmed to 20 turns, active `Recipe` joined in)
2. `apps.api.app.services.agent_runner.run_agent_turn(...)` orchestrates the agent call
3. On success only: `loader.save(context)` → single atomic `UPDATE sessions SET ...`

`SessionContext` (in `apps/api/app/models.py`) is the enriched agent-facing object. `Session` is the raw DB row model. Don't conflate them.

### Database
Supabase Postgres. Two tables in `public` schema, both with RLS enabled (no policies — all access is via `service_role` key from the backend):
- `sessions` — one row per cooking session; `conversation`, `canvas_state`, `preferences` stored as JSONB
- `recipes` — recipe library; `embedding extensions.vector(1536)` with HNSW index for cosine similarity search; `steps` stored as JSONB

The backend connects using `SUPABASE_SERVICE_ROLE_KEY`. The frontend never connects to Supabase directly.

### Python compatibility
The codebase runs on Python 3.9. Use `Optional[X]` from `typing` instead of `X | None`, and add `from __future__ import annotations` at the top of files that use forward references. Pydantic models must not use `X | None` in field annotations — it causes a runtime error on 3.9 even with `__future__`.

### Environment variables
Copy `.env.example` to `.env` in the repo root. The API loads it via `python-dotenv`. The frontend reads `VITE_*` vars at build time via Vite.

### Testing approach
- Backend tests are all unit tests with mocked Supabase client (no live DB required). `conftest.py` provides WebSocket test fixtures; each new test file builds its own mock client inline.
- Frontend tests use vitest + jsdom. The canvas reducer has 100% branch coverage enforced via `vitest.config.ts` threshold.
- CI runs on every PR to `main`: frontend (type-check + build) and backend (install + health check smoke test). Pytest is not yet in CI — it runs locally only.
