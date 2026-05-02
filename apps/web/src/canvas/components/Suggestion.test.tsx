import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, fireEvent, cleanup } from "@testing-library/react";

afterEach(() => cleanup());
import { Suggestion } from "./Suggestion";

const mockSend = vi.fn();
vi.mock("../../contexts/WebSocketContext", () => ({
  useWebSocket: () => ({ send: mockSend }),
}));

describe("Suggestion", () => {
  beforeEach(() => { mockSend.mockClear(); });

  const baseData = { heading: "While you wait", body: "Chop the garlic now." };

  it("renders heading and body", () => {
    const { getByText } = render(<Suggestion data={baseData} />);
    expect(getByText("While you wait")).toBeTruthy();
    expect(getByText("Chop the garlic now.")).toBeTruthy();
  });

  it("renders action button when action_label is provided", () => {
    const { getByRole } = render(
      <Suggestion data={{ ...baseData, action_label: "Got it" }} />
    );
    expect(getByRole("button")).not.toBeNull();
  });

  it("does not render action button without action_label", () => {
    const { container } = render(<Suggestion data={baseData} />);
    expect(container.querySelector("button")).toBeNull();
  });

  it("sends suggestion_dismissed on action click", () => {
    const { getByRole } = render(
      <Suggestion data={{ ...baseData, action_label: "Got it" }} />
    );
    fireEvent.click(getByRole("button"));
    expect(mockSend).toHaveBeenCalledWith({ type: "suggestion_dismissed" });
  });

  it("applies elevated class when focused", () => {
    const { container } = render(<Suggestion data={baseData} focused />);
    expect(container.querySelector(".elevated")).not.toBeNull();
  });

  it("does not apply elevated class when not focused", () => {
    const { container } = render(<Suggestion data={baseData} />);
    expect(container.querySelector(".elevated")).toBeNull();
  });
});
