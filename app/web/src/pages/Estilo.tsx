// Página interna del sistema de diseño: paleta, tipografía y componentes.
import { BrujulaAvatar, BrujulaSays } from "../components/Brujula";
import { BudgetBar, DrawdownGauge } from "../components/charts/Charts";
import { Badge, Button, Card, Check, OrigenBadge, PageHeader, Stat } from "../components/ui";

const COLORES = [
  ["canvas", "Fondo"],
  ["surface", "Superficie"],
  ["surface-2", "Superficie 2"],
  ["line", "Línea"],
  ["ink", "Texto"],
  ["ink-muted", "Texto secundario"],
  ["accent", "Acento"],
  ["gain", "Ganancia"],
  ["loss", "Pérdida"],
  ["warn", "Alerta"],
  ["neutral", "Neutral"],
  ["demo", "Demo"],
] as const;

export function Estilo() {
  return (
    <>
      <PageHeader title="Sistema de diseño" intro="Tokens y componentes del Centro de Mando. Si algo no está aquí, no debería estar en la app." />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Paleta (tema actual)">
          <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {COLORES.map(([token, name]) => (
              <li key={token} className="flex items-center gap-2 text-sm">
                <span className="h-8 w-8 rounded-lg border border-line" style={{ background: `var(--${token})` }} />
                <span>
                  {name}
                  <code className="block font-mono text-[11px] text-ink-muted">--{token}</code>
                </span>
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Tipografía">
          <p className="font-display text-3xl font-bold">Space Grotesk · títulos</p>
          <p className="mt-2">Inter · texto de lectura cómoda en pantalla y en el celular.</p>
          <p className="cifra mt-2 text-2xl">1,234.56 · 0.516 R · 19.2%</p>
          <p className="mt-2 font-mono text-sm">JetBrains Mono · JSON y códigos</p>
        </Card>
        <Card title="Semántica: nunca solo color">
          <div className="flex flex-wrap gap-2">
            <Check ok label="cumple" />
            <Check ok={false} label="no cumple" />
            <Check ok={null} label="pendiente" />
            <Badge tone="gain">ganancia</Badge>
            <Badge tone="loss">pérdida</Badge>
            <Badge tone="warn">alerta</Badge>
            <OrigenBadge origen="real" />
            <OrigenBadge origen="backtest" />
            <OrigenBadge origen="demo" />
          </div>
        </Card>
        <Card title="Componentes">
          <div className="grid gap-3 sm:grid-cols-2">
            <Stat label="Esperanza neta" value="+0.52 R" tone="gain" hint="IC90% [+0.21, +0.85]" explain="Ejemplo de métrica con su explicación." />
            <div className="space-y-3">
              <Button>Acción principal</Button>
              <Button variant="ghost">Secundaria</Button>
            </div>
          </div>
          <div className="mt-4 space-y-3">
            <DrawdownGauge value={0.06} halt={0.15} hard={0.2} />
            <BudgetBar label="Presupuesto de ejemplo" used={0.008} limit={0.02} />
          </div>
        </Card>
        <Card title="Datos de demostración" demo>
          <p className="text-sm">Franjas diagonales y marca de agua: se distinguen sin depender del color.</p>
        </Card>
        <Card title="Brújula">
          <div className="mb-3 flex items-center gap-3">
            <BrujulaAvatar size={64} />
            <BrujulaAvatar size={40} />
            <BrujulaAvatar size={24} />
          </div>
          <BrujulaSays validated>Hoy no hubo señales que cumplan las reglas. No operar también es una decisión, y hoy fue la correcta.</BrujulaSays>
        </Card>
      </div>
    </>
  );
}
