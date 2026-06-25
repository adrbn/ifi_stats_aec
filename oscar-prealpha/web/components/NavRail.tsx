"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV } from "@/lib/nav";

export function NavRail() {
  const pathname = usePathname();
  const exportBtn = (href: string, label: string) => {
    const active = pathname === href;
    return (
      <Link
        href={href}
        className={`block rounded-md border px-3 py-2 text-center text-body-sm font-semibold transition-colors duration-120 ${
          active
            ? "border-accent-400 bg-accent-50 text-accent-700"
            : "border-neutral-300 text-neutral-700 hover:border-accent-400 hover:text-accent-700"
        }`}
      >
        {label}
      </Link>
    );
  };

  return (
    <aside className="sticky top-0 hidden h-screen w-[236px] flex-shrink-0 flex-col border-r border-neutral-200 bg-neutral-50 lg:flex">
      <div className="flex items-center gap-2 px-5 py-4">
        <span className="text-[16px] font-bold tracking-[0.14em] text-neutral-900">OSCAR</span>
        <span className="rounded-xs bg-neutral-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-neutral-600">
          v3 parser
        </span>
      </div>
      <nav className="thin-scroll flex-1 overflow-y-auto px-3 pb-6">
        {NAV.map((group) => (
          <div key={group.title} className="mb-4">
            <div className="px-2 pb-1.5 text-eyebrow font-semibold uppercase tracking-[0.06em] text-neutral-500">
              {group.title}
            </div>
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const active = pathname === item.href;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={`block rounded-sm px-2 py-1.5 text-body-sm transition-colors duration-120 ${
                        active
                          ? "bg-accent-100 font-semibold text-accent-700"
                          : "text-neutral-700 hover:bg-neutral-100 hover:text-neutral-900"
                      }`}
                    >
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Zone export / présentation — séparée du reste pour signaler la sortie du tableau de bord. */}
      <div className="border-t border-neutral-200 px-3 pb-3 pt-3">
        <div className="px-1 pb-2 text-eyebrow font-semibold uppercase tracking-[0.08em] text-neutral-400">
          Export &amp; présentation
        </div>
        <div className="space-y-2">
          {exportBtn("/rapport", "Rapport PDF")}
          {exportBtn("/presentation", "Présentation")}
        </div>
      </div>

      <div className="border-t border-neutral-200 px-5 py-3">
        <div className="text-body-sm font-semibold text-neutral-900">Adrien Robino</div>
        <Link href="/" className="text-caption text-neutral-500 hover:text-accent-600">
          Accueil
        </Link>
      </div>
    </aside>
  );
}
