import type { CanvasComponent, CanvasOperation, ComponentType, PositionToken } from "@pair-cooking/types";

// ── Zone defaults ─────────────────────────────────────────────────────────────
// PRIMARY types compete for their zone (one per zone, camera > step-view in center).
// COMPANION types never displace a primary — they appear as attached siblings.

export const DEFAULT_ZONE: Record<ComponentType, PositionToken> = {
  "step-view":       "center",
  "progress-bar":    "top",
  "timer":           "corner-br",
  "suggestion":      "bottom",
  "alert":           "top",       // companion-below of progress-bar
  "recipe-grid":     "center",
  "recipe-option":   "center",    // child of recipe-grid
  "ingredient-list": "left",
  "camera":          "center",    // takes center priority; step-view becomes mini above it
  "text-card":       "center",    // companion-below of step-view
};

// Companions are rendered contextually (below/above a primary) rather than
// competing for the zone slot. They survive zone clears triggered by primaries.
export const COMPANION_TYPES = new Set<ComponentType>(["alert", "text-card"]);

// When camera is added, these types are kept in state (not evicted) because
// they render as companions above the camera instead.
export const PRESERVED_WITH_CAMERA = new Set<ComponentType>(["step-view"]);

export function getZone(comp: Pick<CanvasComponent, "type" | "position">): PositionToken {
  return comp.position ?? DEFAULT_ZONE[comp.type];
}

/** Zones that a batch of PRIMARY ops will occupy. Companion types excluded. */
export function targetZonesForOps(ops: CanvasOperation[]): Set<PositionToken> {
  const zones = new Set<PositionToken>();
  for (const op of ops) {
    if (op.op !== "add" && op.op !== "skeleton") continue;
    if (op.type === "recipe-option") continue;
    if (COMPANION_TYPES.has(op.type)) continue;
    const zone = (op.op === "add" ? op.position : undefined) ?? DEFAULT_ZONE[op.type];
    zones.add(zone);
  }
  return zones;
}
