import * as Dialog from "@radix-ui/react-dialog";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  BookMarked,
  CandlestickChart,
  ClipboardList,
  FileDown,
  FlaskConical,
  Gauge,
  Home,
  Map,
  Menu,
  Moon,
  Palette,
  Power,
  Settings,
  ShieldCheck,
  Sun,
  X,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router";
import { api, type Estado } from "../lib/api";
import { IN_ANDROID_APP } from "../lib/env";
import { usePrefs } from "../lib/prefs";
import { BrujulaAvatar } from "./Brujula";
import { GlossaryButton, Onboarding } from "./Dialogs";
import { Switch, cx } from "./ui";

export const NAV = [
  { to: "/", label: "Hoy", icon: Home },
  { to: "/en-vivo", label: "En vivo", icon: Activity },
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

/** Pestañas de la barra inferior del celular; el resto de páginas está en "Más". */
const TABS = [NAV[0], NAV[1], NAV[3], NAV[5]] as const;
const MORE = NAV.filter((n) => !TABS.some((t) => t.to === n.to));

function BottomBar() {
  const [open, setOpen] = useState(false);
  const item = "flex min-w-0 flex-1 flex-col items-center gap-0.5 rounded-xl px-1 py-1.5 text-[11px] font-medium transition";
  return (
    <nav
      aria-label="Secciones (móvil)"
      className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/95 px-2 pt-1 backdrop-blur lg:hidden"
      style={{ paddingBottom: "max(0.25rem, env(safe-area-inset-bottom))" }}
    >
      <div className="mx-auto flex max-w-lg items-stretch">
        {TABS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) => cx(item, isActive ? "bg-accent-soft text-accent" : "text-ink-muted")}
          >
            <Icon aria-hidden size={21} />
            {label}
          </NavLink>
        ))}
        <Dialog.Root open={open} onOpenChange={setOpen}>
          <Dialog.Trigger className={cx(item, "text-ink-muted")} aria-label="Más secciones">
            <Menu aria-hidden size={21} />
            Más
          </Dialog.Trigger>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" />
            <Dialog.Content
              className="fixed inset-x-0 bottom-0 z-50 rounded-t-3xl border-t border-line bg-surface p-4 text-ink shadow-card"
              style={{ paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}
            >
              <div className="mb-3 flex items-center justify-between">
                <Dialog.Title className="text-base font-semibold">Más secciones</Dialog.Title>
                <Dialog.Close className="rounded-lg p-1.5 text-ink-muted hover:bg-surface-2" aria-label="Cerrar">
                  <X aria-hidden size={18} />
                </Dialog.Close>
              </div>
              <Dialog.Description className="sr-only">Resto de páginas del Centro de Mando</Dialog.Description>
              <div className="grid grid-cols-3 gap-2">
                {[...MORE, { to: "/estilo", label: "Diseño", icon: Palette }].map(({ to, label, icon: Icon }) => (
                  <NavLink
                    key={to}
                    to={to}
                    onClick={() => setOpen(false)}
                    className={({ isActive }) =>
                      cx(
                        "flex flex-col items-center gap-1.5 rounded-2xl border border-line px-2 py-3 text-xs font-medium",
                        isActive ? "bg-accent-soft text-accent" : "bg-surface-2 text-ink",
                      )
                    }
                  >
                    <Icon aria-hidden size={22} />
                    {label}
                  </NavLink>
                ))}
              </div>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>
      </div>
    </nav>
  );
}

export function Layout() {
  const { theme, setTheme, explain, setExplain } = usePrefs();
  const { data: estado } = useQuery({ queryKey: ["estado"], queryFn: () => api.get<Estado>("/api/estado") });

  const links = () =>
    NAV.map(({ to, label, icon: Icon }) => (
      <NavLink
        key={to}
        to={to}
        end={to === "/"}
        className={({ isActive }) =>
          cx(
            "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition",
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
            {links()}
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
        </header>
        <main id="contenido" className={cx("mx-auto max-w-7xl px-4 pt-5 sm:px-6 sm:pt-7", IN_ANDROID_APP ? "pb-6" : "pb-28 lg:pb-7")}>
          <Outlet />
        </main>
        <footer className={cx("px-6 text-xs text-ink-muted", IN_ANDROID_APP ? "pb-6" : "pb-24 lg:pb-6")}>
          No es asesoría financiera, legal ni fiscal. La rentabilidad es una hipótesis que el sistema tiene que demostrar.
        </footer>
      </div>
      {!IN_ANDROID_APP && <BottomBar />}
      <Onboarding />
    </div>
  );
}
