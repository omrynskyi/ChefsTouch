import React from "react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, act, fireEvent } from "@testing-library/react";
import type { CanvasComponent, CanvasMap, CanvasState } from "@pair-cooking/types";
import { Canvas } from "./Canvas";

// Framer-motion exit animations don't complete in jsdom — mock it as a transparent wrapper
vi.mock("framer-motion", () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  motion: new Proxy({}, {
    get: (_t, tag: string) =>
      ({ children, initial: _i, animate: _a, exit: _e, transition: _tr, ...rest }: Record<string, unknown>) =>
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (React as any).createElement(tag, rest, children),
  }),
}));

// ─── Context mocks ───────────────────────────────────────────────────────────

const mockSend = vi.fn();
const mockDispatch = vi.fn();

function activeState(...entries: [string, CanvasComponent][]): CanvasState {
  const m: CanvasMap = new Map(entries);
  return { active: m, staged: new Map() };
}

let mockCanvasState: CanvasState = { active: new Map(), staged: new Map() };

vi.mock("../contexts/CanvasContext", () => ({
  useCanvas: () => ({ state: mockCanvasState, dispatch: mockDispatch }),
}));

vi.mock("../contexts/WebSocketContext", () => ({
  useWebSocket: () => ({
    status: "connected",
    send: mockSend,
    subscribe: () => () => {},
    sessionId: null,
  }),
}));

// ─── Helpers ─────────────────────────────────────────────────────────────────

function renderCanvas(state: CanvasState) {
  mockCanvasState = state;
  return render(<Canvas />);
}

const EMPTY: CanvasState = { active: new Map(), staged: new Map() };

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("Canvas", () => {
  beforeEach(() => {
    mockCanvasState = EMPTY;
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders idle mic icon when canvas is empty", () => {
    const { container } = renderCanvas(EMPTY);
    expect(container.querySelector('[zone="center"]')?.textContent).toContain("🎙️");
    expect(container).toMatchSnapshot();
  });

  it("renders progress-bar in top zone", () => {
    const state = activeState(["p1", { id: "p1", type: "progress-bar", data: { current: 2, total: 6 } }]);
    const { container } = renderCanvas(state);
    const topZone = container.querySelector('[zone="top"]');
    expect(topZone).not.toBeNull();
    expect(topZone!.textContent).toContain("Step 2 of 6");
    expect(container).toMatchSnapshot();
  });

  it("renders alert in top zone", () => {
    const state = activeState(["a1", { id: "a1", type: "alert", data: { text: "Pan is too hot!", urgent: true } }]);
    const { container } = renderCanvas(state);
    const topZone = container.querySelector('[zone="top"]');
    expect(topZone!.textContent).toContain("Pan is too hot!");
    expect(container).toMatchSnapshot();
  });

  it("renders timer in corner-br zone", () => {
    const state = activeState(["t1", { id: "t1", type: "timer", data: { duration_seconds: 300, label: "Boiling", auto_start: false } }]);
    const { container } = renderCanvas(state);
    const zone = container.querySelector('[zone="corner-br"]');
    expect(zone!.textContent).toContain("Boiling");
    expect(container).toMatchSnapshot();
  });

  it("does not render assistant-message directly in canvas corner-tl", () => {
    const state = activeState(["sys-assistant-message", {
      id: "sys-assistant-message",
      type: "assistant-message",
      data: { text: "One sec, I'm on it." },
    }]);
    const { container } = renderCanvas(state);
    const zone = container.querySelector('[zone="corner-tl"]');
    expect(zone!.textContent).toBe("");
    expect(container).toMatchSnapshot();
  });

  it("renders suggestion in bottom zone", () => {
    const state = activeState(["s1", { id: "s1", type: "suggestion", data: { heading: "While you wait", body: "Chop the garlic.", action_label: "Got it" } }]);
    const { container } = renderCanvas(state);
    const zone = container.querySelector('[zone="bottom"]');
    expect(zone!.textContent).toContain("Chop the garlic.");
    expect(container).toMatchSnapshot();
  });

  it("renders step-view in center zone", () => {
    const state = activeState(["sv1", { id: "sv1", type: "step-view", data: { step_number: 1, total_steps: 6, recipe: "Pasta", instruction: "Boil water", tip: "Use lots of salt", tags: ["~10 min"], action: "next_step" } }]);
    const { container } = renderCanvas(state);
    const zone = container.querySelector('[zone="center"]');
    expect(zone!.textContent).toContain("Boil water");
    expect(container).toMatchSnapshot();
  });

  it("renders ingredient-list in left zone", () => {
    const state = activeState(["il1", { id: "il1", type: "ingredient-list", data: { items: [{ name: "Pasta", qty: "200g" }, { name: "Salt", qty: "1 tsp" }] } }]);
    const { container } = renderCanvas(state);
    const zone = container.querySelector('[zone="left"]');
    expect(zone!.textContent).toContain("Pasta");
    expect(zone!.textContent).toContain("200g");
    expect(container).toMatchSnapshot();
  });

  it("renders text-card in center zone with markdown", () => {
    const state = activeState(["tc1", { id: "tc1", type: "text-card", data: { body: "Use **fresh** pasta for _best_ results." } }]);
    const { container } = renderCanvas(state);
    const zone = container.querySelector('[zone="center"]');
    expect(zone!.querySelector("strong")!.textContent).toBe("fresh");
    expect(zone!.querySelector("em")!.textContent).toBe("best");
    expect(container).toMatchSnapshot();
  });

  it("renders text-card clarification input and submits free text", () => {
    const state = activeState(["tc1", {
      id: "tc1",
      type: "text-card",
      data: {
        body: "What protein do you want with the rice?",
        input_placeholder: "Type your answer",
        submit_label: "Answer",
        input_action_prefix: "User clarification:",
      },
    }]);
    const { getByPlaceholderText, getByText } = renderCanvas(state);

    fireEvent.change(getByPlaceholderText("Type your answer"), { target: { value: "salmon" } });
    fireEvent.click(getByText("Answer"));

    expect(mockSend).toHaveBeenCalledWith({ type: "action", action: "User clarification: salmon" });
  });

  it("renders camera in center zone", () => {
    const state = activeState(["cam1", { id: "cam1", type: "camera", data: { prompt: "Is the chicken cooked through?" } }]);
    const { container } = renderCanvas(state);
    const zone = container.querySelector('[zone="center"]');
    expect(zone!.textContent).toContain("Is the chicken cooked through?");
    expect(container).toMatchSnapshot();
  });

  it("renders recipe-grid with recipe-option children in center zone", () => {
    const state = activeState(
      ["grid1", { id: "grid1", type: "recipe-grid", data: {} }],
      ["r1", { id: "r1", type: "recipe-option", parent: "grid1", data: { title: "Carbonara", action: "select_carbonara" } }],
      ["r2", { id: "r2", type: "recipe-option", parent: "grid1", data: { title: "Aglio e Olio", action: "select_aglio" } }],
    );
    const { container } = renderCanvas(state);
    const zone = container.querySelector('[zone="center"]');
    expect(zone!.textContent).toContain("Carbonara");
    expect(zone!.textContent).toContain("Aglio e Olio");
    const allZones = container.querySelectorAll("[zone]");
    const recipeOptionOutsideGrid = Array.from(allZones).filter(
      (z) => z.getAttribute("zone") === "center" && z !== zone
    );
    expect(recipeOptionOutsideGrid).toHaveLength(0);
    expect(container).toMatchSnapshot();
  });

  it("renders skeleton placeholder for skeleton components", () => {
    const state = activeState(["sk1", { id: "sk1", type: "step-view", data: null, skeleton: true }]);
    const { container } = renderCanvas(state);
    const shimmer = container.querySelector(".skeleton-shimmer");
    expect(shimmer).not.toBeNull();
    expect(shimmer?.getAttribute("aria-hidden")).toBe("true");
    expect(container).toMatchSnapshot();
  });

  it("applies elevated class to focused components", () => {
    const state = activeState(["p1", { id: "p1", type: "progress-bar", data: { current: 3, total: 6 }, focused: true }]);
    const { container } = renderCanvas(state);
    expect(container.querySelector(".elevated")).not.toBeNull();
  });

  it("renders component when added to state", () => {
    const state = activeState(["p1", { id: "p1", type: "progress-bar", data: { current: 1, total: 6 } }]);
    const { container } = renderCanvas(state);
    expect(container.querySelector('[zone="top"]')!.textContent).toContain("Step 1 of 6");
  });

  it("removes component when it leaves state", () => {
    const state = activeState(["p1", { id: "p1", type: "progress-bar", data: { current: 1, total: 6 } }]);
    const { container, rerender } = renderCanvas(state);
    expect(container.querySelector('[zone="top"]')!.textContent).toContain("Step 1 of 6");

    mockCanvasState = EMPTY;
    act(() => { rerender(<Canvas />); });
    expect(container.querySelector('[zone="top"]')!.textContent).not.toContain("Step 1 of 6");
  });
});
