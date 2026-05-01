import type { AlertData } from "@pair-cooking/types";

interface Props {
  data: AlertData;
  focused?: boolean;
  attached?: boolean;
  onDismiss?: () => void;
}

export function Alert({ data, focused, attached, onDismiss }: Props) {
  return (
    <div
      className={[
        "alert",
        data.urgent ? "alert-urgent" : "",
        focused ? "elevated" : "",
        attached ? "alert--attached" : "",
      ].filter(Boolean).join(" ")}
      role="alert"
    >
      <span className="alert-text">{data.text}</span>
      {onDismiss && (
        <button className="alert-dismiss" onClick={onDismiss} aria-label="Dismiss">✕</button>
      )}
    </div>
  );
}
