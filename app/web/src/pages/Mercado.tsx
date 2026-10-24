import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { CandleChart } from "../components/charts/CandleChart";
import { Card, ErrorState, ExplainLine, Loading, OrigenBadge, PageHeader } from "../components/ui";
import { api, type Origen, type Velas } from "../lib/api";
import { pct } from "../lib/format";

interface Regimenes {
  origen: Origen;
  tramos: { regimen: string; desde: string; hasta: string }[];
}
interface Correlaciones {
  origen: Origen;
  ventana?: string;
  simbolos: string[];
  matriz: (number | null)[][];
}

const REGIMEN_TONO: Record<string, string> = {
  alcista: "var(--gain)",
  bajista: "var(--loss)",
  lateral: "var(--neutral)",
  "sin etiqueta": "var(--line)",
};

export function Mercado() {
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [interval, setInterval] = useState<"4h" | "1d">("4h");
  const symbols = useQuery({
    queryKey: ["simbolos"],
    queryFn: () => api.get<{ origen: Origen; simbolos: string[] }>("/api/mercado/simbolos"),
  });
  const days = interval === "4h" ? 120 : 720;
  const candles = useQuery({
    queryKey: ["velas", symbol, interval],
    queryFn: () => api.get<Velas>(`/api/mercado/velas?simbolo=${symbol}&intervalo=${interval}&dias=${days}`),
  });
  const regimes = useQuery({ queryKey: ["regimenes"], queryFn: () => api.get<Regimenes>("/api/mercado/regimenes") });
  const corr = useQuery({ queryKey: ["correlaciones"], queryFn: () => api.get<Correlaciones>("/api/mercado/correlaciones") });

  const funding = candles.data?.funding ?? [];
  const lastFunding = funding.at(-1);
  const tramos = (regimes.data?.tramos ?? []).filter((t) => t.hasta >= "2020-01-01");
  const totalDays = tramos.reduce((acc, t) => acc + (Date.parse(t.hasta) - Date.parse(t.desde)) / 864e5 + 1, 0) || 1;

  return (
    <>
      <PageHeader
        title="Mercado"
        intro="Velas reales del archivo público de Binance (2020-2024) con los indicadores que usan las hipótesis. El holdout de 2025 en adelante no se muestra."
        origen={candles.data?.origen}
      />
      <Card
        title={`${symbol} · ${interval}`}
        action={
          <div className="flex flex-wrap items-center gap-2">
            <label className="text-sm">
              <span className="sr-only">Activo</span>
              <select
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className="rounded-lg border border-line bg-surface px-2 py-1.5 text-sm"
                aria-label="Activo"
              >
                {(symbols.data?.simbolos ?? ["BTCUSDT"]).map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </label>
            <div role="group" aria-label="Intervalo" className="flex rounded-lg border border-line p-0.5">
              {(["4h", "1d"] as const).map((i) => (
                <button
                  key={i}
                  type="button"
                  aria-pressed={interval === i}
                  onClick={() => setInterval(i)}
                  className={`rounded-md px-3 py-1 text-sm ${interval === i ? "bg-accent text-accent-ink" : "text-ink-muted"}`}
                >
                  {i}
                </button>
              ))}
            </div>
          </div>
        }
        demo={candles.data?.origen === "demo"}
      >
        {candles.isLoading ? <Loading /> : candles.error ? <ErrorState error={candles.error} /> : candles.data && <CandleChart data={candles.data} />}
        <ExplainLine text="H2 entra cuando el cierre rompe el canal de 60 velas con la volatilidad en aumento, y sale por el canal de 20. H1 sigue el signo de la rentabilidad de 7 días." />
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card title="Funding" subtitle="Tasa por 8 h; positiva = pagan los largos.">
          {lastFunding ? (
            <>
              <div className="cifra text-3xl font-semibold">{pct(lastFunding.tasa_8h, 4)}</div>
              <p className="text-sm text-ink-muted">Última liquidación del periodo ({lastFunding.t.slice(0, 10)}).</p>
              <div className="mt-3 flex h-16 items-end gap-px" aria-hidden>
                {funding.slice(-90).map((f) => (
                  <span
                    key={f.t}
                    className="flex-1 rounded-t-sm"
                    style={{
                      height: `${Math.min(Math.abs(f.tasa_8h) / 0.001, 1) * 100}%`,
                      background: f.tasa_8h >= 0 ? "var(--accent)" : "var(--loss)",
                      minHeight: 1,
                    }}
                  />
                ))}
              </div>
            </>
          ) : (
            <p className="text-sm text-ink-muted">Sin funding para este activo en el periodo.</p>
          )}
          <ExplainLine text="Pago entre largos y cortos cada pocas horas. El ADR-013 propone no entrar si el funding en contra supera 0.10% cada 8 h." />
        </Card>

        <Card title="Régimen de BTC" subtitle="Media de 200 días del par spot (solo para etiquetar)" action={<OrigenBadge origen={regimes.data?.origen ?? "real"} />}>
          <div className="flex h-6 overflow-hidden rounded-full border border-line" role="img" aria-label="Línea de tiempo de regímenes 2020-2024">
            {tramos.map((t) => (
              <span
                key={t.desde}
                title={`${t.regimen}: ${t.desde} → ${t.hasta}`}
                style={{
                  width: `${(((Date.parse(t.hasta) - Date.parse(t.desde)) / 864e5 + 1) / totalDays) * 100}%`,
                  background: REGIMEN_TONO[t.regimen] ?? "var(--line)",
                }}
              />
            ))}
          </div>
          <ul className="mt-3 flex flex-wrap gap-3 text-xs">
            {["alcista", "bajista", "lateral"].map((r) => (
              <li key={r} className="flex items-center gap-1">
                <span className="h-2.5 w-2.5 rounded-sm" style={{ background: REGIMEN_TONO[r] }} /> {r}
              </li>
            ))}
          </ul>
          <ExplainLine text="Alcista: precio sobre su media de 200 días y la media subiendo. Bajista: lo contrario. Lateral: el resto." />
        </Card>

        <Card title="Correlaciones" subtitle={corr.data?.ventana ?? "Rendimientos diarios"} action={<OrigenBadge origen={corr.data?.origen ?? "real"} />}>
          <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Matriz de correlaciones (desplazable)">
            <table className="tabular border-separate border-spacing-0.5 text-[10px]">
              <caption className="sr-only">Matriz de correlaciones de los rendimientos diarios</caption>
              <thead>
                <tr>
                  <th />
                  {corr.data?.simbolos.map((s) => (
                    <th key={s} scope="col" className="px-0.5 font-medium text-ink-muted">
                      {s.replace("USDT", "")}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {corr.data?.matriz.map((row, i) => (
                  <tr key={corr.data?.simbolos[i]}>
                    <th scope="row" className="pr-1 text-right font-medium text-ink-muted">
                      {corr.data?.simbolos[i]?.replace("USDT", "")}
                    </th>
                    {row.map((v, j) => (
                      <td
                        key={j}
                        className="h-7 w-8 rounded text-center"
                        style={{ background: v === null ? "var(--surface-2)" : `color-mix(in srgb, var(--accent) ${Math.round(Math.abs(v) * 40)}%, transparent)` }}
                      >
                        {v === null ? "·" : v.toFixed(1)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ExplainLine text="Cerca de 1: se mueven juntos. Por eso BTC y ETH cuentan como una sola apuesta en el motor de riesgo." />
        </Card>
      </div>
    </>
  );
}
