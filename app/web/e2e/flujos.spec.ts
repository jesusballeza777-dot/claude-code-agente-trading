import { readFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";
import { expectAccessible, PAGES, prepare, settle } from "./helpers";

test.beforeEach(async ({ page }) => prepare(page));

test("inicio: seguridad visible, parte del día y demo rotulado", async ({ page }) => {
  await page.goto("/");
  await settle(page);
  await expect(page.getByTestId("live-trading").first()).toContainText("LIVE_TRADING apagado");
  await expect(page.getByTestId("parte-del-dia")).toContainText("LIVE_TRADING sigue apagado");
  await expect(page.getByText("DATOS DE DEMOSTRACIÓN").first()).toBeVisible();
  await expect(page.getByTestId("pendientes")).toContainText("ADR-013");
});

test("calculadora de riesgo: el motor real explica el veto", async ({ page }) => {
  await page.goto("/riesgo");
  await settle(page);
  await expect(page.getByTestId("resultado-calculo")).toContainText("El motor la aprobaría");
  await page.getByLabel("Stop (USD)").fill("61000");
  await page.getByRole("button", { name: "Calcular" }).click();
  const result = page.getByTestId("resultado-calculo");
  await expect(result).toContainText("El motor la vetaría");
  await expect(result).toContainText("Stop mal colocado");
  await expect(result).toContainText("INVALID_STOP");
});

test("laboratorio: gate completo y contador de intentos", async ({ page }) => {
  await page.goto("/laboratorio");
  await settle(page);
  await expect(page.getByTestId("intentos")).toContainText("principales");
  await page.getByRole("button", { name: /^H2-v1/ }).click();
  const gate = page.getByTestId("gate");
  await expect(gate).toContainText("PBO ≤ 0.30");
  await expect(gate).toContainText("criterio 9 (holdout): sellado");
  await page.getByRole("tab", { name: "Curvas" }).click();
  await expect(page.getByRole("img", { name: "Curva de capital neta" })).toBeVisible();
});

test("reportes: la ficha de estrategia se descarga como PDF", async ({ page }) => {
  await page.goto("/reportes");
  await settle(page);
  const card = page.getByTestId("reporte-ficha");
  const [download] = await Promise.all([page.waitForEvent("download"), card.getByRole("link", { name: "PDF" }).click()]);
  expect(download.suggestedFilename()).toMatch(/^ficha-.*\.pdf$/);
  const content = await readFile((await download.path()) ?? "");
  expect(content.subarray(0, 4).toString()).toBe("%PDF");
});

test("diario: se guarda una nota (la única escritura de la app)", async ({ page }) => {
  await page.goto("/diario");
  await settle(page);
  const texto = `Nota E2E ${Date.now()}`;
  await page.getByLabel("Nota", { exact: true }).fill(texto);
  await page.getByRole("button", { name: "Guardar nota" }).click();
  await expect(page.getByText(texto)).toBeVisible();
});

for (const theme of ["dark", "light"] as const) {
  test(`accesibilidad sin violaciones graves (${theme})`, async ({ page }) => {
    await prepare(page, theme);
    for (const [, path] of PAGES) {
      await page.goto(path);
      await settle(page);
      await expectAccessible(page);
    }
  });
}
