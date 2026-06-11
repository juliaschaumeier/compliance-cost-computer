"use client";

import { useEffect, useRef, useState } from "react";

import { apiClient } from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";
import { RunAllStepKey, useRunAllStepRun } from "@/lib/runAllStepEvents";

type UseRunAllStepCancelOptions = {
  stepKey: RunAllStepKey;
  appSessionId: string;
  setStatus: (status: string | null) => void;
  logScope: string;
};

export function useRunAllStepCancel({
  stepKey,
  appSessionId,
  setStatus,
  logScope,
}: UseRunAllStepCancelOptions) {
  const runAllStep = useRunAllStepRun(stepKey);
  const isRunAllBusy = runAllStep.isBusy && runAllStep.runKind === "run_all";
  const [isCancellingRunAll, setIsCancellingRunAll] = useState(false);
  const isCancellingRunAllRef = useRef(false);

  useEffect(() => {
    if (!isRunAllBusy) {
      isCancellingRunAllRef.current = false;
      setIsCancellingRunAll(false);
    }
  }, [isRunAllBusy]);

  const cancelRunAllForStep = async () => {
    if (!runAllStep.runId) {
      setStatus("Lauf konnte nicht abgebrochen werden: Run-ID fehlt.");
      return;
    }
    if (isCancellingRunAllRef.current) {
      return;
    }
    isCancellingRunAllRef.current = true;
    setIsCancellingRunAll(true);
    setStatus("Abbruch angefordert...");
    try {
      await apiClient.cancelRunAll(runAllStep.runId);
    } catch (error) {
      logClientError(logScope, error, {
        appSessionId,
        runId: runAllStep.runId,
      });
      isCancellingRunAllRef.current = false;
      setIsCancellingRunAll(false);
      setStatus("Abbruch konnte nicht angefordert werden.");
    }
  };

  return {
    isRunAllBusy,
    isCancellingRunAll,
    runAllRunId: runAllStep.runId,
    cancelRunAllForStep,
  };
}
