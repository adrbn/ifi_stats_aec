"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV } from "@/lib/nav";

export function NavRail() {
  const pathname = usePathname();
  return (
    <aside className="hidden w-[236px] flex-shrink-0 flex-col border-r border-neutral-200 bg-neutral-50 lg:flex">
      <div className="flex items-center gap-2 px-5 py-4">
        <span className="text-[16px] font-bold tracking-[0.14em] text-neutral-900">OSCAR</span>
        <span className="rounded-xs bg-neutral-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-neutral-600">
          v3 parser
        </span>
      </div>
      <nav className="thin-scroll flex-1 overflow-y-auto px-3 pb-6">
        <Link
          href="/rapport"
          className={`mb-1 flex items-center gap-2 rounded-sm px-2 py-2 text-body-sm font-semibold transition-colors duration-120 ${
            pathname === "/rapport"
              ? "bg-accent-100 text-accent-700"
              : "text-neutral-700 hover:bg-neutral-100 hover:text-neutral-900"
          }`}
        >
          <span aria-hidden>📄</span> Rapport d'activité
        </Link>
        <Link
          href="/presentation"
          className={`mb-4 flex items-center gap-2 rounded-sm px-2 py-2 text-body-sm font-semibold transition-colors duration-120 ${
            pathname === "/presentation"
              ? "bg-accent-100 text-accent-700"
              : "text-neutral-700 hover:bg-neutral-100 hover:text-neutral-900"
          }`}
        >
          <span aria-hidden>▶</span> Présentation
        </Link>
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
      <div className="border-t border-neutral-200 px-5 py-3">
        <div className="text-body-sm font-semibold text-neutral-900">Adrien Robino</div>
        <Link href="/" className="text-caption text-neutral-500 hover:text-accent-600">
          Accueil
        </Link>
      </div>
    </aside>
  );
}
