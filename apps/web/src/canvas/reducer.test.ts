import { describe, expect, it, vi } from "vitest";
import type { CanvasState } from "@pair-cooking/types";
import { canvasReducer, validateOperation } from "./reducer";

// ─── Fixtures ────────────────────────────────────────────────────────────────

function emptyState(): CanvasState {
  return new Map();
}

function stateWith(...entries: Parameters<CanvasState["set"]>[]): CanvasState {
  const m: CanvasState = new Map();
  for (const [id, comp] of entries) m.set(id, comp);
  return m;
}

const recipeComp = {
  id: "r1",
  type: "text-card" as const,
  data: { body: "Pasta" },
  position: "center" as const,
  focused: false,
};

const stepComp = {
  id: "s1",
  type: "step-view" as const,
  data: { step_number: 1, total_steps: 3, recipe: "Test", instruction: "Boil water", tip: null },
  focused: false,
};

// ─── validateOperation ───────────────────────────────────────────────────────

describe("validateOperation", () => {
  it("accepts all valid op types", () => {
    for (const op of ["add", "update", "remove", "focus", "move", "skeleton"]) {
      expect(validateOperation({ op, id: "x" })).toBe(true);
    }
  });

  it("rejects null", () => expect(validateOperation(null)).toBe(false));
  it("rejects non-object", () => expect(validateOperation("add")).toBe(false));
  it("rejects unknown op type", () => expect(validateOperation({ op: "clear", id: "x" })).toBe(false));
  it("rejects missing id", () => expect(validateOperation({ op: "remove" })).toBe(false));
  it("rejects empty-string id", () => expect(validateOperation({ op: "remove", id: "" })).toBe(false));
  it("rejects non-string id", () => expect(validateOperation({ op: "remove", id: 42 })).toBe(false));
});

// ─── add ─────────────────────────────────────────────────────────────────────

describe("add", () => {
  it("adds a component to an empty state", () => {
    const next = canvasReducer(emptyState(), {
      op: "add",
      id: "r1",
      type: "text-card",
      data: recipeComp.data,
      position: "center",
    });
    expect(next.size).toBe(1);
    expect(next.get("r1")).toMatchObject({ id: "r1", type: "text-card", position: "center" });
  });

  it("preserves existing entries when adding", () => {
    const state = stateWith(["r1", recipeComp]);
    const next = canvasReducer(state, { op: "add", id: "s1", type: "step-view", data: stepComp.data });
    expect(next.size).toBe(2);
  });

  it("upserts (shallow-merges data) on duplicate id", () => {
    const state = stateWith(["r1", recipeComp]);
    const next = canvasReducer(state, { op: "add", id: "r1", type: "text-card", data: { body: "Updated" } });
    expect(next.get("r1")?.data).toEqual({ body: "Updated" });
    expect(next.get("r1")?.skeleton).toBe(false);
  });

  it("replaces skeleton entry when add arrives for same id", () => {
    const skelState = canvasReducer(emptyState(), { op: "skeleton", id: "r1", type: "text-card" });
    const next = canvasReducer(skelState, { op: "add", id: "r1", type: "text-card", data: { body: "Hello" } });
    expect(next.get("r1")?.skeleton).toBe(false);
    expect((next.get("r1")?.data as { body: string }).body).toBe("Hello");
  });

  it("sets focused to false on new component", () => {
    const next = canvasReducer(emptyState(), { op: "add", id: "r1", type: "text-card", data: recipeComp.data });
    expect(next.get("r1")?.focused).toBe(false);
  });
});

// ─── skeleton ────────────────────────────────────────────────────────────────

describe("skeleton", () => {
  it("adds a skeleton placeholder with data null", () => {
    const next = canvasReducer(emptyState(), { op: "skeleton", id: "s1", type: "step-view" });
    expect(next.get("s1")).toMatchObject({ id: "s1", type: "step-view", data: null, skeleton: true });
  });

  it("is a no-op if id already exists", () => {
    const state = stateWith(["s1", stepComp]);
    const next = canvasReducer(state, { op: "skeleton", id: "s1", type: "step-view" });
    expect(next).toBe(state);
  });
});

// ─── update ──────────────────────────────────────────────────────────────────

describe("update", () => {
  it("merges data fields onto existing component", () => {
    const state = stateWith(["r1", recipeComp]);
    const next = canvasReducer(state, { op: "update", id: "r1", data: { body: "Updated" } });
    expect((next.get("r1")?.data as { body: string }).body).toBe("Updated");
  });

  it("does not mutate original state", () => {
    const state = stateWith(["r1", recipeComp]);
    canvasReducer(state, { op: "update", id: "r1", data: { body: "X" } });
    expect((state.get("r1")?.data as { body: string }).body).toBe("Pasta");
  });

  it("is a no-op for unknown id", () => {
    const state = stateWith(["r1", recipeComp]);
    const next = canvasReducer(state, { op: "update", id: "missing", data: { title: "X" } });
    expect(next).toBe(state);
  });
});

// ─── remove ──────────────────────────────────────────────────────────────────

describe("remove", () => {
  it("removes an existing component", () => {
    const state = stateWith(["r1", recipeComp], ["s1", stepComp]);
    const next = canvasReducer(state, { op: "remove", id: "r1" });
    expect(next.has("r1")).toBe(false);
    expect(next.has("s1")).toBe(true);
  });

  it("is a no-op for unknown id", () => {
    const state = stateWith(["r1", recipeComp]);
    const next = canvasReducer(state, { op: "remove", id: "ghost" });
    expect(next).toBe(state);
  });
});

// ─── focus ───────────────────────────────────────────────────────────────────

describe("focus", () => {
  it("sets focused on target and clears all others", () => {
    const state = stateWith(
      ["r1", { ...recipeComp, focused: true }],
      ["s1", { ...stepComp, focused: false }],
    );
    const next = canvasReducer(state, { op: "focus", id: "s1" });
    expect(next.get("r1")?.focused).toBe(false);
    expect(next.get("s1")?.focused).toBe(true);
  });

  it("clears all focused flags when id does not exist", () => {
    const state = stateWith(["r1", { ...recipeComp, focused: true }]);
    const next = canvasReducer(state, { op: "focus", id: "ghost" });
    expect(next.get("r1")?.focused).toBe(false);
  });

  it("works on empty state", () => {
    const next = canvasReducer(emptyState(), { op: "focus", id: "any" });
    expect(next.size).toBe(0);
  });
});

// ─── move ────────────────────────────────────────────────────────────────────

describe("move", () => {
  it("updates the position of an existing component", () => {
    const state = stateWith(["r1", recipeComp]);
    const next = canvasReducer(state, { op: "move", id: "r1", position: "corner-br" });
    expect(next.get("r1")?.position).toBe("corner-br");
  });

  it("is a no-op for unknown id", () => {
    const state = stateWith(["r1", recipeComp]);
    const next = canvasReducer(state, { op: "move", id: "ghost", position: "top" });
    expect(next).toBe(state);
  });
});

// ─── unknown op (runtime guard) ──────────────────────────────────────────────

describe("unknown op", () => {
  it("warns and returns same state", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const state = stateWith(["r1", recipeComp]);
    // Cast to bypass TS — simulates a malformed runtime message
    const next = canvasReducer(state, { op: "clear", id: "r1" } as unknown as Parameters<typeof canvasReducer>[1]);
    expect(next).toBe(state);
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });
});
