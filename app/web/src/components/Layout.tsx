import { useQuery } from "@tanstack/react-query";
import {
  BookMarked,
  CandlestickChart,
  ClipboardList,
  FileDown,
  FlaskConical,
  Gauge,
  Home,
  Map,
  Moon,
  Palette,
  Power,
  Settings,
  ShieldCheck,
  Sun,
} from "lucide-react";
import { NavLink, Outlet } from "react-router";
import { api, type Estado } from "../lib/api";
import { usePrefs } from "../lib/prefs";
import { BrujulaAvatar } from "./Brujula";
import { GlossaryButton, Onboarding } from "./Dialogs";
import { Switch, cx } from "./ui";

export const NAV = [
  { to: "/", label: "Hoy", icon: Home },
  { to: "/mercado", label: "Mercado", icon: CandlestickChart },
  { to: "/laboratorio", label: "Laboratorio", icon: FlaskConical },
  { to: "/decisiones", label: "Decisiones", icon: ClipboardList },
  { to: "/riesgo", label: "Riesgo", icon: ShieldCheck },
  { to: "/diario", label: "Diario", icon: BookMarked },
  { to: "/proyecto", label: "Proyecto", icon: Map },
  { to: "/reportes", label: "Reportes", icon: FileDown },
  { to: "/ajustes", label: "Ajustes", icon: Settings },
] as const;

function LiveTradingPill({ estado }: { estado?: Estado }) {
  const off = estado ? !estado.live_trading : true;
  return (
    <span
      data-testid="live-trading"
      className={cx(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold",
        off ? "border-line bg-surface-2 text-ink" : "border-loss bg-loss text-white",
      )}
    >
      <Power aria-hidden size={13} />
      LIVE_TRADING {off ? "apagado" : "ENCENDIDO"}
    </span>
  );
}

export function Layout() {
  const { theme, setTheme, explain, setExplain } = usePrefs();
  const { data: estado } = useQuery({ queryKey: ["estado"], queryFn: () => api.get<Estado>("/api/estado") });

  const links = (compact: boolean) =>
    NAV.map(({ to, label, icon: Icon }) => (
      <NavLink
        key={to}
        to={to}
        end={to === "/"}
        className={({ isActive }) =>
          cx(
            "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition",
            compact && "shrink-0",
            isActive ? "bg-accent-soft text-accent" : "text-ink-muted hover:bg-surface-2 hover:text-ink",
          )
        }
      >
        <Icon aria-hidden size={17} />
        {label}
      </NavLink>
    ));

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[15rem_1fr]">
      <a href="#contenido" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-surface focus:p-2">
        Saltar al contenido
      </a>
      <aside className="hidden border-r border-line bg-surface lg:block">
        <div className="sticky top-0 flex h-dvh flex-col px-3 py-4">
          <div className="mb-6 flex items-center gap-2 px-2">
            <BrujulaAvatar size={34} />
            <div>
              <div className="font-display text-sm font-bold leading-tight">Centro de Mando</div>
              <div className="text-xs text-ink-muted">con Brújula</div>
            </div>
          </div>
          <nav aria-label="Secciones" className="flex flex-1 flex-col gap-1">
            {links(false)}
          </nav>
          <div className="space-y-2 border-t border-line px-2 pt-3 text-xs text-ink-muted">
            <LiveTradingPill estado={estado} />
            <NavLink to="/estilo" className="flex items-center gap-1 hover:text-accent">
              <Palette aria-hidden size={13} /> Sistema de diseño
            </NavLink>
            <p>Gráficas de velas: TradingView Lightweight Charts™ (Apache-2.0).</p>
          </div>
        </div>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-30 border-b border-line bg-canvas/90 backdrop-blur">
          <div className="flex items-center justify-between gap-2 px-4 py-2.5 sm:px-6">
            <div className="flex min-w-0 items-center gap-2">
              <span className="lg:hidden">
                <BrujulaAvatar size={30} />
              </span>
              <div className="min-w-0">
                <div className="hidden truncate text-xs text-ink-muted sm:block" data-testid="fase">
                  <Gauge aria-hidden size={12} className="mr-1 inline" />
                  {estado?.fase_actual ?? "Cargando estado…"}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <LiveTradingPill estado={estado} />
              <Switch checked={explain} onChange={setExplain} label="Explicar" compact />
              <GlossaryButton />
              <button
                type="button"
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                className="rounded-lg border border-line p-2 text-ink hover:bg-surface-2"
                aria-label={theme === "dark" ? "Cambiar a tema claro" : "Cambiar a tema oscuro"}
              >
                {theme === "dark" ? <Sun aria-hidden size={16} /> : <Moon aria-hidden size={16} />}
              </button>
            </div>
          </div>
          <nav aria-label="Secciones (móvil)" className="flex gap-1 overflow-x-auto px-3 pb-2 lg:hidden">
            {links(true)}
          </nav>
        </header>
        <main id="contenido" className="mx-auto max-w-7xl px-4 py-5 sm:px-6 sm:py-7">
          <Outlet />
        </main>
        <footer className="px-6 pb-6 text-xs text-ink-muted">
          No es asesoría financiera, legal ni fiscal. La rentabilidad es una hipótesis que el sistema tiene que demostrar.
        </footer>
      </div>
      <Onboarding />
    </div>
  );
}
