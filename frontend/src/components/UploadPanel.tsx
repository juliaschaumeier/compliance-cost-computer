"use client";

import { useCallback, useEffect, useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { ApiClientError, apiClient, buildLlmRequestOptions } from "@/lib/api";
import { formatActionErrorMessage, logClientError } from "@/lib/errorFeedback";
import { useRunAllStepBusy } from "@/lib/runAllStepEvents";

type UploadTarget = "current" | "proposed";

export default function UploadPanel() {
  const {
    state,
    setAvailableRegulations,
    setCurrentTab,
    setSelectedCurrentLaw,
    setSelectedRegulation,
    setProcessesReady,
    setRegulationsReady,
    setSummaryReady,
  } = useApp();
  const [uploadFiles, setUploadFiles] = useState<{
    current: File | null;
    proposed: File | null;
  }>({ current: null, proposed: null });
  const [status, setStatus] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState({
    current: false,
    proposed: false,
  });
  const [showLists, setShowLists] = useState({
    current: false,
    proposed: false,
  });
  const [isSummarizing, setIsSummarizing] = useState(false);
  const isRunAllBusy = useRunAllStepBusy("summary");
  const isBusy = isSummarizing || isRunAllBusy;
  const [conflicts, setConflicts] = useState<{
    current: string | null;
    proposed: string | null;
  }>({ current: null, proposed: null });
  const [renameValues, setRenameValues] = useState({
    current: "",
    proposed: "",
  });

  const clearSelection = (target: UploadTarget) => {
    setUploadFiles((prev) => ({ ...prev, [target]: null }));
    setConflicts((prev) => ({ ...prev, [target]: null }));
    setRenameValues((prev) => ({ ...prev, [target]: "" }));
    setStatus(null);
    setSummaryReady(false);
    setRegulationsReady(false);
    setProcessesReady(false);
    setShowLists((prev) => ({ ...prev, [target]: false }));
    if (target === "current") {
      setSelectedCurrentLaw("");
    } else {
      setSelectedRegulation("");
    }
  };

  const selectFromList = (target: UploadTarget, file: string) => {
    if (target === "current") {
      setSelectedCurrentLaw(file);
    } else {
      setSelectedRegulation(file);
    }
    setUploadFiles((prev) => ({ ...prev, [target]: null }));
    setRenameValues((prev) => ({ ...prev, [target]: "" }));
    setStatus(null);
    setConflicts((prev) => ({ ...prev, [target]: null }));
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

  const summarizeRegulation = async (filename: string, currentLaw: string) => {
    setSummaryReady(false);
    setIsSummarizing(true);
    const llm = buildLlmRequestOptions({
      selectedModel: state.selectedModel,
      availableModels: state.availableModels,
    });
    try {
      await apiClient.summarizeRegulation(filename, {
        currentFilename: currentLaw,
        appSessionId: state.appSessionId,
        model: llm.model,
        provider: llm.provider,
        keys: llm.keys,
      });
      window.dispatchEvent(new Event("tiles-updated"));
      setSummaryReady(true);
      setCurrentTab(1);
    } catch (error) {
      logClientError("UploadPanel.summarizeRegulation", error, {
        appSessionId: state.appSessionId,
        filename,
        currentLaw,
      });
      setStatus(formatActionErrorMessage("Zusammenfassung fehlgeschlagen", error));
      setSummaryReady(false);
    } finally {
      setIsSummarizing(false);
    }
  };

  const handleFileSelection = (target: UploadTarget, file: File | null) => {
    setUploadFiles((prev) => ({ ...prev, [target]: file }));
    setStatus(null);
    setConflicts((prev) => ({ ...prev, [target]: null }));
    setSummaryReady(false);
    setShowLists((prev) => ({ ...prev, [target]: false }));
    if (!file) {
      return;
    }
    setRenameValues((prev) => ({ ...prev, [target]: file.name }));
    if (target === "current") {
      setSelectedCurrentLaw("");
    } else {
      setSelectedRegulation("");
    }
    if (state.availableRegulations.includes(file.name)) {
      setConflicts((prev) => ({ ...prev, [target]: file.name }));
      setStatus(`Datei existiert bereits: ${file.name}`);
    }
  };

  const handleUpload = async (
    target: UploadTarget,
    nameOverride?: string
  ): Promise<string | null> => {
    const uploadFile = uploadFiles[target];
    if (!uploadFile) {
      setStatus("Bitte eine Datei auswählen.");
      return null;
    }
    try {
      const response = await apiClient.uploadRegulation(uploadFile, nameOverride);
      setStatus(null);
      setUploadFiles((prev) => ({ ...prev, [target]: null }));
      setConflicts((prev) => ({ ...prev, [target]: null }));
      setRenameValues((prev) => ({ ...prev, [target]: "" }));
      await loadRegulations();
      if (target === "current") {
        setSelectedCurrentLaw(response.filename);
      } else {
        setSelectedRegulation(response.filename);
      }
      setSummaryReady(false);
      return response.filename;
    } catch (error) {
      logClientError("UploadPanel.handleUpload", error, {
        target,
        fileName: uploadFile.name,
        nameOverride,
      });
      const err = error as ApiClientError;
      const details =
        err.details && typeof err.details === "object"
          ? (err.details as { error?: unknown; filename?: unknown })
          : null;
      if (
        err.status === 409 &&
        details?.error === "exists" &&
        typeof details.filename === "string"
      ) {
        setConflicts((prev) => ({
          ...prev,
          [target]: details.filename,
        }));
        setStatus(`Datei existiert bereits: ${details.filename}`);
        return null;
      }
      setStatus("Upload fehlgeschlagen.");
      return null;
    }
  };

  const handleDrop = (target: UploadTarget, file: File | null) => {
    handleFileSelection(target, file);
  };

  const hasCurrent = Boolean(
    uploadFiles.current || state.selectedCurrentLaw
  );
  const hasProposed = Boolean(
    uploadFiles.proposed || state.selectedRegulation
  );
  const hasConflicts = Boolean(conflicts.current || conflicts.proposed);
  const canStart =
    hasCurrent &&
    hasProposed &&
    !isBusy &&
    !hasConflicts &&
    Boolean(state.selectedModel);

  const getSelectedName = (target: UploadTarget) => {
    const uploadName = uploadFiles[target]?.name;
    if (uploadName) {
      return uploadName;
    }
    return target === "current"
      ? state.selectedCurrentLaw
      : state.selectedRegulation;
  };

  const handleStart = async () => {
    if (!state.selectedModel) {
      setStatus("Bitte zuerst ein Modell auswählen.");
      return;
    }
    if (!canStart) {
      return;
    }
    setStatus(null);
    setSummaryReady(false);
    setIsSummarizing(true);
    const currentName = uploadFiles.current
      ? await handleUpload("current")
      : state.selectedCurrentLaw;
    if (!currentName) {
      setIsSummarizing(false);
      return;
    }
    const proposedName = uploadFiles.proposed
      ? await handleUpload("proposed")
      : state.selectedRegulation;
    if (!proposedName) {
      setIsSummarizing(false);
      return;
    }
    await summarizeRegulation(proposedName, currentName);
  };

  return (
    <section className="w-full border-b border-white/60 bg-white/80 px-6 py-4 backdrop-blur">
      <div className="mx-auto max-w-6xl space-y-4">
        <p className="text-xs text-slate-600">
          Laden Sie die benötigten Dokumente hoch und/oder wählen Sie diese in den Menüs aus.
        </p>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
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
                      um aus hochgeladenen Dateien auszuwählen
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
            {conflicts.current && uploadFiles.current && (
              <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-600">
                <span className="rounded-full bg-amber-100 px-3 py-1 font-semibold text-amber-800">
                  Datei existiert bereits
                </span>
                <button
                  onClick={() => selectFromList("current", conflicts.current!)}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700"
                >
                  Vorhandene Datei verwenden
                </button>
                <input
                  value={renameValues.current}
                  onChange={(event) =>
                    setRenameValues((prev) => ({
                      ...prev,
                      current: event.target.value,
                    }))
                  }
                  className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs"
                  placeholder="Neuer Dateiname"
                />
                <button
                  onClick={() => handleUpload("current", renameValues.current)}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700"
                >
                  Umbenannt hochladen
                </button>
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
            {conflicts.proposed && uploadFiles.proposed && (
              <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-600">
                <span className="rounded-full bg-amber-100 px-3 py-1 font-semibold text-amber-800">
                  Datei existiert bereits
                </span>
                <button
                  onClick={() => selectFromList("proposed", conflicts.proposed!)}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700"
                >
                  Vorhandene Datei verwenden
                </button>
                <input
                  value={renameValues.proposed}
                  onChange={(event) =>
                    setRenameValues((prev) => ({
                      ...prev,
                      proposed: event.target.value,
                    }))
                  }
                  className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs"
                  placeholder="Neuer Dateiname"
                />
                <button
                  onClick={() => handleUpload("proposed", renameValues.proposed)}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700"
                >
                  Umbenannt hochladen
                </button>
              </div>
            )}
          </div>
          <div className="flex items-end justify-start lg:justify-center">
            <button
              onClick={handleStart}
              disabled={!canStart}
              className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                canStart
                  ? "bg-slate-900 text-white"
                  : "cursor-not-allowed bg-slate-200 text-slate-500"
              }`}
            >
              {isBusy ? "Bitte warten..." : "CCC starten"}
            </button>
          </div>
        </div>

        {status && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
            {status}
          </div>
        )}
      </div>
    </section>
  );
}
