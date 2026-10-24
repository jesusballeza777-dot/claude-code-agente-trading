// Pulso del sistema: qué piezas trabajan ahora, cuáles aún no existen y qué ha pasado.
// Sondea la API cada pocos segundos; si se pierde la conexión lo dice, no inventa nada.
import { useQuery } from "@tanstack/react-query";
import { CircleCheck, CircleMinus, CirclePause, Clock, FileText, NotebookPen, Power, WifiOff } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Card, ErrorState, Loading, OrigenBadge, PageHeader, cx } from "../components/ui";
import { api, type EnVivo as EnVivoData } from "../lib/api";
import { fechaHora } from "../lib/format";

const POLL_MS = 5_000;

function ago(since: number, now: number): string {
  const seconds = Math.max(0, Math.round((now - since) / 1000));
  if (seconds < 5) return "ahora mismo";
  if (seconds < 60) return `hace ${seconds} s`;
  return `hace ${Math.floor(seconds / 60)} min`;
}

function EstadoMotor({ estado }: { estado: string }) {
  const [Icon, tone] =
    estado === "activo"
      ? [CircleCheck, "text-gain"]
      : estado === "apagada"
        ? [Power, "text-ink-muted"]
        : estado === "sin datos"
          ? [Clock, "text-warn"]
          : estado === "no conectado"
            ? [CirclePause, "text-ink-muted"]
            : [CircleMinus, "text-neutral"];
  return (
    <span className={cx("inline-flex items-center gap-1 text-sm font-medium", tone)}>
      <Icon aria-hidden size={16} /> {estado}
    </span>
  );
}

export function EnVivo() {
  const { data, error, isLoading, dataUpdatedAt, isFetching } = useQuery({
    queryKey: ["en-vivo"],
    queryFn: () => api.get<EnVivoData>("/api/en-vivo"),
    refetchInterval: POLL_MS,
  });
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  if (isLoading) return <Loading />;
  if (!data) return <ErrorState error={error} />;
  const offline = Boolean(error);
  const active = data.motores.filter((m) => m.estado === "activo").length;

  return (
    <>
      <PageHeader
        title="En vivo"
        intro="El pulso del sistema: qué piezas trabajan ahora, cuáles todavía no existen y qué ha pasado. Se actualiza solo."
        origen={data.origen}
      />

      <div
        data-testid="pulso"
        className={cx(
          "mb-4 flex items-center justify-between gap-3 rounded-card border p-4 shadow-card",
          offline ? "border-loss/50 bg-surface" : "border-accent/40 bg-accent-soft",
        )}
      >
        <div className="flex items-center gap-3">
          {offline ? (
            <WifiOff aria-hidden className="text-loss" />
          ) : (
            <span className="relative flex h-3.5 w-3.5" aria-hidden>
              <span className="pulso absolute inline-flex h-full w-full rounded-full bg-accent opacity-60" />
              <span className="relative inline-flex h-3.5 w-3.5 rounded-full bg-accent" />
            </span>
          )}
          <div>
            <div className="font-display text-lg font-semibold leading-tight">
              {offline ? "Sin conexión con el servidor" : `${active} de ${data.motores.length} piezas activas`}
            </div>
            <div className="text-xs text-ink-muted">
              {offline ? "Mostrando lo último recibido; reintento cada 5 s." : "Servidor respondiendo"} · actualizado{" "}
              {ago(dataUpdatedAt, now)}
              {isFetching && !offline ? " · actualizando…" : ""}
            </div>
          </div>
        </div>
        <Badge tone={data.live_trading ? "loss" : "neutral"}>
          <Power aria-hidden size={12} /> LIVE_TRADING {data.live_trading ? "ENCENDIDO" : "apagado"}
        </Badge>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Piezas del sistema" subtitle="Solo lo que existe aparece como activo." className="lg:col-span-2" testId="motores">
          <ul className="divide-y divide-line">
            {data.motores.map((m) => (
              <li key={m.id} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 py-2.5">
                <div>
                  <div className="text-sm font-semibold">{m.nombre}</div>
                  <div className="text-xs text-ink-muted">{m.detalle}</div>
                </div>
                <EstadoMotor estado={m.estado} />
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Actividad" subtitle={`${data.total_eventos} eventos registrados`} testId="actividad">
          {data.eventos.length === 0 ? (
            <p className="text-sm text-ink-muted">
              Aún no hay actividad. Aquí aparecerán tus notas, los reportes que generes y, desde la F7, cada decisión de la sombra.
            </p>
          ) : (
            <ol className="space-y-3">
              {data.eventos.slice(0, 8).map((e) => {
                const Icon = e.tipo === "nota" ? NotebookPen : FileText;
                return (
                  <li key={`${e.t}-${e.texto}`} className="flex gap-2.5">
                    <Icon aria-hidden size={16} className="mt-0.5 shrink-0 text-accent" />
                    <div>
                      <div className="text-sm">{e.texto}</div>
                      <div className="text-xs text-ink-muted">{fechaHora(e.t)}</div>
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
        </Card>

        <Card
          title="Decisiones del analista"
          subtitle={data.decisiones.aviso}
          action={<OrigenBadge origen={data.decisiones.origen} />}
          className="lg:col-span-3"
          demo
          testId="decisiones-en-vivo"
        >
          <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {data.decisiones.items.map((d) => (
              <li key={d.t} className="rounded-xl border border-line bg-surface/80 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="cifra text-sm font-semibold">{d.accion}</span>
                  <span className="text-xs text-ink-muted">{fechaHora(d.t)}</span>
                </div>
                <p className="mt-1 text-xs text-ink-muted">{d.motivo}</p>
                {d.veto && <Badge tone="warn">Veto: {d.veto}</Badge>}
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}
