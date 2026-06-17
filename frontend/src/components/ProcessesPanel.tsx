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

export default function ProcessesPanel() {
  const { state, setCurrentTab, setProcessesReady } = useApp();
  const [status, setStatus] = useState<string | null>(null);
  const runAllCancel = useRunAllStepCancel({
    stepKey: "processes",
    appSessionId: state.appSessionId,
    setStatus,
    logScope: "ProcessesPanel.cancelRunAll",
  });
  const isRunAllBusy = runAllCancel.isRunAllBusy;
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
    if (isRunAllBusy) {
      await runAllCancel.cancelRunAllForStep();
      return;
    }
    await handleCompile();
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
    "processes",
    state.processesReady,
    visibleStepRunStatus
  );

  return (
    <section className="w-full border-b border-white/60 bg-white/80 py-4 backdrop-blur">
      <div className="mx-auto max-w-7xl space-y-4 px-4 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-3">
          <p className="max-w-xl text-xs leading-5 text-slate-600">
            Vorgaben, die in der Praxis in einem Zusammenhang erfüllt werden, werden
            zu gemeinsamen Prozessen je Normadressat gebündelt.
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
