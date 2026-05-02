import { describe, expect, it, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";

afterEach(() => cleanup());
import { ProgressBar } from "./ProgressBar";

describe("ProgressBar", () => {
  it("renders step label with current and total", () => {
    const { getByText } = render(<ProgressBar data={{ current: 2, total: 6 }} />);
    expect(getByText("Step 2 of 6")).toBeTruthy();
  });

  it("sets progress fill width proportionally", () => {
    const { container } = render(<ProgressBar data={{ current: 3, total: 6 }} />);
    const fill = container.querySelector(".progress-fill") as HTMLElement;
    expect(fill.style.width).toBe("50%");
  });

  it("sets 0% width when current is 0", () => {
    const { container } = render(<ProgressBar data={{ current: 0, total: 6 }} />);
    const fill = container.querySelector(".progress-fill") as HTMLElement;
    expect(fill.style.width).toBe("0%");
  });

  it("sets 0% width when total is 0 (avoids division by zero)", () => {
    const { container } = render(<ProgressBar data={{ current: 0, total: 0 }} />);
    const fill = container.querySelector(".progress-fill") as HTMLElement;
    expect(fill.style.width).toBe("0%");
  });

  it("applies elevated class when focused", () => {
    const { container } = render(<ProgressBar data={{ current: 1, total: 6 }} focused />);
    expect(container.querySelector(".elevated")).not.toBeNull();
  });

  it("applies card--joined class when alertBelow is true", () => {
    const { container } = render(
      <ProgressBar data={{ current: 1, total: 6 }} alertBelow />
    );
    expect(container.querySelector(".card--joined")).not.toBeNull();
  });

  it("has progressbar role and ARIA attributes", () => {
    const { container } = render(<ProgressBar data={{ current: 2, total: 6 }} />);
    const pb = container.querySelector('[role="progressbar"]');
    expect(pb).not.toBeNull();
    expect(pb!.getAttribute("aria-valuenow")).toBe("2");
    expect(pb!.getAttribute("aria-valuemax")).toBe("6");
  });
});
