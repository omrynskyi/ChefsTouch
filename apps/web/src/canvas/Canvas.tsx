import { AnimatePresence, motion } from "framer-motion";
import type { CanvasComponent, AlertData, StepViewData, PositionToken } from "@pair-cooking/types";
import { useCanvas } from "../contexts/CanvasContext";
import { useWebSocket } from "../contexts/WebSocketContext";
import { getZone, COMPANION_TYPES } from "./zones";
import { Skeleton } from "./components/Skeleton";
import { Alert } from "./components/Alert";
import { Camera } from "./components/Camera";
import { IngredientList } from "./components/IngredientList";
import { ProgressBar } from "./components/ProgressBar";
import { RecipeGrid } from "./components/RecipeGrid";
import { RecipeOption } from "./components/RecipeOption";
import { StepMini } from "./components/StepMini";
import { StepView } from "./components/StepView";
import { Suggestion } from "./components/Suggestion";
import { TextCard } from "./components/TextCard";
import { Timer } from "./components/Timer";
import { AssistantMessage } from "./components/AssistantMessage";

// ── Zone composition rules ────────────────────────────────────────────────────
//
//  top      │ primary: progress-bar     companion-below: alert (slides from top)
//  center   │ primary: camera > step-view | recipe-grid
//           │   camera active: companion-above = mini step-view
//           │   step-view active: companion-below = text-card (centered, no join)
//  left     │ primary: ingredient-list
//  right    │ any overflow (unused by default)
//  corner-* │ timer / status dot — content-sized
//  bottom   │ suggestion

const TRANSITION = { duration: 0.2, ease: [0.25, 0.1, 0.25, 1] as const };
const COMPANION_IN  = { duration: 0.24, ease: [0.34, 1.1, 0.64, 1] as const };
const CORNER_ZONES = new Set<PositionToken>(["corner-tl", "corner-tr", "corner-bl", "corner-br"]);

function wrap(key: string, node: React.ReactNode, style?: React.CSSProperties) {
  return (
    <motion.div
      key={key}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={TRANSITION}
      style={{ width: "100%", ...style }}
    >
      {node}
    </motion.div>
  );
}

function wrapCompanion(key: string, node: React.ReactNode, fromTop = false, style?: React.CSSProperties) {
  return (
    <motion.div
      key={key}
      initial={{ opacity: 0, y: fromTop ? -10 : 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: fromTop ? -6 : 6 }}
      transition={COMPANION_IN}
      style={{ width: "100%", ...style }}
    >
      {node}
    </motion.div>
  );
}

function PrimaryRenderer({
  comp,
  recipeChildren,
  onDismiss,
}: {
  comp: CanvasComponent;
  recipeChildren: CanvasComponent<"recipe-option">[];
  onDismiss?: () => void;
}) {
  if (comp.skeleton || comp.data === null) return <Skeleton type={comp.type} />;

  switch (comp.type) {
    case "step-view":
      return <StepView data={comp.data as StepViewData} focused={comp.focused} />;
    case "progress-bar":
      return <ProgressBar data={comp.data as import("@pair-cooking/types").ProgressBarData} focused={comp.focused} />;
    case "timer":
      return <Timer data={comp.data as import("@pair-cooking/types").TimerData} focused={comp.focused} />;
    case "suggestion":
      return <Suggestion data={comp.data as import("@pair-cooking/types").SuggestionData} focused={comp.focused} />;
    case "recipe-grid":
      return <RecipeGrid data={comp.data as import("@pair-cooking/types").RecipeGridData} focused={comp.focused} children={recipeChildren} />;
    case "recipe-option":
      return <RecipeOption data={comp.data as import("@pair-cooking/types").RecipeOptionData} focused={comp.focused} />;
    case "ingredient-list":
      return <IngredientList data={comp.data as import("@pair-cooking/types").IngredientListData} focused={comp.focused} />;
    case "camera":
      return <Camera data={comp.data as import("@pair-cooking/types").CameraData} focused={comp.focused} onDismiss={onDismiss} />;
    case "text-card":
      return <TextCard data={comp.data as import("@pair-cooking/types").TextCardData} focused={comp.focused} />;
    case "assistant-message":
      return <AssistantMessage data={comp.data as import("@pair-cooking/types").AssistantMessageData} focused={comp.focused} />;
    case "alert":
      return null;
  }
}

export function Canvas() {
  const { state, dispatch } = useCanvas();
  const { status } = useWebSocket();

  // Recipe-option children
  const recipeChildren = new Map<string, CanvasComponent<"recipe-option">[]>();
  for (const comp of state.active.values()) {
    if (comp.type === "recipe-option" && comp.parent) {
      const list = recipeChildren.get(comp.parent) ?? [];
      list.push(comp as CanvasComponent<"recipe-option">);
      recipeChildren.set(comp.parent, list);
    }
  }

  // Primary zone map — companions excluded; camera takes priority over step-view in center
  const primaryByZone = new Map<PositionToken, CanvasComponent>();
  const entries = [...state.active.values()].sort((a, b) =>
    (a.type === "camera" ? 1 : 0) - (b.type === "camera" ? 1 : 0)
  );
  for (const comp of entries) {
    if (comp.type === "recipe-option" && comp.parent) continue;
    if (COMPANION_TYPES.has(comp.type)) continue;
    primaryByZone.set(getZone(comp), comp);
  }

  // Companion lookups
  const alertComp   = [...state.active.values()].find(c => c.type === "alert"     && c.data !== null) as CanvasComponent<"alert">     | undefined;
  const textCardComp= [...state.active.values()].find(c => c.type === "text-card" && c.data !== null) as CanvasComponent<"text-card"> | undefined;
  const stepViewComp= [...state.active.values()].find(c => c.type === "step-view" && c.data !== null) as CanvasComponent<"step-view"> | undefined;

  const dismissAlert  = alertComp  ? () => dispatch({ op: "remove", id: alertComp.id })  : undefined;

  const idle = state.active.size === 0;

  // ── Top zone ────────────────────────────────────────────────────────────────
  // primary: progress-bar   companion-below: alert (slides down from top bar)

  function renderTop() {
    const primary = primaryByZone.get("top");
    const alertAsCompanion = !!primary && !!alertComp;
    const alertAsPrimary   = !primary  && !!alertComp;

    return (
      <div zone="top" key="top">
        <AnimatePresence mode="popLayout">
          {primary && wrap(primary.id, (
            <PrimaryRenderer
              comp={{ ...primary, ...(alertAsCompanion ? {} : {}) }}
              recipeChildren={[]}
            />
          ))}
        </AnimatePresence>

        <AnimatePresence>
          {alertAsCompanion && alertComp?.data && wrapCompanion(
            alertComp.id + "-c",
            <Alert data={alertComp.data as AlertData} focused={alertComp.focused} attached onDismiss={dismissAlert} />,
            true   // fromTop
          )}
          {alertAsPrimary && alertComp?.data && wrapCompanion(
            alertComp.id + "-p",
            <Alert data={alertComp.data as AlertData} focused={alertComp.focused} onDismiss={dismissAlert} />,
            true
          )}
        </AnimatePresence>
      </div>
    );
  }

  // ── Center zone ─────────────────────────────────────────────────────────────
  // primary: camera (priority) > step-view | recipe-grid | text-card
  //   camera active → companion-above: mini step-view
  //   step-view active → companion-below: text-card (centered, no join)

  function renderCenter() {
    const primary = primaryByZone.get("center");
    const cameraActive  = primary?.type === "camera";
    const stepViewActive = primary?.type === "step-view";

    // Mini step above camera when camera is primary and step-view is in state
    const showMiniStep = cameraActive && !!stepViewComp?.data;
    // Text card below step-view (no visual join — just floats below)
    const showTextCard = stepViewActive && !!textCardComp?.data;
    // If nothing in center, text-card stands alone as primary
    const effectivePrimary = primary ?? textCardComp ?? undefined;

    const dismissCamera = cameraActive && primary
      ? () => dispatch({ op: "remove", id: primary.id })
      : undefined;

    return (
      <div zone="center" key="center">

        {/* Mini step-view above camera */}
        <AnimatePresence>
          {showMiniStep && stepViewComp?.data && wrapCompanion(
            "mini-step",
            <StepMini data={stepViewComp.data as StepViewData} />,
            true   // fromTop (slides down from above)
          )}
        </AnimatePresence>

        {/* Primary */}
        <AnimatePresence mode="popLayout">
          {idle ? (
            <motion.span
              key="idle"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              transition={TRANSITION}
              style={{ fontSize: "3rem" }} role="img" aria-label="Listening"
            >
              🎙️
            </motion.span>
          ) : effectivePrimary ? wrap(
            effectivePrimary.id,
            <PrimaryRenderer
              comp={effectivePrimary}
              recipeChildren={recipeChildren.get(effectivePrimary.id) ?? []}
              onDismiss={dismissCamera}
            />,
            cameraActive ? { flex: 1, minHeight: 0 } : undefined
          ) : null}
        </AnimatePresence>

        {/* Text card — centered, no connection, floats below */}
        <AnimatePresence>
          {showTextCard && textCardComp?.data && wrapCompanion(
            textCardComp.id + "-c",
            <TextCard data={textCardComp.data as import("@pair-cooking/types").TextCardData} focused={textCardComp.focused} />,
            false,
            { display: "flex", justifyContent: "center", marginTop: "var(--space-lg)" }
          )}
        </AnimatePresence>
      </div>
    );
  }

  // ── Generic zone ────────────────────────────────────────────────────────────

  function renderZone(zone: PositionToken) {
    if (zone === "top")    return renderTop();
    if (zone === "center") return renderCenter();

    const comp = primaryByZone.get(zone);
    const isCorner = CORNER_ZONES.has(zone);

    return (
      <div zone={zone} key={zone}>
        <AnimatePresence mode="popLayout">
          {comp ? (
            <motion.div
              key={comp.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={TRANSITION}
              style={isCorner ? { width: "auto" } : { width: "100%" }}
            >
              <PrimaryRenderer comp={comp} recipeChildren={recipeChildren.get(comp.id) ?? []} />
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    );
  }

  return (
    <div className="canvas-grid">
      {renderZone("corner-tl")}
      {renderZone("top")}
      <div zone="corner-tr">
        <div className="status-dot" title={status} data-status={status} />
      </div>
      {renderZone("left")}
      {renderZone("center")}
      {renderZone("right")}
      {renderZone("corner-bl")}
      {renderZone("bottom")}
      {renderZone("corner-br")}
    </div>
  );
}
