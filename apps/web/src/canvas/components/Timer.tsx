import { useEffect, useRef, useState } from "react";
import type { TimerData } from "@pair-cooking/types";

const CIRCUMFERENCE = 2 * Math.PI * 42; // r=42 → ≈ 264

interface Props {
  data: TimerData;
  focused?: boolean;
}

export function Timer({ data, focused }: Props) {
  const [remaining, setRemaining] = useState(data.duration_seconds);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Reset when duration changes (e.g. update op)
  useEffect(() => {
    setRemaining(data.duration_seconds);
  }, [data.duration_seconds]);

  useEffect(() => {
    if (!data.auto_start) return;
    intervalRef.current = setInterval(() => {
      setRemaining((r: number) => {
        if (r <= 1) {
          clearInterval(intervalRef.current!);
          return 0;
        }
        return r - 1;
      });
    }, 1000);
    return () => clearInterval(intervalRef.current!);
  }, [data.auto_start, data.duration_seconds]);

  const mins = Math.floor(remaining / 60);
  const secs = remaining % 60;
  const timeLabel = `${mins}:${String(secs).padStart(2, "0")}`;
  const progress = data.duration_seconds > 0 ? remaining / data.duration_seconds : 0;
  const dashOffset = CIRCUMFERENCE * (1 - progress);
  const finished = remaining === 0;

  return (
    <div className={`card timer-ring-card${focused ? " elevated" : ""}${finished ? " pulse-on-end" : ""}`}>
      <div className="timer-ring-wrap">
        <svg className="timer-ring-svg" viewBox="0 0 104 104" aria-hidden="true">
          <circle className="timer-ring-track" cx="52" cy="52" r="42" />
          <circle
            className="timer-ring-progress"
            cx="52"
            cy="52"
            r="42"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={dashOffset}
          />
        </svg>
        <div className="timer-ring-inner">
          <span className="font-timer">{timeLabel}</span>
          <span className="timer-label">{data.label}</span>
        </div>
      </div>
    </div>
  );
}
