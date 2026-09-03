import path from "node:path";
import { defineConfig } from "vitest/config";

// Minimal Vitest setup for plain TS/logic tests (fetch wrappers, stores).
// No React rendering here, so a "node" environment is enough -- Node 22's
// built-in fetch/Response/ReadableStream cover everything these tests mock.
export default defineConfig({
  test: {
    environment: "node",
    include: ["**/*.test.ts"],
    exclude: ["node_modules", ".next"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
