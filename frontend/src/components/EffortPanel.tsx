"use client";

import { useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { buildLlmRequestOptions } from "@/lib/api";
import { getVisibleFailedStepStatus } from "@/lib/sessionStatus";
import { useCancellableStepRun } from "@/lib/useCancellableStepRun";
import { useRunAllStepCancel } from "@/lib/useRunAllStepCancel";

export default function EffortPanel() {
  const { state, setCurrentTab, setEffortReady } = useApp();
  const [status, setStatus] = useState<string | null>(null);
  const runAllCancel = useRunAllStepCancel({
    stepKey: "effort",
    appSessionId: state.appSessionId,
    setStatus,
    logScope: "EffortPanel.cancelRunAll",
  });
  const isRunAllBusy = runAllCancel.isRunAllBusy;
  const llm = buildLlmRequestOptions({
    selectedModel: state.selectedModel,
    availableModels: state.availableModels,
  });
  const stepRun = useCancellableStepRun({
    appSessionId: state.appSessionId,
    stepKey: "effort",
    stepLabel: "Aufwand berechnen",
    model: llm.model,
    provider: llm.provider,
    keys: llm.keys,
    logScope: "EffortPanel.calculateEffort",
    onCompleted: () => {
      window.dispatchEvent(new Event("tiles-updated"));
      setEffortReady(true);
      setStatus("Aufwand fuer Verwaltung, Wirtschaft und Buerger berechnet.");
      setCurrentTab(6);
    },
    onCancelled: () => {
      window.dispatchEvent(new Event("tiles-updated"));
    },
  });
  const isBusy = stepRun.isRunning || isRunAllBusy;

  const canRun =
    state.processStepsReady &&
    !state.effortReady &&
    Boolean(state.selectedModel) &&
    !isBusy;

  const handleCalculate = async () => {
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
      setStatus("Aufwand konnte nicht gestartet werden.");
    }
  };

  const handleButtonClick = async () => {
    if (stepRun.isRunning) {
      await stepRun.cancel();
      return;
    }
    if (isRunAllBusy) {
      await runAllCancel.cancelRunAllForStep();
      return;
    }
    await handleCalculate();
  };

  const buttonLabel = (() => {
    if (stepRun.isRunning) {
      return stepRun.isCancelling ? "Abbruch wird ausgeführt..." : "Abbrechen";
    }
    if (isRunAllBusy) {
      return runAllCancel.isCancellingRunAll
        ? "Abbruch wird ausgeführt..."
        : "Abbrechen";
    }
    return "Aufwand berechnen";
  })();

  const buttonClass = (() => {
    if (stepRun.isRunning || isRunAllBusy) {
      return stepRun.isCancelling || runAllCancel.isCancellingRunAll
        ? "cursor-not-allowed border border-rose-100 bg-rose-100 text-rose-400"
        : "border border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100";
    }
    return canRun
      ? "bg-slate-900 text-white"
      : "cursor-not-allowed bg-slate-200 text-slate-500";
  })();

  const buttonDisabled =
    stepRun.isCancelling ||
    runAllCancel.isCancellingRunAll ||
    (isRunAllBusy ? !runAllCancel.runAllRunId : !stepRun.isRunning && !canRun);
  const visibleStepRunStatus = stepRun.isRunning ? null : stepRun.statusText;
  const failedStepStatus = getVisibleFailedStepStatus(
    state,
    "effort",
    state.effortReady,
    visibleStepRunStatus
  );

  return (
    <section className="w-full border-b border-white/60 bg-white/80 px-6 py-4 backdrop-blur">
      <div className="mx-auto max-w-6xl space-y-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start">
          <p className="text-xs leading-5 text-slate-600">
            Beim Klick auf „Aufwand berechnen“ werden Fallzahlen je Fallgruppe sowie
            Lohnsatz-, Zeit- und Sachaufwände je Prozessschritt ermittelt. Der Lauf
            berechnet die Werte in einem Durchgang für Verwaltung, Wirtschaft und
            Bürger, erzeugt dabei aber je Normadressat eigene Aufwandssichten. Der
            Umschalter zeigt die Sicht des ausgewählten Normadressaten.
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

        {(status || visibleStepRunStatus || failedStepStatus) && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
            {visibleStepRunStatus || status || failedStepStatus}
          </div>
        )}
      </div>
    </section>
  );
}
