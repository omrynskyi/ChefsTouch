import type { CanvasComponent, CanvasOperation, CanvasState } from "@pair-cooking/types";

const VALID_OPS = new Set(["add", "update", "remove", "focus", "move", "skeleton"]);

export function validateOperation(op: unknown): op is CanvasOperation {
  if (!op || typeof op !== "object") return false;
  const { op: opType, id } = op as Record<string, unknown>;
  if (!VALID_OPS.has(opType as string)) return false;
  if (typeof id !== "string" || id.length === 0) return false;
  return true;
}

export function canvasReducer(state: CanvasState, op: CanvasOperation): CanvasState {
  const next = new Map(state);

  switch (op.op) {
    case "skeleton": {
      if (next.has(op.id)) return state;
      next.set(op.id, { id: op.id, type: op.type, data: null, focused: false, skeleton: true });
      return next;
    }

    case "add": {
      const existing = next.get(op.id);
      const component: CanvasComponent = existing
        ? { ...existing, data: { ...existing.data, ...op.data } as CanvasComponent["data"], skeleton: false }
        : { id: op.id, type: op.type, data: op.data, position: op.position, parent: op.parent, focused: false };
      next.set(op.id, component);
      return next;
    }

    case "update": {
      const existing = next.get(op.id);
      if (!existing) return state;
      next.set(op.id, {
        ...existing,
        data: { ...existing.data, ...op.data } as CanvasComponent["data"],
      });
      return next;
    }

    case "remove": {
      if (!next.has(op.id)) return state;
      next.delete(op.id);
      return next;
    }

    case "focus": {
      for (const [id, comp] of next) {
        next.set(id, { ...comp, focused: id === op.id });
      }
      return next;
    }

    case "move": {
      const existing = next.get(op.id);
      if (!existing) return state;
      next.set(op.id, { ...existing, position: op.position });
      return next;
    }

    default: {
      console.warn("[Canvas] unknown operation type, ignoring", op);
      return state;
    }
  }
}
