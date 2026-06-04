import type { ReactNode } from "react";
import { IconCheck, IconInfo, IconWarn, IconError } from "./icons";

type Variant = "success" | "info" | "warning" | "error";

const MAP: Record<Variant, { cls: string; Icon: typeof IconInfo }> = {
  success: { cls: "bg-success-soft border-success text-success", Icon: IconCheck },
  info: { cls: "bg-info-soft border-info text-info", Icon: IconInfo },
  warning: { cls: "bg-warning-soft border-warning text-warning", Icon: IconWarn },
  error: { cls: "bg-error-soft border-error text-error", Icon: IconError },
};

export function Alert({
  variant = "info",
  title,
  children,
}: {
  variant?: Variant;
  title: string;
  children?: ReactNode;
}) {
  const { cls, Icon } = MAP[variant];
  return (
    <div className={`flex items-start gap-3 rounded-md border-l-[3px] px-4 py-3 text-body-sm ${cls}`}>
      <Icon className="mt-0.5 h-[18px] w-[18px] flex-shrink-0" />
      <div>
        <b className="block font-semibold text-neutral-900">{title}</b>
        {children && <span className="text-neutral-700">{children}</span>}
      </div>
    </div>
  );
}
