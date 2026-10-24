// Gráficas de métricas con Recharts y SVG propio. Ejes limpios, tooltips útiles y zonas
// sombreadas para límites e incertidumbre.
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { pct, r as fmtR, usd } from "../../lib/format";
import { cx } from "../ui";

const axis = { stroke: "var(--ink-muted)", fontSize: 11, tickLine: false };
const grid = { stroke: "var(--line)", strokeDasharray: "3 3" };
const tooltip = {
  contentStyle: {
    background: "var(--surface)",
    border: "1px solid var(--line)",
    borderRadius: 10,
    color: "var(--ink)",
    fontSize: 12,
  },
  labelStyle: { color: "var(--ink-muted)" },
};

export function EquityChart({ data, height = 240 }: { data: { t: string; capital: number }[]; height?: number }) {
  return (
    <div role="img" aria-label="Curva de capital neta">
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ left: 4, right: 8, top: 6, bottom: 0 }}>
          <defs>
            <linearGradient id="relleno-capital" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid {...grid} vertical={false} />
          <XAxis dataKey="t" {...axis} minTickGap={40} />
          <YAxis {...axis} width={56} domain={["auto", "auto"]} tickFormatter={(v: number) => v.toFixed(0)} />
          <Tooltip {...tooltip} formatter={(v) => [usd(Number(v)), "Capital"]} />
          <Area type="monotone" dataKey="capital" stroke="var(--accent)" strokeWidth={2} fill="url(#relleno-capital)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function UnderwaterChart({ data, height = 160 }: { data: { t: string; dd: number }[]; height?: number }) {
  return (
    <div role="img" aria-label="Drawdown desde el máximo (underwater)">
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ left: 4, right: 8, top: 6, bottom: 0 }}>
          <CartesianGrid {...grid} vertical={false} />
          <XAxis dataKey="t" {...axis} minTickGap={40} />
          <YAxis {...axis} width={56} tickFormatter={(v: number) => pct(v, 0)} />
          <Tooltip {...tooltip} formatter={(v) => [pct(Number(v)), "Drawdown"]} />
          <ReferenceLine y={-0.15} stroke="var(--warn)" strokeDasharray="4 4" label={{ value: "parada 15%", fill: "var(--warn)", fontSize: 10 }} />
          <ReferenceLine y={-0.2} stroke="var(--loss)" strokeDasharray="4 4" label={{ value: "corte 20%", fill: "var(--loss)", fontSize: 10 }} />
          <Area type="monotone" dataKey="dd" stroke="var(--loss)" fill="var(--loss)" fillOpacity={0.18} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function RHistogram({ data, height = 200 }: { data: { desde: number; hasta: number; n: number }[]; height?: number }) {
  const rows = data.map((b) => ({ ...b, etiqueta: b.desde.toFixed(2) }));
  return (
    <div role="img" aria-label="Distribución de resultados en R">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={rows} margin={{ left: 0, right: 8, top: 6, bottom: 0 }}>
          <CartesianGrid {...grid} vertical={false} />
          <XAxis dataKey="etiqueta" {...axis} minTickGap={16} />
          <YAxis {...axis} width={36} allowDecimals={false} />
          <Tooltip {...tooltip} formatter={(v) => [v, "Operaciones"]} labelFormatter={(l) => `Desde ${l} R`} />
          <ReferenceLine x="0.00" stroke="var(--ink-muted)" />
          <Bar dataKey="n" radius={[3, 3, 0, 0]}>
            {rows.map((b) => (
              <Cell key={b.desde} fill={b.desde >= 0 ? "var(--gain)" : "var(--loss)"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function MonteCarloFan({
  data,
  height = 220,
}: {
  data: { operacion: number; p5: number; p25: number; p50: number; p75: number; p95: number }[];
  height?: number;
}) {
  const rows = data.map((d) => ({ ...d, banda90: [d.p5, d.p95], banda50: [d.p25, d.p75] }));
  return (
    <div role="img" aria-label="Abanico de Monte Carlo del capital: bandas p5-p95 y p25-p75">
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={rows} margin={{ left: 4, right: 8, top: 6, bottom: 0 }}>
          <CartesianGrid {...grid} vertical={false} />
          <XAxis dataKey="operacion" {...axis} />
          <YAxis {...axis} width={48} tickFormatter={(v: number) => `${v.toFixed(2)}x`} domain={["auto", "auto"]} />
          <Tooltip {...tooltip} formatter={(v) => (Array.isArray(v) ? v.map((x) => Number(x).toFixed(2)).join(" – ") : Number(v).toFixed(2))} />
          <ReferenceLine y={1} stroke="var(--ink-muted)" strokeDasharray="3 3" />
          <Area dataKey="banda90" stroke="none" fill="var(--accent)" fillOpacity={0.15} name="p5-p95" />
          <Area dataKey="banda50" stroke="none" fill="var(--accent)" fillOpacity={0.3} name="p25-p75" />
          <Line dataKey="p50" stroke="var(--accent)" dot={false} strokeWidth={2} name="mediana" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Mapa de calor mensual: celdas con color y cifra (nunca solo color). */
export function MonthlyHeatmap({ data }: { data: { mes: string; r: number }[] }) {
  const years = [...new Set(data.map((d) => d.mes.slice(0, 4)))];
  const max = Math.max(1, ...data.map((d) => Math.abs(d.r)));
  const months = ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];
  return (
    <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Mapa mensual (desplazable)">
      <table className="tabular w-full min-w-[34rem] border-separate border-spacing-1 text-center text-[11px]">
        <caption className="sr-only">Suma de R por mes de salida</caption>
        <thead>
          <tr>
            <th scope="col" className="text-ink-muted">Año</th>
            {months.map((m, i) => (
              <th key={i} scope="col" className="font-medium text-ink-muted">
                {m}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {years.map((year) => (
            <tr key={year}>
              <th scope="row" className="pr-1 text-ink-muted">
                {year}
              </th>
              {months.map((_, i) => {
                const cell = data.find((d) => d.mes === `${year}-${String(i + 1).padStart(2, "0")}`);
                const value = cell?.r ?? 0;
                // Tope del 40% de color: el texto mantiene contraste AA en ambos temas.
                const alpha = Math.min(Math.abs(value) / max, 1) * 0.3 + (value === 0 ? 0 : 0.1);
                return (
                  <td
                    key={i}
                    title={`${year}-${i + 1}: ${fmtR(value)}`}
                    className="rounded-md px-1 py-1.5 text-ink"
                    style={{
                      background:
                        value === 0
                          ? "var(--surface-2)"
                          : `color-mix(in srgb, var(${value > 0 ? "--gain" : "--loss"}) ${Math.round(alpha * 100)}%, transparent)`,
                    }}
                  >
                    {value === 0 ? "·" : value.toFixed(1)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Sensibilidad ±20%: esperanza al mover un parámetro (uno cada vez). */
export function SensitivityGrid({
  rows,
  baseExpectancy,
}: {
  rows: { parametro: string; base: number; valores: { valor: number; esperanza_r: number; operaciones: number }[] }[];
  baseExpectancy: number;
}) {
  return (
    <div className="space-y-2">
      {rows.map((row) => {
        const cells = [...row.valores, { valor: row.base, esperanza_r: baseExpectancy, operaciones: -1 }].sort(
          (a, b) => a.valor - b.valor,
        );
        return (
          <div key={row.parametro} className="grid grid-cols-[8rem_1fr] items-center gap-2 text-sm">
            <span className="truncate text-ink-muted">{row.parametro}</span>
            <div className="grid grid-cols-3 gap-1">
              {cells.map((c) => (
                <div
                  key={c.valor}
                  className={cx(
                    "tabular rounded-md border px-2 py-1 text-center text-xs",
                    c.operaciones === -1 ? "border-accent" : "border-line",
                    c.esperanza_r > 0 ? "text-gain" : "text-loss",
                  )}
                  style={{ background: `color-mix(in srgb, var(${c.esperanza_r > 0 ? "--gain" : "--loss"}) 12%, transparent)` }}
                >
                  <div className="text-ink-muted">{c.valor}</div>
                  <div className="font-semibold">{fmtR(c.esperanza_r)}</div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** Medidor de drawdown frente a los umbrales del 15% y el 20%. */
export function DrawdownGauge({ value, halt, hard }: { value: number; halt: number; hard: number }) {
  const scale = 0.25;
  const position = (v: number) => `${Math.min(v / scale, 1) * 100}%`;
  return (
    <div>
      <div className="relative h-4 overflow-hidden rounded-full border border-line bg-surface-2" role="meter" aria-valuemin={0} aria-valuemax={scale} aria-valuenow={value} aria-label="Drawdown actual">
        <div className="absolute inset-y-0 left-0 rounded-full bg-accent" style={{ width: position(value) }} />
        <div className="absolute inset-y-0 w-0.5 bg-warn" style={{ left: position(halt) }} />
        <div className="absolute inset-y-0 w-0.5 bg-loss" style={{ left: position(hard) }} />
      </div>
      <div className="relative mt-1 h-4 text-[11px] text-ink-muted">
        <span className="absolute" style={{ left: 0 }}>0%</span>
        <span className="absolute -translate-x-1/2 text-warn" style={{ left: position(halt) }}>
          parada {pct(halt, 0)}
        </span>
        <span className="absolute -translate-x-1/2 text-loss" style={{ left: position(hard) }}>
          corte {pct(hard, 0)}
        </span>
      </div>
    </div>
  );
}

export function BudgetBar({ used, limit, label }: { used: number; limit: number; label: string }) {
  const share = limit ? Math.min(used / limit, 1) : 0;
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span>{label}</span>
        <span className="tabular text-ink-muted">
          {pct(used)} de {pct(limit, 0)}
        </span>
      </div>
      <div className="h-2.5 rounded-full bg-surface-2" role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={limit} aria-valuenow={used}>
        <div
          className={cx("h-full rounded-full", share < 0.5 ? "bg-accent" : share < 0.9 ? "bg-warn" : "bg-loss")}
          style={{ width: `${share * 100}%` }}
        />
      </div>
    </div>
  );
}
