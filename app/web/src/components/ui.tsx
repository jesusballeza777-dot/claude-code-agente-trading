// Componentes base del sistema de diseño (al estilo shadcn/ui, sobre Radix donde aporta
// accesibilidad: tooltips, diálogos, interruptores y pestañas).
import * as SwitchPrimitive from "@radix-ui/react-switch";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { AlertTriangle, CircleCheck, CircleMinus, CircleX, FlaskConical, HelpCircle, TrendingDown, TrendingUp } from "lucide-react";
import { motion } from "motion/react";
import { useEffect, useState, type ComponentProps, type ReactNode } from "react";
import type { Origen } from "../lib/api";
import { usePrefs } from "../lib/prefs";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

export function Card({
  title,
  subtitle,
  action,
  children,
  className,
  demo = false,
  testId,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  demo?: boolean;
  testId?: string;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      data-testid={testId}
      className={cx(
        "relative overflow-hidden rounded-card border border-line bg-surface p-4 shadow-card sm:p-5",
        demo && "franjas-demo marca-agua-demo",
        className,
      )}
    >
      {(title || action) && (
        <header className="mb-3 flex flex-wrap items-start justify-between gap-2">
          <div>
            {title && <h2 className="text-base font-semibold text-ink">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-sm text-ink-muted">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className="relative">{children}</div>
    </motion.section>
  );
}

const ORIGEN_ETIQUETA: Record<Origen, string> = {
  real: "Datos reales",
  backtest: "Backtest 2020-2024",
  demo: "DATOS DE DEMOSTRACIÓN",
};

export function OrigenBadge({ origen }: { origen: Origen }) {
  const Icon = origen === "demo" ? AlertTriangle : origen === "backtest" ? FlaskConical : CircleCheck;
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold",
        origen === "demo" && "border-demo bg-demo-soft text-demo",
        origen === "backtest" && "border-line bg-surface-2 text-ink-muted",
        origen === "real" && "border-accent/40 bg-accent-soft text-accent",
      )}
    >
      <Icon aria-hidden size={13} />
      {ORIGEN_ETIQUETA[origen]}
    </span>
  );
}

export function Badge({
  tone = "neutral",
  children,
}: {
  tone?: "gain" | "loss" | "warn" | "neutral" | "accent";
  children: ReactNode;
}) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
        tone === "gain" && "border-gain/40 text-gain",
        tone === "loss" && "border-loss/40 text-loss",
        tone === "warn" && "border-warn/40 text-warn",
        tone === "neutral" && "border-line text-ink-muted",
        tone === "accent" && "border-accent/40 text-accent",
      )}
    >
      {children}
    </span>
  );
}

/** Indicador de sí/no con icono, nunca solo color. */
export function Check({ ok, label }: { ok: boolean | null; label?: string }) {
  if (ok === null) {
    return (
      <span className="inline-flex items-center gap-1 text-neutral">
        <CircleMinus aria-hidden size={16} /> {label ?? "pendiente"}
      </span>
    );
  }
  return ok ? (
    <span className="inline-flex items-center gap-1 text-gain">
      <CircleCheck aria-hidden size={16} /> {label ?? "sí"}
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-loss">
      <CircleX aria-hidden size={16} /> {label ?? "no"}
    </span>
  );
}

export function SignedIcon({ value }: { value: number }) {
  if (value > 0) return <TrendingUp aria-label="positivo" size={16} className="text-gain" />;
  if (value < 0) return <TrendingDown aria-label="negativo" size={16} className="text-loss" />;
  return <CircleMinus aria-label="cero" size={16} className="text-neutral" />;
}

/** Número que se anima suavemente al cargar (respeta "reducir movimiento"). */
export function AnimatedNumber({ value, format }: { value: number; format: (n: number) => string }) {
  const [shown, setShown] = useState(value);
  useEffect(() => {
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce || !Number.isFinite(value)) {
      setShown(value);
      return;
    }
    const start = performance.now();
    const from = 0;
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min((now - start) / 600, 1);
      setShown(from + (value - from) * (1 - (1 - t) ** 3));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value]);
  return <>{format(shown)}</>;
}

export function Stat({
  label,
  value,
  hint,
  explain,
  tone,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  explain?: string;
  tone?: "gain" | "loss" | "neutral";
}) {
  return (
    <div className="rounded-xl border border-line bg-surface-2/60 p-3">
      <div className="flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-ink-muted">
        {label}
        {explain && <Explain text={explain} />}
      </div>
      <div
        className={cx(
          "cifra mt-1 text-2xl font-semibold",
          tone === "gain" && "text-gain",
          tone === "loss" && "text-loss",
        )}
      >
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-ink-muted">{hint}</div>}
    </div>
  );
}

/** "¿Qué significa esto?": icono con tooltip siempre; texto visible en modo explicativo. */
export function Explain({ text }: { text: string }) {
  const { explain } = usePrefs();
  return (
    <>
      <Tip content={text}>
        <button type="button" className="text-ink-muted hover:text-accent" aria-label={`¿Qué significa esto? ${text}`}>
          <HelpCircle aria-hidden size={14} />
        </button>
      </Tip>
      {explain && <span className="sr-only">{text}</span>}
    </>
  );
}

export function ExplainLine({ text }: { text: string }) {
  const { explain } = usePrefs();
  if (!explain) return null;
  return (
    <p className="mt-2 rounded-lg border border-accent/30 bg-accent-soft px-3 py-2 text-sm text-ink">
      <span className="font-semibold text-accent">¿Qué significa esto? </span>
      {text}
    </p>
  );
}

export function Tip({ content, children }: { content: ReactNode; children: ReactNode }) {
  return (
    <TooltipPrimitive.Root delayDuration={150}>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          sideOffset={6}
          className="z-50 max-w-xs rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink shadow-card"
        >
          {content}
          <TooltipPrimitive.Arrow className="fill-surface" />
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}

export function Button({ variant = "primary", className, ...props }: ComponentProps<"button"> & { variant?: "primary" | "ghost" }) {
  return (
    <button
      type="button"
      {...props}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition disabled:opacity-50",
        variant === "primary" && "bg-accent text-accent-ink hover:brightness-110",
        variant === "ghost" && "border border-line text-ink hover:bg-surface-2",
        className,
      )}
    />
  );
}

export function Switch({
  checked,
  onChange,
  label,
  compact = false,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  compact?: boolean;
}) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-2 text-sm">
      <SwitchPrimitive.Root
        checked={checked}
        onCheckedChange={onChange}
        aria-label={label}
        className="relative h-6 w-11 rounded-full border border-line bg-surface-2 transition data-[state=checked]:bg-accent"
      >
        <SwitchPrimitive.Thumb className="block h-5 w-5 translate-x-0.5 rounded-full bg-ink shadow transition data-[state=checked]:translate-x-[1.35rem] data-[state=checked]:bg-accent-ink" />
      </SwitchPrimitive.Root>
      <span className={compact ? "hidden sm:inline" : undefined}>{label}</span>
    </label>
  );
}

export const Tabs = TabsPrimitive.Root;
export function TabsList({ children, label }: { children: ReactNode; label: string }) {
  return (
    <TabsPrimitive.List aria-label={label} className="mb-3 flex flex-wrap gap-1 rounded-xl border border-line bg-surface-2 p-1">
      {children}
    </TabsPrimitive.List>
  );
}
export function TabsTrigger({ value, children }: { value: string; children: ReactNode }) {
  return (
    <TabsPrimitive.Trigger
      value={value}
      className="rounded-lg px-3 py-1.5 text-sm font-medium text-ink-muted data-[state=active]:bg-surface data-[state=active]:text-ink data-[state=active]:shadow"
    >
      {children}
    </TabsPrimitive.Trigger>
  );
}
export const TabsContent = TabsPrimitive.Content;

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cx("animate-pulse rounded-xl bg-surface-2", className)} />;
}

export function Loading({ label = "Cargando…" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <span className="sr-only">{label}</span>
      <Skeleton className="h-24" />
      <Skeleton className="h-40" />
    </div>
  );
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div role="alert" className="rounded-xl border border-loss/40 bg-surface p-4 text-sm text-loss">
      <AlertTriangle aria-hidden className="mr-2 inline" size={16} />
      No se pudo cargar: {message}
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <p className="rounded-xl border border-dashed border-line p-4 text-sm text-ink-muted">{children}</p>;
}

export function PageHeader({ title, intro, origen, children }: { title: string; intro: string; origen?: Origen; children?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold sm:text-3xl">{title}</h1>
        <p className="mt-1 max-w-3xl text-sm text-ink-muted">{intro}</p>
      </div>
      <div className="flex items-center gap-2">
        {origen && <OrigenBadge origen={origen} />}
        {children}
      </div>
    </div>
  );
}

export function Table({ head, rows, caption }: { head: ReactNode[]; rows: ReactNode[][]; caption?: string }) {
  return (
    <div className="overflow-x-auto" tabIndex={0} role="region" aria-label={caption ?? "Tabla desplazable"}>
      <table className="tabular w-full min-w-[32rem] text-left text-sm">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr className="border-b border-line text-xs uppercase tracking-wide text-ink-muted">
            {head.map((cell, i) => (
              <th key={i} scope="col" className="px-2 py-2 font-medium">
                {cell}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-line/60 last:border-0">
              {row.map((cell, j) => (
                <td key={j} className="px-2 py-2 align-top">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
