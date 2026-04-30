import { Canvas } from "./canvas/Canvas";
import { AgentStatusBar } from "./canvas/AgentStatusBar";
import { DebugPanel } from "./canvas/DebugPanel";

export default function App() {
  return (
    <>
      <AgentStatusBar />
      <Canvas />
      {import.meta.env.DEV && <DebugPanel />}
    </>
  );
}
