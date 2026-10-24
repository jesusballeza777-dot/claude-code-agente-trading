import { mkdir } from "node:fs/promises";
import { test } from "@playwright/test";
import { PAGES, prepare, settle } from "./helpers";

// Capturas de cada página en oscuro, claro y móvil para docs/capturas/ (`npm run capturas`).
const OUT = "../../docs/capturas";
const VARIANTS = [
  { name: "oscuro", theme: "dark", viewport: { width: 1440, height: 900 } },
  { name: "claro", theme: "light", viewport: { width: 1440, height: 900 } },
  { name: "movil", theme: "dark", viewport: { width: 390, height: 844 } },
] as const;

test.skip(!process.env.CAPTURAS, "solo con CAPTURAS=1");

for (const variant of VARIANTS) {
  test(`capturas ${variant.name}`, async ({ page }) => {
    await mkdir(OUT, { recursive: true });
    await page.setViewportSize(variant.viewport);
    await prepare(page, variant.theme);
    for (const [name, path] of PAGES) {
      await page.goto(path);
      await settle(page);
      await page.screenshot({ path: `${OUT}/${name}-${variant.name}.jpg`, fullPage: true, type: "jpeg", quality: 78 });
    }
  });
}
