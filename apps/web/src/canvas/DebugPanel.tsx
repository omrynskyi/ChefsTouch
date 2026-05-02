import { useRef, useState } from "react";
import { useCanvas } from "../contexts/CanvasContext";
import { useWebSocket } from "../contexts/WebSocketContext";

// ── Preset prompts ────────────────────────────────────────────────────────────

const PRESETS: { section: string; prompts: { label: string; action: string }[] }[] = [
  {
    section: "Recipe discovery",
    prompts: [
      { label: "Pasta carbonara",        action: "I want to make pasta carbonara" },
      { label: "Chicken + lemon",        action: "What can I cook with chicken, garlic, and lemon?" },
      { label: "Quick vegetarian",       action: "Something quick and vegetarian, under 30 minutes" },
      { label: "Use what I have",        action: "I have eggs, cheese, and some leftover vegetables — what can I make?" },
    ],
  },
  {
    section: "During a cook",
    prompts: [
      { label: "Next step →",            action: "Next step please" },
      { label: "Repeat current step",    action: "Can you repeat the current step?" },
      { label: "How long left?",         action: "How much longer do I have on the timer?" },
      { label: "I'm ready",              action: "I'm ready to continue" },
      { label: "Set 10-min timer",       action: "Set a timer for 10 minutes" },
    ],
  },
  {
    section: "Camera checks",
    prompts: [
      { label: "Check if done",          action: "Can you check if this looks right?" },
      { label: "Is pasta cooked?",       action: "Is the pasta cooked enough?" },
      { label: "Is chicken through?",    action: "Is the chicken cooked through?" },
    ],
  },
  {
    section: "Substitutions & help",
    prompts: [
      { label: "No pecorino",            action: "I don't have pecorino, what can I substitute?" },
      { label: "Swap guanciale",         action: "Can I use bacon instead of guanciale?" },
      { label: "Make it spicier",        action: "How do I make this spicier?" },
      { label: "Skip this step",         action: "Can we skip this step?" },
    ],
  },
  {
    section: "Session",
    prompts: [
      { label: "What are we making?",    action: "What recipe are we making?" },
      { label: "Start over",             action: "Let's start over with a different recipe" },
      { label: "How's it going?",        action: "Give me a quick summary of where we are" },
    ],
  },
];

// ── Styles ────────────────────────────────────────────────────────────────────

const btnStyle: React.CSSProperties = {
  background: "rgba(255,255,255,0.07)",
  color: "#e8d8c0",
  border: "none",
  borderRadius: "5px",
  padding: "4px 9px",
  cursor: "pointer",
  textAlign: "left",
  fontSize: "12px",
  fontFamily: "var(--font-mono)",
  transition: "background 0.1s",
  whiteSpace: "nowrap",
  overflow: "hidden",
  textOverflow: "ellipsis",
};

function DbgButton({
  onClick,
  children,
  accent,
  disabled,
  full,
}: {
  onClick: () => void;
  children: React.ReactNode;
  accent?: boolean;
  disabled?: boolean;
  full?: boolean;
}) {
  const base: React.CSSProperties = accent
    ? { ...btnStyle, background: "rgba(200,95,58,0.2)", color: "#c85f3a" }
    : btnStyle;
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{ ...base, opacity: disabled ? 0.4 : 1, width: full ? "100%" : undefined }}
      onMouseEnter={(e) => {
        if (!disabled)
          e.currentTarget.style.background = accent
            ? "rgba(200,95,58,0.35)"
            : "rgba(255,255,255,0.15)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = accent
          ? "rgba(200,95,58,0.2)"
          : "rgba(255,255,255,0.07)";
      }}
    >
      {children}
    </button>
  );
}

function Divider() {
  return (
    <hr style={{ border: "none", borderTop: "1px solid rgba(255,255,255,0.08)", margin: "6px 0" }} />
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        color: "#a89880",
        fontWeight: 600,
        fontSize: "10px",
        letterSpacing: "0.1em",
        textTransform: "uppercase",
        display: "block",
        marginBottom: "4px",
        marginTop: "2px",
      }}
    >
      {children}
    </span>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export function DebugPanel() {
  const { state, dispatch } = useCanvas();
  const { send, status } = useWebSocket();
  const [open, setOpen] = useState(false);
  const [freeText, setFreeText] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const connected = status === "connected";

  const sendAction = (action: string) => {
    if (!action.trim() || !connected) return;
    send({ type: "action", action: action.trim() });
    setFreeText("");
    inputRef.current?.focus();
  };

  const clearCanvas = () => {
    for (const id of state.active.keys()) dispatch({ op: "remove", id });
  };

  return (
    <div
      style={{
        position: "fixed",
        bottom: "var(--space-md)",
        left: "var(--space-md)",
        zIndex: 9999,
        fontFamily: "var(--font-mono)",
        fontSize: "12px",
      }}
    >
      {open && (
        <div
          style={{
            background: "rgba(20,15,10,0.93)",
            backdropFilter: "blur(10px)",
            borderRadius: "var(--radius-md)",
            padding: "10px 12px",
            marginBottom: "6px",
            display: "flex",
            flexDirection: "column",
            gap: "3px",
            width: "260px",
            maxHeight: "82vh",
            overflowY: "auto",
            boxShadow: "0 4px 28px rgba(0,0,0,0.5)",
          }}
        >
          {/* Connection status + free-text input */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              marginBottom: "4px",
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                background: connected ? "#22c55e" : "#ef4444",
                flexShrink: 0,
              }}
            />
            <input
              ref={inputRef}
              value={freeText}
              onChange={(e) => setFreeText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") sendAction(freeText);
              }}
              placeholder="Type an intent…"
              disabled={!connected}
              style={{
                flex: 1,
                background: "rgba(255,255,255,0.06)",
                color: "#e8d8c0",
                border: "1px solid rgba(255,255,255,0.13)",
                borderRadius: "5px",
                padding: "4px 8px",
                fontSize: "12px",
                fontFamily: "var(--font-mono)",
                outline: "none",
                minWidth: 0,
              }}
            />
            <DbgButton onClick={() => sendAction(freeText)} disabled={!connected}>
              ↵
            </DbgButton>
          </div>

          <Divider />

          {/* Preset prompts by category */}
          {PRESETS.map((section, si) => (
            <div key={si}>
              <SectionLabel>{section.section}</SectionLabel>
              <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
                {section.prompts.map((p) => (
                  <DbgButton
                    key={p.action}
                    onClick={() => sendAction(p.action)}
                    disabled={!connected}
                    full
                  >
                    {p.label}
                  </DbgButton>
                ))}
              </div>
              {si < PRESETS.length - 1 && <Divider />}
            </div>
          ))}

          <Divider />
          <DbgButton accent onClick={clearCanvas} full>
            Clear canvas
          </DbgButton>
        </div>
      )}

      {/* Toggle button */}
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          background: "rgba(20,15,10,0.85)",
          color: "#a89880",
          border: "1px solid rgba(255,255,255,0.12)",
          borderRadius: "var(--radius-sm)",
          padding: "5px 12px",
          cursor: "pointer",
          fontSize: "12px",
          fontFamily: "var(--font-mono)",
          backdropFilter: "blur(8px)",
        }}
      >
        {open ? "✕ close" : "⚙ debug"}
      </button>
    </div>
  );
}
