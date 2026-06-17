"use client";

import { useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { buildLlmRequestOptions } from "@/lib/api";
import { getVisibleFailedStepStatus } from "@/lib/sessionStatus";
import { useCancellableStepRun } from "@/lib/useCancellableStepRun";
import { useRunAllStepCancel } from "@/lib/useRunAllStepCancel";
import { getWorkflowStepActionButtonState } from "@/lib/workflowStepActionButton";
import StepRunButton from "@/components/StepRunButton";
import WorkflowControls from "@/components/WorkflowControls";

export default function RegulationsPanel() {
  const { state, setCurrentTab, setRegulationsReady, setProcessesReady } = useApp();
  const [status, setStatus] = useState<string | null>(null);
  const runAllCancel = useRunAllStepCancel({
    stepKey: "regulations",
    appSessionId: state.appSessionId,
    setStatus,
    logScope: "RegulationsPanel.cancelRunAll",
  });
  const isRunAllBusy = runAllCancel.isRunAllBusy;
  const llm = buildLlmRequestOptions({
    selectedModel: state.selectedModel,
    availableModels: state.availableModels,
  });
  const stepRun = useCancellableStepRun({
    appSessionId: state.appSessionId,
    stepKey: "regulations",
    stepLabel: "Vorgaben identifizieren",
    model: llm.model,
    provider: llm.provider,
    keys: llm.keys,
    logScope: "RegulationsPanel.identifyRegulations",
    onCompleted: () => {
      window.dispatchEvent(new Event("tiles-updated"));
      setRegulationsReady(true);
      setProcessesReady(false);
      setCurrentTab(2);
    },
    onCancelled: () => {
      window.dispatchEvent(new Event("tiles-updated"));
    },
  });
  const isBusy = stepRun.isRunning || isRunAllBusy;

  const canRun =
    state.summaryReady &&
    !state.regulationsReady &&
    !isBusy &&
    Boolean(state.selectedModel);

  const handleIdentify = async () => {
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
      setStatus("Vorgaben konnten nicht gestartet werden.");
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
    await handleIdentify();
  };
  const buttonState = getWorkflowStepActionButtonState({
    idleLabel: "Ausführen",
    canRun,
    isManualRunning: stepRun.isRunning,
    isManualCancelling: stepRun.isCancelling,
    isRunAllBusy,
    isRunAllCancelling: runAllCancel.isCancellingRunAll,
    runAllRunId: runAllCancel.runAllRunId,
  });
  const visibleStepRunStatus = stepRun.isRunning ? null : stepRun.statusText;
  const failedStepStatus = getVisibleFailedStepStatus(
    state,
    "regulations",
    state.regulationsReady,
    visibleStepRunStatus
  );

  return (
    <section className="w-full border-b border-white/60 bg-white/80 py-4 backdrop-blur">
      <div className="mx-auto max-w-7xl space-y-4 px-4 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-3">
          <p className="max-w-xl text-xs leading-5 text-slate-600">
            Beim Klick auf &quot;Vorgaben identifizieren&quot; werden die zwei gewählten
            Gesetzestexte analysiert und die relevanten Vorgaben je Normadressat
            ermittelt.
          </p>
          <StepRunButton
            onClick={handleButtonClick}
            disabled={buttonState.disabled}
            className={buttonState.className}
            isRunning={buttonState.isRunning}
          >
            {buttonState.label}
          </StepRunButton>
          <div className="xl:ml-auto">
            <WorkflowControls />
          </div>
        </div>

        {(status || visibleStepRunStatus || failedStepStatus) && (
          <div className="ccc-status-warning whitespace-pre-line rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
            {visibleStepRunStatus || status || failedStepStatus}
          </div>
        )}
      </div>
    </section>
  );
}
