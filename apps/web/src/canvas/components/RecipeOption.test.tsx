import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, fireEvent, cleanup } from "@testing-library/react";

afterEach(() => cleanup());
import { RecipeOption } from "./RecipeOption";

const mockSend = vi.fn();
vi.mock("../../contexts/WebSocketContext", () => ({
  useWebSocket: () => ({ send: mockSend }),
}));

describe("RecipeOption", () => {
  beforeEach(() => { mockSend.mockClear(); });

  const baseData = { title: "Carbonara", action: "select_carbonara" };

  it("renders title", () => {
    const { getByText } = render(<RecipeOption data={baseData} />);
    expect(getByText("Carbonara")).toBeTruthy();
  });

  it("renders optional description", () => {
    const { getByText } = render(
      <RecipeOption data={{ ...baseData, description: "Classic Italian pasta" }} />
    );
    expect(getByText("Classic Italian pasta")).toBeTruthy();
  });

  it("renders optional duration", () => {
    const { getByText } = render(
      <RecipeOption data={{ ...baseData, duration: "20 min" }} />
    );
    expect(getByText("20 min")).toBeTruthy();
  });

  it("renders tags", () => {
    const { getByText } = render(
      <RecipeOption data={{ ...baseData, tags: ["vegetarian", "quick"] }} />
    );
    expect(getByText("vegetarian")).toBeTruthy();
    expect(getByText("quick")).toBeTruthy();
  });

  it("sends action via WebSocket on click", () => {
    const { getByRole } = render(<RecipeOption data={baseData} />);
    fireEvent.click(getByRole("button"));
    expect(mockSend).toHaveBeenCalledWith({ type: "action", action: "select_carbonara" });
  });

  it("applies elevated class when focused", () => {
    const { container } = render(<RecipeOption data={baseData} focused />);
    expect(container.querySelector(".elevated")).not.toBeNull();
  });

  it("does not apply elevated class when not focused", () => {
    const { container } = render(<RecipeOption data={baseData} />);
    expect(container.querySelector(".elevated")).toBeNull();
  });

  it("renders as a button element", () => {
    const { getByRole } = render(<RecipeOption data={baseData} />);
    expect(getByRole("button")).not.toBeNull();
  });
});
