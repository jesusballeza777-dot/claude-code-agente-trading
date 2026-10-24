// Brújula, el copiloto: avatar SVG original y globo de texto. Sus textos vienen del backend
// (plantillas deterministas); aquí solo se muestran.
import { ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { cx } from "./ui";

export function BrujulaAvatar({ size = 44, className }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label="Brújula, tu copiloto"
      className={cx("shrink-0", className)}
    >
      <defs>
        <linearGradient id="brujula-aro" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="var(--accent)" />
          <stop offset="1" stopColor="var(--demo)" />
        </linearGradient>
      </defs>
      <circle cx="32" cy="32" r="29" fill="var(--surface-2)" stroke="url(#brujula-aro)" strokeWidth="4" />
      {[0, 90, 180, 270].map((angle) => (
        <rect
          key={angle}
          x="31"
          y="6"
          width="2"
          height="6"
          rx="1"
          fill="var(--ink-muted)"
          transform={`rotate(${angle} 32 32)`}
        />
      ))}
      <path d="M32 13 L38.5 32 L32 51 L25.5 32 Z" fill="var(--accent)" />
      <path d="M32 32 L38.5 32 L32 51 Z" fill="var(--demo)" opacity="0.9" />
      <circle cx="32" cy="32" r="3.2" fill="var(--surface)" stroke="var(--ink)" strokeWidth="1.5" />
      <circle cx="26.5" cy="24" r="1.6" fill="var(--ink)" />
      <circle cx="37.5" cy="24" r="1.6" fill="var(--ink)" />
    </svg>
  );
}

export function BrujulaSays({
  children,
  validated,
  className,
}: {
  children: ReactNode;
  validated?: boolean;
  className?: string;
}) {
  return (
    <div className={cx("flex items-start gap-3", className)}>
      <BrujulaAvatar />
      <div className="relative rounded-2xl rounded-tl-sm border border-accent/30 bg-accent-soft px-4 py-3 text-sm leading-relaxed text-ink">
        <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-accent">
          Brújula
          {validated && (
            <span className="inline-flex items-center gap-1 font-medium normal-case tracking-normal text-ink-muted">
              <ShieldCheck aria-hidden size={13} /> cifras verificadas con los datos
            </span>
          )}
        </div>
        {children}
      </div>
    </div>
  );
}
