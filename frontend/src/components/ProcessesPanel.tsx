"use client";

import { useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { apiClient, buildLlmRequestOptions } from "@/lib/api";
import { formatActionErrorMessage, logClientError } from "@/lib/errorFeedback";
import { useRunAllStepBusy } from "@/lib/runAllStepEvents";
import { AUTOMATED_NORM_ADDRESSEES } from "@/types";

export default function ProcessesPanel() {
  const { state, setCurrentTab, setProcessesReady } = useApp();
  const [status, setStatus] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const isRunAllBusy = useRunAllStepBusy("processes");
  const isBusy = isRunning || isRunAllBusy;

  const canRun =
    state.regulationsReady &&
    !state.processesReady &&
    Boolean(state.selectedModel) &&
    !isBusy;

  const handleCompile = async () => {
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
      await Promise.all(
        AUTOMATED_NORM_ADDRESSEES.map((normAddressee) =>
          apiClient.compileProcesses({
            appSessionId: state.appSessionId,
            normAddressee,
            model: llm.model,
            provider: llm.provider,
            keys: llm.keys,
          })
        )
      );
      window.dispatchEvent(new Event("tiles-updated"));
      setProcessesReady(true);
      setCurrentTab(3);
    } catch (error) {
      logClientError("ProcessesPanel.compileProcesses", error, {
        appSessionId: state.appSessionId,
      });
      setStatus(formatActionErrorMessage("Prozesse konnten nicht gebündelt werden", error));
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <section className="w-full border-b border-white/60 bg-white/80 px-6 py-4 backdrop-blur">
      <div className="mx-auto max-w-6xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="text-xs text-slate-600">
            Vorgaben, die in der Praxis in einem Zusammenhang erfüllt werden, werden
            zu gemeinsamen Prozessen gebündelt. Der Lauf entwickelt die Daten fuer
            Verwaltung, Wirtschaft und Buerger gleichzeitig; der Umschalter in der
            Graph-Ansicht wechselt nur die Darstellung.
          </p>
          <button
            onClick={handleCompile}
            disabled={!canRun}
            className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
              canRun
                ? "bg-slate-900 text-white"
                : "cursor-not-allowed bg-slate-200 text-slate-500"
            }`}
          >
            {isBusy ? "Bitte warten..." : "Prozesse bündeln"}
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
