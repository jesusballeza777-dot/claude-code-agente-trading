// Velas con TradingView Lightweight Charts (Apache-2.0; se muestra su atribución).
import {
  CandlestickSeries,
  ColorType,
  createChart,
  createSeriesMarkers,
  LineSeries,
  LineStyle,
  type IChartApi,
  type SeriesMarker,
  type UTCTimestamp,
} from "lightweight-charts";
import { useEffect, useRef } from "react";
import type { Velas } from "../../lib/api";
import { usePrefs } from "../../lib/prefs";

const ts = (iso: string) => Math.floor(Date.parse(iso) / 1000) as UTCTimestamp;

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888";
}

const OVERLAYS: Record<string, { color: string; style: LineStyle }> = {
  canal_alto: { color: "--accent", style: LineStyle.Solid },
  canal_bajo: { color: "--accent", style: LineStyle.Solid },
  salida_alta: { color: "--demo", style: LineStyle.Dashed },
  salida_baja: { color: "--demo", style: LineStyle.Dashed },
  sma200: { color: "--demo", style: LineStyle.Solid },
};

export function CandleChart({ data, height = 420 }: { data: Velas; height?: number }) {
  const container = useRef<HTMLDivElement>(null);
  const { theme } = usePrefs();

  useEffect(() => {
    const element = container.current;
    if (!element) return;
    const chart: IChartApi = createChart(element, {
      height,
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: cssVar("--ink-muted"),
        fontFamily: "Inter Variable, system-ui, sans-serif",
        attributionLogo: true,
      },
      grid: {
        vertLines: { color: cssVar("--line") },
        horzLines: { color: cssVar("--line") },
      },
      rightPriceScale: { borderColor: cssVar("--line") },
      timeScale: { borderColor: cssVar("--line"), timeVisible: data.intervalo === "4h" },
    });
    const candles = chart.addSeries(CandlestickSeries, {
      upColor: cssVar("--gain"),
      downColor: cssVar("--loss"),
      borderVisible: false,
      wickUpColor: cssVar("--gain"),
      wickDownColor: cssVar("--loss"),
    });
    candles.setData(data.velas.map((v) => ({ time: ts(v.t), open: v.o, high: v.h, low: v.l, close: v.c })));

    for (const [name, style] of Object.entries(OVERLAYS)) {
      const values = data.indicadores[name];
      if (!values) continue;
      const line = chart.addSeries(LineSeries, {
        color: cssVar(style.color),
        lineWidth: 1,
        lineStyle: style.style,
        priceLineVisible: false,
        lastValueVisible: false,
        title: name.replace("_", " "),
      });
      line.setData(
        data.velas.flatMap((v, i) => {
          const value = values[i];
          return value === null || value === undefined ? [] : [{ time: ts(v.t), value }];
        }),
      );
    }

    const markers: SeriesMarker<UTCTimestamp>[] = data.marcadores
      .filter((m) => m.t >= (data.velas[0]?.t ?? ""))
      .map((m) =>
        m.tipo === "entrada"
          ? {
              time: ts(m.t),
              position: m.lado === "LONG" ? ("belowBar" as const) : ("aboveBar" as const),
              shape: m.lado === "LONG" ? ("arrowUp" as const) : ("arrowDown" as const),
              color: cssVar("--accent"),
              text: m.lado === "LONG" ? "Largo" : "Corto",
            }
          : {
              time: ts(m.t),
              position: "aboveBar" as const,
              shape: "circle" as const,
              color: cssVar(m.r >= 0 ? "--gain" : "--loss"),
              text: `${m.r >= 0 ? "+" : "−"}${Math.abs(m.r).toFixed(1)}R`,
            },
      )
      .sort((a, b) => a.time - b.time);
    createSeriesMarkers(candles, markers);
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [data, height, theme]);

  return (
    <figure aria-label={`Velas de ${data.simbolo} (${data.intervalo})`}>
      <div ref={container} style={{ height }} />
      <figcaption className="mt-1 text-xs text-ink-muted">
        Líneas: canal de entrada de H2 (turquesa) y de salida (punteado) en 4h; media de 200 días en 1d. Flechas: entradas
        del backtest; círculos: salidas con su resultado en R.
      </figcaption>
    </figure>
  );
}
