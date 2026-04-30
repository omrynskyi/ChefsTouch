import type { CameraData } from "@pair-cooking/types";

interface Props {
  data: CameraData;
  focused?: boolean;
  onDismiss?: () => void;
}

export function Camera({ data, focused, onDismiss }: Props) {
  return (
    <div
      className={`card camera-card${focused ? " elevated" : ""}`}
      style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)", position: "relative" }}
    >
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="camera-dismiss"
          aria-label="Dismiss camera"
        >
          ✕
        </button>
      )}
      <div className="camera-frame">
        Camera feed
      </div>
      <p className="text-secondary size-sm">{data.prompt}</p>
    </div>
  );
}
