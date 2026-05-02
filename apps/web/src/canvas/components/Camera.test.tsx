import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, act, fireEvent, cleanup } from "@testing-library/react";
import { Camera } from "./Camera";

// ─── getUserMedia mock ────────────────────────────────────────────────────────

const mockStop = vi.fn();
const mockGetUserMedia = vi.fn();

beforeEach(() => {
  mockStop.mockClear();
  mockGetUserMedia.mockClear();
  Object.defineProperty(globalThis.navigator, "mediaDevices", {
    value: { getUserMedia: mockGetUserMedia },
    configurable: true,
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function makeStream() {
  return {
    getTracks: () => [{ stop: mockStop }],
  };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("Camera", () => {
  it("shows requesting state before getUserMedia resolves", () => {
    // Never resolves during this test
    mockGetUserMedia.mockReturnValue(new Promise(() => {}));

    const { getByText } = render(<Camera data={{ prompt: "Is it done?" }} />);
    expect(getByText("Opening camera…")).toBeTruthy();
  });

  it("renders the prompt text in all states", () => {
    mockGetUserMedia.mockReturnValue(new Promise(() => {}));
    const { getByText } = render(<Camera data={{ prompt: "Is the chicken cooked?" }} />);
    expect(getByText("Is the chicken cooked?")).toBeTruthy();
  });

  it("shows video element after getUserMedia resolves", async () => {
    mockGetUserMedia.mockResolvedValue(makeStream());

    const { container } = render(<Camera data={{ prompt: "Check it." }} />);

    await act(async () => {});

    expect(container.querySelector("video")).not.toBeNull();
  });

  it("shows capture button in active state", async () => {
    mockGetUserMedia.mockResolvedValue(makeStream());

    const { getByText } = render(<Camera data={{ prompt: "Check it." }} />);

    await act(async () => {});

    expect(getByText("Capture")).toBeTruthy();
  });

  it("shows denied error when NotAllowedError is thrown", async () => {
    const err = new Error("Permission denied");
    err.name = "NotAllowedError";
    mockGetUserMedia.mockRejectedValue(err);

    const { getByText } = render(<Camera data={{ prompt: "Check it." }} />);

    await act(async () => {});

    expect(getByText(/Camera access denied/)).toBeTruthy();
  });

  it("shows denied error for PermissionDeniedError too", async () => {
    const err = new Error("Permission denied");
    err.name = "PermissionDeniedError";
    mockGetUserMedia.mockRejectedValue(err);

    const { getByText } = render(<Camera data={{ prompt: "Check it." }} />);

    await act(async () => {});

    expect(getByText(/Camera access denied/)).toBeTruthy();
  });

  it("shows generic error state for other errors", async () => {
    const err = new Error("Device not found");
    err.name = "NotFoundError";
    mockGetUserMedia.mockRejectedValue(err);

    const { getByText } = render(<Camera data={{ prompt: "Check it." }} />);

    await act(async () => {});

    expect(getByText(/Camera unavailable/)).toBeTruthy();
  });

  it("calls onDismiss when capture button is clicked", async () => {
    mockGetUserMedia.mockResolvedValue(makeStream());
    const onDismiss = vi.fn();

    const { getByText } = render(
      <Camera data={{ prompt: "Check it." }} onDismiss={onDismiss} />
    );

    await act(async () => {});

    fireEvent.click(getByText("Capture"));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("renders dismiss (✕) button when onDismiss provided", () => {
    mockGetUserMedia.mockReturnValue(new Promise(() => {}));
    const onDismiss = vi.fn();

    const { getByLabelText } = render(
      <Camera data={{ prompt: "Check it." }} onDismiss={onDismiss} />
    );
    expect(getByLabelText("Dismiss camera")).toBeTruthy();
  });

  it("calls onDismiss when ✕ button is clicked", () => {
    mockGetUserMedia.mockReturnValue(new Promise(() => {}));
    const onDismiss = vi.fn();

    const { getByLabelText } = render(
      <Camera data={{ prompt: "Check it." }} onDismiss={onDismiss} />
    );
    fireEvent.click(getByLabelText("Dismiss camera"));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("does not render dismiss (✕) button without onDismiss", () => {
    mockGetUserMedia.mockReturnValue(new Promise(() => {}));
    const { container } = render(<Camera data={{ prompt: "Check it." }} />);
    expect(container.querySelector(".camera-dismiss")).toBeNull();
  });

  it("stops tracks on unmount", async () => {
    mockGetUserMedia.mockResolvedValue(makeStream());

    const { unmount } = render(<Camera data={{ prompt: "Check it." }} />);
    await act(async () => {});

    unmount();
    expect(mockStop).toHaveBeenCalled();
  });

  it("applies elevated class when focused", () => {
    mockGetUserMedia.mockReturnValue(new Promise(() => {}));
    const { container } = render(<Camera data={{ prompt: "Check it." }} focused />);
    expect(container.querySelector(".elevated")).not.toBeNull();
  });
});
