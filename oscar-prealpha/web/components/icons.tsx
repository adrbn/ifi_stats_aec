import type { SVGProps } from "react";

type P = SVGProps<SVGSVGElement>;
const base = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export const IconArrowUp = (p: P) => (
  <svg viewBox="0 0 10 10" {...p}><path d="M5 2L8 7H2z" fill="currentColor" /></svg>
);
export const IconArrowDown = (p: P) => (
  <svg viewBox="0 0 10 10" {...p}><path d="M5 8L8 3H2z" fill="currentColor" /></svg>
);
export const IconHome = (p: P) => (
  <svg viewBox="0 0 16 16" {...p}><path {...base} d="M2 8L8 2l6 6M4 7v7h8V7" /></svg>
);
export const IconSparkles = (p: P) => (
  <svg viewBox="0 0 16 16" {...p}>
    <path {...base} d="M8 1.5l1.4 3.6L13 6.5l-3.6 1.4L8 11.5 6.6 7.9 3 6.5l3.6-1.4z" />
    <path {...base} d="M12.5 10.5l.6 1.4 1.4.6-1.4.6-.6 1.4-.6-1.4L11 12.5l1.4-.6z" />
  </svg>
);
export const IconChevron = (p: P) => (
  <svg viewBox="0 0 16 16" {...p}><path {...base} d="M6 4l4 4-4 4" /></svg>
);
export const IconChevronRight = IconChevron;
export const IconClose = (p: P) => (
  <svg viewBox="0 0 16 16" {...p}><path {...base} strokeWidth={2} d="M4 4l8 8M12 4l-8 8" /></svg>
);
export const IconSend = (p: P) => (
  <svg viewBox="0 0 16 16" {...p}><path {...base} strokeWidth={2} d="M2 8h12M9 4l5 4-5 4" /></svg>
);
export const IconHistory = (p: P) => (
  <svg viewBox="0 0 16 16" {...p}><path {...base} d="M8 4v4l3 2M8 2a6 6 0 1 0 6 6" /></svg>
);
export const IconTrash = (p: P) => (
  <svg viewBox="0 0 16 16" {...p}><path {...base} d="M3 4h10M6 4V2h4v2M5 4l1 10h4l1-10" /></svg>
);
export const IconCheck = (p: P) => (
  <svg viewBox="0 0 16 16" {...p}><path {...base} strokeWidth={2} d="M3 8.5l3 3 7-7" /></svg>
);
export const IconInfo = (p: P) => (
  <svg viewBox="0 0 16 16" {...p}><circle {...base} cx="8" cy="8" r="7" /><path {...base} strokeWidth={2} d="M8 7v5M8 4.5v.5" /></svg>
);
export const IconWarn = (p: P) => (
  <svg viewBox="0 0 16 16" {...p}><path {...base} d="M8 2l7 12H1z" /><path {...base} strokeWidth={2} d="M8 7v3M8 12v.5" /></svg>
);
export const IconError = (p: P) => (
  <svg viewBox="0 0 16 16" {...p}><circle {...base} cx="8" cy="8" r="7" /><path {...base} strokeWidth={2} d="M5 5l6 6M11 5l-6 6" /></svg>
);
export const IconGrid = (p: P) => (
  <svg viewBox="0 0 16 16" {...p}><path {...base} d="M2 2h5v5H2zM9 2h5v5H9zM2 9h5v5H2zM9 9h5v5H9z" /></svg>
);
