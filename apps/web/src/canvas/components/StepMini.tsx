import type { StepViewData } from "@pair-cooking/types";

export function StepMini({ data }: { data: StepViewData }) {
  return (
    <div className="card step-mini">
      <span className="label-muted">{data.recipe} · {data.step_number}/{data.total_steps}</span>
      <p className="text-primary size-sm" style={{ marginTop: "var(--space-xs)", lineHeight: 1.4 }}>
        {data.instruction}
      </p>
    </div>
  );
}
