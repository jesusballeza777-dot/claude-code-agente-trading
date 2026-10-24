import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

export const PAGES = [
  ["hoy", "/"],
  ["mercado", "/mercado"],
  ["laboratorio", "/laboratorio"],
  ["decisiones", "/decisiones"],
  ["riesgo", "/riesgo"],
  ["diario", "/diario"],
  ["proyecto", "/proyecto"],
  ["reportes", "/reportes"],
  ["ajustes", "/ajustes"],
  ["estilo", "/estilo"],
] as const;

export async function prepare(page: Page, theme: "dark" | "light" = "dark") {
  await page.addInitScript((t) => {
    localStorage.setItem("cm.bienvenida", "1");
    localStorage.setItem("cm.tema", t);
  }, theme);
}

export async function settle(page: Page) {
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("status")).toHaveCount(0, { timeout: 20_000 });
  await page.waitForTimeout(700);
}

/** Sin violaciones graves ni críticas de accesibilidad (axe, WCAG 2 A/AA). */
export async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(
    serious.map((v) => `${v.id}: ${v.help} (${v.nodes.length}) ${v.nodes.slice(0, 2).map((n) => n.target.join(" ")).join(" | ")}`),
  ).toEqual([]);
}
