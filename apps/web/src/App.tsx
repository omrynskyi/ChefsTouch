import { Canvas } from "./canvas/Canvas";
import { DebugPanel } from "./canvas/DebugPanel";

export default function App() {
  return (
    <>
      <Canvas />
      {import.meta.env.DEV && <DebugPanel />}
    </>
  );
}
