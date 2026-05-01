import type { TextCardData } from "@pair-cooking/types";
import { useState } from "react";
import { useWebSocket } from "../../contexts/WebSocketContext";

interface Props {
  data: TextCardData;
  focused?: boolean;
}

// Supports **bold** and _italic_ inline markdown
function renderInline(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|_[^_]+_)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("_") && part.endsWith("_")) {
      return <em key={i}>{part.slice(1, -1)}</em>;
    }
    return part;
  });
}

export function TextCard({ data, focused }: Props) {
  const { send } = useWebSocket();
  const [value, setValue] = useState("");

  const hasInput = typeof data.input_placeholder === "string" && data.input_placeholder.trim().length > 0;

  const handleSubmit = () => {
    const answer = value.trim();
    if (!answer) return;
    const prefix = data.input_action_prefix?.trim();
    const action = prefix ? `${prefix} ${answer}` : answer;
    send({ type: "action", action });
    setValue("");
  };

  return (
    <div className={`card comp-medium${focused ? " elevated" : ""}`}>
      <p className="text-primary size-md">{renderInline(data.body)}</p>
      {hasInput && (
        <div style={{ display: "flex", gap: "var(--space-sm)", marginTop: "var(--space-md)" }}>
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSubmit();
            }}
            placeholder={data.input_placeholder}
            aria-label={data.input_placeholder}
            style={{
              flex: 1,
              background: "rgba(255,255,255,0.7)",
              color: "var(--text-primary)",
              border: "1px solid rgba(37,29,23,0.14)",
              borderRadius: "999px",
              padding: "10px 14px",
              fontSize: "0.95rem",
              outline: "none",
            }}
          />
          <button className="btn-primary" onClick={handleSubmit}>
            {data.submit_label?.trim() || "Send"}
          </button>
        </div>
      )}
    </div>
  );
}
