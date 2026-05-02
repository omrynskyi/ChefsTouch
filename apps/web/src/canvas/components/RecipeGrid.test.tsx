import React from "react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";

afterEach(() => cleanup());
import type { CanvasComponent } from "@pair-cooking/types";
import { RecipeGrid } from "./RecipeGrid";

// Mock framer-motion as a transparent pass-through (same as Canvas.test.tsx)
vi.mock("framer-motion", () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  motion: new Proxy({}, {
    get: (_t, tag: string) =>
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ({ children, initial: _i, animate: _a, exit: _e, transition: _tr, ...rest }: Record<string, unknown>) =>
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (React as any).createElement(tag, rest, children),
  }),
}));

const mockSend = vi.fn();
vi.mock("../../contexts/WebSocketContext", () => ({
  useWebSocket: () => ({ send: mockSend }),
}));

function makeChild(id: string, title: string): CanvasComponent<"recipe-option"> {
  return {
    id,
    type: "recipe-option",
    data: { title, action: `select_${id}` },
    focused: false,
  };
}

describe("RecipeGrid", () => {
  beforeEach(() => { mockSend.mockClear(); });

  it("renders with no children without crashing", () => {
    const { container } = render(<RecipeGrid data={{}} children={[]} />);
    expect(container.querySelector(".recipe-grid")).not.toBeNull();
  });

  it("renders each child recipe option", () => {
    const children = [
      makeChild("r1", "Carbonara"),
      makeChild("r2", "Aglio e Olio"),
    ];
    const { getByText } = render(<RecipeGrid data={{}} children={children} />);
    expect(getByText("Carbonara")).toBeTruthy();
    expect(getByText("Aglio e Olio")).toBeTruthy();
  });

  it("renders the correct number of option buttons", () => {
    const children = [
      makeChild("r1", "Carbonara"),
      makeChild("r2", "Aglio e Olio"),
      makeChild("r3", "Cacio e Pepe"),
    ];
    const { getAllByRole } = render(<RecipeGrid data={{}} children={children} />);
    expect(getAllByRole("button")).toHaveLength(3);
  });

  it("applies elevated class when focused", () => {
    const { container } = render(<RecipeGrid data={{}} children={[]} focused />);
    expect(container.querySelector(".elevated")).not.toBeNull();
  });

  it("updates when a new child is added (progressive insertion)", () => {
    const initial = [makeChild("r1", "Carbonara")];
    const { getByText, rerender, queryByText } = render(
      <RecipeGrid data={{}} children={initial} />
    );
    expect(getByText("Carbonara")).toBeTruthy();
    expect(queryByText("Aglio e Olio")).toBeNull();

    rerender(
      <RecipeGrid data={{}} children={[...initial, makeChild("r2", "Aglio e Olio")]} />
    );
    expect(getByText("Aglio e Olio")).toBeTruthy();
  });
});
