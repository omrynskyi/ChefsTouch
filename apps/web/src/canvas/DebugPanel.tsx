import { useState } from "react";
import { useCanvas } from "../contexts/CanvasContext";
import type { CanvasOperation } from "@pair-cooking/types";
import { getZone, targetZonesForOps, COMPANION_TYPES } from "./zones";

const STEPS = [
  { n: 1, instruction: "Bring a large pot of well-salted water to a rolling boil.", tip: "Salt until it tastes like the sea — about 1 tbsp per litre.", tags: ["~5 min", "stovetop"] },
  { n: 2, instruction: "Add the pasta to the boiling water and cook until al dente.", tip: "Use at least 4 litres — it should taste like the sea.", tags: ["~10 min", "stovetop"] },
  { n: 3, instruction: "While the pasta cooks, fry the guanciale in a cold pan over medium heat.", tip: "Starting cold renders the fat slowly for maximum crispness.", tags: ["~8 min", "stovetop"] },
  { n: 4, instruction: "Whisk together eggs, pecorino, and black pepper in a bowl.", tip: "Keep it off heat — the egg mixture must stay cold until the final step.", tags: ["~3 min", "off-heat"] },
  { n: 5, instruction: "Reserve a mug of pasta water, drain the pasta, and add to the guanciale pan.", tip: "The pasta water starch is what makes the sauce silky.", tags: ["stovetop"] },
  { n: 6, instruction: "Off the heat, pour the egg mixture over the pasta and toss vigorously.", tip: "Work fast — the residual heat cooks the eggs without scrambling them.", tags: ["~2 min", "off-heat"] },
];

const FIXTURES: { label: string; ops: CanvasOperation[] }[] = [
  {
    label: "Step view",
    ops: [
      { op: "add", id: "dbg-step", type: "step-view", data: { step_number: 2, total_steps: 6, recipe: "Pasta Carbonara", instruction: STEPS[1].instruction, tip: STEPS[1].tip, tags: STEPS[1].tags, action: "next_step" } },
      { op: "add", id: "dbg-progress", type: "progress-bar", data: { current: 2, total: 6 } },
      { op: "add", id: "dbg-timer", type: "timer", data: { duration_seconds: 600, label: "Boiling", auto_start: true } },
    ],
  },
  {
    label: "Alert (urgent)",
    ops: [
      { op: "add", id: "dbg-alert", type: "alert", data: { text: "Pan is too hot — reduce heat immediately!", urgent: true } },
    ],
  },
  {
    label: "Alert (warning)",
    ops: [
      { op: "add", id: "dbg-alert", type: "alert", data: { text: "Pasta is almost done — start the sauce now.", urgent: false } },
    ],
  },
  {
    label: "Suggestion",
    ops: [
      { op: "add", id: "dbg-suggestion", type: "suggestion", data: { heading: "While you wait", body: "You could chop the garlic now — it'll save you time in step 3.", action_label: "Got it" } },
    ],
  },
  {
    label: "Recipe grid",
    ops: [
      { op: "add", id: "dbg-grid", type: "recipe-grid", data: {} },
      { op: "add", id: "dbg-r1", type: "recipe-option", parent: "dbg-grid", data: { title: "Pasta Carbonara", description: "Classic Roman pasta", duration: "30 min", tags: ["italian"], action: "select_carbonara" } },
      { op: "add", id: "dbg-r2", type: "recipe-option", parent: "dbg-grid", data: { title: "Aglio e Olio", description: "Garlic, oil, and chilli", duration: "20 min", tags: ["italian", "quick"], action: "select_aglio" } },
      { op: "add", id: "dbg-r3", type: "recipe-option", parent: "dbg-grid", data: { title: "Cacio e Pepe", description: "Cheese and black pepper", duration: "25 min", tags: ["italian"], action: "select_cacio" } },
    ],
  },
  {
    label: "Ingredient list",
    ops: [
      { op: "add", id: "dbg-ingredients", type: "ingredient-list", data: { items: [{ name: "Spaghetti", qty: "200g" }, { name: "Guanciale", qty: "100g" }, { name: "Pecorino Romano", qty: "50g" }, { name: "Eggs", qty: "3 large" }, { name: "Black pepper", qty: "1 tsp" }] } },
    ],
  },
  {
    label: "Text card",
    ops: [
      { op: "add", id: "dbg-text", type: "text-card", data: { body: "Use **fresh** pasta for _best_ results. The starch content is higher, which helps the sauce cling." } },
    ],
  },
  {
    label: "Camera",
    ops: [
      { op: "add", id: "dbg-camera", type: "camera", data: { prompt: "Is the chicken cooked through? Look for clear juices and no pink meat." } },
    ],
  },
  {
    label: "Skeleton (step-view)",
    ops: [
      { op: "skeleton", id: "dbg-skeleton-step", type: "step-view" },
      { op: "skeleton", id: "dbg-skeleton-progress", type: "progress-bar" },
      { op: "skeleton", id: "dbg-skeleton-timer", type: "timer" },
    ],
  },
  {
    label: "Focused component",
    ops: [
      { op: "add", id: "dbg-step", type: "step-view", data: { step_number: 1, total_steps: 4, recipe: "Risotto", instruction: "Toast the rice in butter until translucent.", tags: ["stovetop"] } },
      { op: "focus", id: "dbg-step" },
    ],
  },
];

const btnStyle: React.CSSProperties = {
  background: "rgba(255,255,255,0.08)",
  color: "#e8d8c0",
  border: "none",
  borderRadius: "6px",
  padding: "5px 10px",
  cursor: "pointer",
  textAlign: "left",
  fontSize: "12px",
  fontFamily: "var(--font-mono)",
  transition: "background 0.1s",
};

function DbgButton({ onClick, children, accent }: { onClick: () => void; children: React.ReactNode; accent?: boolean }) {
  return (
    <button
      onClick={onClick}
      style={accent ? { ...btnStyle, background: "rgba(200,95,58,0.2)", color: "#c85f3a" } : btnStyle}
      onMouseEnter={(e) => (e.currentTarget.style.background = accent ? "rgba(200,95,58,0.35)" : "rgba(255,255,255,0.16)")}
      onMouseLeave={(e) => (e.currentTarget.style.background = accent ? "rgba(200,95,58,0.2)" : "rgba(255,255,255,0.08)")}
    >
      {children}
    </button>
  );
}

function Divider() {
  return <hr style={{ border: "none", borderTop: "1px solid rgba(255,255,255,0.1)", margin: "4px 0" }} />;
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <span style={{ color: "#a89880", fontWeight: 600, marginBottom: "2px", fontSize: "11px", letterSpacing: "0.08em", textTransform: "uppercase" }}>
      {children}
    </span>
  );
}

export function DebugPanel() {
  const { state, dispatch } = useCanvas();
  const [open, setOpen] = useState(false);
  const [stepIdx, setStepIdx] = useState(1); // 0-based index into STEPS

  const hasStepView = state.has("dbg-step");
  const hasProgress = state.has("dbg-progress");

  const clearCanvas = () => {
    for (const id of state.keys()) dispatch({ op: "remove", id });
  };

  const inject = (ops: CanvasOperation[]) => {
    // Companions (alert, text-card) never displace primaries — just add them.
    // Primary ops clear only the zones they will occupy.
    const zones = targetZonesForOps(ops);
    for (const [id, comp] of state) {
      if (!COMPANION_TYPES.has(comp.type) && zones.has(getZone(comp))) {
        dispatch({ op: "remove", id });
      }
    }
    for (const op of ops) dispatch(op);
  };

  const goToStep = (idx: number) => {
    const clamped = Math.max(0, Math.min(STEPS.length - 1, idx));
    setStepIdx(clamped);
    const s = STEPS[clamped];
    if (hasStepView) {
      dispatch({ op: "update", id: "dbg-step", data: { step_number: s.n, total_steps: 6, instruction: s.instruction, tip: s.tip ?? null, tags: s.tags, action: clamped < STEPS.length - 1 ? "next_step" : null } });
    }
    if (hasProgress) {
      dispatch({ op: "update", id: "dbg-progress", data: { current: s.n, total: 6 } });
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        bottom: "var(--space-md)",
        left: "var(--space-md)",
        zIndex: 9999,
        fontFamily: "var(--font-mono)",
        fontSize: "12px",
      }}
    >
      {open && (
        <div
          style={{
            background: "rgba(20,15,10,0.92)",
            backdropFilter: "blur(8px)",
            borderRadius: "var(--radius-md)",
            padding: "var(--space-sm) var(--space-md)",
            marginBottom: "var(--space-xs)",
            display: "flex",
            flexDirection: "column",
            gap: "4px",
            minWidth: "220px",
            maxHeight: "80vh",
            overflowY: "auto",
            boxShadow: "0 4px 24px rgba(0,0,0,0.4)",
          }}
        >
          <SectionLabel>Fixtures</SectionLabel>
          {FIXTURES.map((f) => (
            <DbgButton key={f.label} onClick={() => inject(f.ops)}>
              {f.label}
            </DbgButton>
          ))}

          <Divider />
          <SectionLabel>Step cycling</SectionLabel>
          <div style={{ color: "#a89880", fontSize: "11px", marginBottom: "2px" }}>
            Step {STEPS[stepIdx].n} of {STEPS.length}
            {!hasStepView && <span style={{ color: "#c85f3a" }}> — load Step view first</span>}
          </div>
          <div style={{ display: "flex", gap: "4px" }}>
            <DbgButton onClick={() => goToStep(stepIdx - 1)}>← Prev</DbgButton>
            <DbgButton onClick={() => goToStep(stepIdx + 1)}>Next →</DbgButton>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "2px" }}>
            {STEPS.map((s, i) => (
              <DbgButton key={i} onClick={() => goToStep(i)}>
                {stepIdx === i ? `[${s.n}]` : `${s.n}`}
              </DbgButton>
            ))}
          </div>

          <Divider />
          <DbgButton accent onClick={clearCanvas}>Clear canvas</DbgButton>
        </div>
      )}
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          background: "rgba(20,15,10,0.85)",
          color: "#a89880",
          border: "1px solid rgba(255,255,255,0.12)",
          borderRadius: "var(--radius-sm)",
          padding: "5px 12px",
          cursor: "pointer",
          fontSize: "12px",
          fontFamily: "var(--font-mono)",
          backdropFilter: "blur(8px)",
        }}
      >
        {open ? "✕ close" : "⚙ debug"}
      </button>
    </div>
  );
}
