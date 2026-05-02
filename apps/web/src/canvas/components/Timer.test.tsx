import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, act, cleanup } from "@testing-library/react";
import { Timer } from "./Timer";

describe("Timer", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    localStorage.clear();
  });

  const baseData = { duration_seconds: 300, label: "Boiling", auto_start: false };

  it("displays initial time in M:SS format", () => {
    const { getByText } = render(
      <Timer id="t1" data={baseData} />
    );
    expect(getByText("5:00")).toBeTruthy();
  });

  it("renders the label", () => {
    const { getByText } = render(<Timer id="t1" data={baseData} />);
    expect(getByText("Boiling")).toBeTruthy();
  });

  it("applies elevated class when focused", () => {
    const { container } = render(<Timer id="t1" data={baseData} focused />);
    expect(container.querySelector(".elevated")).not.toBeNull();
  });

  it("does not decrement when auto_start is false", () => {
    const { getByText } = render(<Timer id="t1" data={baseData} />);
    act(() => { vi.advanceTimersByTime(5000); });
    expect(getByText("5:00")).toBeTruthy();
  });

  it("decrements each second when auto_start is true", () => {
    const { getByText } = render(
      <Timer id="t1" data={{ ...baseData, auto_start: true }} />
    );
    act(() => { vi.advanceTimersByTime(3000); });
    expect(getByText("4:57")).toBeTruthy();
  });

  it("stops at 0:00 and does not go negative", () => {
    const { getByText } = render(
      <Timer id="t1" data={{ duration_seconds: 3, label: "Quick", auto_start: true }} />
    );
    act(() => { vi.advanceTimersByTime(10000); });
    expect(getByText("0:00")).toBeTruthy();
  });

  it("applies pulse-on-end class when finished", () => {
    const { container } = render(
      <Timer id="t1" data={{ duration_seconds: 1, label: "Quick", auto_start: true }} />
    );
    act(() => { vi.advanceTimersByTime(2000); });
    expect(container.querySelector(".pulse-on-end")).not.toBeNull();
  });

  it("stores start time in localStorage on auto_start", () => {
    const now = Date.now();
    vi.setSystemTime(now);

    render(<Timer id="t1" data={{ ...baseData, auto_start: true }} />);

    const stored = localStorage.getItem("timer-start-t1");
    expect(stored).toBe(String(now));
  });

  it("resumes from stored start time on reconnect", () => {
    const thirtySecondsAgo = Date.now() - 30_000;
    localStorage.setItem("timer-start-t1", String(thirtySecondsAgo));

    const { getByText } = render(
      <Timer id="t1" data={{ ...baseData, auto_start: true }} />
    );
    // 300 - 30 = 270 seconds remaining → 4:30
    expect(getByText("4:30")).toBeTruthy();
  });

  it("clears stored start time when duration changes", () => {
    localStorage.setItem("timer-start-t1", String(Date.now() - 10_000));

    const { rerender } = render(
      <Timer id="t1" data={{ ...baseData, auto_start: true }} />
    );
    rerender(
      <Timer id="t1" data={{ duration_seconds: 120, label: "New", auto_start: false }} />
    );

    expect(localStorage.getItem("timer-start-t1")).toBeNull();
  });

  it("clears stored start time when timer finishes", () => {
    localStorage.setItem("timer-start-t1", String(Date.now()));

    render(
      <Timer id="t1" data={{ duration_seconds: 2, label: "Quick", auto_start: true }} />
    );
    act(() => { vi.advanceTimersByTime(3000); });

    expect(localStorage.getItem("timer-start-t1")).toBeNull();
  });

  it("formats single-digit seconds with leading zero", () => {
    const { getByText } = render(
      <Timer id="t1" data={{ duration_seconds: 65, label: "Test", auto_start: false }} />
    );
    expect(getByText("1:05")).toBeTruthy();
  });
});
