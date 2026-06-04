import type { KpiFormat } from "./types";

const NBSP = " "; // narrow no-break space — French thousands separator

export function formatInt(n: number): string {
  return Math.round(n)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, NBSP);
}

export function formatEur(n: number): string {
  if (Math.abs(n) >= 1_000_000) {
    return `${(n / 1_000_000).toFixed(1).replace(".", ",")}${NBSP}M€`;
  }
  return `${formatInt(n)}${NBSP}€`;
}

export function formatDec1(n: number): string {
  return n.toFixed(1).replace(".", ",");
}

export function formatPct(n: number): string {
  return `${n.toFixed(1).replace(".", ",")}${NBSP}%`;
}

export function formatKpi(value: number, fmt: KpiFormat): string {
  switch (fmt) {
    case "eur":
      return formatEur(value);
    case "dec1":
      return formatDec1(value);
    default:
      return formatInt(value);
  }
}

export function formatDelta(delta: number, fmt: KpiFormat): string {
  if (delta === 0) return "stable";
  const sign = delta > 0 ? "+" : "−";
  const abs = Math.abs(delta);
  if (fmt === "dec1") return `${sign}${formatDec1(abs)}`;
  return `${sign}${abs.toFixed(1).replace(".", ",")}${NBSP}%`;
}
