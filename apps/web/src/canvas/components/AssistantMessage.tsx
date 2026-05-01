import type { AssistantMessageData } from "@pair-cooking/types";

interface Props {
  data: AssistantMessageData;
  focused?: boolean;
}

export function AssistantMessage({ data, focused }: Props) {
  return (
    <div
      className={focused ? "elevated" : undefined}
      style={{
        maxWidth: "min(28rem, 100%)",
        background: "rgba(28, 23, 18, 0.9)",
        color: "rgba(255, 248, 236, 0.95)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
        borderRadius: "18px",
        padding: "12px 14px",
        boxShadow: "0 8px 24px rgba(0,0,0,0.18)",
        backdropFilter: "blur(10px)",
        WebkitBackdropFilter: "blur(10px)",
      }}
    >
      <p
        style={{
          margin: 0,
          fontFamily: "var(--font-sans)",
          fontSize: "0.95rem",
          lineHeight: 1.4,
          fontWeight: 450,
        }}
      >
        {data.text}
      </p>
    </div>
  );
}
