"use client";

import { useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { apiClient, buildLlmRequestOptions } from "@/lib/api";
import { formatActionErrorMessage, logClientError } from "@/lib/errorFeedback";
import { useRunAllStepBusy } from "@/lib/runAllStepEvents";

export default function RegulationsPanel() {
  const { state, setCurrentTab, setRegulationsReady, setProcessesReady } = useApp();
  const [status, setStatus] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const isRunAllBusy = useRunAllStepBusy("regulations");
  const isBusy = isRunning || isRunAllBusy;

  const canRun =
    state.summaryReady &&
    !state.regulationsReady &&
    !isBusy &&
    Boolean(state.selectedModel) &&
    Boolean(state.selectedCurrentLaw) &&
    Boolean(state.selectedRegulation);

  const handleIdentify = async () => {
    if (!state.selectedModel) {
      setStatus("Bitte zuerst ein Modell auswählen.");
      return;
    }
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
      await apiClient.identifyRegulations({
        currentFilename: state.selectedCurrentLaw,
        proposedFilename: state.selectedRegulation,
        appSessionId: state.appSessionId,
        model: llm.model,
        provider: llm.provider,
        keys: llm.keys,
      });
      window.dispatchEvent(new Event("tiles-updated"));
      setRegulationsReady(true);
      setProcessesReady(false);
      setCurrentTab(2);
    } catch (error) {
      logClientError("RegulationsPanel.identifyRegulations", error, {
        appSessionId: state.appSessionId,
      });
      setStatus(formatActionErrorMessage("Vorgaben konnten nicht bestimmt werden", error));
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
            {isBusy ? "Bitte warten..." : "Vorgaben bestimmen"}
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
