"use client";

import { createContext, useContext, type ComponentProps, type ReactNode } from "react";
import { ResponsiveContainer as RechartsResponsiveContainer } from "recharts";

/** Hauteur imposée aux graphes quand un panneau est en plein écran (sinon undefined
 *  → chaque graphe garde sa hauteur normale). Fourni par <Panel> via ChartFsHeight. */
const FsHeightContext = createContext<number | undefined>(undefined);

export function ChartFsHeight({ height, children }: { height?: number; children: ReactNode }) {
  return <FsHeightContext.Provider value={height}>{children}</FsHeightContext.Provider>;
}

/**
 * Remplace le ResponsiveContainer de recharts : en plein écran, il substitue la
 * hauteur du contexte au prop `height` → le graphe (SVG) se re-rend réellement à
 * la nouvelle taille (recharts calcule la hauteur du SVG depuis le prop, pas
 * depuis la CSS du conteneur). Ailleurs, comportement identique à recharts.
 */
export function ResponsiveContainer(props: ComponentProps<typeof RechartsResponsiveContainer>) {
  const fsHeight = useContext(FsHeightContext);
  return <RechartsResponsiveContainer {...props} height={fsHeight ?? props.height} />;
}
