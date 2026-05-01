import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useCanvas } from "../contexts/CanvasContext";
import { useWebSocket } from "../contexts/WebSocketContext";
import { AssistantMessage } from "./components/AssistantMessage";

export function AgentStatusBar() {
  const { subscribe } = useWebSocket();
  const { state } = useCanvas();
  const [text, setText] = useState("");
  const [spokenText, setSpokenText] = useState("");
  const clearTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const assistantMessage = [...state.active.values()].find(
    (comp) => comp.type === "assistant-message" && comp.data !== null
  );
  const assistantTextFromCanvas =
    assistantMessage?.data && "text" in assistantMessage.data
      ? assistantMessage.data.text
      : "";
  const assistantText = assistantTextFromCanvas || spokenText;

  useEffect(() => {
    return subscribe((msg) => {
      if (msg.type === "agent_status") {
        if (clearTimer.current) clearTimeout(clearTimer.current);
        setText(msg.text);
      }
      if (msg.type === "tts_text") {
        setSpokenText(msg.text);
        // Clear bar 1.5s after the agent finishes speaking
        clearTimer.current = setTimeout(() => setText(""), 1500);
      }
      if (msg.type === "speech_commit") {
        setSpokenText(msg.text);
        clearTimer.current = setTimeout(() => setText(""), 1500);
      }
      if (msg.type === "speech_cancel") {
        if (clearTimer.current) clearTimeout(clearTimer.current);
        setText("");
      }
    });
  }, [subscribe]);

  useEffect(() => () => {
    if (clearTimer.current) clearTimeout(clearTimer.current);
  }, []);

  if (!text && !assistantText) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: "var(--space-md)",
        left: "var(--space-md)",
        zIndex: 1000,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
        gap: 10,
        width: "min(28rem, calc(100vw - var(--space-md) * 2))",
        pointerEvents: "none",
      }}
    >
      <AnimatePresence>
        {text && (
          <motion.div
            key="agent-status"
            initial={{ opacity: 0, y: -8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }}
            transition={{ duration: 0.18, ease: [0.25, 0.1, 0.25, 1] }}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "7px 14px 7px 10px",
              background: "rgba(28, 23, 18, 0.88)",
              backdropFilter: "blur(10px)",
              WebkitBackdropFilter: "blur(10px)",
              borderRadius: "var(--radius-pill)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              boxShadow: "0 4px 16px rgba(0,0,0,0.22)",
              userSelect: "none",
              whiteSpace: "nowrap",
              maxWidth: "100%",
            }}
          >
            <PulseDot />
            <span
              style={{
                fontFamily: "var(--font-sans)",
                fontSize: 13,
                fontWeight: 450,
                letterSpacing: "0.01em",
                color: "rgba(255, 248, 236, 0.90)",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {text}
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {assistantText && (
          <motion.div
            key="assistant-message"
            initial={{ opacity: 0, y: -8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.2, ease: [0.25, 0.1, 0.25, 1] }}
            style={{ width: "100%" }}
          >
            <AssistantMessage data={{ text: assistantText }} focused={assistantMessage?.focused} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function PulseDot() {
  return (
    <span
      style={{
        position: "relative",
        display: "inline-flex",
        width: 8,
        height: 8,
        flexShrink: 0,
      }}
    >
      {/* Ripple */}
      <span
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: "50%",
          background: "rgba(200, 95, 58, 0.5)",
          animation: "pip-ripple 1.4s ease-out infinite",
        }}
      />
      {/* Core dot */}
      <span
        style={{
          position: "relative",
          borderRadius: "50%",
          width: "100%",
          height: "100%",
          background: "var(--accent)",
        }}
      />
      <style>{`
        @keyframes pip-ripple {
          0%   { transform: scale(1);   opacity: 0.7; }
          70%  { transform: scale(2.4); opacity: 0; }
          100% { transform: scale(2.4); opacity: 0; }
        }
      `}</style>
    </span>
  );
}
