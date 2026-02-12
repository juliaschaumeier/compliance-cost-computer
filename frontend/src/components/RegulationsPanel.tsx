"use client";

import { useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";

export default function RegulationsPanel() {
  const { state, setCurrentTab, setRegulationsReady, setProcessesReady } = useApp();
  const [status, setStatus] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const canRun =
    state.summaryReady &&
    !state.regulationsReady &&
    !isRunning &&
    Boolean(state.selectedCurrentLaw) &&
    Boolean(state.selectedRegulation);

  const handleIdentify = async () => {
    if (!canRun) {
      return;
    }
    setStatus(null);
    setIsRunning(true);
    const selectedModel = state.selectedModel;
    const selectedModelData = state.availableModels.find(
      (model) => model.id === selectedModel
    );
    const provider = selectedModelData?.provider?.toLowerCase();
    try {
      await apiClient.identifyRegulations({
        currentFilename: state.selectedCurrentLaw,
        proposedFilename: state.selectedRegulation,
        appSessionId: state.sessionId,
        model: selectedModel || undefined,
        provider,
        keys: {
          openaiApiKey: localStorage.getItem("openai_api_key") || undefined,
          deepinfraApiKey: localStorage.getItem("deepinfra_api_key") || undefined,
          geminiApiKey: localStorage.getItem("gemini_api_key") || undefined,
        },
      });
      window.dispatchEvent(new Event("tiles-updated"));
      setRegulationsReady(true);
      setProcessesReady(false);
      setCurrentTab(2);
    } catch (error) {
      setStatus("Vorgaben konnten nicht bestimmt werden.");
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <section className="w-full border-b border-white/60 bg-white/80 px-6 py-4 backdrop-blur">
      <div className="mx-auto max-w-6xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="text-xs text-slate-600">
            Beim Klick auf &quot;Vorgaben bestimmen&quot; werden die zwei gewählten
            Gesetzestexte analysiert und die relevanten Vorgaben ermittelt.
          </p>
          <button
            onClick={handleIdentify}
            disabled={!canRun}
            className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
              canRun
                ? "bg-slate-900 text-white"
                : "cursor-not-allowed bg-slate-200 text-slate-500"
            }`}
          >
            {isRunning ? "Bitte warten..." : "Vorgaben bestimmen"}
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
