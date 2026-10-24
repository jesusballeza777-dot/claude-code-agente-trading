import { defineConfig } from "@playwright/test";

// E2E contra el backend real (solo 127.0.0.1, sin autenticación de desarrollo) sirviendo la
// app compilada. En CI no hay datos de mercado descargados: esas vistas salen como demo.
// PLAYWRIGHT_CHROMIUM: ruta a un Chromium ya instalado; si no, el de `npx playwright install`.
const chromium = process.env.PLAYWRIGHT_CHROMIUM;

export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:8000",
    launchOptions: chromium ? { executablePath: chromium } : {},
  },
  webServer: {
    command: "cd ../.. && uv run python -m trading.api",
    url: "http://127.0.0.1:8000/api/estado",
    reuseExistingServer: true,
    timeout: 120_000,
    env: {
      TRADING_API_AUTH: "disabled",
      TRADING_APP_STATE: process.env.TRADING_APP_STATE ?? "/tmp/centro-de-mando-e2e",
    },
  },
});
