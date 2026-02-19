"use client";

import { useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { apiClient, buildLlmRequestOptions } from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";

export default function ProcessStepsPanel() {
  const { state, setCurrentTab, setProcessStepsReady } = useApp();
  const [status, setStatus] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const canRun = state.caseGroupsReady && !state.processStepsReady && !isRunning;

  const handleAnalyze = async () => {
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
      await apiClient.analyzeProcessSteps({
        appSessionId: state.appSessionId,
        model: llm.model,
        provider: llm.provider,
        keys: llm.keys,
      });
      window.dispatchEvent(new Event("tiles-updated"));
      setProcessStepsReady(true);
      setCurrentTab(5);
    } catch (error) {
      logClientError("ProcessStepsPanel.analyzeProcessSteps", error, {
        appSessionId: state.appSessionId,
      });
      setStatus("Prozessschritte konnten nicht bestimmt werden.");
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <section className="w-full border-b border-white/60 bg-white/80 px-6 py-4 backdrop-blur">
      <div className="mx-auto max-w-6xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="text-xs text-slate-600">
            Für jede Fallgruppe werden die notwendigen Tätigkeiten identifiziert
            und als Prozessschritte erfasst.
          </p>
          <button
            onClick={handleAnalyze}
            disabled={!canRun}
            className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
              canRun
                ? "bg-slate-900 text-white"
                : "cursor-not-allowed bg-slate-200 text-slate-500"
            }`}
          >
            {isRunning ? "Bitte warten..." : "Prozessschritte bestimmen"}
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
