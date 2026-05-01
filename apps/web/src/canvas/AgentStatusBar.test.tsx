import React from "react";
import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CanvasState, ServerMessage } from "@pair-cooking/types";
import { AgentStatusBar } from "./AgentStatusBar";

vi.mock("framer-motion", () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  motion: new Proxy({}, {
    get: (_t, tag: string) =>
      ({ children, initial: _i, animate: _a, exit: _e, transition: _tr, ...rest }: Record<string, unknown>) =>
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (React as any).createElement(tag, rest, children),
  }),
}));

let mockCanvasState: CanvasState = { active: new Map(), staged: new Map() };
let subscriptionHandler: ((msg: ServerMessage) => void) | null = null;

vi.mock("../contexts/CanvasContext", () => ({
  useCanvas: () => ({ state: mockCanvasState, dispatch: vi.fn() }),
}));

vi.mock("../contexts/WebSocketContext", () => ({
  useWebSocket: () => ({
    status: "connected",
    sessionId: null,
    send: vi.fn(),
    subscribe: (handler: (msg: ServerMessage) => void) => {
      subscriptionHandler = handler;
      return () => {
        if (subscriptionHandler === handler) subscriptionHandler = null;
      };
    },
  }),
}));

describe("AgentStatusBar", () => {
  beforeEach(() => {
    mockCanvasState = { active: new Map(), staged: new Map() };
    subscriptionHandler = null;
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  it("renders streamed agent status in the top-left surface", () => {
    render(<AgentStatusBar />);

    act(() => {
      subscriptionHandler?.({ type: "agent_status", text: "Thinking..." });
    });

    expect(screen.getByText("Thinking...")).toBeTruthy();
  });

  it("renders the assistant message in the same panel", () => {
    mockCanvasState = {
      active: new Map([
        [
          "sys-assistant-message",
          {
            id: "sys-assistant-message",
            type: "assistant-message",
            data: { text: "One sec, I'm on it." },
          },
        ],
      ]),
      staged: new Map(),
    };

    render(<AgentStatusBar />);

    expect(screen.getByText("One sec, I'm on it.")).toBeTruthy();
  });

  it("falls back to the latest tts text when canvas assistant-message is missing", () => {
    render(<AgentStatusBar />);

    act(() => {
      subscriptionHandler?.({ type: "tts_text", text: "No worries, pick a lane." });
    });

    expect(screen.getByText("No worries, pick a lane.")).toBeTruthy();
  });

  it("accepts canonical speech_commit messages", () => {
    render(<AgentStatusBar />);

    act(() => {
      subscriptionHandler?.({
        type: "speech_commit",
        turn_id: "turn-1",
        generation_id: 1,
        message_id: "msg-1",
        text: "Working on it.",
      });
    });

    expect(screen.getByText("Working on it.")).toBeTruthy();
  });
});
