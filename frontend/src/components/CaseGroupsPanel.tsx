"use client";

import { useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { buildLlmRequestOptions } from "@/lib/api";
import { getVisibleFailedStepStatus } from "@/lib/sessionStatus";
import { useCancellableStepRun } from "@/lib/useCancellableStepRun";
import { useRunAllStepCancel } from "@/lib/useRunAllStepCancel";

export default function CaseGroupsPanel() {
  const { state, setCurrentTab, setCaseGroupsReady } = useApp();
  const [status, setStatus] = useState<string | null>(null);
  const runAllCancel = useRunAllStepCancel({
    stepKey: "case_groups",
    appSessionId: state.appSessionId,
    setStatus,
    logScope: "CaseGroupsPanel.cancelRunAll",
  });
  const isRunAllBusy = runAllCancel.isRunAllBusy;
  const llm = buildLlmRequestOptions({
    selectedModel: state.selectedModel,
    availableModels: state.availableModels,
  });
  const stepRun = useCancellableStepRun({
    appSessionId: state.appSessionId,
    stepKey: "case_groups",
    stepLabel: "Fallgruppen entwickeln",
    model: llm.model,
    provider: llm.provider,
    keys: llm.keys,
    logScope: "CaseGroupsPanel.developCaseGroups",
    onCompleted: () => {
      window.dispatchEvent(new Event("tiles-updated"));
      setCaseGroupsReady(true);
      setCurrentTab(4);
    },
    onCancelled: () => {
      window.dispatchEvent(new Event("tiles-updated"));
    },
  });
  const isBusy = stepRun.isRunning || isRunAllBusy;

  const canRun =
    state.processesReady &&
    !state.caseGroupsReady &&
    Boolean(state.selectedModel) &&
    !isBusy;

  const handleDevelop = async () => {
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
      setStatus("Fallgruppen konnten nicht gestartet werden.");
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
    await handleDevelop();
  };
  const buttonLabel = stepRun.isRunning
    ? stepRun.isCancelling
      ? "Abbruch wird ausgeführt..."
      : "Abbrechen"
    : isRunAllBusy
      ? runAllCancel.isCancellingRunAll
        ? "Abbruch wird ausgeführt..."
        : "Abbrechen"
      : "Fallgruppen entwickeln";
  const buttonClass =
    stepRun.isRunning || isRunAllBusy
      ? stepRun.isCancelling || runAllCancel.isCancellingRunAll
        ? "cursor-not-allowed border border-rose-100 bg-rose-100 text-rose-400"
        : "border border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100"
      : canRun
        ? "bg-slate-900 text-white"
        : "cursor-not-allowed bg-slate-200 text-slate-500";
  const buttonDisabled =
    stepRun.isCancelling ||
    runAllCancel.isCancellingRunAll ||
    (isRunAllBusy ? !runAllCancel.runAllRunId : !stepRun.isRunning && !canRun);
  const visibleStepRunStatus = stepRun.isRunning ? null : stepRun.statusText;
  const failedStepStatus = getVisibleFailedStepStatus(
    state,
    "case_groups",
    state.caseGroupsReady,
    visibleStepRunStatus
  );

  return (
    <section className="w-full border-b border-white/60 bg-white/80 px-6 py-4 backdrop-blur">
      <div className="mx-auto max-w-6xl space-y-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start">
          <p className="text-xs leading-5 text-slate-600">
            Wenn Prozesse auf unterschiedlichen Wegen erfüllt werden, werden
            Fallgruppen gebildet. Jede Fallgruppe beschreibt eine typische
            Ausprägung der Ausführung, damit der Erfüllungsaufwand getrennt
            ermittelt werden kann. Der Lauf entwickelt Fallgruppen in einem
            Durchgang für Verwaltung, Wirtschaft und Bürger, erzeugt dabei aber
            je Normadressat eine eigene fachliche Sicht. Der Umschalter zeigt
            die Sicht des ausgewählten Normadressaten.
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
