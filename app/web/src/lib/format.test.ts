import { describe, expect, it } from "vitest";
import { fecha, fechaHora, num, pct, r, tono, usd } from "./format";

describe("formato de cifras", () => {
  it("muestra dólares con separador de miles y guion si falta el dato", () => {
    expect(usd("1500")).toBe("USD 1,500.00");
    expect(usd(7.5)).toBe("USD 7.50");
    expect(usd(null)).toBe("—");
    expect(usd("abc")).toBe("—");
  });

  it("muestra porcentajes y múltiplos de R con signo tipográfico", () => {
    expect(pct(0.15)).toBe("15.0%");
    expect(pct(0.0001, 4)).toBe("0.0100%");
    expect(pct(undefined)).toBe("—");
    expect(r(0.516, 3)).toBe("+0.516 R");
    expect(r(-1)).toBe("−1.00 R");
    expect(r(0)).toBe("0.00 R");
    expect(r(Number.NaN)).toBe("—");
  });

  it("formatea números y fechas UTC", () => {
    expect(num("0.00625000", 6)).toBe("0.00625");
    expect(num(null)).toBe("—");
    expect(fecha("2024-12-31T20:00:00+00:00")).toBe("2024-12-31");
    expect(fechaHora("2024-12-31T20:00:00+00:00")).toBe("2024-12-31 20:00 UTC");
  });

  it("asigna un tono semántico", () => {
    expect(tono(1)).toBe("gain");
    expect(tono(-1)).toBe("loss");
    expect(tono(0)).toBe("neutral");
    expect(tono(null)).toBe("neutral");
  });
});
