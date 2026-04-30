import { describe, expect, it, vi } from "vitest";
import type { CanvasMap, CanvasState } from "@pair-cooking/types";
import { canvasReducer, validateOperation, INITIAL_CANVAS_STATE } from "./reducer";

// ─── Fixtures ────────────────────────────────────────────────────────────────

function emptyState(): CanvasState {
  return { active: new Map(), staged: new Map() };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function activeMap(...entries: [string, any][]): CanvasMap {
  const m: CanvasMap = new Map();
  for (const [id, comp] of entries) m.set(id, comp);
  return m;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function stateWith(...entries: [string, any][]): CanvasState {
  return { active: activeMap(...entries), staged: new Map() };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function stagedWith(...entries: [string, any][]): CanvasState {
  return { active: new Map(), staged: activeMap(...entries) };
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
  data: { step_number: 1, total_steps: 3, recipe: "Test", instruction: "Boil water", tip: null as string | null | undefined },
  focused: false,
};

// ─── INITIAL_CANVAS_STATE ────────────────────────────────────────────────────

describe("INITIAL_CANVAS_STATE", () => {
  it("has empty active and staged maps", () => {
    expect(INITIAL_CANVAS_STATE.active.size).toBe(0);
    expect(INITIAL_CANVAS_STATE.staged.size).toBe(0);
  });
});

// ─── validateOperation ───────────────────────────────────────────────────────

describe("validateOperation", () => {
  it("accepts all id-bearing op types", () => {
    for (const op of ["add", "update", "remove", "focus", "move", "skeleton", "stage", "commit", "swap"]) {
      expect(validateOperation({ op, id: "x" })).toBe(true);
    }
  });

  it("accepts clear_staged without id", () => {
    expect(validateOperation({ op: "clear_staged" })).toBe(true);
  });

  it("rejects null", () => expect(validateOperation(null)).toBe(false));
  it("rejects non-object", () => expect(validateOperation("add")).toBe(false));
  it("rejects unknown op type", () => expect(validateOperation({ op: "clear", id: "x" })).toBe(false));
  it("rejects missing id for id-requiring ops", () => expect(validateOperation({ op: "remove" })).toBe(false));
  it("rejects empty-string id", () => expect(validateOperation({ op: "remove", id: "" })).toBe(false));
  it("rejects non-string id", () => expect(validateOperation({ op: "remove", id: 42 })).toBe(false));
});

// ─── add ─────────────────────────────────────────────────────────────────────

describe("add", () => {
  it("adds a component to active map", () => {
    const next = canvasReducer(emptyState(), {
      op: "add",
      id: "r1",
      type: "text-card",
      data: recipeComp.data,
      position: "center",
    });
    expect(next.active.size).toBe(1);
    expect(next.active.get("r1")).toMatchObject({ id: "r1", type: "text-card", position: "center" });
    expect(next.staged.size).toBe(0);
  });

  it("preserves existing entries when adding", () => {
    const state = stateWith(["r1", recipeComp]);
    const next = canvasReducer(state, { op: "add", id: "s1", type: "step-view", data: stepComp.data });
    expect(next.active.size).toBe(2);
  });

  it("upserts (shallow-merges data) on duplicate id", () => {
    const state = stateWith(["r1", recipeComp]);
    const next = canvasReducer(state, { op: "add", id: "r1", type: "text-card", data: { body: "Updated" } });
    expect(next.active.get("r1")?.data).toEqual({ body: "Updated" });
    expect(next.active.get("r1")?.skeleton).toBe(false);
  });

  it("replaces skeleton entry when add arrives for same id", () => {
    const skelState = canvasReducer(emptyState(), { op: "skeleton", id: "r1", type: "text-card" });
    const next = canvasReducer(skelState, { op: "add", id: "r1", type: "text-card", data: { body: "Hello" } });
    expect(next.active.get("r1")?.skeleton).toBe(false);
    expect((next.active.get("r1")?.data as { body: string }).body).toBe("Hello");
  });

  it("sets focused to false on new component", () => {
    const next = canvasReducer(emptyState(), { op: "add", id: "r1", type: "text-card", data: recipeComp.data });
    expect(next.active.get("r1")?.focused).toBe(false);
  });

  it("does not touch staged map", () => {
    const state: CanvasState = { active: new Map(), staged: activeMap(["s2", stepComp]) };
    const next = canvasReducer(state, { op: "add", id: "r1", type: "text-card", data: recipeComp.data });
    expect(next.staged.size).toBe(1);
  });
});

// ─── skeleton ────────────────────────────────────────────────────────────────

describe("skeleton", () => {
  it("adds a skeleton placeholder with data null to active", () => {
    const next = canvasReducer(emptyState(), { op: "skeleton", id: "s1", type: "step-view" });
    expect(next.active.get("s1")).toMatchObject({ id: "s1", type: "step-view", data: null, skeleton: true });
  });

  it("is a no-op if id already exists in active", () => {
    const state = stateWith(["s1", stepComp]);
    const next = canvasReducer(state, { op: "skeleton", id: "s1", type: "step-view" });
    expect(next).toBe(state);
  });
});

// ─── update ──────────────────────────────────────────────────────────────────

describe("update", () => {
  it("replaces data entirely (total replacement, not merge)", () => {
    const state = stateWith(["r1", { ...recipeComp, data: { body: "Pasta" } }]);
    const next = canvasReducer(state, { op: "update", id: "r1", data: { body: "Updated" } });
    expect(next.active.get("r1")?.data).toEqual({ body: "Updated" });
  });

  it("does not carry over fields not present in new data", () => {
    const state = stateWith(["s1", stepComp]);
    const next = canvasReducer(state, { op: "update", id: "s1", data: { step_number: 2, total_steps: 3, recipe: "X", instruction: "New" } });
    const d = next.active.get("s1")?.data as Record<string, unknown>;
    expect(d.step_number).toBe(2);
    expect(d.tip).toBeUndefined();
  });

  it("does not mutate original state", () => {
    const state = stateWith(["r1", recipeComp]);
    canvasReducer(state, { op: "update", id: "r1", data: { body: "X" } });
    expect((state.active.get("r1")?.data as { body: string }).body).toBe("Pasta");
  });

  it("is a no-op for unknown id", () => {
    const state = stateWith(["r1", recipeComp]);
    const next = canvasReducer(state, { op: "update", id: "missing", data: { body: "X" } });
    expect(next).toBe(state);
  });

  it("updates component in staged map", () => {
    const state = stagedWith(["s1", stepComp]);
    const next = canvasReducer(state, { op: "update", id: "s1", data: { step_number: 2, total_steps: 3, recipe: "X", instruction: "New" } });
    expect((next.staged.get("s1")?.data as Record<string, unknown>).step_number).toBe(2);
  });
});

// ─── remove ──────────────────────────────────────────────────────────────────

describe("remove", () => {
  it("removes an existing component from active", () => {
    const state = stateWith(["r1", recipeComp], ["s1", stepComp]);
    const next = canvasReducer(state, { op: "remove", id: "r1" });
    expect(next.active.has("r1")).toBe(false);
    expect(next.active.has("s1")).toBe(true);
  });

  it("removes an existing component from staged", () => {
    const state = stagedWith(["s1", stepComp]);
    const next = canvasReducer(state, { op: "remove", id: "s1" });
    expect(next.staged.has("s1")).toBe(false);
  });

  it("is a no-op for unknown id", () => {
    const state = stateWith(["r1", recipeComp]);
    const next = canvasReducer(state, { op: "remove", id: "ghost" });
    expect(next).toBe(state);
  });
});

// ─── focus ───────────────────────────────────────────────────────────────────

describe("focus", () => {
  it("sets focused on target and clears all others in active", () => {
    const state = stateWith(
      ["r1", { ...recipeComp, focused: true }],
      ["s1", { ...stepComp, focused: false }],
    );
    const next = canvasReducer(state, { op: "focus", id: "s1" });
    expect(next.active.get("r1")?.focused).toBe(false);
    expect(next.active.get("s1")?.focused).toBe(true);
  });

  it("clears all focused flags when id does not exist", () => {
    const state = stateWith(["r1", { ...recipeComp, focused: true }]);
    const next = canvasReducer(state, { op: "focus", id: "ghost" });
    expect(next.active.get("r1")?.focused).toBe(false);
  });

  it("works on empty state", () => {
    const next = canvasReducer(emptyState(), { op: "focus", id: "any" });
    expect(next.active.size).toBe(0);
  });
});

// ─── move ────────────────────────────────────────────────────────────────────

describe("move", () => {
  it("updates the position of an existing component in active", () => {
    const state = stateWith(["r1", recipeComp]);
    const next = canvasReducer(state, { op: "move", id: "r1", position: "corner-br" });
    expect(next.active.get("r1")?.position).toBe("corner-br");
  });

  it("is a no-op for unknown id", () => {
    const state = stateWith(["r1", recipeComp]);
    const next = canvasReducer(state, { op: "move", id: "ghost", position: "top" });
    expect(next).toBe(state);
  });
});

// ─── stage ───────────────────────────────────────────────────────────────────

describe("stage", () => {
  it("adds component to staged map only", () => {
    const next = canvasReducer(emptyState(), {
      op: "stage",
      id: "s2",
      type: "step-view",
      data: { step_number: 2, total_steps: 3, recipe: "Test", instruction: "Add pasta" },
    });
    expect(next.staged.has("s2")).toBe(true);
    expect(next.active.has("s2")).toBe(false);
  });

  it("does not affect existing active components", () => {
    const state = stateWith(["r1", recipeComp]);
    const next = canvasReducer(state, {
      op: "stage",
      id: "s2",
      type: "step-view",
      data: stepComp.data,
    });
    expect(next.active.size).toBe(1);
    expect(next.staged.size).toBe(1);
  });
});

// ─── commit ──────────────────────────────────────────────────────────────────

describe("commit", () => {
  it("moves component from staged to active", () => {
    const state = stagedWith(["s2", stepComp]);
    const next = canvasReducer(state, { op: "commit", id: "s2" });
    expect(next.active.has("s2")).toBe(true);
    expect(next.staged.has("s2")).toBe(false);
  });

  it("is a no-op if id not in staged", () => {
    const state = emptyState();
    const next = canvasReducer(state, { op: "commit", id: "ghost" });
    expect(next).toBe(state);
  });

  it("preserves existing active components", () => {
    const state: CanvasState = { active: activeMap(["r1", recipeComp]), staged: activeMap(["s2", stepComp]) };
    const next = canvasReducer(state, { op: "commit", id: "s2" });
    expect(next.active.has("r1")).toBe(true);
    expect(next.active.has("s2")).toBe(true);
  });
});

// ─── swap ────────────────────────────────────────────────────────────────────

describe("swap", () => {
  it("removes out_id from active and commits id from staged", () => {
    const state: CanvasState = {
      active: activeMap(["s1", stepComp]),
      staged: activeMap(["s2", { ...stepComp, id: "s2" }]),
    };
    const next = canvasReducer(state, { op: "swap", id: "s2", out_id: "s1" });
    expect(next.active.has("s2")).toBe(true);
    expect(next.active.has("s1")).toBe(false);
    expect(next.staged.has("s2")).toBe(false);
  });

  it("is a no-op if in_id not in staged", () => {
    const state = stateWith(["s1", stepComp]);
    const next = canvasReducer(state, { op: "swap", id: "ghost", out_id: "s1" });
    expect(next).toBe(state);
  });
});

// ─── clear_staged ─────────────────────────────────────────────────────────────

describe("clear_staged", () => {
  it("wipes all staged components", () => {
    const state = stagedWith(["a", stepComp], ["b", recipeComp]);
    const next = canvasReducer(state, { op: "clear_staged" });
    expect(next.staged.size).toBe(0);
    expect(next.active.size).toBe(0);
  });

  it("is a no-op if staged is already empty", () => {
    const state = emptyState();
    const next = canvasReducer(state, { op: "clear_staged" });
    expect(next).toBe(state);
  });

  it("does not affect active map", () => {
    const state: CanvasState = {
      active: activeMap(["r1", recipeComp]),
      staged: activeMap(["s2", stepComp]),
    };
    const next = canvasReducer(state, { op: "clear_staged" });
    expect(next.active.has("r1")).toBe(true);
    expect(next.staged.size).toBe(0);
  });
});

// ─── unknown op (runtime guard) ──────────────────────────────────────────────

describe("unknown op", () => {
  it("warns and returns same state", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const state = stateWith(["r1", recipeComp]);
    const next = canvasReducer(state, { op: "clear", id: "r1" } as unknown as Parameters<typeof canvasReducer>[1]);
    expect(next).toBe(state);
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });
});
