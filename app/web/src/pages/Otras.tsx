// Decisiones, Diario, Proyecto, Reportes y Ajustes.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleCheck, CircleDot, CircleMinus, Clock, Download, FileJson, FileSpreadsheet, FileText, NotebookPen, Settings } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { BrujulaSays } from "../components/Brujula";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  ExplainLine,
  Loading,
  OrigenBadge,
  PageHeader,
  SignedIcon,
  Switch,
  Table,
  cx,
} from "../components/ui";
import { api, type Decisiones as DecisionesData, type Diario as DiarioData, type Limites, type Proyecto as ProyectoData, type Reportes as ReportesData } from "../lib/api";
import { IN_ANDROID_APP } from "../lib/env";
import { fechaHora, pct, r, usd } from "../lib/format";
import { usePrefs } from "../lib/prefs";

export function Decisiones() {
  const { data, error, isLoading } = useQuery({ queryKey: ["decisiones"], queryFn: () => api.get<DecisionesData>("/api/decisiones") });
  const [open, setOpen] = useState<number | null>(null);
  if (isLoading) return <Loading />;
  if (error || !data) return <ErrorState error={error} />;
  return (
    <>
      <PageHeader title="Decisiones del analista" intro="Cada decisión de Claude con su acción, nivel, motivo, evidencia y los vetos del motor. Llega con la F5." origen={data.origen} />
      <BrujulaSays className="mb-4">{data.vacio}</BrujulaSays>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Línea de tiempo" className="lg:col-span-2" demo>
          <ol className="space-y-2">
            {data.decisiones.map((d, i) => (
              <li key={d.t} className="rounded-xl border border-line bg-surface/80 p-3">
                <button type="button" className="flex w-full flex-wrap items-center justify-between gap-2 text-left" onClick={() => setOpen(open === i ? null : i)} aria-expanded={open === i}>
                  <span className="flex items-center gap-2">
                    <Badge tone={d.accion.startsWith("ENTER") ? "accent" : "neutral"}>{d.accion}</Badge>
                    <span className="text-sm">{d.motivo}</span>
                  </span>
                  <span className="flex items-center gap-2 text-xs text-ink-muted">
                    nivel {d.nivel}
                    {d.veto && <Badge tone="loss">vetada: {d.veto}</Badge>}
                    {fechaHora(d.t)}
                  </span>
                </button>
                {open === i && (
                  <pre className="mt-2 overflow-x-auto rounded-lg bg-surface-2 p-3 font-mono text-xs">{JSON.stringify(d.json, null, 2)}</pre>
                )}
              </li>
            ))}
          </ol>
        </Card>
        <Card title="Libros A/B/C" subtitle="Regla pura, regla + veto de Claude y placebo de vetos al azar" demo>
          <Table
            caption="Comparación de libros"
            head={["Libro", "Operaciones", "Esperanza"]}
            rows={data.libros.map((l) => [l.libro, l.operaciones, l.esperanza_r === null ? "—" : r(l.esperanza_r)])}
          />
          <ExplainLine text="Si el libro B (con el veto de Claude) no supera al placebo C, el analista no aporta nada y no se usa." />
        </Card>
      </div>
    </>
  );
}

export function Diario() {
  const client = useQueryClient();
  const { data, error, isLoading } = useQuery({ queryKey: ["diario"], queryFn: () => api.get<DiarioData>("/api/diario") });
  const [texto, setTexto] = useState("");
  const [referencia, setReferencia] = useState("");
  const save = useMutation({
    mutationFn: () => api.post("/api/diario/notas", { referencia, texto }),
    onSuccess: () => {
      setTexto("");
      setReferencia("");
      void client.invalidateQueries({ queryKey: ["diario"] });
    },
  });
  if (isLoading) return <Loading />;
  if (error || !data) return <ErrorState error={error} />;
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (texto.trim()) save.mutate();
  };
  return (
    <>
      <PageHeader title="Diario de operaciones" intro={data.aviso} origen={data.origen} />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Operaciones" className="lg:col-span-2" subtitle={`${data.operaciones.length} más recientes de H1 y H2`}>
          <Table
            caption="Operaciones del backtest"
            head={["Id", "Activo", "Lado", "Entrada", "Salida", "Motivo", "Resultado"]}
            rows={data.operaciones.slice(0, 60).map((o) => [
              <code key="i" className="font-mono text-xs">{o.id}</code>,
              o.simbolo.replace("USDT", ""),
              o.lado === "LONG" ? "Largo" : "Corto",
              o.entrada.slice(0, 16).replace("T", " "),
              o.salida.slice(0, 16).replace("T", " "),
              o.motivo_salida,
              <span key="r" className="inline-flex items-center gap-1 tabular">
                <SignedIcon value={o.r} /> {r(o.r)} · {usd(o.pnl)}
              </span>,
            ])}
          />
        </Card>
        <Card title={<span className="inline-flex items-center gap-2"><NotebookPen aria-hidden size={17} /> Tus notas</span>} subtitle="La única escritura de la app: no toca riesgo ni ejecución.">
          <form onSubmit={submit} className="space-y-2" aria-label="Nueva nota">
            <input value={referencia} onChange={(e) => setReferencia(e.target.value)} placeholder="Referencia (por ejemplo H2-v1-0001)" maxLength={80} className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm" aria-label="Referencia" />
            <textarea value={texto} onChange={(e) => setTexto(e.target.value)} rows={4} maxLength={2000} placeholder="¿Qué aprendiste de esta operación?" className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm" aria-label="Nota" />
            <Button type="submit" disabled={save.isPending || !texto.trim()}>
              Guardar nota
            </Button>
            {save.error && <ErrorState error={save.error} />}
          </form>
          <ul className="mt-4 space-y-2">
            {data.notas.length === 0 && <EmptyState>Todavía no hay notas.</EmptyState>}
            {[...data.notas].reverse().map((n) => (
              <li key={n.id} className="rounded-lg border border-line p-2 text-sm">
                <div className="text-xs text-ink-muted">
                  {n.fecha_utc.replace("T", " ").replace("Z", " UTC")} {n.referencia && `· ${n.referencia}`}
                </div>
                <p className="whitespace-pre-wrap">{n.texto}</p>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}

// El registro escribe la probabilidad en femenino (Alta) y el impacto en masculino (Alto).
const NIVEL: Record<string, number> = { Baja: 0, Bajo: 0, Media: 1, Medio: 1, Alta: 2, Alto: 2 };
const nivel = (text: string) => NIVEL[text.split(" ")[0] ?? ""] ?? -1;

/** Estado de una fase: hecha, en curso, pendiente de ti o no empezada (icono + texto, no solo color). */
function PhaseStatus({ estado }: { estado: string }) {
  const [Icon, tone] = /^(cerrada|hecha)/.test(estado)
    ? [CircleCheck, "text-gain"]
    : estado.startsWith("pendiente")
      ? [Clock, "text-warn"]
      : estado.startsWith("en curso")
        ? [CircleDot, "text-accent"]
        : [CircleMinus, "text-neutral"];
  return (
    <span className={cx("inline-flex items-center gap-1 text-right", tone)}>
      <Icon aria-hidden size={16} className="shrink-0" /> {estado}
    </span>
  );
}

export function Proyecto() {
  const { data, error, isLoading } = useQuery({ queryKey: ["proyecto"], queryFn: () => api.get<ProyectoData>("/api/proyecto") });
  if (isLoading) return <Loading />;
  if (error || !data) return <ErrorState error={error} />;
  const matrix = [2, 1, 0].map((p) => [0, 1, 2].map((i) => data.riesgos.filter((x) => nivel(x.probabilidad) === p && nivel(x.impacto) === i)));
  const outside = data.riesgos.filter((x) => nivel(x.probabilidad) < 0 || nivel(x.impacto) < 0);
  const probLabel = ["baja", "media", "alta"];
  const impactLabel = ["bajo", "medio", "alto"];
  return (
    <>
      <PageHeader title="Proyecto" intro="Roadmap, decisiones de arquitectura, riesgos y costes, leídos de los documentos del repositorio." origen={data.origen} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Roadmap F0-F9">
          <ol className="space-y-1.5">
            {data.fases.map((f) => (
              <li key={f.id} className="flex items-center justify-between gap-2 text-sm">
                <span>
                  <span className="cifra font-semibold">{f.id}</span> {f.nombre}
                </span>
                <PhaseStatus estado={f.estado} />
              </li>
            ))}
          </ol>
        </Card>
        <Card title="Tus pendientes">
          <ol className="list-decimal space-y-2 pl-5 text-sm">
            {data.pendientes_propietario.map((p) => (
              <li key={p.tarea}>
                {p.tarea} <span className="text-xs text-ink-muted">({p.documento})</span>
              </li>
            ))}
          </ol>
        </Card>
        <Card title="Matriz de riesgos" subtitle="Probabilidad × impacto (docs/risk_register.md)">
          <div data-testid="matriz-riesgos">
            <div className="grid grid-cols-[4rem_repeat(3,1fr)] gap-1 text-xs">
              <span />
              {impactLabel.map((l) => (
                <span key={l} className="text-center text-ink-muted">
                  Impacto {l}
                </span>
              ))}
              {matrix.map((row, p) => (
                <div key={p} className="contents">
                  <span className="flex items-center text-ink-muted">Prob. {probLabel[2 - p]}</span>
                  {row.map((cell, i) => (
                    <div
                      key={i}
                      className="min-h-14 rounded-lg border border-line p-1.5"
                      style={{ background: `color-mix(in srgb, var(--loss) ${((2 - p) + i) * 8}%, transparent)` }}
                      title={cell.map((c) => `${c.id}: ${c.riesgo}`).join("\n")}
                    >
                      <div className="flex flex-wrap gap-1">
                        {cell.map((c) => (
                          <span key={c.id} className="rounded bg-surface px-1 font-mono">
                            {c.id}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
            {outside.length > 0 && (
              <p className="mt-3 text-xs text-ink-muted">
                Fuera de la matriz: {outside.map((x) => `${x.id} (${x.probabilidad.toLowerCase()})`).join(", ")}.
              </p>
            )}
          </div>
        </Card>
        <Card title="Costes" subtitle={`Tipo de cambio: ${data.costes.tipo_de_cambio.mxn_por_usd} MXN/USD (${data.costes.tipo_de_cambio.estado})`}>
          <Table caption="Presupuesto mensual" head={["Concepto", "USD/mes", "Estado"]} rows={data.costes.conceptos.map((c) => [c.concepto, c.usd_mes, c.estado])} />
          <p className="mt-3 text-xs text-ink-muted">
            <OrigenBadge origen={data.costes.uso_api_claude.origen} /> {data.costes.uso_api_claude.nota}
          </p>
        </Card>
        <Card title="Decisiones de arquitectura (ADR)" className="lg:col-span-2">
          <Table
            caption="ADR y su estado"
            head={["ADR", "Título", "Estado"]}
            rows={data.adr.map((a) => [a.id, a.titulo, <Badge key="e" tone={a.estado.includes("Propuesto") ? "warn" : "neutral"}>{a.estado}</Badge>])}
          />
        </Card>
      </div>
    </>
  );
}

const ICONOS: Record<string, typeof FileText> = { pdf: FileText, xlsx: FileSpreadsheet, csv: FileSpreadsheet, json: FileJson, parquet: Download };
const DESCRIPCION: Record<string, string> = {
  semanal: "Parte de la semana, cuenta, presupuesto de riesgo, decisiones, vetos y próximos pasos.",
  mensual: "Lo del semanal más desempeño por hipótesis, costes y avance del roadmap.",
  ficha: "Pre-registro, gate completo con IC, curva de capital y contador de intentos.",
  contador: "Cada operación en USD y MXN al FIX de Banxico (o «por completar»).",
  auditoria: "Registro de decisiones con hashes encadenados verificables.",
  datos: "Las operaciones visibles en la app.",
};

export function Reportes() {
  const client = useQueryClient();
  const { data, error, isLoading } = useQuery({ queryKey: ["reportes"], queryFn: () => api.get<ReportesData>("/api/reportes") });
  const [hipotesis, setHipotesis] = useState("H2-v1");
  if (isLoading) return <Loading />;
  if (error || !data) return <ErrorState error={error} />;
  const byKind = new Map<string, ReportesData["reportes"]>();
  for (const report of data.reportes) byKind.set(report.tipo, [...(byKind.get(report.tipo) ?? []), report]);
  return (
    <>
      <PageHeader title="Reportes" intro="Todos llevan fecha UTC, commit, versión del pre-registro y de los límites, origen de los datos y la marca DEMO si aplica." origen={data.origen} />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {[...byKind.entries()].map(([kind, formats]) => (
          <Card key={kind} title={formats[0]?.nombre} subtitle={DESCRIPCION[kind]} testId={`reporte-${kind}`}>
            {kind === "ficha" && (
              <label className="mb-2 block text-sm">
                <span className="mr-2">Hipótesis</span>
                <select value={hipotesis} onChange={(e) => setHipotesis(e.target.value)} className="rounded-lg border border-line bg-surface px-2 py-1" aria-label="Hipótesis de la ficha">
                  {["H1-v1", "H2-v1", "H4-H1-v1", "H4-H2-v1"].map((h) => (
                    <option key={h}>{h}</option>
                  ))}
                </select>
              </label>
            )}
            <div className="flex flex-wrap gap-2">
              {formats.map((f) => {
                const Icon = ICONOS[f.formato] ?? Download;
                return (
                  <a
                    key={f.formato}
                    href={`/api/reportes/${f.tipo}/${f.formato}?hipotesis=${hipotesis}`}
                    download
                    onClick={() => window.setTimeout(() => void client.invalidateQueries({ queryKey: ["reportes"] }), 1500)}
                    className="inline-flex items-center gap-2 rounded-lg border border-line px-3 py-2 text-sm font-semibold hover:bg-surface-2"
                  >
                    <Icon aria-hidden size={16} /> {f.formato.toUpperCase()}
                  </a>
                );
              })}
            </div>
          </Card>
        ))}
      </div>
      <Card title="Historial" className="mt-4">
        {data.historial.length === 0 ? (
          <EmptyState>Todavía no has generado reportes. Empieza por la ficha de una estrategia.</EmptyState>
        ) : (
          <Table
            caption="Reportes generados"
            head={["Fecha", "Archivo", "DEMO", "SHA-256"]}
            rows={data.historial.map((h) => [h.fecha_utc.replace("T", " ").replace("Z", " UTC"), h.archivo, h.demo ? "sí" : "no", <code key="s" className="font-mono text-xs">{h.sha256.slice(0, 16)}…</code>])}
          />
        )}
      </Card>
    </>
  );
}

export function Ajustes() {
  const { theme, setTheme, explain, setExplain, setWelcomed } = usePrefs();
  const limits = useQuery({ queryKey: ["limites"], queryFn: () => api.get<Limites>("/api/riesgo/limites") });
  return (
    <>
      <PageHeader title="Ajustes" intro="Preferencias de la app. Los límites de riesgo se ven, pero no se editan aquí." />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Apariencia y ayuda">
          <div className="space-y-4">
            <Switch checked={theme === "dark"} onChange={(on) => setTheme(on ? "dark" : "light")} label="Tema oscuro" />
            <Switch checked={explain} onChange={setExplain} label="Modo explicativo" />
            <Button variant="ghost" onClick={() => setWelcomed(false)}>
              Ver otra vez la bienvenida
            </Button>
          </div>
        </Card>
        {IN_ANDROID_APP && (
          <Card title="App Android" subtitle="Estás viendo el Centro de Mando dentro de la app." testId="ajustes-app">
            <a
              href="brujula://ajustes"
              className="inline-flex items-center gap-2 rounded-lg border border-line px-3 py-2 text-sm font-medium text-accent hover:bg-surface-2"
            >
              <Settings aria-hidden size={16} /> Servidor, bloqueo y privacidad
            </a>
          </Card>
        )}
        <Card title="Notificaciones" subtitle="Llegan con la F6 (alertas por Telegram o la app Android, sin datos sensibles).">
          <EmptyState>Aún no hay notificaciones que configurar.</EmptyState>
        </Card>
        <Card title="Límites de riesgo (solo lectura)" className="lg:col-span-2">
          {limits.data ? (
            <>
              <ul className="grid gap-2 sm:grid-cols-2">
                {limits.data.vigentes.map((l) => (
                  <li key={l.nombre} className={cx("flex justify-between rounded-lg border border-line px-3 py-2 text-sm")}>
                    <span>{l.nombre}</span>
                    <span className="tabular font-semibold">{l.unidad === "fracción" ? pct(Number(l.valor)) : `${l.valor}x`}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-sm text-ink-muted">
                {limits.data.aviso} Ver <Link to="/proyecto" className="text-accent underline">ADR-007 y ADR-013</Link>.
              </p>
            </>
          ) : (
            <Loading />
          )}
        </Card>
      </div>
    </>
  );
}
