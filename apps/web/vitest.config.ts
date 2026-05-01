import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    coverage: {
      provider: "v8",
      include: ["src/canvas/reducer.ts"],
      thresholds: { branches: 100 },
    },
  },
});
