import Link from "next/link";
import { IconArrowUp, IconGrid, IconSparkles } from "@/components/icons";

export default function Home() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-neutral-200 bg-surface/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1280px] items-center justify-between px-6 py-3">
          <div className="flex items-baseline gap-3">
            <span className="text-[16px] font-bold tracking-[0.14em] text-neutral-900">OSCAR</span>
            <span className="text-body-sm text-neutral-500">Pre-alpha · Next.js</span>
          </div>
          <Link
            href="/cours/synthese"
            className="rounded-md bg-neutral-900 px-4 py-2 text-body-sm font-semibold text-white transition-colors hover:bg-neutral-800"
          >
            Ouvrir le tableau de bord
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-[1280px] px-6">
        <section className="border-b border-neutral-200 py-14">
          <div className="text-eyebrow font-semibold uppercase tracking-[0.1em] text-accent-600">
            Institut français Italia · pilotage statistique
          </div>
          <h1 className="mt-2 max-w-[820px] text-[40px] font-bold leading-[1.1] tracking-[-0.02em] text-neutral-900">
            Le réseau IFI, en un coup d'œil.
          </h1>
          <p className="mt-4 max-w-[680px] text-[17px] leading-relaxed text-neutral-700">
            Inscriptions, cours, recettes et taux de remplissage des quatre antennes —
            Milan, Florence, Naples, Palerme — sur plusieurs années. Données calculées par le
            moteur OSCAR, présentées dans une interface repensée.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/cours/synthese"
              className="inline-flex items-center gap-2 rounded-md bg-accent-500 px-5 py-2.5 text-body font-semibold text-white shadow-sm transition-colors hover:bg-accent-600"
            >
              <IconGrid className="h-4 w-4" />
              Voir la synthèse
            </Link>
            <Link
              href="/cours/carte"
              className="inline-flex items-center gap-2 rounded-md border border-neutral-200 bg-surface px-5 py-2.5 text-body font-semibold text-neutral-700 transition-colors hover:border-neutral-300 hover:text-neutral-900"
            >
              Carte 3D du réseau
            </Link>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 py-10 md:grid-cols-3">
          <FeatureCard
            title="Synthèse & secteurs"
            body="KPI consolidés, comparaison par antenne, tableau détaillé par secteur d'activité avec ligne TOTAL distincte."
            href="/cours/synthese"
          />
          <FeatureCard
            title="Évolutions"
            body="Tendances pluriannuelles des inscriptions et recettes, par antenne, sur l'historique disponible."
            href="/cours/evolutions"
          />
          <FeatureCard
            title="Assistant OSCAR"
            body="Posez vos questions en langage naturel : meilleure antenne, secteur le plus rentable, totaux."
            href="/cours/synthese"
            icon={<IconSparkles className="h-4 w-4 text-accent-600" />}
          />
        </section>

        <section className="grid grid-cols-2 gap-4 border-t border-neutral-200 py-10 sm:grid-cols-4">
          {[
            { c: "IFM", n: "Milano", color: "#FF8C00" },
            { c: "IFF", n: "Firenze", color: "#8B5CF6" },
            { c: "IFN", n: "Napoli", color: "#22C55E" },
            { c: "IFP", n: "Palermo", color: "#EF4444" },
          ].map((a) => (
            <div key={a.c} className="flex items-center gap-3 rounded-md border border-neutral-200 bg-surface p-4">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: a.color }} />
              <div>
                <div className="text-body font-semibold text-neutral-900">{a.c}</div>
                <div className="text-caption text-neutral-500">{a.n}</div>
              </div>
            </div>
          ))}
        </section>
      </main>

      <footer className="border-t border-neutral-200 py-6">
        <div className="mx-auto flex max-w-[1280px] items-center justify-between px-6 text-caption text-neutral-500">
          <span>OSCAR · pre-alpha · Next.js + Tailwind + Three.js — moteur de calcul pandas réutilisé</span>
          <span>IBM Plex Sans · 6px radius · bleu IFI</span>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({
  title,
  body,
  href,
  icon,
}: {
  title: string;
  body: string;
  href: string;
  icon?: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="group rounded-lg border border-neutral-200 bg-surface p-5 shadow-xs transition-[border-color,box-shadow] hover:border-neutral-300 hover:shadow-md"
    >
      <div className="mb-2 flex items-center gap-2">
        {icon}
        <h3 className="text-h3 font-semibold text-neutral-900">{title}</h3>
      </div>
      <p className="text-body-sm leading-relaxed text-neutral-600">{body}</p>
      <span className="mt-3 inline-flex items-center gap-1 text-body-sm font-semibold text-accent-600">
        Ouvrir
        <IconArrowUp className="h-2.5 w-2.5 rotate-90" />
      </span>
    </Link>
  );
}
