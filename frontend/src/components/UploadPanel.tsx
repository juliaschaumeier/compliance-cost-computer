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

const LAW_CARD_CLASS =
  "rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-sm";
const LEGISLLM_CARD_CLASS =
  "rounded-2xl border border-slate-300 bg-slate-50 px-4 py-4 shadow-sm lg:mr-4 xl:mr-6";
const LAW_HEADING_CLASS = "text-sm font-semibold text-slate-800";
const LEGISLLM_HEADING_CLASS = "text-sm font-semibold text-slate-800";
const DROP_ZONE_CLASS =
  "relative flex min-h-[64px] flex-1 flex-col items-start justify-center gap-1 rounded-2xl border-2 border-dashed px-4 py-2 text-sm font-semibold text-slate-700 transition";
const DROP_ZONE_IDLE_CLASS = "border-slate-200 bg-white";
const DROP_ZONE_ACTIVE_CLASS = "border-teal-500 bg-teal-50";
const LEGISLLM_DROP_ZONE_IDLE_CLASS = "border-slate-300 bg-white";
const LEGISLLM_DROP_ZONE_ACTIVE_CLASS = "border-slate-500 bg-slate-100";
const DROP_ZONE_HELPER_CLASS = "text-xs font-normal text-slate-500";

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
  const [statusTone, setStatusTone] = useState<"warning" | "success">("warning");
  const [isDragging, setIsDragging] = useState({
    current: false,
    proposed: false,
    legisllm: false,
  });
  const [isImportingLegisLlm, setIsImportingLegisLlm] = useState(false);
  const [showLists, setShowLists] = useState({
    current: false,
    proposed: false,
  });
  const runAllCancel = useRunAllStepCancel({
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
    setStatusTone("warning");
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
    setStatusTone("warning");
    setSummaryReady(false);
    setRegulationsReady(false);
    setProcessesReady(false);
    setShowLists((prev) => ({ ...prev, [target]: false }));
  };

  const loadRegulations = useCallback(async () => {
    try {
      const response = await apiClient.fetchRegulations();
      setAvailableRegulations(response.files);
      if (
        state.selectedCurrentLaw &&
        !response.files.includes(state.selectedCurrentLaw)
      ) {
        setSelectedCurrentLaw("");
      }
      if (
        state.selectedRegulation &&
        !response.files.includes(state.selectedRegulation)
      ) {
        setSelectedRegulation("");
      }
    } catch (error) {
      logClientError("UploadPanel.loadRegulations", error);
      setStatus("Regelungen konnten nicht geladen werden.");
    }
  }, [
    setAvailableRegulations,
    setSelectedCurrentLaw,
    setSelectedRegulation,
    state.selectedCurrentLaw,
    state.selectedRegulation,
  ]);

  useEffect(() => {
    loadRegulations();
  }, [loadRegulations]);

  useEffect(() => {
    setStatus(null);
    setShowLists({ current: false, proposed: false });
    setIsDragging({ current: false, proposed: false, legisllm: false });
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
      setStatusTone("warning");
      setStatus(`Datei existiert bereits: ${file.name}`);
    }
  };

  const handleDrop = (target: UploadTarget, file: File | null) => {
    handleFileSelection(target, file);
  };

  const handleLegisLlmDrop = async (file: File | null) => {
    setStatus(null);
    setShowLists({ current: false, proposed: false });
    if (!file) {
      return;
    }
    setIsImportingLegisLlm(true);
    try {
      const response = await apiClient.importLegisLlmExport(file);
      const refreshed = await apiClient.fetchRegulations();
      setAvailableRegulations(refreshed.files);
      setSelectedCurrentLaw(response.current_filename);
      setSelectedRegulation(response.proposed_filename);
      setPendingCurrentUpload(null);
      setPendingProposedUpload(null);
      setPendingCurrentUploadName("");
      setPendingProposedUploadName("");
      setSummaryReady(false);
      setRegulationsReady(false);
      setProcessesReady(false);
      setStatusTone("success");
      setStatus(response.message);
    } catch (error) {
      logClientError("UploadPanel.handleLegisLlmDrop", error, {
        appSessionId: state.appSessionId,
      });
      setStatus(formatSessionStartError(error));
      setStatusTone("warning");
    } finally {
      setIsImportingLegisLlm(false);
    }
  };

  const updatePendingUploadName = (target: UploadTarget, value: string) => {
    setStatus(null);
    setStatusTone("warning");
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
    hasProposed &&
    !isBusy &&
    !isImportingLegisLlm &&
    !hasConflicts &&
    Boolean(state.selectedModel);

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
    setStatusTone("warning");
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
      setStatusTone("warning");
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
    {
      activeStatusText: visibleStepRunStatus,
      isStepActive: stepRun.isRunning || isRunAllBusy,
    }
  );
  const displayedStatus = visibleStepRunStatus || status || failedStepStatus;
  const displayedStatusTone =
    status && displayedStatus === status ? statusTone : "warning";

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

        <div
          data-testid="law-selection-grid"
          className={
            isBusy ? "hidden" : "grid grid-cols-1 gap-4 lg:grid-cols-[220px_minmax(0,1fr)_minmax(0,1fr)]"
          }
        >
          <div className={LEGISLLM_CARD_CLASS}>
            <h3 className={LEGISLLM_HEADING_CLASS}>LegisLLM Import</h3>
            <div className="mt-3">
              <div
                onDragEnter={() =>
                  setIsDragging((prev) => ({ ...prev, legisllm: true }))
                }
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={() =>
                  setIsDragging((prev) => ({ ...prev, legisllm: false }))
                }
                onDrop={(event) => {
                  event.preventDefault();
                  setIsDragging((prev) => ({ ...prev, legisllm: false }));
                  const droppedFile = event.dataTransfer.files?.[0] || null;
                  void handleLegisLlmDrop(droppedFile);
                }}
                className={`${DROP_ZONE_CLASS} cursor-default ${
                  isDragging.legisllm
                    ? LEGISLLM_DROP_ZONE_ACTIVE_CLASS
                    : LEGISLLM_DROP_ZONE_IDLE_CLASS
                }`}
              >
                {isImportingLegisLlm ? (
                  <span className="pointer-events-none">Importiere...</span>
                ) : (
                  <div className="pointer-events-none">
                    <span>Exportiertes JSON</span>
                    <span className={`block ${DROP_ZONE_HELPER_CLASS}`}>
                      hierher ziehen
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className={LAW_CARD_CLASS}>
            <h3 className={LAW_HEADING_CLASS}>Gültiges Gesetz</h3>
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
                className={`${DROP_ZONE_CLASS} cursor-pointer ${
                  isDragging.current
                    ? DROP_ZONE_ACTIVE_CLASS
                    : DROP_ZONE_IDLE_CLASS
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
                  <span className="pointer-events-none break-words pr-7 text-xs font-normal text-slate-500">
                    Ausgewählt: {getSelectedName("current")}
                  </span>
                ) : (
                  <div className="pointer-events-none">
                    <span>Datei hierher ziehen oder klicken</span>
                    <span className={`block ${DROP_ZONE_HELPER_CLASS}`}>
                      um aus hochgeladenen Dateien auszuwählen
                    </span>
                  </div>
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

          <div className={LAW_CARD_CLASS}>
            <h3 className={LAW_HEADING_CLASS}>Gesetzesvorschlag</h3>
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
                className={`${DROP_ZONE_CLASS} cursor-pointer ${
                  isDragging.proposed
                    ? DROP_ZONE_ACTIVE_CLASS
                    : DROP_ZONE_IDLE_CLASS
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
                  <span className="pointer-events-none break-words pr-7 text-xs font-normal text-slate-500">
                    Ausgewählt: {getSelectedName("proposed")}
                  </span>
                ) : (
                  <div className="pointer-events-none">
                    <span>Datei hierher ziehen oder klicken</span>
                    <span className={`block ${DROP_ZONE_HELPER_CLASS}`}>
                      um aus hochgeladenen Dateien auszuwählen
                    </span>
                  </div>
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

        {displayedStatus && (
          <div
            className={`whitespace-pre-line rounded-xl border px-3 py-2 text-xs font-semibold ${
              displayedStatusTone === "success"
                ? "ccc-status-success border-teal-700 bg-teal-50 text-teal-800"
                : "ccc-status-warning border-amber-200 bg-amber-50 text-amber-800"
            }`}
          >
            {displayedStatus}
          </div>
        )}
      </div>
    </section>
  );
}
