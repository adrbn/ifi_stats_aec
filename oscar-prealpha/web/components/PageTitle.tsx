import type { ReactNode } from "react";
import { Eyebrow } from "./Card";

export function PageTitle({
  eyebrow,
  title,
  children,
}: {
  eyebrow?: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="mb-5">
      {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
      <h1 className="mt-1 text-h1 font-semibold tracking-[-0.01em] text-neutral-900">{title}</h1>
      {children && <p className="mt-1 max-w-[760px] text-body-sm text-neutral-500">{children}</p>}
    </div>
  );
}
