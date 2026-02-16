"use client";

import { useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";

export default function TotalCostPanel() {
  const { state, setCurrentTab } = useApp();
  const [status, setStatus] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const canRun =
    state.processStepsReady &&
    state.effortReady &&
    !state.totalCostReady &&
    !isRunning;

  const label = state.totalCostReady
    ? "Bereits berechnet"
    : isRunning
      ? "Bitte warten..."
      : "Gesamtkosten berechnen";

  const handleCompute = async () => {
    if (!canRun) {
      return;
    }
    setStatus(null);
    setIsRunning(true);
    try {
      await apiClient.computeTotalCost({ appSessionId: state.appSessionId });
      window.dispatchEvent(new Event("tiles-updated"));
      setCurrentTab(6);
    } catch (error) {
      setStatus("Gesamtkosten konnten nicht berechnet werden.");
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <section className="w-full border-b border-white/60 bg-white/80 px-6 py-4 backdrop-blur">
      <div className="mx-auto max-w-6xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="text-xs text-slate-600">
            Beim Klick auf „Gesamtkosten berechnen“ werden Schritt-, Fallgruppen-
            und Prozesskosten summiert und als Gesamtkosten ausgewiesen.
          </p>
          <button
            onClick={handleCompute}
            disabled={!canRun}
            className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
              canRun
                ? "bg-slate-900 text-white"
                : "cursor-not-allowed bg-slate-200 text-slate-500"
            }`}
          >
            {label}
          </button>
        </div>

        {status && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
            {status}
          </div>
        )}
      </div>
    </section>
  );
}
