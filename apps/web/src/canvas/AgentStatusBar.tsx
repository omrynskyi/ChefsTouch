import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useWebSocket } from "../contexts/WebSocketContext";

export function AgentStatusBar() {
  const { subscribe } = useWebSocket();
  const [text, setText] = useState("");
  const clearTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return subscribe((msg) => {
      if (msg.type === "agent_status") {
        if (clearTimer.current) clearTimeout(clearTimer.current);
        setText(msg.text);
      }
      if (msg.type === "tts_text") {
        // Clear bar 1.5s after the agent finishes speaking
        clearTimer.current = setTimeout(() => setText(""), 1500);
      }
    });
  }, [subscribe]);

  useEffect(() => () => {
    if (clearTimer.current) clearTimeout(clearTimer.current);
  }, []);

  return (
    <AnimatePresence>
      {text && (
        <motion.div
          key="agent-status"
          initial={{ opacity: 0, y: -8, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -6, scale: 0.97 }}
          transition={{ duration: 0.18, ease: [0.25, 0.1, 0.25, 1] }}
          style={{
            position: "fixed",
            top: "var(--space-md)",
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 1000,
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
            pointerEvents: "none",
            userSelect: "none",
            whiteSpace: "nowrap",
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
            }}
          >
            {text}
          </span>
        </motion.div>
      )}
    </AnimatePresence>
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
