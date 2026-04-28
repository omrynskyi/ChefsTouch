import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { CanvasProvider } from "./contexts/CanvasContext";
import { WebSocketProvider } from "./contexts/WebSocketContext";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <WebSocketProvider>
      <CanvasProvider>
        <App />
      </CanvasProvider>
    </WebSocketProvider>
  </StrictMode>
);
