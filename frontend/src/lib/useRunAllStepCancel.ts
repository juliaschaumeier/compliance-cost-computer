"use client";

import { Dispatch, SetStateAction, useEffect, useRef, useState } from "react";

import { apiClient } from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";
import { RunAllStepKey, useRunAllStepRun } from "@/lib/runAllStepEvents";

type UseRunAllStepCancelOptions = {
  stepKey: RunAllStepKey;
  appSessionId: string;
  setStatus: Dispatch<SetStateAction<string | null>>;
  logScope: string;
};

const CANCEL_REQUESTED_STATUS = "Abbruch angefordert...";

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
      setStatus((current) =>
        current === CANCEL_REQUESTED_STATUS ? null : current
      );
    }
  }, [isRunAllBusy, setStatus]);

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
    setStatus(CANCEL_REQUESTED_STATUS);
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
