import Link from "next/link";

import BmfFundingImage from "@/components/BmfFundingImage";

export const metadata = {
  title: "Impressum | Compliance-Cost Computer",
  description: "Impressum, Lizenz und Förderhinweis zum Compliance-Cost Computer.",
};

export default function ImpressumPage() {
  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10 text-slate-900">
      <div className="mx-auto max-w-3xl rounded-2xl border border-slate-200 bg-white p-6 shadow-xl sm:p-8">
        <Link
          href="/"
          className="inline-flex rounded-full border border-slate-200 px-3 py-1 text-xs font-semibold text-slate-600 transition hover:bg-slate-50"
        >
          Zurück zum CCC
        </Link>

        <div className="mt-8 flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-900 text-lg font-bold text-white shadow-inner">
            CCC
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Compliance-Cost Computer
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              Impressum
            </h1>
          </div>
        </div>

        <p className="mt-4 text-sm leading-7 text-slate-600">
          Der Compliance-Cost Computer ist ein Forschungsprototyp. Seine
          Ergebnisse sollen Orientierung geben und sollten fachlich sorgfältig
          geprüft werden.
        </p>

        <section className="mt-8 space-y-3">
          <h2 className="text-lg font-semibold text-slate-950">
            Entwicklung und Kontakt
          </h2>
          <div className="text-sm leading-7 text-slate-700">
            <p>Technische Universität München</p>
            <p>Arbeitsgruppe Legal Tech</p>
            <p>Boltzmannstraße 3</p>
            <p>85748 Garching</p>
            <p className="mt-3">
              E-Mail:{" "}
              <a
                href="mailto:j.schaumeier@tum.de"
                className="font-semibold text-slate-950 underline decoration-slate-300 underline-offset-4 hover:decoration-slate-700"
              >
                j.schaumeier@tum.de
              </a>
            </p>
          </div>
        </section>

        <section id="lizenz" className="mt-8 space-y-3">
          <h2 className="text-lg font-semibold text-slate-950">Lizenz</h2>
          <p className="text-sm leading-7 text-slate-700">
            Der Compliance-Cost Computer ist als Open-Source-Software unter der{" "}
            <span className="font-semibold text-slate-950">
              GNU General Public License v3.0 or later
            </span>{" "}
            veröffentlicht. Weitere Informationen stehen in der Datei{" "}
            <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs">
              LICENSE
            </code>{" "}
            im Quellcode des Projekts.
          </p>
        </section>

        <section className="mt-8 space-y-3">
          <h2 className="text-lg font-semibold text-slate-950">Förderung</h2>
          <p className="text-sm leading-7 text-slate-700">
            Dieses Forschungsprojekt wird durch das Bundesministerium der
            Finanzen gefördert.
          </p>
          <BmfFundingImage />
        </section>

        <p className="mt-8 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Stand: 02.10.2026
        </p>
      </div>
    </main>
  );
}
