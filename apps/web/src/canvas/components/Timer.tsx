import { useEffect, useRef, useState } from "react";
import type { TimerData } from "@pair-cooking/types";

const CIRCUMFERENCE = 2 * Math.PI * 42; // r=42 → ≈ 264

const storageKey = (id: string) => `timer-start-${id}`;

interface Props {
  data: TimerData;
  id: string;
  focused?: boolean;
}

export function Timer({ data, id, focused }: Props) {
  const [remaining, setRemaining] = useState(data.duration_seconds);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Single effect handles both initial setup and duration/auto_start changes.
  // Merging avoids a race where the reset effect clears localStorage before
  // the auto_start effect can read it on initial mount.
  useEffect(() => {
    clearInterval(intervalRef.current!);

    if (!data.auto_start) {
      // No timer running — just display the full duration and clear any stale key.
      setRemaining(data.duration_seconds);
      localStorage.removeItem(storageKey(id));
      return;
    }

    // Reconnect persistence: compute remaining from stored start time if present.
    const stored = localStorage.getItem(storageKey(id));
    if (stored) {
      const elapsed = Math.floor((Date.now() - parseInt(stored, 10)) / 1000);
      const resumed = Math.max(0, data.duration_seconds - elapsed);
      setRemaining(resumed);
      if (resumed === 0) {
        localStorage.removeItem(storageKey(id));
        return; // Already finished — no interval needed.
      }
    } else {
      // Fresh start — record when the timer began.
      localStorage.setItem(storageKey(id), String(Date.now()));
      setRemaining(data.duration_seconds);
    }

    intervalRef.current = setInterval(() => {
      setRemaining((r: number) => {
        if (r <= 1) {
          clearInterval(intervalRef.current!);
          localStorage.removeItem(storageKey(id));
          return 0;
        }
        return r - 1;
      });
    }, 1000);

    return () => clearInterval(intervalRef.current!);
  }, [id, data.auto_start, data.duration_seconds]);

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
