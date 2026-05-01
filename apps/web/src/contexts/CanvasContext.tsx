import { createContext, useContext, useEffect, useReducer } from "react";
import type { CanvasOperation, CanvasState } from "@pair-cooking/types";
import { canvasReducer, validateOperation, INITIAL_CANVAS_STATE } from "../canvas/reducer";
import { useWebSocket } from "./WebSocketContext";

export interface CanvasContextValue {
  state: CanvasState;
  dispatch: (op: CanvasOperation) => void;
}

const CanvasContext = createContext<CanvasContextValue | null>(null);

const INITIAL_STATE: CanvasState = INITIAL_CANVAS_STATE;

export function CanvasProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(canvasReducer, INITIAL_STATE);
  const { subscribe } = useWebSocket();

  useEffect(() => {
    return subscribe((msg) => {
      if (msg.type === "canvas_ops") {
        for (const op of msg.operations) {
          if (validateOperation(op)) {
            dispatch(op);
          } else {
            console.warn("[Canvas] invalid operation from server, discarding", op);
          }
        }
      }
    });
  }, [subscribe]);

  return (
    <CanvasContext.Provider value={{ state, dispatch }}>
      {children}
    </CanvasContext.Provider>
  );
}

export function useCanvas(): CanvasContextValue {
  const ctx = useContext(CanvasContext);
  if (!ctx) throw new Error("useCanvas must be used within CanvasProvider");
  return ctx;
}
