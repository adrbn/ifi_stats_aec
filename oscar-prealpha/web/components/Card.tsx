import type { ReactNode } from "react";

export function Panel({
  title,
  subtitle,
  right,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`min-w-0 rounded-lg border border-neutral-200 bg-surface shadow-xs ${className}`}>
      {(title || right) && (
        <header className="flex items-start justify-between gap-4 border-b border-neutral-200 px-5 py-4">
          <div>
            {title && <h2 className="text-h2 font-semibold text-neutral-900">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-body-sm text-neutral-500">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <div className="text-eyebrow font-semibold uppercase tracking-[0.1em] text-accent-600">
      {children}
    </div>
  );
}
