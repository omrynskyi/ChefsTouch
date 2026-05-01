import type { StepViewData } from "@pair-cooking/types";
import { useWebSocket } from "../../contexts/WebSocketContext";

interface Props {
  data: StepViewData;
  focused?: boolean;
  companionBelow?: boolean;
}

export function StepView({ data, focused, companionBelow }: Props) {
  const { send } = useWebSocket();

  return (
    <div className={`card${focused ? " elevated" : ""}${companionBelow ? " card--joined" : ""}`} style={{ width: "100%" }}>
      <span className="label-muted">
        {data.recipe} · Step {data.step_number} of {data.total_steps}
      </span>
      <p className="text-primary size-lg">{data.instruction}</p>
      {data.tip && (
        <p className="text-secondary size-sm" style={{ marginTop: "var(--space-sm)" }}>
          {data.tip}
        </p>
      )}
      {data.tags && data.tags.length > 0 && (
        <div className="tag-row">
          {data.tags.map((tag) => (
            <span key={tag} className="tag">{tag}</span>
          ))}
        </div>
      )}
      {data.action && (
        <button
          className="btn-primary"
          style={{ marginTop: "var(--space-md)" }}
          onClick={() => send({ type: "action", action: data.action! })}
        >
          Next step →
        </button>
      )}
    </div>
  );
}
