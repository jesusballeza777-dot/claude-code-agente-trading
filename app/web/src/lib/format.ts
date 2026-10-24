// Formato de cifras para la app. Los números los calcula el backend; aquí solo se muestran.

const nf = (min: number, max: number) =>
  new Intl.NumberFormat("es-MX", { minimumFractionDigits: min, maximumFractionDigits: max });

export function usd(value: string | number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) return "—";
  return `USD ${nf(decimals, decimals).format(n)}`;
}

export function pct(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return `${nf(decimals, decimals).format(value * 100)}%`;
}

export function r(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${nf(decimals, decimals).format(Math.abs(value))} R`;
}

export function num(value: string | number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) return "—";
  return nf(0, decimals).format(n);
}

export function fecha(iso: string): string {
  return iso.slice(0, 10);
}

export function fechaHora(iso: string): string {
  return `${iso.slice(0, 10)} ${iso.slice(11, 16)} UTC`;
}

/** Tono semántico de una cifra con signo: ganancia, pérdida o neutral. */
export function tono(value: number | null | undefined): "gain" | "loss" | "neutral" {
  if (value === null || value === undefined || value === 0 || !Number.isFinite(value)) {
    return "neutral";
  }
  return value > 0 ? "gain" : "loss";
}
