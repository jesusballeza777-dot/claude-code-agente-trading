import { useQuery } from "@tanstack/react-query";
import { Calculator, ShieldAlert, ShieldCheck } from "lucide-react";
import { useState, type FormEvent } from "react";
import { BrujulaSays } from "../components/Brujula";
import { Badge, Button, Card, ErrorState, ExplainLine, Loading, OrigenBadge, PageHeader, Stat, Table } from "../components/ui";
import { api, type Calculo, type Limites, type VetoContado } from "../lib/api";
import { num, pct, usd } from "../lib/format";

interface Form {
  simbolo: string;
  lado: "LONG" | "SHORT";
  entrada: string;
  stop: string;
  apalancamiento: string;
  capital: string;
  mercado: "PERPETUAL" | "SPOT";
}

const INICIAL: Form = { simbolo: "BTCUSDT", lado: "LONG", entrada: "60000", stop: "58800", apalancamiento: "3", capital: "1500", mercado: "PERPETUAL" };

function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium">{label}</span>
      {children}
      {hint && <span className="mt-0.5 block text-xs text-ink-muted">{hint}</span>}
    </label>
  );
}

const input = "w-full rounded-lg border border-line bg-surface px-3 py-2 tabular";

function Calculadora() {
  const [form, setForm] = useState<Form>(INICIAL);
  const [query, setQuery] = useState<Form>(INICIAL);
  const params = new URLSearchParams({ ...query });
  const { data, error, isFetching } = useQuery({
    queryKey: ["calculo", params.toString()],
    queryFn: () => api.get<Calculo>(`/api/riesgo/calculadora?${params.toString()}`),
  });
  const set = (key: keyof Form) => (e: { target: { value: string } }) => setForm({ ...form, [key]: e.target.value });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    setQuery(form);
  };

  return (
    <Card
      title={
        <span className="inline-flex items-center gap-2">
          <Calculator aria-hidden size={18} /> Calculadora con el motor real
        </span>
      }
      subtitle="Mismo código que vetaría una operación de verdad. No envía nada a ningún exchange."
      testId="calculadora"
    >
      <div className="grid gap-5 lg:grid-cols-[22rem_1fr]">
        <form onSubmit={submit} className="grid grid-cols-2 gap-3" aria-label="Datos de la operación">
          <Field label="Activo">
            <input className={input} value={form.simbolo} onChange={set("simbolo")} pattern="[A-Z0-9]{2,20}USDT" name="simbolo" />
          </Field>
          <Field label="Mercado">
            <select className={input} value={form.mercado} onChange={set("mercado")} name="mercado">
              <option value="PERPETUAL">Perpetuo</option>
              <option value="SPOT">Spot</option>
            </select>
          </Field>
          <Field label="Dirección">
            <select className={input} value={form.lado} onChange={set("lado")} name="lado">
              <option value="LONG">Largo</option>
              <option value="SHORT">Corto</option>
            </select>
          </Field>
          <Field label="Apalancamiento del exchange" hint="Fija la liquidación, no el riesgo">
            <input className={input} value={form.apalancamiento} onChange={set("apalancamiento")} inputMode="decimal" name="apalancamiento" />
          </Field>
          <Field label="Entrada (USD)">
            <input className={input} value={form.entrada} onChange={set("entrada")} inputMode="decimal" name="entrada" />
          </Field>
          <Field label="Stop (USD)">
            <input className={input} value={form.stop} onChange={set("stop")} inputMode="decimal" name="stop" />
          </Field>
          <Field label="Capital (USD)">
            <input className={input} value={form.capital} onChange={set("capital")} inputMode="decimal" name="capital" />
          </Field>
          <div className="flex items-end">
            <Button type="submit" className="w-full" disabled={isFetching}>
              Calcular
            </Button>
          </div>
        </form>
        <div aria-live="polite">
          {error ? (
            <ErrorState error={error} />
          ) : !data ? (
            <Loading />
          ) : (
            <div className="space-y-4" data-testid="resultado-calculo">
              <div className="flex items-center gap-2">
                {data.aprobada ? (
                  <Badge tone="gain">
                    <ShieldCheck aria-hidden size={14} /> El motor la aprobaría
                  </Badge>
                ) : (
                  <Badge tone="loss">
                    <ShieldAlert aria-hidden size={14} /> El motor la vetaría
                  </Badge>
                )}
                <OrigenBadge origen={data.origen} />
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <Stat label="Tamaño" value={num(data.cantidad, 6)} hint={`${form.simbolo.replace("USDT", "")}`} />
                <Stat label="Nocional" value={usd(data.nocional)} />
                <Stat label="Riesgo con costes" value={usd(data.riesgo_usd)} hint={`Presupuesto: ${usd(data.presupuesto_usd)}`} explain="Lo que perderías si salta el stop, contando comisión y slippage de entrada y salida." />
                <Stat label="Apalancamiento efectivo" value={data.apalancamiento_efectivo ? `${num(data.apalancamiento_efectivo, 2)}x` : "—"} explain="Tamaño de las posiciones entre el capital. El límite es 2x." />
                <Stat label="Liquidación estimada" value={usd(data.precio_liquidacion)} explain="Debe quedar al menos 3 veces más lejos que el stop." />
                <Stat label="Costes supuestos" value={`${pct(Number(data.costes.comision), 2)} + ${pct(Number(data.costes.slippage), 2)}`} hint="comisión + slippage por lado" />
              </div>
              {data.vetos.length > 0 ? (
                <ul className="space-y-2" aria-label="Vetos">
                  {data.vetos.map((v) => (
                    <li key={v.code} className="rounded-xl border border-loss/40 bg-surface-2 p-3 text-sm">
                      <div className="flex items-center gap-2 font-semibold text-loss">
                        <ShieldAlert aria-hidden size={15} /> {v.title}
                        <code className="font-mono text-[11px] text-ink-muted">{v.code}</code>
                      </div>
                      <p className="mt-1 text-ink">{v.message}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <BrujulaSays>Esta operación respeta todos los límites. Aun así, aprobarla no significa que vaya a ganar: solo que, si pierde, pierde dentro de lo acordado.</BrujulaSays>
              )}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

export function Riesgo() {
  const limits = useQuery({ queryKey: ["limites"], queryFn: () => api.get<Limites>("/api/riesgo/limites") });
  const vetos = useQuery({
    queryKey: ["vetos"],
    queryFn: () => api.get<{ origen: "backtest"; nota: string; vetos: VetoContado[] }>("/api/riesgo/vetos"),
  });
  return (
    <>
      <PageHeader title="Riesgo" intro="El motor de riesgo tiene veto absoluto y no depende de Claude. Sus límites solo cambian con un ADR que apruebas tú." />
      <Calculadora />
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="Límites vigentes" subtitle={limits.data?.aviso} action={limits.data && <OrigenBadge origen={limits.data.origen} />}>
          {limits.isLoading ? (
            <Loading />
          ) : limits.data ? (
            <>
              <Table
                caption="Límites vigentes y techos del plan"
                head={["Límite", "Vigente", "Techo del plan", "ADR"]}
                rows={limits.data.vigentes.map((l) => [
                  l.nombre,
                  l.unidad === "fracción" ? pct(Number(l.valor), 1) : `${l.valor}x`,
                  l.unidad === "fracción" ? pct(Number(l.techo_plan), 1) : `${l.techo_plan}x`,
                  <span key="adr" className="whitespace-nowrap">{l.adr}</span>,
                ])}
              />
              <p className="mt-3 text-sm text-ink-muted">
                BTC y ETH cuentan como una sola exposición: {limits.data.grupos_correlacionados.map((g) => g.join(" + ")).join("; ")}.
              </p>
              <ExplainLine text="Las reglas del ADR-013 (exposición ajustada por beta, alts, depeg, eventos macro, disyuntores y funding) están propuestas: activas en simulación hasta que las apruebes." />
            </>
          ) : (
            <ErrorState error={limits.error} />
          )}
        </Card>
        <Card title="Historial de vetos" subtitle={vetos.data?.nota} action={vetos.data && <OrigenBadge origen={vetos.data.origen} />}>
          {vetos.data ? (
            <Table
              caption="Vetos de las corridas principales de la F4"
              head={["Veto", "Qué significa", "Veces"]}
              rows={vetos.data.vetos.map((v) => [v.titulo, v.explicacion, v.veces])}
            />
          ) : (
            <Loading />
          )}
        </Card>
      </div>
    </>
  );
}
