// Glosario y bienvenida guiada (diálogos accesibles de Radix).
import * as Dialog from "@radix-ui/react-dialog";
import { useQuery } from "@tanstack/react-query";
import { BookOpen, X } from "lucide-react";
import { useState, type ReactNode } from "react";
import { api, type Glosario } from "../lib/api";
import { usePrefs } from "../lib/prefs";
import { BrujulaAvatar } from "./Brujula";
import { Button } from "./ui";

function Shell({
  open,
  onOpenChange,
  title,
  description,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[85dvh] w-[min(36rem,calc(100vw-2rem))] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border border-line bg-surface p-5 text-ink shadow-card">
          <div className="mb-3 flex items-start justify-between gap-3">
            <div>
              <Dialog.Title className="text-lg font-semibold">{title}</Dialog.Title>
              <Dialog.Description className="text-sm text-ink-muted">{description}</Dialog.Description>
            </div>
            <Dialog.Close className="rounded-lg p-1 text-ink-muted hover:bg-surface-2" aria-label="Cerrar">
              <X aria-hidden size={18} />
            </Dialog.Close>
          </div>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function GlossaryButton() {
  const [open, setOpen] = useState(false);
  const { data } = useQuery({ queryKey: ["glosario"], queryFn: () => api.get<Glosario>("/api/glosario"), enabled: open });
  return (
    <>
      <Button variant="ghost" onClick={() => setOpen(true)} aria-label="Abrir el glosario">
        <BookOpen aria-hidden size={16} />
        <span className="hidden sm:inline">Glosario</span>
      </Button>
      <Shell open={open} onOpenChange={setOpen} title="Glosario" description="Las palabras que verás en la app, en una frase.">
        <dl className="space-y-3">
          {Object.entries(data?.terminos ?? {}).map(([term, meaning]) => (
            <div key={term}>
              <dt className="font-semibold text-accent">{term}</dt>
              <dd className="text-sm text-ink">{meaning}</dd>
            </div>
          ))}
        </dl>
      </Shell>
    </>
  );
}

const STEPS: { title: string; body: string }[] = [
  {
    title: "Hola, soy Brújula",
    body: "Te acompaño en el Centro de Mando. Aquí ves cómo va el sistema, qué ha aprendido y qué falta. Todo lo calcula el código; yo solo te lo cuento claro.",
  },
  {
    title: "Primero, la seguridad",
    body: "Desde aquí no se puede operar ni mover dinero. LIVE_TRADING está apagado y solo tú puedes encenderlo, fuera de la app, con TOTP y un commit firmado.",
  },
  {
    title: "Honestidad visual",
    body: "Lo que es de demostración lleva franjas y la etiqueta DATOS DE DEMOSTRACIÓN. Los resultados son netos de costes y siempre con su rango de incertidumbre.",
  },
  {
    title: "El laboratorio",
    body: "Cada estrategia pasa un examen (el gate de la F4) antes de acercarse al dinero. Si no lo pasa, no avanza. Hoy ninguna lo pasa, y eso también es información valiosa.",
  },
  {
    title: "Modo explicativo",
    body: "Si activas el modo explicativo (arriba a la derecha), cada métrica te dice qué significa. El glosario tiene el resto.",
  },
];

export function Onboarding() {
  const { welcomed, setWelcomed } = usePrefs();
  const [step, setStep] = useState(0);
  const current = STEPS[step] ?? STEPS[0]!;
  const last = step === STEPS.length - 1;
  return (
    <Shell
      open={!welcomed}
      onOpenChange={(open) => !open && setWelcomed(true)}
      title={current.title}
      description={`Bienvenida, paso ${step + 1} de ${STEPS.length}`}
    >
      <div className="flex items-start gap-3">
        <BrujulaAvatar size={56} />
        <p className="text-sm leading-relaxed">{current.body}</p>
      </div>
      <div className="mt-5 flex items-center justify-between">
        <div className="flex gap-1" aria-hidden>
          {STEPS.map((_, i) => (
            <span key={i} className={`h-1.5 w-6 rounded-full ${i <= step ? "bg-accent" : "bg-line"}`} />
          ))}
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={() => setWelcomed(true)}>
            Saltar
          </Button>
          <Button onClick={() => (last ? setWelcomed(true) : setStep(step + 1))}>{last ? "Empezar" : "Siguiente"}</Button>
        </div>
      </div>
    </Shell>
  );
}
