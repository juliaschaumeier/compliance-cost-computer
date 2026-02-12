"use client";

import ModelSelector from "@/components/ModelSelector";

export default function Header() {
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
        <ModelSelector />
      </div>
    </header>
  );
}
