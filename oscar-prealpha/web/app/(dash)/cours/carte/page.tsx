"use client";

import dynamic from "next/dynamic";
import { useSnapshot } from "@/lib/useSnapshot";
import { Panel } from "@/components/Card";
import { PageTitle } from "@/components/PageTitle";

// Three.js / WebGL must be client-only (no SSR).
const ItalyMap3D = dynamic(() => import("@/components/ItalyMap3D"), {
  ssr: false,
  loading: () => (
    <div className="grid h-[420px] place-items-center rounded-md border border-neutral-200 bg-[#0f172a] text-body-sm text-neutral-400">
      Chargement de la carte 3D…
    </div>
  ),
});

export default function CartePage() {
  const { data } = useSnapshot();
  return (
    <div className="space-y-5">
      <PageTitle eyebrow={`Réseau · ${data.filters.year}`} title="Carte du réseau">
        Les quatre antennes positionnées géographiquement — hauteur des piliers proportionnelle aux
        inscriptions, reliées au hub IFI. Glissez pour pivoter.
      </PageTitle>
      <Panel title="Réseau IFI en Italie" subtitle="Inscriptions par antenne · vue 3D interactive">
        <ItalyMap3D rows={data.byAntenna} antennas={data.meta.antennas} />
      </Panel>
    </div>
  );
}
