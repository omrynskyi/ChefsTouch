import type { SuggestionData } from "@pair-cooking/types";
import { useWebSocket } from "../../contexts/WebSocketContext";

interface Props {
  data: SuggestionData;
  focused?: boolean;
}

export function Suggestion({ data, focused }: Props) {
  const { send } = useWebSocket();

  const handleDismiss = () => {
    send({ type: "suggestion_dismissed" });
  };

  return (
    <div className={`card glass suggestion-card${focused ? " elevated" : ""}`}>
      <div className="suggestion-body">
        <span className="label-muted">{data.heading}</span>
        <p className="text-secondary size-sm suggestion-text">{data.body}</p>
      </div>
      {data.action_label && (
        <button className="suggestion-action" onClick={handleDismiss}>
          {data.action_label}
        </button>
      )}
    </div>
  );
}
