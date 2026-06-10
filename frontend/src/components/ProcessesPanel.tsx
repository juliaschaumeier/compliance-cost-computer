"use client";

import { useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { buildLlmRequestOptions } from "@/lib/api";
import { useRunAllStepBusy } from "@/lib/runAllStepEvents";
import { useCancellableStepRun } from "@/lib/useCancellableStepRun";

export default function ProcessesPanel() {
  const { state, setCurrentTab, setProcessesReady } = useApp();
  const [status, setStatus] = useState<string | null>(null);
  const isRunAllBusy = useRunAllStepBusy("processes");
  const llm = buildLlmRequestOptions({
    selectedModel: state.selectedModel,
    availableModels: state.availableModels,
  });
  const stepRun = useCancellableStepRun({
    appSessionId: state.appSessionId,
    stepKey: "processes",
    stepLabel: "Prozesse bündeln",
    model: llm.model,
    provider: llm.provider,
    keys: llm.keys,
    logScope: "ProcessesPanel.compileProcesses",
    onCompleted: () => {
      window.dispatchEvent(new Event("tiles-updated"));
      setProcessesReady(true);
      setCurrentTab(3);
    },
    onCancelled: () => {
      window.dispatchEvent(new Event("tiles-updated"));
    },
  });
  const isBusy = stepRun.isRunning || isRunAllBusy;

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
    try {
      await stepRun.start();
    } catch {
      setStatus("Prozesse konnten nicht gestartet werden.");
    }
  };
  const handleButtonClick = async () => {
    if (stepRun.isRunning) {
      await stepRun.cancel();
      return;
    }
    await handleCompile();
  };
  const buttonLabel = stepRun.isRunning
    ? stepRun.isCancelling
      ? "Abbruch wird ausgeführt..."
      : "Abbrechen"
    : isRunAllBusy
      ? "Abbrechen"
      : "Prozesse bündeln";
  const buttonClass =
    stepRun.isRunning || isRunAllBusy
      ? stepRun.isCancelling
        ? "cursor-not-allowed border border-rose-100 bg-rose-100 text-rose-400"
        : "border border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100"
      : canRun
        ? "bg-slate-900 text-white"
        : "cursor-not-allowed bg-slate-200 text-slate-500";
  const buttonDisabled = isRunAllBusy || stepRun.isCancelling || (!stepRun.isRunning && !canRun);
  const visibleStepRunStatus = stepRun.isRunning ? null : stepRun.statusText;

  return (
    <section className="w-full border-b border-white/60 bg-white/80 px-6 py-4 backdrop-blur">
      <div className="mx-auto max-w-6xl space-y-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start">
          <p className="text-xs leading-5 text-slate-600">
            Vorgaben, die in der Praxis in einem Zusammenhang erfüllt werden, werden
            zu gemeinsamen Prozessen gebündelt. Der Lauf bündelt die Vorgaben in einem
            Durchgang für Verwaltung, Wirtschaft und Bürger, erzeugt dabei aber je
            Normadressat eine eigene Prozesssicht. Der Umschalter zeigt die Sicht des
            ausgewählten Normadressaten.
          </p>
          <button
            onClick={handleButtonClick}
            disabled={buttonDisabled}
            className={`inline-flex items-center gap-2 justify-self-start whitespace-nowrap rounded-full px-4 py-2 text-sm font-semibold transition sm:justify-self-end ${buttonClass}`}
          >
            {(stepRun.isRunning || isRunAllBusy) && (
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
            )}
            {buttonLabel}
          </button>
        </div>

        {(status || visibleStepRunStatus) && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
            {visibleStepRunStatus || status}
          </div>
        )}
      </div>
    </section>
  );
}
