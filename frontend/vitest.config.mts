import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: { alias: { "@": import.meta.dirname } },
  test: { environment: "node", setupFiles: ["fake-indexeddb/auto"], include: ["__tests__/**/*.test.ts"] },
});
