import type {
  CanvasComponent,
  CanvasMap,
  CanvasOperation,
  CanvasState,
} from "@pair-cooking/types";

const VALID_OPS = new Set([
  "add", "update", "remove", "focus", "move", "skeleton",
  "stage", "commit", "swap", "clear_staged",
]);

export const INITIAL_CANVAS_STATE: CanvasState = {
  active: new Map(),
  staged: new Map(),
};

export function validateOperation(op: unknown): op is CanvasOperation {
  if (!op || typeof op !== "object") return false;
  const { op: opType, id } = op as Record<string, unknown>;
  if (!VALID_OPS.has(opType as string)) return false;
  if (opType === "clear_staged") return true;
  if (typeof id !== "string" || id.length === 0) return false;
  return true;
}

export function canvasReducer(state: CanvasState, op: CanvasOperation): CanvasState {
  switch (op.op) {
    case "skeleton": {
      if (state.active.has(op.id)) return state;
      const next: CanvasMap = new Map(state.active);
      next.set(op.id, { id: op.id, type: op.type, data: null, focused: false, skeleton: true });
      return { ...state, active: next };
    }

    case "add": {
      const existing = state.active.get(op.id);
      const component: CanvasComponent = existing
        ? { ...existing, data: { ...existing.data, ...op.data } as CanvasComponent["data"], skeleton: false }
        : { id: op.id, type: op.type, data: op.data, position: op.position, parent: op.parent, focused: false };
      const next: CanvasMap = new Map(state.active);
      next.set(op.id, component);
      return { ...state, active: next };
    }

    case "update": {
      if (state.active.has(op.id)) {
        const existing = state.active.get(op.id)!;
        const next: CanvasMap = new Map(state.active);
        next.set(op.id, { ...existing, data: op.data as CanvasComponent["data"] });
        return { ...state, active: next };
      }
      if (state.staged.has(op.id)) {
        const existing = state.staged.get(op.id)!;
        const next: CanvasMap = new Map(state.staged);
        next.set(op.id, { ...existing, data: op.data as CanvasComponent["data"] });
        return { ...state, staged: next };
      }
      return state;
    }

    case "remove": {
      if (state.active.has(op.id)) {
        const next: CanvasMap = new Map(state.active);
        next.delete(op.id);
        return { ...state, active: next };
      }
      if (state.staged.has(op.id)) {
        const next: CanvasMap = new Map(state.staged);
        next.delete(op.id);
        return { ...state, staged: next };
      }
      return state;
    }

    case "focus": {
      const next: CanvasMap = new Map(state.active);
      for (const [id, comp] of next) {
        next.set(id, { ...comp, focused: id === op.id });
      }
      return { ...state, active: next };
    }

    case "move": {
      const existing = state.active.get(op.id);
      if (!existing) return state;
      const next: CanvasMap = new Map(state.active);
      next.set(op.id, { ...existing, position: op.position });
      return { ...state, active: next };
    }

    case "stage": {
      const next: CanvasMap = new Map(state.staged);
      next.set(op.id, {
        id: op.id,
        type: op.type,
        data: op.data,
        position: op.position,
        parent: op.parent,
        focused: false,
      });
      return { ...state, staged: next };
    }

    case "commit": {
      const comp = state.staged.get(op.id);
      if (!comp) return state;
      const nextStaged: CanvasMap = new Map(state.staged);
      nextStaged.delete(op.id);
      const nextActive: CanvasMap = new Map(state.active);
      nextActive.set(op.id, comp);
      return { active: nextActive, staged: nextStaged };
    }

    case "swap": {
      const comp = state.staged.get(op.id);
      if (!comp) return state;
      const nextStaged: CanvasMap = new Map(state.staged);
      nextStaged.delete(op.id);
      const nextActive: CanvasMap = new Map(state.active);
      nextActive.delete(op.out_id);
      nextActive.set(op.id, comp);
      return { active: nextActive, staged: nextStaged };
    }

    case "clear_staged": {
      if (state.staged.size === 0) return state;
      return { ...state, staged: new Map() };
    }

    default: {
      console.warn("[Canvas] unknown operation type, ignoring", op);
      return state;
    }
  }
}
