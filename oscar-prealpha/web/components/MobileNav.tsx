"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV } from "@/lib/nav";

/** Bouton hamburger (mobile/tablette) + tiroir de navigation plein écran.
 *  La NavRail latérale est masquée en dessous de `lg` ; ce tiroir la remplace. */
export function MobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        aria-label="Ouvrir le menu"
        className="-ml-1 inline-flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-md text-neutral-700 hover:bg-neutral-100 lg:hidden"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <path d="M3 6h18M3 12h18M3 18h18" />
        </svg>
      </button>

      {open && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-neutral-900/40 backdrop-blur-[1px]" onClick={() => setOpen(false)} />
          <aside className="absolute left-0 top-0 flex h-full w-[280px] max-w-[85%] flex-col bg-neutral-50 shadow-2xl">
            <div className="flex items-center justify-between px-5 py-4">
              <div className="flex items-center gap-2">
                <span className="text-[16px] font-bold tracking-[0.14em] text-neutral-900">OSCAR</span>
                <span className="rounded-xs bg-neutral-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-neutral-600">v3</span>
              </div>
              <button
                onClick={() => setOpen(false)}
                aria-label="Fermer le menu"
                className="inline-flex h-8 w-8 items-center justify-center rounded-md text-neutral-500 hover:bg-neutral-200 hover:text-neutral-900"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <nav className="thin-scroll flex-1 overflow-y-auto px-3 pb-8">
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
                            onClick={() => setOpen(false)}
                            className={`block rounded-sm px-2.5 py-2 text-body-sm transition-colors ${
                              active ? "bg-accent-100 font-semibold text-accent-700" : "text-neutral-700 hover:bg-neutral-100 hover:text-neutral-900"
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
          </aside>
        </div>
      )}
    </>
  );
}
