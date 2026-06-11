"use client";

import { useEffect, useState } from "react";

export type RunAllStepKey =
  | "summary"
  | "regulations"
  | "processes"
  | "case_groups"
  | "process_steps"
  | "effort"
  | "total_cost";

export const RUN_ALL_STEP_STARTED_EVENT = "run-all-step-started";
export const RUN_ALL_STEP_CLEARED_EVENT = "run-all-step-cleared";
export type WorkflowRunKind = "run_all" | "step";

let currentRunAllStepKey: string | null = null;
let currentRunAllRunId: string | null = null;
let currentWorkflowRunKind: WorkflowRunKind | null = null;
let currentWorkflowRunLabel: string | null = null;

type RunAllStepStartedDetail = {
  key?: string;
  runId?: string;
  runKind?: WorkflowRunKind;
  label?: string;
};

export function emitRunAllStepStarted(
  key?: string | null,
  runId?: string | null,
  runKind: WorkflowRunKind = "run_all",
  label?: string | null
): void {
  if (typeof window === "undefined") {
    return;
  }
  currentRunAllStepKey = key ? String(key) : null;
  currentRunAllRunId = runId ? String(runId) : null;
  currentWorkflowRunKind = runKind;
  currentWorkflowRunLabel = label ? String(label) : null;
  window.dispatchEvent(
    new CustomEvent<RunAllStepStartedDetail>(RUN_ALL_STEP_STARTED_EVENT, {
      detail: {
        ...(key ? { key } : {}),
        ...(runId ? { runId } : {}),
        runKind,
        ...(label ? { label } : {}),
      },
    })
  );
}

export function emitRunAllStepCleared(): void {
  if (typeof window === "undefined") {
    return;
  }
  currentRunAllStepKey = null;
  currentRunAllRunId = null;
  currentWorkflowRunKind = null;
  currentWorkflowRunLabel = null;
  window.dispatchEvent(new Event(RUN_ALL_STEP_CLEARED_EVENT));
}

export type WorkflowRunState = {
  isActive: boolean;
  stepKey: string | null;
  runId: string | null;
  runKind: WorkflowRunKind | null;
  label: string | null;
};

export function useRunAllStepRun(stepKey: RunAllStepKey): {
  isBusy: boolean;
  runId: string | null;
  runKind: WorkflowRunKind | null;
} {
  const [state, setState] = useState({
    isBusy: currentRunAllStepKey === stepKey,
    runId: currentRunAllStepKey === stepKey ? currentRunAllRunId : null,
    runKind: currentRunAllStepKey === stepKey ? currentWorkflowRunKind : null,
  });

  useEffect(() => {
    setState({
      isBusy: currentRunAllStepKey === stepKey,
      runId: currentRunAllStepKey === stepKey ? currentRunAllRunId : null,
      runKind: currentRunAllStepKey === stepKey ? currentWorkflowRunKind : null,
    });
    const handleStarted = (event: Event) => {
      const detail = (event as CustomEvent<RunAllStepStartedDetail>).detail;
      setState({
        isBusy: detail?.key === stepKey,
        runId: detail?.key === stepKey ? detail?.runId ?? null : null,
        runKind: detail?.key === stepKey ? detail?.runKind ?? null : null,
      });
    };
    const handleCleared = () => {
      setState({ isBusy: false, runId: null, runKind: null });
    };

    window.addEventListener(RUN_ALL_STEP_STARTED_EVENT, handleStarted);
    window.addEventListener(RUN_ALL_STEP_CLEARED_EVENT, handleCleared);
    return () => {
      window.removeEventListener(RUN_ALL_STEP_STARTED_EVENT, handleStarted);
      window.removeEventListener(RUN_ALL_STEP_CLEARED_EVENT, handleCleared);
    };
  }, [stepKey]);

  return state;
}

export function useRunAllStepBusy(stepKey: RunAllStepKey): boolean {
  return useRunAllStepRun(stepKey).isBusy;
}

export function useActiveWorkflowRun(): WorkflowRunState {
  const [state, setState] = useState<WorkflowRunState>({
    isActive: Boolean(currentRunAllRunId),
    stepKey: currentRunAllStepKey,
    runId: currentRunAllRunId,
    runKind: currentWorkflowRunKind,
    label: currentWorkflowRunLabel,
  });

  useEffect(() => {
    setState({
      isActive: Boolean(currentRunAllRunId),
      stepKey: currentRunAllStepKey,
      runId: currentRunAllRunId,
      runKind: currentWorkflowRunKind,
      label: currentWorkflowRunLabel,
    });
    const handleStarted = (event: Event) => {
      const detail = (event as CustomEvent<RunAllStepStartedDetail>).detail;
      setState({
        isActive: Boolean(detail?.runId),
        stepKey: detail?.key ?? null,
        runId: detail?.runId ?? null,
        runKind: detail?.runKind ?? null,
        label: detail?.label ?? null,
      });
    };
    const handleCleared = () => {
      setState({
        isActive: false,
        stepKey: null,
        runId: null,
        runKind: null,
        label: null,
      });
    };

    window.addEventListener(RUN_ALL_STEP_STARTED_EVENT, handleStarted);
    window.addEventListener(RUN_ALL_STEP_CLEARED_EVENT, handleCleared);
    return () => {
      window.removeEventListener(RUN_ALL_STEP_STARTED_EVENT, handleStarted);
      window.removeEventListener(RUN_ALL_STEP_CLEARED_EVENT, handleCleared);
    };
  }, []);

  return state;
}
