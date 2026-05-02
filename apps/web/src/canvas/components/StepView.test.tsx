import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, fireEvent, cleanup } from "@testing-library/react";

afterEach(() => cleanup());
import { StepView } from "./StepView";

const mockSend = vi.fn();
vi.mock("../../contexts/WebSocketContext", () => ({
  useWebSocket: () => ({ send: mockSend }),
}));

describe("StepView", () => {
  beforeEach(() => { mockSend.mockClear(); });

  const baseData = {
    step_number: 2,
    total_steps: 6,
    recipe: "Pasta Carbonara",
    instruction: "Add the eggs and cheese.",
  };

  it("renders the instruction", () => {
    const { getByText } = render(<StepView data={baseData} />);
    expect(getByText("Add the eggs and cheese.")).toBeTruthy();
  });

  it("renders recipe name and step counter", () => {
    const { getByText } = render(<StepView data={baseData} />);
    expect(getByText(/Pasta Carbonara/)).toBeTruthy();
    expect(getByText(/Step 2 of 6/)).toBeTruthy();
  });

  it("renders optional tip", () => {
    const { getByText } = render(
      <StepView data={{ ...baseData, tip: "Work quickly off the heat." }} />
    );
    expect(getByText("Work quickly off the heat.")).toBeTruthy();
  });

  it("does not render tip section when tip is absent", () => {
    const { container } = render(<StepView data={baseData} />);
    // Only the instruction <p> should be present (no secondary text-secondary)
    const secondaryTexts = container.querySelectorAll(".text-secondary");
    expect(secondaryTexts).toHaveLength(0);
  });

  it("renders tags", () => {
    const { getByText } = render(
      <StepView data={{ ...baseData, tags: ["~5 min", "hot"] }} />
    );
    expect(getByText("~5 min")).toBeTruthy();
    expect(getByText("hot")).toBeTruthy();
  });

  it("renders action button when action is provided", () => {
    const { getByRole } = render(
      <StepView data={{ ...baseData, action: "next_step" }} />
    );
    expect(getByRole("button")).not.toBeNull();
  });

  it("sends action on button click", () => {
    const { getByRole } = render(
      <StepView data={{ ...baseData, action: "next_step" }} />
    );
    fireEvent.click(getByRole("button"));
    expect(mockSend).toHaveBeenCalledWith({ type: "action", action: "next_step" });
  });

  it("does not render action button without action", () => {
    const { container } = render(<StepView data={baseData} />);
    expect(container.querySelector("button")).toBeNull();
  });

  it("applies elevated class when focused", () => {
    const { container } = render(<StepView data={baseData} focused />);
    expect(container.querySelector(".elevated")).not.toBeNull();
  });

  it("applies card--joined class when companionBelow is true", () => {
    const { container } = render(<StepView data={baseData} companionBelow />);
    expect(container.querySelector(".card--joined")).not.toBeNull();
  });
});
