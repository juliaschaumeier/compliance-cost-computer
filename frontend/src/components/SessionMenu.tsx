"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { useApp } from "@/contexts/AppContext";
import {
  apiClient,
  buildLlmRequestOptions,
  type ApiClientError,
} from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";
import {
  emitRunAllStepCleared,
  emitRunAllStepStarted,
  type RunAllStepKey,
} from "@/lib/runAllStepEvents";
import { deriveTabFromStatus } from "@/lib/sessionStatus";
import { SessionStatus, SessionSummary } from "@/types";

type SessionMenuProps = {
  compact?: boolean;
};

type SessionStepResult = { status: string; message?: string };
type RunStepStartedEvent = { key?: string; label?: string };
type RunStepStatusEvent = { session_status?: SessionStatus };
type RunCompletedEvent = { final_status?: SessionStatus; ok?: boolean };
type RunFailedEvent = {
  final_status?: SessionStatus;
  message?: string;
  steps?: SessionStepResult[];
};
type RunCancelledEvent = { final_status?: SessionStatus; message?: string };

function deriveRunAllStepKeyFromStatus(
  sessionStatus: SessionStatus | undefined
): RunAllStepKey | null {
  if (!sessionStatus) {
    return null;
  }
  if (!sessionStatus.summary_ready) return "summary";
  if (!sessionStatus.regulations_ready) return "regulations";
  if (!sessionStatus.processes_ready) return "processes";
  if (!sessionStatus.case_groups_ready) return "case_groups";
  if (!sessionStatus.process_steps_ready) return "process_steps";
  if (!sessionStatus.effort_ready) return "effort";
  if (!sessionStatus.total_cost_ready) return "total_cost";
  return null;
}

export default function SessionMenu({ compact }: SessionMenuProps) {
  const {
    state,
    setCurrentTab,
    setAppSessionId,
    setSummaryReady,
    setRegulationsReady,
    setLastCompletedStep,
    setLastCompletedLabel,
  } = useApp();
  const [isOpen, setIsOpen] = useState(false);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedSession, setSelectedSession] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [isUndoing, setIsUndoing] = useState(false);
  const [isRunningAll, setIsRunningAll] = useState(false);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [isCancellingRun, setIsCancellingRun] = useState(false);
  const runEventSourceRef = useRef<EventSource | null>(null);
  const runPollTimerRef = useRef<number | null>(null);
  const [isMounted, setIsMounted] = useState(false);
  const triggerRef = useRef<HTMLDivElement | null>(null);
  const [menuPos, setMenuPos] = useState<{ top: number; left: number }>({
    top: 96,
    left: 16,
  });

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    return () => {
      if (runEventSourceRef.current) {
        runEventSourceRef.current.close();
        runEventSourceRef.current = null;
      }
      if (runPollTimerRef.current !== null) {
        window.clearTimeout(runPollTimerRef.current);
        runPollTimerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    let cancelled = false;
    const loadSessions = async () => {
      try {
        const payload = await apiClient.listSessions(50);
        if (!cancelled) {
          setSessions(payload.sessions);
        }
      } catch (error) {
        logClientError("SessionMenu.loadSessions", error);
        if (!cancelled) {
          setSessions([]);
        }
      }
    };
    loadSessions();
    return () => {
      cancelled = true;
    };
  }, [isOpen]);

  const formattedSessions = useMemo(() => {
    return sessions.map((session) => {
      const date = new Date(session.created_at);
      const label = Number.isNaN(date.getTime())
        ? session.created_at
        : date.toLocaleString("de-DE", {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
          });
      const usedModels = (session.used_llm_models || "").trim();
      return {
        ...session,
        label: usedModels
          ? `${session.app_session_id} · ${label} · ${usedModels}`
          : `${session.app_session_id} · ${label}`,
      };
    });
  }, [sessions]);

  const resetStatus = () => setStatus(null);
  const getErrorStatus = (error: unknown): number | undefined => {
    const status = (error as ApiClientError)?.status;
    return typeof status === "number" ? status : undefined;
  };
  const getRunStatusErrorMessage = (error: unknown): string => {
    const err = error as ApiClientError;
    const rawMessage =
      typeof err?.message === "string" ? err.message.trim() : "";
    const lower = rawMessage.toLowerCase();
    const status = getErrorStatus(error);

    if (lower.includes("failed to fetch")) {
      return "Backend ist nicht erreichbar. Bitte Backend prüfen und erneut versuchen.";
    }
    if (status) {
      return `Status der Schritte konnte nicht aktualisiert werden (HTTP ${status}).`;
    }
    if (rawMessage && rawMessage !== "Failed to load run-all status") {
      return `Status der Schritte konnte nicht aktualisiert werden: ${rawMessage}`;
    }
    return "Status der Schritte konnte nicht aktualisiert werden.";
  };

  const lastStepLabel = state.lastCompletedLabel;

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const updatePosition = () => {
      const width = 320;
      const padding = 16;
      if (!triggerRef.current) {
        setMenuPos({ top: 96, left: padding });
        return;
      }
      const rect = triggerRef.current.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) {
        setMenuPos({ top: 96, left: padding });
        return;
      }
      let left = rect.right - width;
      if (left < padding) {
        left = padding;
      }
      if (left + width > window.innerWidth - padding) {
        left = window.innerWidth - padding - width;
      }
      const top = rect.bottom + 8;
      setMenuPos({ top, left });
    };
    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [isOpen]);

  const handleRebuildCurrent = async () => {
    try {
      resetStatus();
      await apiClient.rebuildTiles(state.appSessionId);
      window.dispatchEvent(new Event("tiles-updated"));
      setStatus("Tiles der Session wurden neu geladen.");
    } catch (error) {
      logClientError("SessionMenu.rebuildTiles", error, {
        appSessionId: state.appSessionId,
      });
      setStatus("Tiles konnten nicht neu geladen werden.");
    }
  };

  const handleNewSession = () => {
    sessionStorage.clear();
    window.location.reload();
  };

  const handleLoadSession = async () => {
    if (!selectedSession) {
      setStatus("Bitte eine Session auswählen.");
      return;
    }
    try {
      resetStatus();
      const sessionStatus = await apiClient.getSessionStatus(selectedSession);
      setAppSessionId(selectedSession);
      applySessionStatus(sessionStatus);
      await apiClient.rebuildTiles(selectedSession);
      setIsOpen(false);
    } catch (error) {
      logClientError("SessionMenu.loadSession", error, {
        selectedSession,
      });
      setStatus("Session konnte nicht geladen werden.");
    }
  };

  const handleUndoLastStep = async () => {
    if (!lastStepLabel || isUndoing) {
      return;
    }
    try {
      resetStatus();
      setIsUndoing(true);
      const result = await apiClient.undoLastStep(state.appSessionId);
      if (result.status === "no-op") {
        setStatus("Kein Schritt zum Zurücksetzen vorhanden.");
        return;
      }
      await apiClient.rebuildTiles(state.appSessionId);
      window.dispatchEvent(new Event("tiles-updated"));
      setStatus(`Letzter Schritt zurückgesetzt: ${result.undone_label || lastStepLabel}`);
    } catch (error) {
      logClientError("SessionMenu.undoLastStep", error, {
        appSessionId: state.appSessionId,
        lastStepLabel,
      });
      setStatus("Letzter Schritt konnte nicht zurückgesetzt werden.");
    } finally {
      setIsUndoing(false);
    }
  };

  const handleExportSession = async () => {
    try {
      resetStatus();
      const result = await apiClient.exportSession(state.appSessionId);
      const blob = new Blob([result.markdown], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = result.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setStatus("Session exportiert.");
    } catch (error) {
      logClientError("SessionMenu.exportSession", error, {
        appSessionId: state.appSessionId,
      });
      setStatus("Export fehlgeschlagen.");
    }
  };

  const applySessionStatus = (sessionStatus: SessionStatus) => {
    setSummaryReady(sessionStatus.summary_ready);
    setRegulationsReady(sessionStatus.regulations_ready);
    setLastCompletedStep(sessionStatus.last_completed_step ?? null);
    setLastCompletedLabel(sessionStatus.last_completed_label ?? null);
    setCurrentTab(deriveTabFromStatus(sessionStatus));
    window.dispatchEvent(new Event("tiles-updated"));
  };

  const stopRunMonitoring = () => {
    if (runEventSourceRef.current) {
      runEventSourceRef.current.close();
      runEventSourceRef.current = null;
    }
    if (runPollTimerRef.current !== null) {
      window.clearTimeout(runPollTimerRef.current);
      runPollTimerRef.current = null;
    }
  };

  const resetRunUiState = () => {
    setIsRunningAll(false);
    setCurrentRunId(null);
    setIsCancellingRun(false);
    emitRunAllStepCleared();
    stopRunMonitoring();
  };

  const handleMissingRunState = async (runId: string, error: unknown) => {
    logClientError("SessionMenu.missingRunState", error, {
      runId,
      appSessionId: state.appSessionId,
    });
    try {
      const sessionStatus = await apiClient.getSessionStatus(state.appSessionId);
      applySessionStatus(sessionStatus);
    } catch (statusError) {
      logClientError("SessionMenu.refreshStatusAfterMissingRun", statusError, {
        runId,
        appSessionId: state.appSessionId,
      });
    } finally {
      setStatus(
        "Backend-Neustart erkannt. Laufstatus wurde verworfen, bitte erneut starten."
      );
      resetRunUiState();
    }
  };

  const pollRunStatus = (runId: string) => {
    runPollTimerRef.current = window.setTimeout(async () => {
      try {
        const progress = await apiClient.getRunAllStatus(runId);
        if (progress.final_status) {
          applySessionStatus(progress.final_status);
        }
        if (progress.status === "running") {
          pollRunStatus(runId);
          return;
        }
        resetRunUiState();
        if (progress.status === "completed" && progress.ok) {
          setStatus("Alle Schritte wurden ausgeführt.");
        } else if (progress.status === "cancelled") {
          setStatus(
            "Ausführung abgebrochen. Bereits abgeschlossene Schritte bleiben erhalten."
          );
        } else {
          const failedStep = progress.steps.find((step) => step.status === "failed");
          setStatus(
            failedStep?.message ||
              "Schritte konnten nicht vollständig ausgeführt werden."
          );
        }
      } catch (error) {
        if (getErrorStatus(error) === 404) {
          await handleMissingRunState(runId, error);
          return;
        }
        logClientError("SessionMenu.pollRunStatus", error, { runId });
        resetRunUiState();
        setStatus(getRunStatusErrorMessage(error));
      }
    }, 1500);
  };

  const beginRunEventStream = (runId: string) => {
    stopRunMonitoring();
    const source = new EventSource(apiClient.getRunAllEventsUrl(runId));
    runEventSourceRef.current = source;

    source.addEventListener("step_started", (event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data) as RunStepStartedEvent;
        emitRunAllStepStarted(payload.key);
        if (payload.label) {
          setStatus(`Läuft: ${payload.label}`);
        }
      } catch (error) {
        logClientError("SessionMenu.stepStartedEvent", error, { runId });
        // Ignore malformed progress event.
      }
    });

    const applyEventStatus = (event: Event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data) as RunStepStatusEvent;
        if (payload.session_status) {
          applySessionStatus(payload.session_status);
          const inferredStep = deriveRunAllStepKeyFromStatus(payload.session_status);
          if (inferredStep) {
            emitRunAllStepStarted(inferredStep);
          }
        }
      } catch (error) {
        logClientError("SessionMenu.stepStatusEvent", error, { runId });
        // Ignore malformed status event.
      }
    };

    source.addEventListener("step_completed", applyEventStatus);
    source.addEventListener("step_skipped", applyEventStatus);
    source.addEventListener("step_failed", applyEventStatus);
    source.addEventListener("run_cancelling", () => {
      setStatus("Abbruch angefordert...");
    });

    source.addEventListener("run_completed", (event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data) as RunCompletedEvent;
        if (payload.final_status) {
          applySessionStatus(payload.final_status);
        }
        setStatus(payload.ok ? "Alle Schritte wurden ausgeführt." : "Lauf beendet.");
      } catch (error) {
        logClientError("SessionMenu.runCompletedEvent", error, { runId });
        setStatus("Alle Schritte wurden ausgeführt.");
      } finally {
        setIsRunningAll(false);
        setCurrentRunId(null);
        setIsCancellingRun(false);
        emitRunAllStepCleared();
        stopRunMonitoring();
      }
    });

    source.addEventListener("run_failed", (event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data) as RunFailedEvent;
        if (payload.final_status) {
          applySessionStatus(payload.final_status);
        }
        const failedStep = payload.steps?.find((step) => step.status === "failed");
        setStatus(
          failedStep?.message ||
            payload.message ||
            "Schritte konnten nicht vollständig ausgeführt werden."
        );
      } catch (error) {
        logClientError("SessionMenu.runFailedEvent", error, { runId });
        setStatus("Schritte konnten nicht vollständig ausgeführt werden.");
      } finally {
        setIsRunningAll(false);
        setCurrentRunId(null);
        setIsCancellingRun(false);
        emitRunAllStepCleared();
        stopRunMonitoring();
      }
    });
    source.addEventListener("run_cancelled", (event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data) as RunCancelledEvent;
        if (payload.final_status) {
          applySessionStatus(payload.final_status);
        }
        setStatus(
          payload.message ||
            "Ausführung abgebrochen. Bereits abgeschlossene Schritte bleiben erhalten."
        );
      } catch (error) {
        logClientError("SessionMenu.runCancelledEvent", error, { runId });
        setStatus(
          "Ausführung abgebrochen. Bereits abgeschlossene Schritte bleiben erhalten."
        );
      } finally {
        setIsRunningAll(false);
        setCurrentRunId(null);
        setIsCancellingRun(false);
        emitRunAllStepCleared();
        stopRunMonitoring();
      }
    });

    source.onerror = () => {
      source.close();
      runEventSourceRef.current = null;
      pollRunStatus(runId);
    };
  };

  const handleRunAllSteps = async () => {
    if (isRunningAll) {
      if (!currentRunId) {
        setStatus("Lauf läuft bereits.");
        return;
      }
      if (isCancellingRun) {
        setStatus("Abbruch läuft bereits...");
        return;
      }
      try {
        setIsCancellingRun(true);
        setStatus("Abbruch angefordert...");
        await apiClient.cancelRunAll(currentRunId);
      } catch (error) {
        if (getErrorStatus(error) === 404) {
          await handleMissingRunState(currentRunId, error);
          return;
        }
        logClientError("SessionMenu.cancelRunAll", error, {
          runId: currentRunId,
        });
        const err = error as Error;
        setIsCancellingRun(false);
        setStatus(err?.message || "Abbruch konnte nicht angefordert werden.");
      }
      return;
    }
    if (!state.selectedModel) {
      setStatus("Bitte zuerst ein Modell auswählen.");
      return;
    }
    if (state.totalCostReady) {
      setStatus("Alle Schritte sind bereits abgeschlossen.");
      return;
    }
    resetStatus();
    setIsRunningAll(true);
    emitRunAllStepCleared();
    const { model, provider, keys } = buildLlmRequestOptions({
      selectedModel: state.selectedModel,
      availableModels: state.availableModels,
    });
    try {
      const start = await apiClient.startRunAllSteps({
        appSessionId: state.appSessionId,
        currentFilename: state.selectedCurrentLaw || undefined,
        proposedFilename: state.selectedRegulation || undefined,
        model,
        provider,
        keys,
      });
      setStatus(
        start.started
          ? "Schritte werden ausgeführt..."
          : "Lauf läuft bereits. Status wird synchronisiert..."
      );
      setCurrentRunId(start.run_id);
      setIsCancellingRun(false);
      beginRunEventStream(start.run_id);
    } catch (error) {
      logClientError("SessionMenu.startRunAll", error, {
        appSessionId: state.appSessionId,
      });
      const err = error as Error;
      setStatus(err?.message || "Schritte konnten nicht gestartet werden.");
      setIsRunningAll(false);
      setCurrentRunId(null);
      setIsCancellingRun(false);
      emitRunAllStepCleared();
      stopRunMonitoring();
    }
  };

  const menuContent = (
    <div
      className="fixed z-[60] w-80 rounded-2xl border border-slate-200 bg-white p-4 text-xs text-slate-700 shadow-2xl"
      style={{ top: menuPos.top, left: menuPos.left }}
    >
      <div className="flex items-center justify-between">
        <div className="font-semibold text-slate-900">Session Aktionen</div>
        <button
          onClick={() => setIsOpen(false)}
          className="rounded-full border border-slate-200 px-2 py-0.5 text-[10px] text-slate-500"
        >
          Schließen
        </button>
      </div>
      <div className="mt-4 space-y-2">
        <button
          onClick={handleNewSession}
          className="w-full rounded-xl bg-slate-900 px-3 py-2 text-left text-xs font-semibold text-white"
        >
          Neue Session starten
        </button>
        <button
          onClick={handleRebuildCurrent}
          className="w-full rounded-xl bg-slate-900 px-3 py-2 text-left text-xs font-semibold text-white"
        >
          Kacheln dieser Session neu laden
        </button>
        <button
          onClick={handleExportSession}
          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-left text-xs font-semibold text-slate-700 hover:bg-slate-50"
        >
          Session exportieren (Mermaid)
        </button>
        <button
          onClick={handleRunAllSteps}
          className={`w-full rounded-xl px-3 py-2 text-left text-xs font-semibold transition ${
            isRunningAll
              ? "border border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100"
              : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
          }`}
          disabled={isRunningAll && isCancellingRun}
        >
          {isRunningAll
            ? isCancellingRun
              ? "Abbruch wird ausgeführt..."
              : "Ausführung abbrechen"
            : "Alle Schritte ausführen"}
        </button>
        <button
          onClick={handleUndoLastStep}
          disabled={!lastStepLabel || isUndoing}
          className={`w-full rounded-xl px-3 py-2 text-left text-xs font-semibold transition ${
            lastStepLabel && !isUndoing
              ? "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              : "cursor-not-allowed border border-slate-100 bg-slate-100 text-slate-400"
          }`}
        >
          {isUndoing
            ? "Bitte warten..."
            : `\"${lastStepLabel || "Letzten Schritt"}\" zurücksetzen`}
        </button>
      </div>
      <div className="mt-4">
        <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
          Session wechseln
        </div>
        <select
          value={selectedSession}
          onChange={(event) => setSelectedSession(event.target.value)}
          className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2 text-xs"
        >
          <option value="">Session auswählen</option>
          {formattedSessions.map((session) => (
            <option key={session.app_session_id} value={session.app_session_id}>
              {session.label}
            </option>
          ))}
        </select>
        <div className="mt-2 flex justify-end">
          <button
            onClick={handleLoadSession}
            className="rounded-xl bg-slate-900 px-4 py-2 text-xs font-semibold text-white"
          >
            Wechseln
          </button>
        </div>
      </div>
      {status && (
        <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] font-semibold text-amber-800">
          {status}
        </div>
      )}
    </div>
  );

  return (
    <div ref={triggerRef} className="relative">
      <div
        className={`rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-700 ${
          compact ? "px-3 py-2 text-[11px]" : ""
        }`}
      >
        <span className="block text-[10px] uppercase tracking-wide text-slate-500">
          Session
        </span>
        <span className="block select-text font-mono text-sm">
          {state.appSessionId}
        </span>
      </div>
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        title="Session Aktionen"
        className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full border border-slate-200 bg-white text-[10px] text-slate-600 shadow-sm"
      >
        ↻
      </button>
      {isOpen && isMounted ? createPortal(menuContent, document.body) : null}
    </div>
  );
}
