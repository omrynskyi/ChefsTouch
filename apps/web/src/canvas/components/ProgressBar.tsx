import type { ProgressBarData } from "@pair-cooking/types";

interface Props {
  data: ProgressBarData;
  focused?: boolean;
  alertBelow?: boolean;
}

export function ProgressBar({ data, focused, alertBelow }: Props) {
  const pct = data.total > 0 ? Math.round((data.current / data.total) * 100) : 0;
  return (
    <div className={`progress-bar card${focused ? " elevated" : ""}${alertBelow ? " card--joined" : ""}`}>
      <span className="label-muted">
        Step {data.current} of {data.total}
      </span>
      <div className="progress-track" role="progressbar" aria-valuenow={data.current} aria-valuemin={0} aria-valuemax={data.total}>
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
