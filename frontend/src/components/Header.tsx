"use client";

import { useState } from "react";

import EaEditDrawerShell from "@/components/ea_edit/EaEditDrawerShell";
import ModelSelector from "@/components/ModelSelector";
import { useApp } from "@/contexts/AppContext";

export default function Header() {
  const { state } = useApp();
  const [eaEditOpen, setEaEditOpen] = useState(false);
  const canOpenEditor = state.totalCostReady;

  return (
    <header className="border-b border-white/20 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-700 text-white shadow-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10 text-xl font-bold shadow-inner">
            CCC
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight sm:text-xl">
              Compliance-Cost Computer
            </h1>
            <p className="text-xs text-slate-200/80 sm:text-sm">
              Errechnet den jährlichen Erfüllungsaufwand einer Gesetzesänderung seitens der Verwaltung
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setEaEditOpen(true)}
            disabled={!canOpenEditor}
            className={`rounded-full border px-3 py-2 text-xs font-semibold transition ${
              canOpenEditor
                ? "border-white/40 bg-white/10 text-white hover:bg-white/20"
                : "cursor-not-allowed border-white/20 bg-white/5 text-slate-300"
            }`}
            title={
              canOpenEditor
                ? "EA-Editor öffnen"
                : "EA-Editor ist nach Gesamtkosten-Berechnung verfügbar"
            }
          >
            EA bearbeiten
          </button>
          <ModelSelector />
        </div>
      </div>
      <EaEditDrawerShell open={eaEditOpen} onClose={() => setEaEditOpen(false)} />
    </header>
  );
}
