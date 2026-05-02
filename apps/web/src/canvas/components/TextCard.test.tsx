import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, fireEvent, cleanup } from "@testing-library/react";

afterEach(() => cleanup());
import { TextCard } from "./TextCard";

const mockSend = vi.fn();
vi.mock("../../contexts/WebSocketContext", () => ({
  useWebSocket: () => ({ send: mockSend }),
}));

describe("TextCard", () => {
  beforeEach(() => { mockSend.mockClear(); });

  it("renders plain body text", () => {
    const { getByText } = render(<TextCard data={{ body: "Hello world" }} />);
    expect(getByText("Hello world")).toBeTruthy();
  });

  it("renders bold inline markdown", () => {
    const { container } = render(
      <TextCard data={{ body: "Use **fresh** pasta." }} />
    );
    expect(container.querySelector("strong")!.textContent).toBe("fresh");
  });

  it("renders italic inline markdown", () => {
    const { container } = render(
      <TextCard data={{ body: "Use _fresh_ pasta." }} />
    );
    expect(container.querySelector("em")!.textContent).toBe("fresh");
  });

  it("does not show expand toggle for short body", () => {
    const { container } = render(<TextCard data={{ body: "Short text." }} />);
    expect(container.querySelector(".btn-text")).toBeNull();
  });

  it("shows expand toggle for body longer than 200 characters", () => {
    const longBody = "A".repeat(201);
    const { getByText } = render(<TextCard data={{ body: longBody }} />);
    expect(getByText("Show more ↓")).toBeTruthy();
  });

  it("toggles between expanded and collapsed on click", () => {
    const longBody = "A".repeat(201);
    const { getByText } = render(<TextCard data={{ body: longBody }} />);

    const btn = getByText("Show more ↓");
    fireEvent.click(btn);
    expect(getByText("Show less ↑")).toBeTruthy();

    fireEvent.click(getByText("Show less ↑"));
    expect(getByText("Show more ↓")).toBeTruthy();
  });

  it("does not render input when input_placeholder is absent", () => {
    const { container } = render(<TextCard data={{ body: "No input here." }} />);
    expect(container.querySelector("input")).toBeNull();
  });

  it("renders input when input_placeholder is provided", () => {
    const { getByPlaceholderText } = render(
      <TextCard data={{ body: "Q:", input_placeholder: "Type here" }} />
    );
    expect(getByPlaceholderText("Type here")).toBeTruthy();
  });

  it("sends action with input value on button click", () => {
    const { getByPlaceholderText, getByText } = render(
      <TextCard
        data={{
          body: "Q:",
          input_placeholder: "Your answer",
          submit_label: "Send",
        }}
      />
    );
    fireEvent.change(getByPlaceholderText("Your answer"), {
      target: { value: "salmon" },
    });
    fireEvent.click(getByText("Send"));
    expect(mockSend).toHaveBeenCalledWith({ type: "action", action: "salmon" });
  });

  it("prepends input_action_prefix to submitted value", () => {
    const { getByPlaceholderText, getByText } = render(
      <TextCard
        data={{
          body: "Q:",
          input_placeholder: "Your answer",
          submit_label: "Go",
          input_action_prefix: "User says:",
        }}
      />
    );
    fireEvent.change(getByPlaceholderText("Your answer"), {
      target: { value: "salmon" },
    });
    fireEvent.click(getByText("Go"));
    expect(mockSend).toHaveBeenCalledWith({
      type: "action",
      action: "User says: salmon",
    });
  });

  it("submits on Enter key", () => {
    const { getByPlaceholderText } = render(
      <TextCard
        data={{ body: "Q:", input_placeholder: "Answer", input_action_prefix: "Ans:" }}
      />
    );
    const input = getByPlaceholderText("Answer");
    fireEvent.change(input, { target: { value: "chicken" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(mockSend).toHaveBeenCalledWith({ type: "action", action: "Ans: chicken" });
  });

  it("does not send empty input on submit", () => {
    const { getByText } = render(
      <TextCard
        data={{ body: "Q:", input_placeholder: "Answer", submit_label: "Send" }}
      />
    );
    fireEvent.click(getByText("Send"));
    expect(mockSend).not.toHaveBeenCalled();
  });

  it("applies elevated class when focused", () => {
    const { container } = render(<TextCard data={{ body: "Hi" }} focused />);
    expect(container.querySelector(".elevated")).not.toBeNull();
  });
});
