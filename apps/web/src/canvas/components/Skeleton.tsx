import type { ComponentType } from "@pair-cooking/types";

const SKELETON_HEIGHT_VAR: Record<ComponentType, string> = {
  "step-view":       "--sk-h-step-view",
  "progress-bar":    "--sk-h-progress-bar",
  "timer":           "--sk-h-timer",
  "suggestion":      "--sk-h-suggestion",
  "alert":           "--sk-h-alert",
  "recipe-grid":     "--sk-h-recipe-grid",
  "recipe-option":   "--sk-h-recipe-option",
  "ingredient-list": "--sk-h-ingredient-list",
  "camera":          "--sk-h-camera",
  "text-card":       "--sk-h-text-card",
};

export function Skeleton({ type }: { type: ComponentType }) {
  return (
    <div
      className="skeleton-shimmer"
      style={{ width: "100%", height: `var(${SKELETON_HEIGHT_VAR[type]})` }}
      aria-hidden="true"
    />
  );
}
