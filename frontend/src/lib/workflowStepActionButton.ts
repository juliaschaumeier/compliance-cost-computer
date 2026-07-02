type WorkflowStepActionButtonOptions = {
  idleLabel: string;
  canRun: boolean;
  isManualRunning?: boolean;
  isManualCancelling?: boolean;
  manualRunningLabel?: string;
  canCancelManualRun?: boolean;
  isRunAllBusy?: boolean;
  isRunAllCancelling?: boolean;
  runAllRunId?: string | null;
};

type WorkflowStepActionButtonState = {
  label: string;
  className: string;
  disabled: boolean;
  isRunning: boolean;
};

const runningClass =
  "border border-slate-300 bg-slate-50 text-slate-700 hover:bg-slate-100";
const cancellingClass =
  "cursor-not-allowed border border-slate-200 bg-slate-100 text-slate-400";
const enabledClass = "bg-slate-800 text-white";
const disabledClass = "cursor-not-allowed bg-slate-200 text-slate-500";

export function getWorkflowStepActionButtonState({
  idleLabel,
  canRun,
  isManualRunning = false,
  isManualCancelling = false,
  manualRunningLabel = "Abbrechen",
  canCancelManualRun = true,
  isRunAllBusy = false,
  isRunAllCancelling = false,
  runAllRunId = null,
}: WorkflowStepActionButtonOptions): WorkflowStepActionButtonState {
  const isRunning = isManualRunning || isRunAllBusy;
  const isCancelling = isManualCancelling || isRunAllCancelling;
  const label = isManualRunning
    ? isManualCancelling
      ? "Abbruch wird ausgeführt..."
      : manualRunningLabel
    : isRunAllBusy
      ? isRunAllCancelling
        ? "Abbruch wird ausgeführt..."
        : "Abbrechen"
      : idleLabel;

  const disabled =
    isManualCancelling ||
    isRunAllCancelling ||
    (isManualRunning && !canCancelManualRun) ||
    (isRunAllBusy ? !runAllRunId : !isManualRunning && !canRun);

  const className = isRunning
    ? isCancelling || (isManualRunning && !canCancelManualRun)
      ? cancellingClass
      : runningClass
    : canRun
      ? enabledClass
      : disabledClass;

  return {
    label,
    className,
    disabled,
    isRunning,
  };
}
