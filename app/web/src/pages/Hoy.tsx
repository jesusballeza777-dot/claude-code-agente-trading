import { useQuery } from "@tanstack/react-query";
import { Activity, Database, Lock, Power, ShieldCheck } from "lucide-react";
import { Link } from "react-router";
import { BrujulaSays } from "../components/Brujula";
import { BudgetBar, DrawdownGauge, EquityChart } from "../components/charts/Charts";
import {
  AnimatedNumber,
  Card,
  EmptyState,
  ErrorState,
  ExplainLine,
  Loading,
  OrigenBadge,
  PageHeader,
  Stat,
} from "../components/ui";
import { api, type Hoy as HoyData } from "../lib/api";
import { pct, usd } from "../lib/format";

function Light({ icon: Icon, label, value, ok }: { icon: typeof Power; label: string; value: string; ok: boolean }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-line bg-surface-2/60 p-3">
      <Icon aria-hidden size={18} className={ok ? "mt-0.5 text-gain" : "mt-0.5 text-warn"} />
      <div>
        <div className="text-xs uppercase tracking-wide text-ink-muted">{label}</div>
        <div className="text-sm font-medium">{value}</div>
      </div>
    </div>
  );
}

export function Hoy() {
  const { data, error, isLoading } = useQuery({ queryKey: ["hoy"], queryFn: () => api.get<HoyData>("/api/hoy") });
  if (isLoading) return <Loading />;
  if (error || !data) return <ErrorState error={error} />;
  const { estado, cuenta } = data;

  return (
    <>
      <PageHeader title="Hoy" intro="¿Estoy a salvo? ¿Qué ha decidido el sistema? ¿Está aprendiendo de verdad? Aquí, en segundos." />
      <div className="grid gap-4 lg:grid-cols-3 lg:items-start">
        <Card title="Semáforo del sistema" className="lg:col-span-2" testId="semaforo">
          <div className="grid gap-2 sm:grid-cols-2">
            <Light icon={Power} label="Ejecución real" value="LIVE_TRADING apagado" ok={!estado.live_trading} />
            <Light icon={Activity} label="Fase" value={estado.fase_actual} ok />
            <Light
              icon={Database}
              label="Datos"
              value={
                estado.datos.disponible
                  ? `2020-2024 al ${pct(estado.datos.completitud ?? null, 2)} · última vela ${estado.datos.ultima_vela}`
                  : "Sin datos descargados todavía"
              }
              ok={estado.datos.disponible}
            />
            <Light icon={ShieldCheck} label="Motor de riesgo" value={`${estado.motor_de_riesgo.estado} · ${estado.motor_de_riesgo.limites}`} ok />
            <Light icon={Lock} label="Holdout" value={estado.holdout.sellado ? `Sellado desde ${estado.holdout.desde}` : "Abierto con autorización"} ok={estado.holdout.sellado} />
            <Light
              icon={Activity}
              label="Intentos registrados"
              value={`${estado.intentos.principales} principales · ${estado.intentos.total} corridas en total`}
              ok
            />
          </div>
        </Card>
        <Card title="Parte del día" testId="parte-del-dia">
          <BrujulaSays validated={data.parte_del_dia.validado}>{data.parte_del_dia.texto}</BrujulaSays>
        </Card>

        <Card
          title="Capital y drawdown"
          subtitle="La simulación en sombra empieza en la F7; esto es una muestra."
          action={<OrigenBadge origen={cuenta.origen} />}
          demo={cuenta.origen === "demo"}
          className="lg:col-span-2"
        >
          <div className="grid gap-3 sm:grid-cols-3">
            <Stat label="Capital" value={<AnimatedNumber value={Number(cuenta.capital)} format={(n) => usd(n)} />} />
            <Stat label="Máximo" value={usd(cuenta.maximo)} />
            <Stat
              label="Drawdown"
              value={pct(cuenta.drawdown, 2)}
              explain="Cuánto ha caído el capital desde su máximo. Al 15% se detienen las entradas; al 20% se cierra todo."
            />
          </div>
          <div className="mt-4">
            <DrawdownGauge value={cuenta.drawdown} halt={cuenta.umbrales.parada} hard={cuenta.umbrales.corte_duro} />
          </div>
          <div className="mt-3">
            <EquityChart data={cuenta.curva} height={180} />
          </div>
        </Card>

        <Card title="Presupuesto de pérdida" action={<OrigenBadge origen={cuenta.origen} />} demo={cuenta.origen === "demo"}>
          <div className="space-y-4">
            <BudgetBar label="Pérdida diaria" used={cuenta.presupuesto.diario.usado} limit={cuenta.presupuesto.diario.limite} />
            <BudgetBar label="Pérdida semanal" used={cuenta.presupuesto.semanal.usado} limit={cuenta.presupuesto.semanal.limite} />
            <p className="text-sm text-ink-muted">{cuenta.presupuesto.diario.texto}</p>
          </div>
          <ExplainLine text="Es lo que podrías perder en el día o la semana si saltaran todos los stops abiertos. El motor no deja abrir nada que lo supere." />
        </Card>

        <Card title="Posiciones abiertas" action={<OrigenBadge origen={data.posiciones.origen} />}>
          <EmptyState>
            {data.posiciones.vacio}{" "}
            <Link to="/riesgo" className="font-semibold text-accent underline-offset-2 hover:underline">
              Ir a la calculadora
            </Link>
          </EmptyState>
        </Card>
        <Card title="Próximos eventos macro">
          <EmptyState>{data.eventos_macro.vacio}</EmptyState>
        </Card>
        <Card title="Tus pendientes" subtitle="En orden. Ninguno se puede hacer desde la app." testId="pendientes">
          <ol className="list-decimal space-y-2 pl-5 text-sm">
            {estado.pendientes_propietario.map((p) => (
              <li key={p.tarea}>
                {p.tarea} <span className="text-xs text-ink-muted">({p.documento})</span>
              </li>
            ))}
          </ol>
        </Card>
      </div>
    </>
  );
}
