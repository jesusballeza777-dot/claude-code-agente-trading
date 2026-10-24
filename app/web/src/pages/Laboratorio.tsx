import { useQuery } from "@tanstack/react-query";
import { CircleDot, Hash } from "lucide-react";
import { useState } from "react";
import { BrujulaSays } from "../components/Brujula";
import {
  EquityChart,
  MonteCarloFan,
  MonthlyHeatmap,
  RHistogram,
  SensitivityGrid,
  UnderwaterChart,
} from "../components/charts/Charts";
import {
  Badge,
  Card,
  Check,
  ErrorState,
  ExplainLine,
  Loading,
  PageHeader,
  SignedIcon,
  Stat,
  Table,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  cx,
} from "../components/ui";
import { api, type DetalleHipotesis, type Gate, type Laboratorio as LabData } from "../lib/api";
import { num, pct, r, tono } from "../lib/format";

const CRITERIOS: Record<string, { nombre: string; explica: string }> = {
  "1_operaciones_>=200": { nombre: "≥200 operaciones", explica: "Muestra mínima para que el resultado no sea suerte." },
  "2_ic90_inferior_>0": { nombre: "IC90% de la esperanza > 0", explica: "Incluso en el escenario pesimista del rango, gana." },
  "3_pf_>=1.25": { nombre: "Profit factor ≥ 1.25", explica: "Gana al menos 1.25 veces lo que pierde." },
  "4a_dsr_>=0.90": { nombre: "DSR ≥ 0.90", explica: "El Sharpe sigue siendo bueno después de corregir por todas las pruebas." },
  "4b_pbo_<=0.30": { nombre: "PBO ≤ 0.30", explica: "Poca probabilidad de que el resultado dependa de un punto concreto de parámetros." },
  "5_maxdd_p95_mc_<=25%": { nombre: "MaxDD p95 ≤ 25%", explica: "En el 95% de las simulaciones la peor caída no pasa del 25%." },
  "6a_parametros_±20%_esperanza_>0": { nombre: "Robusta a ±20% en parámetros", explica: "Mover cada parámetro un 20% no la vuelve perdedora." },
  "6b_costes_x1.5_ic90_inferior_>0": { nombre: "Aguanta costes ×1.5", explica: "Con comisiones, slippage y funding 50% peores, sigue ganando." },
  "7_positiva_en_>=2_de_3_regimenes": { nombre: "Positiva en ≥2 de 3 regímenes", explica: "No depende solo de un tipo de mercado." },
  "8_ningun_mes_>30%": { nombre: "Ningún mes > 30% del beneficio", explica: "El resultado no viene de un solo mes afortunado." },
  "h4_k_>=20": { nombre: "El filtro quita ≥ 20 entradas", explica: "Con menos, no hay potencia para evaluar el filtro." },
  h4_mejor_que_base: { nombre: "Mejor que la base", explica: "El filtro mejora la estrategia sin filtrar." },
  h4_mejor_que_p90_aleatorio: { nombre: "Mejor que el p90 de filtros al azar", explica: "Mejora más que quitar operaciones al azar." },
};

function valorDe(key: string, gate: Gate): string {
  const v = gate.valores;
  switch (key) {
    case "1_operaciones_>=200":
      return String(v.operaciones);
    case "2_ic90_inferior_>0":
      return `[${r(v.ic90_r[0])}, ${r(v.ic90_r[1])}]`;
    case "3_pf_>=1.25":
      return num(v.pf, 2);
    case "4a_dsr_>=0.90":
      return v.dsr.toFixed(3);
    case "4b_pbo_<=0.30":
      return v.pbo.toFixed(3);
    case "5_maxdd_p95_mc_<=25%":
      return pct(v.maxdd_p95_mc);
    case "6b_costes_x1.5_ic90_inferior_>0":
      return `[${r(v["costes_x1.5_ic90"][0])}, ${r(v["costes_x1.5_ic90"][1])}]`;
    case "7_positiva_en_>=2_de_3_regimenes":
      return v.regimenes_positivos.join(", ") || "ninguno";
    case "8_ningun_mes_>30%":
      return v.max_peso_mes === null ? "total ≤ 0" : pct(v.max_peso_mes);
    default:
      return "";
  }
}

function GateChecklist({ gate }: { gate: Gate }) {
  const passed = Object.values(gate.criterios).filter(Boolean).length;
  const total = Object.keys(gate.criterios).length;
  return (
    <div data-testid="gate">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Badge tone={gate.pasa_gate_sin_holdout ? "gain" : "loss"}>
          {gate.pasa_gate_sin_holdout ? "Pasa los criterios 1-8" : "No pasa el gate"}
        </Badge>
        <span className="text-sm text-ink-muted">
          {passed} de {total} criterios · criterio 9 (holdout): sellado
        </span>
      </div>
      <ul className="divide-y divide-line">
        {Object.entries(gate.criterios).map(([key, ok]) => (
          <li key={key} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
            <div>
              <div className="font-medium">{CRITERIOS[key]?.nombre ?? key}</div>
              <div className="text-xs text-ink-muted">{CRITERIOS[key]?.explica}</div>
            </div>
            <div className="flex items-center gap-3">
              <span className="tabular text-ink-muted">{valorDe(key, gate)}</span>
              <Check ok={ok} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Detail({ id }: { id: string }) {
  const { data, error, isLoading } = useQuery({
    queryKey: ["lab", id],
    queryFn: () => api.get<DetalleHipotesis>(`/api/laboratorio/${id}`),
  });
  if (isLoading) return <Loading />;
  if (error || !data) return <ErrorState error={error} />;
  const s = data.resumen;
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Operaciones" value={s.operaciones} />
        <Stat
          label="Esperanza neta"
          value={r(s.esperanza_r, 3)}
          tone={tono(s.esperanza_r)}
          hint={`IC90% [${r(s.ic90_r[0])}, ${r(s.ic90_r[1])}]`}
          explain="Lo que gana o pierde en promedio cada operación, en R, ya con comisiones, slippage y funding."
        />
        <Stat label="Profit factor" value={num(s.pf, 2)} explain="Suma de lo ganado entre suma de lo perdido." />
        <Stat label="Acierto" value={pct(s.tasa_acierto)} hint="Con stops, ganar menos de la mitad puede ser rentable." />
      </div>
      <Tabs defaultValue="gate">
        <TabsList label="Vistas del laboratorio">
          <TabsTrigger value="gate">Gate</TabsTrigger>
          <TabsTrigger value="curvas">Curvas</TabsTrigger>
          <TabsTrigger value="distribucion">Distribución</TabsTrigger>
          <TabsTrigger value="robustez">Robustez</TabsTrigger>
          <TabsTrigger value="grupos">Regímenes y dirección</TabsTrigger>
        </TabsList>
        <TabsContent value="gate">
          {data.gate ? <GateChecklist gate={data.gate} /> : <p className="text-sm text-ink-muted">Sin gate calculado.</p>}
          <ExplainLine text="El gate de la F4 es el examen que una estrategia tiene que pasar antes de acercarse al dinero. Se fijó antes de ver resultados y no se relaja." />
        </TabsContent>
        <TabsContent value="curvas" className="space-y-4">
          <div>
            <h3 className="mb-1 text-sm font-semibold">Curva de capital neta (USD 1,500 iniciales)</h3>
            <EquityChart data={data.curva} />
          </div>
          <div>
            <h3 className="mb-1 text-sm font-semibold">Drawdown desde el máximo</h3>
            <UnderwaterChart data={data.underwater} />
          </div>
          <div>
            <h3 className="mb-1 text-sm font-semibold">Abanico de Monte Carlo (capital relativo, 0.5% de riesgo)</h3>
            <MonteCarloFan data={data.abanico_monte_carlo} />
          </div>
        </TabsContent>
        <TabsContent value="distribucion" className="space-y-4">
          <div>
            <h3 className="mb-1 text-sm font-semibold">Resultados en R</h3>
            <RHistogram data={data.distribucion_r} />
          </div>
          <div>
            <h3 className="mb-1 text-sm font-semibold">Suma de R por mes</h3>
            <MonthlyHeatmap data={data.mapa_mensual} />
          </div>
        </TabsContent>
        <TabsContent value="robustez" className="space-y-4">
          <div>
            <h3 className="mb-2 text-sm font-semibold">Sensibilidad ±20% (un parámetro cada vez; el recuadro es el valor pre-registrado)</h3>
            <SensitivityGrid rows={data.sensibilidad} baseExpectancy={s.esperanza_r} />
          </div>
          <Table
            caption="Variantes de estrés y sensibilidad"
            head={["Variante", "Tipo", "Operaciones", "Esperanza", "IC90%"]}
            rows={data.variantes_extra.map((v) => [
              v.variante,
              v.tipo,
              v.resumen.operaciones,
              <span className="inline-flex items-center gap-1" key="e">
                <SignedIcon value={v.resumen.esperanza_r} /> {r(v.resumen.esperanza_r, 3)}
              </span>,
              `[${r(v.resumen.ic90_r[0])}, ${r(v.resumen.ic90_r[1])}]`,
            ])}
          />
        </TabsContent>
        <TabsContent value="grupos" className="space-y-4">
          <Table
            caption="Resultados por régimen y dirección"
            head={["Grupo", "Operaciones", "Esperanza"]}
            rows={[
              ...Object.entries(s.por_regimen).map(([k, v]) => [`Régimen ${k}`, v.n, r(v.esperanza_r, 3)]),
              ...Object.entries(s.por_direccion).map(([k, v]) => [k === "LONG" ? "Largos" : "Cortos", v.n, r(v.esperanza_r, 3)]),
            ]}
          />
          <Table
            caption="Vetos del motor de riesgo en esta corrida"
            head={["Veto", "Qué significa", "Veces"]}
            rows={data.vetos.map((v) => [v.titulo, v.explicacion, v.veces])}
          />
        </TabsContent>
      </Tabs>
      <p className="text-xs text-ink-muted">
        Corrida {data.trial_id} · parámetros {JSON.stringify(data.parametros)} · código {data.codigo_commit.slice(0, 7)} · dataset {data.dataset_id.slice(0, 7)}
      </p>
    </div>
  );
}

export function Laboratorio() {
  const { data, error, isLoading } = useQuery({ queryKey: ["lab"], queryFn: () => api.get<LabData>("/api/laboratorio") });
  const [selected, setSelected] = useState("H2-v1");
  if (isLoading) return <Loading />;
  if (error || !data) return <ErrorState error={error} />;
  const evaluated = data.hipotesis.filter((h) => h.evaluada);
  const passing = evaluated.filter((h) => h.gate?.pasa_sin_holdout);

  return (
    <>
      <PageHeader
        title="Laboratorio de estrategias"
        intro="Cada hipótesis se escribió y se congeló antes de ver datos. Aquí ves su examen completo, con costes y con su incertidumbre."
        origen={data.origen}
      >
        <span data-testid="intentos" className="inline-flex items-center gap-1 rounded-full border border-line px-2.5 py-1 text-xs font-semibold" title={data.intentos.explicacion}>
          <Hash aria-hidden size={13} /> Intentos: {data.intentos.principales} principales · {data.intentos.total} corridas
        </span>
      </PageHeader>
      <BrujulaSays className="mb-4">
        {passing.length === 0
          ? `Ninguna de las ${evaluated.length} hipótesis evaluadas pasa el examen. H2 se quedó a un criterio (el PBO). No es un fracaso: es el sistema evitando que arriesgues dinero sin evidencia.`
          : `${passing.length} hipótesis pasan los criterios 1-8. Falta el holdout, que se abre una sola vez y con tu autorización.`}
      </BrujulaSays>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {data.hipotesis.map((h) => (
          <button
            key={h.id}
            type="button"
            disabled={!h.evaluada}
            onClick={() => setSelected(h.id)}
            aria-pressed={selected === h.id}
            className={cx(
              "rounded-2xl border bg-surface p-3 text-left transition disabled:opacity-70",
              selected === h.id ? "border-accent ring-2 ring-accent/30" : "border-line hover:border-accent/50",
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-display font-semibold">{h.id}</span>
              {h.gate ? (
                <Check ok={h.gate.pasa_sin_holdout} label={h.gate.pasa_sin_holdout ? "pasa" : "no pasa"} />
              ) : (
                <Check ok={null} label={h.evaluada ? "sin gate" : "aplazada"} />
              )}
            </div>
            <div className="mt-1 text-sm text-ink-muted">{h.titulo}</div>
            {h.resumen && (
              <div className="tabular mt-2 text-sm">
                {h.resumen.operaciones} operaciones · {r(h.resumen.esperanza_r, 3)}
              </div>
            )}
            <ol className="mt-2 flex flex-wrap gap-1" aria-label="Ciclo de vida">
              {h.ciclo.map((c) => (
                <li
                  key={c.etapa}
                  title={`${c.etapa}: ${c.estado}`}
                  className={cx(
                    "inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px]",
                    c.estado.startsWith("hecho") || c.estado.startsWith("aprobado") ? "border-gain/40 text-gain" : c.estado === "rechazado" ? "border-loss/40 text-loss" : "border-line text-ink-muted",
                  )}
                >
                  <CircleDot aria-hidden size={9} />
                  {c.etapa}
                </li>
              ))}
            </ol>
            {h.pista && <p className="mt-2 text-xs text-ink-muted">{h.pista}</p>}
          </button>
        ))}
      </div>
      <Card title={`Detalle de ${selected}`} className="mt-4">
        <Detail id={selected} />
      </Card>
    </>
  );
}
