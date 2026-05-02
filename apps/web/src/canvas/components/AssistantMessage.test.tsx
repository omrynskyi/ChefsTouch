import { describe, expect, it, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";

afterEach(() => cleanup());
import { AssistantMessage } from "./AssistantMessage";

describe("AssistantMessage", () => {
  it("renders the text content", () => {
    const { getByText } = render(
      <AssistantMessage data={{ text: "One sec, I'm on it." }} />
    );
    expect(getByText("One sec, I'm on it.")).toBeTruthy();
  });

  it("applies elevated class when focused", () => {
    const { container } = render(
      <AssistantMessage data={{ text: "Hello" }} focused />
    );
    expect(container.querySelector(".elevated")).not.toBeNull();
  });

  it("does not apply elevated class when not focused", () => {
    const { container } = render(
      <AssistantMessage data={{ text: "Hello" }} />
    );
    expect(container.querySelector(".elevated")).toBeNull();
  });

  it("renders long text without truncation", () => {
    const longText = "A".repeat(300);
    const { getByText } = render(<AssistantMessage data={{ text: longText }} />);
    expect(getByText(longText)).toBeTruthy();
  });
});
