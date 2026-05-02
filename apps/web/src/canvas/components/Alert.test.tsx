import { describe, expect, it, vi, afterEach } from "vitest";
import { render, fireEvent, cleanup } from "@testing-library/react";

afterEach(() => cleanup());
import { Alert } from "./Alert";

describe("Alert", () => {
  it("renders text content", () => {
    const { getByText } = render(<Alert data={{ text: "Pan is too hot!" }} />);
    expect(getByText("Pan is too hot!")).toBeTruthy();
  });

  it("applies urgent class when urgent is true", () => {
    const { container } = render(<Alert data={{ text: "Burn risk", urgent: true }} />);
    expect(container.querySelector(".alert-urgent")).not.toBeNull();
  });

  it("does not apply urgent class when urgent is false", () => {
    const { container } = render(<Alert data={{ text: "Info", urgent: false }} />);
    expect(container.querySelector(".alert-urgent")).toBeNull();
  });

  it("applies attached class when attached prop is true", () => {
    const { container } = render(<Alert data={{ text: "Note" }} attached />);
    expect(container.querySelector(".alert--attached")).not.toBeNull();
  });

  it("applies elevated class when focused", () => {
    const { container } = render(<Alert data={{ text: "Note" }} focused />);
    expect(container.querySelector(".elevated")).not.toBeNull();
  });

  it("renders dismiss button when onDismiss provided", () => {
    const onDismiss = vi.fn();
    const { getByLabelText } = render(
      <Alert data={{ text: "Note" }} onDismiss={onDismiss} />
    );
    const btn = getByLabelText("Dismiss");
    fireEvent.click(btn);
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("does not render dismiss button without onDismiss", () => {
    const { container } = render(<Alert data={{ text: "Note" }} />);
    expect(container.querySelector(".alert-dismiss")).toBeNull();
  });

  it("has role=alert for accessibility", () => {
    const { container } = render(<Alert data={{ text: "Warning" }} />);
    expect(container.querySelector('[role="alert"]')).not.toBeNull();
  });
});
