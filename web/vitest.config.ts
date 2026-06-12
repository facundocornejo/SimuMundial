import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // Solo unit tests: los e2e de Playwright (web/e2e/*.spec.ts) corren con `npm run test:e2e`
    include: ["tests/**/*.test.ts"],
  },
});
