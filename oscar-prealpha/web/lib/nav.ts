export interface NavItem {
  label: string;
  href: string;
}
export interface NavGroup {
  title: string;
  items: NavItem[];
}

/**
 * Navigation tree — mirrors the OSCAR analytical domains (Cours / Profils /
 * Produits) and their sub-views. Direction "C" rail = zero navigation
 * confusion across the 11+ views.
 */
export const NAV: NavGroup[] = [
  {
    title: "Cours",
    items: [
      { label: "Synthèse", href: "/cours/synthese" },
      { label: "Par antenne", href: "/cours/antennes" },
      { label: "Par secteurs", href: "/cours/secteurs" },
      { label: "Répartition", href: "/cours/repartition" },
      { label: "Année vs année", href: "/cours/annee" },
      { label: "Rentabilité", href: "/cours/rentabilite" },
      { label: "Évolutions", href: "/cours/evolutions" },
      { label: "Graphiques", href: "/cours/graphiques" },
      { label: "Carte du réseau", href: "/cours/carte" },
    ],
  },
  {
    title: "Profils",
    items: [
      { label: "Synthèse", href: "/profils/synthese" },
      { label: "Démographie", href: "/profils/demographie" },
      { label: "Nationalités", href: "/profils/nationalites" },
      { label: "Motivation & acquisition", href: "/profils/motivation" },
    ],
  },
  {
    title: "Produits",
    items: [
      { label: "Catalogue", href: "/produits/catalogue" },
      { label: "Par type", href: "/produits/types" },
      { label: "Tarifs", href: "/produits/tarifs" },
    ],
  },
];

export const NAV_FLAT = NAV.flatMap((g) =>
  g.items.map((i) => ({ ...i, group: g.title })),
);

export function crumbFor(pathname: string): { group: string; label: string } | null {
  const hit = NAV_FLAT.find((i) => i.href === pathname);
  return hit ? { group: hit.group, label: hit.label } : null;
}
