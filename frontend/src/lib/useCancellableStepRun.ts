"use client";

import { useEffect, useRef, useState } from "react";

import { apiClient, ApiKeys } from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";
import {
  emitRunAllStepCleared,
  emitRunAllStepStarted,
  type RunAllStepKey,
} from "@/lib/runAllStepEvents";
import { RunAllStatusResponse, SessionStatus } from "@/types";

type UseCancellableStepRunOptions = {
  appSessionId: string;
  stepKey: string;
  stepLabel: string;
  model?: string;
  provider?: string;
  keys?: ApiKeys;
  onFinalStatus?: (status: SessionStatus) => void;
  onStarted?: () => void;
  onCompleted?: (status: RunAllStatusResponse) => void;
  onFailed?: (message: string) => void;
  onCancelled?: () => void;
  logScope: string;
};

type StepRunStartOverrides = {
  currentFilename?: string;
  proposedFilename?: string;
};

function finalMessage(status: RunAllStatusResponse): string {
  const failedStep = status.steps.find((step) => step.status === "failed");
  return (
    failedStep?.message ||
    status.last_error ||
    "Der Schritt konnte nicht vollständig ausgeführt werden."
  );
}

export function useCancellableStepRun({
  appSessionId,
  stepKey,
  stepLabel,
  model,
  provider,
  keys,
  onFinalStatus,
  onStarted,
  onCompleted,
  onFailed,
  onCancelled,
  logScope,
}: UseCancellableStepRunOptions) {
  const [runId, setRunId] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [statusText, setStatusText] = useState<string | null>(null);
  const pollTimerRef = useRef<number | null>(null);

  const clearPoll = () => {
    if (pollTimerRef.current !== null) {
      window.clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  };

  useEffect(() => clearPoll, []);

  const finish = (status: RunAllStatusResponse) => {
    clearPoll();
    emitRunAllStepCleared();
    setRunId(null);
    setIsRunning(false);
    setIsCancelling(false);
    if (status.final_status) {
      onFinalStatus?.(status.final_status);
    }
    if (status.status === "completed" && status.ok !== false) {
      setStatusText(null);
      onCompleted?.(status);
      return;
    }
    if (status.status === "cancelled") {
      setStatusText("Ausführung abgebrochen. Der Schritt wurde nicht abgeschlossen.");
      onCancelled?.();
      return;
    }
    const message = finalMessage(status);
    setStatusText(message);
    onFailed?.(message);
  };

  const loadStatus = async (activeRunId: string) => {
    try {
      const status = await apiClient.getStepRunStatus(activeRunId);
      if (status.final_status) {
        onFinalStatus?.(status.final_status);
      }
      if (status.status === "running") {
        const activeLabel = status.current_label || stepLabel;
        setStatusText(`Läuft: ${activeLabel}`);
        poll(activeRunId);
        return;
      }
      finish(status);
    } catch (error) {
      logClientError(`${logScope}.poll`, error, {
        appSessionId,
        runId: activeRunId,
      });
      clearPoll();
      setRunId(null);
      setIsRunning(false);
      setIsCancelling(false);
      emitRunAllStepCleared();
      setStatusText("Status konnte nicht aktualisiert werden.");
    }
  };

  const poll = (activeRunId: string) => {
    pollTimerRef.current = window.setTimeout(() => {
      void loadStatus(activeRunId);
    }, 500);
  };

  const start = async (overrides: StepRunStartOverrides = {}) => {
    setStatusText(null);
    onStarted?.();
    setIsRunning(true);
    try {
      const response = await apiClient.startStepRun({
        appSessionId,
        stepKey,
        currentFilename: overrides.currentFilename,
        proposedFilename: overrides.proposedFilename,
        model,
        provider,
        keys,
      });
      setRunId(response.run_id);
      setIsCancelling(false);
      setStatusText(`Läuft: ${stepLabel}`);
      emitRunAllStepStarted(
        stepKey as RunAllStepKey,
        response.run_id,
        "step",
        stepLabel
      );
      await loadStatus(response.run_id);
    } catch (error) {
      logClientError(`${logScope}.start`, error, { appSessionId });
      setIsRunning(false);
      setRunId(null);
      setIsCancelling(false);
      emitRunAllStepCleared();
      throw error;
    }
  };

  const cancel = async () => {
    if (!runId || isCancelling) {
      return;
    }
    setIsCancelling(true);
    setStatusText("Abbruch angefordert...");
    try {
      await apiClient.cancelStepRun(runId);
    } catch (error) {
      logClientError(`${logScope}.cancel`, error, { appSessionId, runId });
      setIsCancelling(false);
      setStatusText("Abbruch konnte nicht angefordert werden.");
    }
  };

  return {
    isRunning,
    isCancelling,
    statusText,
    start,
    cancel,
  };
}
