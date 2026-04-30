import type { RecipeOptionData } from "@pair-cooking/types";
import { useWebSocket } from "../../contexts/WebSocketContext";

interface Props {
  data: RecipeOptionData;
  focused?: boolean;
}

export function RecipeOption({ data, focused }: Props) {
  const { send } = useWebSocket();

  return (
    <button
      className={`recipe-option${focused ? " elevated" : ""}`}
      onClick={() => send({ type: "action", action: data.action })}
      aria-label={data.title}
    >
      <span className="recipe-title">{data.title}</span>
      {data.description && <span className="recipe-meta">{data.description}</span>}
      {data.duration && <span className="recipe-meta muted">{data.duration}</span>}
      {data.tags && data.tags.length > 0 && (
        <div className="tag-row">
          {data.tags.map((tag) => (
            <span key={tag} className="tag">{tag}</span>
          ))}
        </div>
      )}
    </button>
  );
}
