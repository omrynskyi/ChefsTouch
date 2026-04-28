import { useWebSocket } from "./contexts/WebSocketContext";
import type { ConnectionStatus } from "./contexts/WebSocketContext";

const STATUS_COLOR: Record<ConnectionStatus, string> = {
  connected: "#22c55e",
  reconnecting: "#f59e0b",
  failed: "#ef4444",
};

export default function App() {
  const { status } = useWebSocket();

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: "100dvh",
        margin: 0,
        background: "#0a0a0a",
        color: "#fff",
        fontFamily: "system-ui, sans-serif",
        position: "relative",
      }}
    >
      <span style={{ fontSize: "3rem" }}>🎙️</span>

      {/* Connection status indicator */}
      <div
        title={status}
        style={{
          position: "absolute",
          top: "1rem",
          right: "1rem",
          width: "10px",
          height: "10px",
          borderRadius: "50%",
          background: STATUS_COLOR[status],
          opacity: status === "reconnecting" ? undefined : 1,
          animation: status === "reconnecting" ? "pulse 1.2s ease-in-out infinite" : undefined,
        }}
      />

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}
