"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { apiClient, buildLlmRequestOptions } from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";
import { getVisibleFailedStepStatus } from "@/lib/sessionStatus";
import StepRunButton from "@/components/StepRunButton";
import {
  formatSessionStartError,
  logSessionStartError,
  prepareSessionDocuments,
} from "@/lib/sessionStart";
import { useCancellableStepRun } from "@/lib/useCancellableStepRun";
import { useRunAllStepCancel } from "@/lib/useRunAllStepCancel";
import { getWorkflowStepActionButtonState } from "@/lib/workflowStepActionButton";

type UploadTarget = "current" | "proposed";

export default function UploadPanel() {
  const {
    state,
    setAvailableRegulations,
    setCurrentTab,
    setSelectedCurrentLaw,
    setSelectedRegulation,
    setPendingCurrentUpload,
    setPendingProposedUpload,
    setPendingCurrentUploadName,
    setPendingProposedUploadName,
    setProcessesReady,
    setRegulationsReady,
    setSummaryReady,
    setLastFailedStep,
    setLastFailedLabel,
    setLastFailedMessage,
  } = useApp();
  const [status, setStatus] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState({
    current: false,
    proposed: false,
  });
  const [showLists, setShowLists] = useState({
    current: false,
    proposed: false,
  });
  const runAllCancel = useRunAllStepCancel({
    stepKey: "summary",
    appSessionId: state.appSessionId,
    setStatus,
    logScope: "UploadPanel.cancelRunAll",
  });
  const isRunAllBusy = runAllCancel.isRunAllBusy;
  const llm = buildLlmRequestOptions({
    selectedModel: state.selectedModel,
    availableModels: state.availableModels,
  });
  const stepRun = useCancellableStepRun({
    appSessionId: state.appSessionId,
    stepKey: "summary",
    stepLabel: "CCC starten",
    model: llm.model,
    provider: llm.provider,
    keys: llm.keys,
    logScope: "UploadPanel.startSummary",
    onCompleted: () => {
      window.dispatchEvent(new Event("tiles-updated"));
      setSummaryReady(true);
      setRegulationsReady(false);
      setProcessesReady(false);
      setCurrentTab(1);
    },
    onCancelled: () => {
      window.dispatchEvent(new Event("tiles-updated"));
      setSummaryReady(false);
    },
  });
  const isBusy = stepRun.isRunning || isRunAllBusy;

  const pendingUploads = useMemo(
    () => ({
      current: {
        file: state.pendingCurrentUpload,
        desiredName: state.pendingCurrentUploadName,
      },
      proposed: {
        file: state.pendingProposedUpload,
        desiredName: state.pendingProposedUploadName,
      },
    }),
    [
      state.pendingCurrentUpload,
      state.pendingCurrentUploadName,
      state.pendingProposedUpload,
      state.pendingProposedUploadName,
    ]
  );

  const conflicts = useMemo(
    () => ({
      current:
        pendingUploads.current.file &&
        pendingUploads.current.desiredName &&
        state.availableRegulations.includes(pendingUploads.current.desiredName)
          ? pendingUploads.current.desiredName
          : null,
      proposed:
        pendingUploads.proposed.file &&
        pendingUploads.proposed.desiredName &&
        state.availableRegulations.includes(pendingUploads.proposed.desiredName)
          ? pendingUploads.proposed.desiredName
          : null,
    }),
    [pendingUploads, state.availableRegulations]
  );

  const clearSelection = (target: UploadTarget) => {
    if (target === "current") {
      setPendingCurrentUpload(null);
      setPendingCurrentUploadName("");
      setSelectedCurrentLaw("");
    } else {
      setPendingProposedUpload(null);
      setPendingProposedUploadName("");
      setSelectedRegulation("");
    }
    setStatus(null);
    setSummaryReady(false);
    setRegulationsReady(false);
    setProcessesReady(false);
    setShowLists((prev) => ({ ...prev, [target]: false }));
  };

  const selectFromList = (target: UploadTarget, file: string) => {
    if (target === "current") {
      setSelectedCurrentLaw(file);
      setPendingCurrentUpload(null);
      setPendingCurrentUploadName("");
    } else {
      setSelectedRegulation(file);
      setPendingProposedUpload(null);
      setPendingProposedUploadName("");
    }
    setStatus(null);
    setSummaryReady(false);
    setRegulationsReady(false);
    setProcessesReady(false);
    setShowLists((prev) => ({ ...prev, [target]: false }));
  };

  const loadRegulations = useCallback(async () => {
    try {
      const response = await apiClient.fetchRegulations();
      setAvailableRegulations(response.files);
    } catch (error) {
      logClientError("UploadPanel.loadRegulations", error);
      setStatus("Regelungen konnten nicht geladen werden.");
    }
  }, [setAvailableRegulations]);

  useEffect(() => {
    loadRegulations();
  }, [loadRegulations]);

  useEffect(() => {
    setStatus(null);
    setShowLists({ current: false, proposed: false });
    setIsDragging({ current: false, proposed: false });
  }, [state.appSessionId]);

  const handleFileSelection = (target: UploadTarget, file: File | null) => {
    setStatus(null);
    setSummaryReady(false);
    setShowLists((prev) => ({ ...prev, [target]: false }));
    if (target === "current") {
      setPendingCurrentUpload(file);
      if (file) {
        setPendingCurrentUploadName(file.name);
      }
      setSelectedCurrentLaw("");
    } else {
      setPendingProposedUpload(file);
      if (file) {
        setPendingProposedUploadName(file.name);
      }
      setSelectedRegulation("");
    }
    if (file && state.availableRegulations.includes(file.name)) {
      setStatus(`Datei existiert bereits: ${file.name}`);
    }
  };

  const handleDrop = (target: UploadTarget, file: File | null) => {
    handleFileSelection(target, file);
  };

  const updatePendingUploadName = (target: UploadTarget, value: string) => {
    setStatus(null);
    if (target === "current") {
      setPendingCurrentUploadName(value);
    } else {
      setPendingProposedUploadName(value);
    }
  };

  const hasProposed = Boolean(
    pendingUploads.proposed.file || state.selectedRegulation
  );
  const hasConflicts = Boolean(conflicts.current || conflicts.proposed);
  const canStart =
    hasProposed && !isBusy && !hasConflicts && Boolean(state.selectedModel);

  const getSelectedName = (target: UploadTarget) => {
    const upload = target === "current" ? pendingUploads.current : pendingUploads.proposed;
    if (upload.file) {
      return upload.desiredName || upload.file.name;
    }
    return target === "current"
      ? state.selectedCurrentLaw
      : state.selectedRegulation;
  };

  const handleStart = async () => {
    if (!canStart) {
      return;
    }
    setStatus(null);
    setLastFailedStep(null);
    setLastFailedLabel(null);
    setLastFailedMessage(null);
    setSummaryReady(false);
    try {
      const { currentFilename, proposedFilename } = await prepareSessionDocuments({
        appSessionId: state.appSessionId,
        selectedModel: state.selectedModel,
        availableModels: state.availableModels,
        availableRegulations: state.availableRegulations,
        selectedCurrentLaw: state.selectedCurrentLaw,
        selectedRegulation: state.selectedRegulation,
        pendingCurrent: pendingUploads.current,
        pendingProposed: pendingUploads.proposed,
        setSelectedCurrentLaw,
        setSelectedRegulation,
        setPendingCurrentUpload,
        setPendingProposedUpload,
        setPendingCurrentUploadName,
        setPendingProposedUploadName,
        setAvailableRegulations,
      });
      await stepRun.start({ currentFilename, proposedFilename });
    } catch (error) {
      logSessionStartError("UploadPanel.handleStart", error, {
        appSessionId: state.appSessionId,
      });
      setStatus(formatSessionStartError(error));
      setSummaryReady(false);
    }
  };

  const handleStartButton = async () => {
    if (stepRun.isRunning) {
      await stepRun.cancel();
      return;
    }
    if (isRunAllBusy) {
      await runAllCancel.cancelRunAllForStep();
      return;
    }
    await handleStart();
  };

  const startButtonState = getWorkflowStepActionButtonState({
    idleLabel: "CCC starten",
    canRun: canStart,
    isManualRunning: stepRun.isRunning,
    isManualCancelling: stepRun.isCancelling,
    isRunAllBusy,
    isRunAllCancelling: runAllCancel.isCancellingRunAll,
    runAllRunId: runAllCancel.runAllRunId,
  });
  const visibleStepRunStatus = stepRun.isRunning ? null : stepRun.statusText;
  const failedStepStatus = getVisibleFailedStepStatus(
    state,
    "summary",
    state.summaryReady,
    visibleStepRunStatus
  );

  return (
    <section className="w-full border-b border-white/60 bg-white/80 py-4 backdrop-blur">
      <div className="mx-auto max-w-7xl space-y-4 px-4 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-3">
          <p className="max-w-xl text-xs leading-5 text-slate-600">
            Wählen Sie das gültige Gesetz und den Gesetzesvorschlag aus oder
            laden Sie die benötigten Dokumente hoch.
          </p>
          <StepRunButton
            onClick={handleStartButton}
            disabled={startButtonState.disabled}
            className={startButtonState.className}
            isRunning={startButtonState.isRunning}
          >
            {startButtonState.label}
          </StepRunButton>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-800">
              Gültiges Gesetz
            </h3>
            <div className="mt-3">
              <div
                onClick={() =>
                  setShowLists((prev) => ({
                    current: !prev.current,
                    proposed: false,
                  }))
                }
                onDragEnter={() =>
                  setIsDragging((prev) => ({ ...prev, current: true }))
                }
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={() =>
                  setIsDragging((prev) => ({ ...prev, current: false }))
                }
                onDrop={(event) => {
                  event.preventDefault();
                  setIsDragging((prev) => ({ ...prev, current: false }));
                  const droppedFile = event.dataTransfer.files?.[0] || null;
                  handleDrop("current", droppedFile);
                }}
                className={`relative flex min-h-[64px] flex-1 cursor-pointer flex-col items-start justify-center gap-1 rounded-2xl border-2 border-dashed px-4 py-2 text-sm font-semibold text-slate-700 transition ${
                  isDragging.current
                    ? "border-teal-500 bg-teal-50"
                    : "border-slate-200 bg-white"
                }`}
              >
                {getSelectedName("current") && (
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      clearSelection("current");
                    }}
                    className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full border border-slate-200 bg-white text-[10px] font-semibold text-slate-500 shadow-sm transition hover:text-slate-700"
                    aria-label="Auswahl entfernen"
                  >
                    ×
                  </button>
                )}
                {getSelectedName("current") ? (
                  <span className="text-xs font-normal text-slate-500">
                    Ausgewählt: {getSelectedName("current")}
                  </span>
                ) : (
                  <>
                    <span>Datei hierher ziehen oder klicken</span>
                    <span className="text-xs font-normal text-slate-500">
                      optional: aus hochgeladenen Dateien auswählen
                    </span>
                  </>
                )}
              </div>
              {showLists.current && (
                <div className="mt-3 max-h-44 overflow-auto rounded-xl border border-slate-200 bg-slate-50 p-2 text-xs text-slate-600">
                  {state.availableRegulations.length === 0 ? (
                    <div className="px-2 py-2 text-slate-500">
                      Keine Dateien hochgeladen.
                    </div>
                  ) : (
                    state.availableRegulations.map((file) => (
                      <button
                        key={file}
                        onClick={() => selectFromList("current", file)}
                        className="flex w-full items-center justify-between rounded-lg px-2 py-1 text-left hover:bg-white"
                      >
                        <span className="truncate">{file}</span>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
            {conflicts.current && pendingUploads.current.file && (
              <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-600">
                <span className="ccc-status-warning rounded-full bg-amber-100 px-3 py-1 font-semibold text-amber-800">
                  Datei existiert bereits
                </span>
                <button
                  onClick={() => selectFromList("current", conflicts.current!)}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700"
                >
                  Vorhandene Datei verwenden
                </button>
                <input
                  value={state.pendingCurrentUploadName}
                  onChange={(event) =>
                    updatePendingUploadName("current", event.target.value)
                  }
                  className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs"
                  placeholder="Neuer Dateiname"
                />
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-800">
              Gesetzesvorschlag
            </h3>
            <div className="mt-3">
              <div
                onClick={() =>
                  setShowLists((prev) => ({
                    current: false,
                    proposed: !prev.proposed,
                  }))
                }
                onDragEnter={() =>
                  setIsDragging((prev) => ({ ...prev, proposed: true }))
                }
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={() =>
                  setIsDragging((prev) => ({ ...prev, proposed: false }))
                }
                onDrop={(event) => {
                  event.preventDefault();
                  setIsDragging((prev) => ({ ...prev, proposed: false }));
                  const droppedFile = event.dataTransfer.files?.[0] || null;
                  handleDrop("proposed", droppedFile);
                }}
                className={`relative flex min-h-[64px] flex-1 cursor-pointer flex-col items-start justify-center gap-1 rounded-2xl border-2 border-dashed px-4 py-2 text-sm font-semibold text-slate-700 transition ${
                  isDragging.proposed
                    ? "border-teal-500 bg-teal-50"
                    : "border-slate-200 bg-white"
                }`}
              >
                {getSelectedName("proposed") && (
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      clearSelection("proposed");
                    }}
                    className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full border border-slate-200 bg-white text-[10px] font-semibold text-slate-500 shadow-sm transition hover:text-slate-700"
                    aria-label="Auswahl entfernen"
                  >
                    ×
                  </button>
                )}
                {getSelectedName("proposed") ? (
                  <span className="text-xs font-normal text-slate-500">
                    Ausgewählt: {getSelectedName("proposed")}
                  </span>
                ) : (
                  <>
                    <span>Datei hierher ziehen oder klicken</span>
                    <span className="text-xs font-normal text-slate-500">
                      um aus hochgeladenen Dateien auszuwählen
                    </span>
                  </>
                )}
              </div>
              {showLists.proposed && (
                <div className="mt-3 max-h-44 overflow-auto rounded-xl border border-slate-200 bg-slate-50 p-2 text-xs text-slate-600">
                  {state.availableRegulations.length === 0 ? (
                    <div className="px-2 py-2 text-slate-500">
                      Keine Dateien hochgeladen.
                    </div>
                  ) : (
                    state.availableRegulations.map((file) => (
                      <button
                        key={file}
                        onClick={() => selectFromList("proposed", file)}
                        className="flex w-full items-center justify-between rounded-lg px-2 py-1 text-left hover:bg-white"
                      >
                        <span className="truncate">{file}</span>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
            {conflicts.proposed && pendingUploads.proposed.file && (
              <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-600">
                <span className="ccc-status-warning rounded-full bg-amber-100 px-3 py-1 font-semibold text-amber-800">
                  Datei existiert bereits
                </span>
                <button
                  onClick={() => selectFromList("proposed", conflicts.proposed!)}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700"
                >
                  Vorhandene Datei verwenden
                </button>
                <input
                  value={state.pendingProposedUploadName}
                  onChange={(event) =>
                    updatePendingUploadName("proposed", event.target.value)
                  }
                  className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs"
                  placeholder="Neuer Dateiname"
                />
              </div>
            )}
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
