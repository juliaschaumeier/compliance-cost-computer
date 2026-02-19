"use client";

import { useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { apiClient, buildLlmRequestOptions } from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";

export default function EffortPanel() {
  const { state, setCurrentTab, setEffortReady } = useApp();
  const [status, setStatus] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const canRun = state.processStepsReady && !state.effortReady && !isRunning;

  const handleCalculate = async () => {
    if (!canRun) {
      return;
    }
    setStatus(null);
    setIsRunning(true);
    const llm = buildLlmRequestOptions({
      selectedModel: state.selectedModel,
      availableModels: state.availableModels,
    });
    try {
      const result = await apiClient.calculateEffort({
        appSessionId: state.appSessionId,
        model: llm.model,
        provider: llm.provider,
        keys: llm.keys,
      });
      if (result.status === "existing") {
        setStatus("Aufwand wurde bereits berechnet.");
        setEffortReady(true);
        setCurrentTab(6);
        return;
      }
      window.dispatchEvent(new Event("tiles-updated"));
      setEffortReady(true);
      setCurrentTab(6);
    } catch (error) {
      logClientError("EffortPanel.calculateEffort", error, {
        appSessionId: state.appSessionId,
      });
      const message =
        error instanceof Error && error.message
          ? error.message
          : "Unbekannter Fehler";
      setStatus(`Aufwand konnte nicht berechnet werden: ${message}`);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <section className="w-full border-b border-white/60 bg-white/80 px-6 py-4 backdrop-blur">
      <div className="mx-auto max-w-6xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="text-xs text-slate-600">
            Beim Klick auf „Aufwand berechnen“ werden Fallzahlen je Fallgruppe sowie
            Lohnsatz-, Zeit- und Sachaufwände je Prozessschritt ermittelt.
          </p>
          <button
            onClick={handleCalculate}
            disabled={!canRun}
            className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
              canRun
                ? "bg-slate-900 text-white"
                : "cursor-not-allowed bg-slate-200 text-slate-500"
            }`}
          >
            {isRunning ? "Bitte warten..." : "Aufwand berechnen"}
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
