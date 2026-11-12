import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, ".") },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    // Con jsdom, las pruebas que escriben en formularios pasan los 5 s por omisión cuando la
    // máquina está ocupada (todas las suites a la vez, o el producto levantado), y fallan sin error real.
    testTimeout: 15000,
  },
});