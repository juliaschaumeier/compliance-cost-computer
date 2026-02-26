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

type RunAllStepStartedDetail = {
  key?: string;
};

export function emitRunAllStepStarted(key?: string | null): void {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(
    new CustomEvent<RunAllStepStartedDetail>(RUN_ALL_STEP_STARTED_EVENT, {
      detail: key ? { key } : {},
    })
  );
}

export function emitRunAllStepCleared(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new Event(RUN_ALL_STEP_CLEARED_EVENT));
}

export function useRunAllStepBusy(stepKey: RunAllStepKey): boolean {
  const [isBusy, setIsBusy] = useState(false);

  useEffect(() => {
    const handleStarted = (event: Event) => {
      const detail = (event as CustomEvent<RunAllStepStartedDetail>).detail;
      setIsBusy(detail?.key === stepKey);
    };
    const handleCleared = () => {
      setIsBusy(false);
    };

    window.addEventListener(RUN_ALL_STEP_STARTED_EVENT, handleStarted);
    window.addEventListener(RUN_ALL_STEP_CLEARED_EVENT, handleCleared);
    return () => {
      window.removeEventListener(RUN_ALL_STEP_STARTED_EVENT, handleStarted);
      window.removeEventListener(RUN_ALL_STEP_CLEARED_EVENT, handleCleared);
    };
  }, [stepKey]);

  return isBusy;
}
