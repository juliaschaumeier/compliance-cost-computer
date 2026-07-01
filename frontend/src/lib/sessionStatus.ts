export type SessionStatusFlags = {
  summary_ready: boolean;
  regulations_ready: boolean;
  processes_ready: boolean;
  case_groups_ready: boolean;
  process_steps_ready: boolean;
  effort_ready: boolean;
  total_cost_ready: boolean;
};

export type FailedStepStatusSource = {
  lastFailedStep?: string | null;
  lastFailedMessage?: string | null;
};

export function deriveTabFromStatus(status: SessionStatusFlags): number {
  if (!status.summary_ready) return 0;
  if (!status.regulations_ready) return 1;
  if (!status.processes_ready) return 2;
  if (!status.case_groups_ready) return 3;
  if (!status.process_steps_ready) return 4;
  if (!status.effort_ready) return 5;
  return 6;
}

export function getVisibleFailedStepStatus(
  status: FailedStepStatusSource,
  stepKey: string,
  isStepReady: boolean,
  options: {
    activeStatusText?: string | null;
    isStepActive?: boolean;
  } = {}
): string | null {
  if (
    options.isStepActive ||
    options.activeStatusText ||
    isStepReady ||
    status.lastFailedStep !== stepKey
  ) {
    return null;
  }
  return status.lastFailedMessage || null;
}
