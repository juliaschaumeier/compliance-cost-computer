"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { useApp } from "@/contexts/AppContext";
import {
  apiClient,
  buildLlmRequestOptions,
  type ApiClientError,
  type ComplianceTextUserEditPolicy,
} from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";
import {
  emitRunAllStepCleared,
  emitRunAllStepStarted,
  type RunAllStepKey,
  useActiveWorkflowRun,
} from "@/lib/runAllStepEvents";
import {
  formatSessionStartError,
  logSessionStartError,
  prepareSessionDocuments,
} from "@/lib/sessionStart";
import { deriveTabFromStatus } from "@/lib/sessionStatus";
import { RunAllStatusResponse, SessionStatus, SessionSummary } from "@/types";

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

function formatElapsedDuration(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")} min`;
}

export default function SessionMenu({ compact }: SessionMenuProps) {
  const {
    state,
    setAvailableRegulations,
    setCurrentTab,
    setAppSessionId,
    setSelectedCurrentLaw,
    setSelectedRegulation,
    setPendingCurrentUpload,
    setPendingProposedUpload,
    setPendingCurrentUploadName,
    setPendingProposedUploadName,
    setSummaryReady,
    setRegulationsReady,
    setLastCompletedStep,
    setLastCompletedLabel,
    setLastFailedStep,
    setLastFailedLabel,
    setLastFailedMessage,
    setIsComplianceExportRunning,
  } = useApp();
  const [isOpen, setIsOpen] = useState(false);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedSession, setSelectedSession] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [isUndoing, setIsUndoing] = useState(false);
  const [researchEnabled, setResearchEnabled] = useState(false);
  const [researchStatus, setResearchStatus] = useState("idle");
  const [researchElapsedSeconds, setResearchElapsedSeconds] = useState<
    number | null
  >(null);
  const [researchElapsedLoadedAt, setResearchElapsedLoadedAt] = useState<
    number | null
  >(null);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const [researchLocked, setResearchLocked] = useState(false);
  const [isUpdatingResearch, setIsUpdatingResearch] = useState(false);
  const [isDownloadingResearch, setIsDownloadingResearch] = useState(false);
  const [isDownloadingComplianceExport, setIsDownloadingComplianceExport] =
    useState(false);
  const [
    isComplianceEditChoiceVisible,
    setIsComplianceEditChoiceVisible,
  ] = useState(false);
  const [isRunningAll, setIsRunningAll] = useState(false);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [isCancellingRun, setIsCancellingRun] = useState(false);
  const isCancellingRunRef = useRef(false);
  const activeWorkflowRun = useActiveWorkflowRun();
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

  const refreshResearchSettings = useCallback(
    async (options: { ignoreCancelled?: () => boolean } = {}) => {
      try {
        const research = await apiClient.getCaseGroupResearchSettings(
          state.appSessionId
        );
        if (options.ignoreCancelled?.()) {
          return;
        }
        setResearchEnabled(research.enabled);
        setResearchStatus(research.status);
        setResearchLocked(research.locked);
        setResearchElapsedSeconds(research.elapsed_seconds ?? null);
        setResearchElapsedLoadedAt(
          typeof research.elapsed_seconds === "number" ? Date.now() : null
        );
      } catch (error) {
        logClientError("SessionMenu.loadResearchSettings", error, {
          appSessionId: state.appSessionId,
        });
      }
    },
    [state.appSessionId]
  );

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
    setSelectedSession(state.appSessionId);
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
    void refreshResearchSettings({ ignoreCancelled: () => cancelled });
    return () => {
      cancelled = true;
    };
  }, [isOpen, refreshResearchSettings, state.appSessionId]);

  useEffect(() => {
    setSelectedSession(isOpen ? state.appSessionId : "");
    resetStatus();
    setIsComplianceEditChoiceVisible(false);
  }, [isOpen, state.appSessionId]);

  useEffect(() => {
    if (!isOpen || researchStatus !== "running") {
      return;
    }
    const timer = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [isOpen, researchStatus]);

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

  const hasPendingSessionSwitch =
    Boolean(selectedSession) && selectedSession !== state.appSessionId;

  const resetStatus = () => setStatus(null);
  const getErrorStatus = (error: unknown): number | undefined => {
    const status = (error as ApiClientError)?.status;
    return typeof status === "number" ? status : undefined;
  };
  const getDetailError = (error: unknown): string | undefined => {
    const details = (error as ApiClientError)?.details;
    if (
      details &&
      typeof details === "object" &&
      "error" in details &&
      typeof (details as { error?: unknown }).error === "string"
    ) {
      return (details as { error: string }).error;
    }
    return undefined;
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
  const hasActiveWorkflowRun = activeWorkflowRun.isActive || isRunningAll;
  const isSingleStepWorkflowRunning =
    activeWorkflowRun.isActive && activeWorkflowRun.runKind === "step";
  const hasAnyCompletedWorkflowStep =
    state.summaryReady ||
    state.regulationsReady ||
    state.processesReady ||
    state.caseGroupsReady ||
    state.processStepsReady ||
    state.effortReady ||
    state.totalCostReady;
  const runAllActionLabel = state.totalCostReady
    ? "Alle Schritte abgeschlossen"
    : hasAnyCompletedWorkflowStep
      ? "Verbleibende Schritte ausführen"
      : "Alle Schritte ausführen";
  const isRunAllActionDisabled =
    (!isRunningAll && (state.totalCostReady || isSingleStepWorkflowRunning)) ||
    (isRunningAll && isCancellingRun);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const updatePosition = () => {
      const width = 360;
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

  const handleNewSession = () => {
    sessionStorage.clear();
    window.location.reload();
  };

  const handleLoadSession = async () => {
    if (!hasPendingSessionSwitch) {
      setStatus("Bitte eine Session auswählen.");
      return;
    }
    try {
      resetStatus();
      const sessionStatus = await apiClient.getSessionStatus(selectedSession);
      setAppSessionId(selectedSession);
      applySessionStatus(sessionStatus);
      await apiClient.rebuildTiles(
        selectedSession,
        state.selectedNormAddressee
      );
      setIsOpen(false);
    } catch (error) {
      logClientError("SessionMenu.loadSession", error, {
        selectedSession,
      });
      setStatus("Session konnte nicht geladen werden.");
    }
  };

  const handleUndoLastStep = async () => {
    if (!lastStepLabel || isUndoing || hasActiveWorkflowRun) {
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
      await apiClient.rebuildTiles(
        state.appSessionId,
        state.selectedNormAddressee
      );
      const sessionStatus = await apiClient.getSessionStatus(state.appSessionId);
      applySessionStatus(sessionStatus);
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

  const handleToggleDeepResearch = async () => {
    if (isUpdatingResearch || researchLocked || hasActiveWorkflowRun) {
      return;
    }
    try {
      resetStatus();
      setIsUpdatingResearch(true);
      const result = await apiClient.updateCaseGroupResearchSettings(
        state.appSessionId,
        !researchEnabled
      );
      setResearchEnabled(result.enabled);
      setResearchStatus(result.status);
      setResearchLocked(result.locked);
      setResearchElapsedSeconds(result.elapsed_seconds ?? null);
      setResearchElapsedLoadedAt(
        typeof result.elapsed_seconds === "number" ? Date.now() : null
      );
      setStatus(
        result.enabled
          ? "Deep Research für Fallzahlen aktiviert."
          : "Deep Research für Fallzahlen deaktiviert."
      );
    } catch (error) {
      logClientError("SessionMenu.toggleDeepResearch", error, {
        appSessionId: state.appSessionId,
      });
      setStatus("Deep-Research-Einstellung konnte nicht gespeichert werden.");
    } finally {
      setIsUpdatingResearch(false);
    }
  };

  const handleDownloadDeepResearchReport = async () => {
    try {
      resetStatus();
      setIsDownloadingResearch(true);
      const blob = await apiClient.downloadDeepResearchReport(state.appSessionId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `ccc_deep_research_${state.appSessionId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setStatus("Deep-Research-Bericht heruntergeladen.");
    } catch (error) {
      logClientError("SessionMenu.downloadDeepResearchReport", error, {
        appSessionId: state.appSessionId,
      });
      setStatus("Deep-Research-Bericht ist noch nicht verfügbar.");
    } finally {
      setIsDownloadingResearch(false);
    }
  };

  const downloadComplianceExport = async (
    userEditPolicy: ComplianceTextUserEditPolicy,
    appSessionId: string
  ) => {
    const llm = buildLlmRequestOptions({
      selectedModel: state.selectedModel,
      availableModels: state.availableModels,
    });
    const blob = await apiClient.downloadComplianceTextExport({
      appSessionId,
      model: llm.model,
      provider: llm.provider,
      keys: llm.keys,
      userEditPolicy,
    });
    const suffix =
      userEditPolicy === "use_user_edits"
        ? "_ea_bearbeitet"
        : "";
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `ccc_vorblatt_begruendung_${appSessionId}${suffix}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const handleDownloadComplianceExport = async () => {
    if (!state.totalCostReady) {
      setStatus("Vorblatt/Begründung kann erst nach Abschluss aller Schritte exportiert werden.");
      return;
    }
    if (!state.selectedModel) {
      setStatus("Bitte zuerst ein Modell auswählen.");
      return;
    }
    const exportSessionId = state.appSessionId;
    try {
      resetStatus();
      setIsComplianceEditChoiceVisible(false);
      setIsDownloadingComplianceExport(true);
      setIsComplianceExportRunning(true);
      await downloadComplianceExport("reject_if_user_edits", exportSessionId);
      setStatus("Vorblatt/Begründung exportiert.");
    } catch (error) {
      if (getErrorStatus(error) === 409 && getDetailError(error) === "user_edits_present") {
        setIsComplianceEditChoiceVisible(true);
        setStatus("Es gibt bearbeitete EA-Werte. Bitte Exportvariante auswählen.");
      } else {
        logClientError("SessionMenu.downloadComplianceExport", error, {
          appSessionId: exportSessionId,
        });
        setStatus("Vorblatt/Begründung-Export fehlgeschlagen.");
      }
    } finally {
      setIsDownloadingComplianceExport(false);
      setIsComplianceExportRunning(false);
    }
  };

  const handleComplianceEditChoice = async (
    userEditPolicy: ComplianceTextUserEditPolicy | null
  ) => {
    if (userEditPolicy === null) {
      setIsComplianceEditChoiceVisible(false);
      setStatus("Vorblatt/Begründung-Export abgebrochen.");
      return;
    }
    const exportSessionId = state.appSessionId;
    try {
      resetStatus();
      setIsDownloadingComplianceExport(true);
      setIsComplianceEditChoiceVisible(false);
      setIsComplianceExportRunning(true);
      await downloadComplianceExport(userEditPolicy, exportSessionId);
      setStatus(
        userEditPolicy === "use_user_edits"
          ? "Vorblatt/Begründung mit bearbeiteten EA-Werten exportiert."
          : "Vorblatt/Begründung exportiert."
      );
    } catch (error) {
      logClientError("SessionMenu.downloadComplianceExport.retry", error, {
        appSessionId: exportSessionId,
      });
      setStatus("Vorblatt/Begründung-Export fehlgeschlagen.");
    } finally {
      setIsDownloadingComplianceExport(false);
      setIsComplianceExportRunning(false);
    }
  };

  const applySessionStatus = (sessionStatus: SessionStatus) => {
    setSummaryReady(sessionStatus.summary_ready);
    setRegulationsReady(sessionStatus.regulations_ready);
    setLastCompletedStep(sessionStatus.last_completed_step ?? null);
    setLastCompletedLabel(sessionStatus.last_completed_label ?? null);
    setLastFailedStep(sessionStatus.last_failed_step ?? null);
    setLastFailedLabel(sessionStatus.last_failed_label ?? null);
    setLastFailedMessage(sessionStatus.last_failed_message ?? null);
    setResearchEnabled(Boolean(sessionStatus.case_group_research_enabled));
    setResearchStatus(sessionStatus.case_group_research_status || "idle");
    setResearchElapsedSeconds(
      sessionStatus.case_group_research_elapsed_seconds ?? null
    );
    setResearchElapsedLoadedAt(
      typeof sessionStatus.case_group_research_elapsed_seconds === "number"
        ? Date.now()
        : null
    );
    setResearchLocked(
      sessionStatus.effort_ready ||
        sessionStatus.total_cost_ready ||
      !["idle", "failed", "cancelled"].includes(
        sessionStatus.case_group_research_status || "idle"
      )
    );
    setCurrentTab(deriveTabFromStatus(sessionStatus));
    window.dispatchEvent(new Event("tiles-updated"));
  };

  const researchElapsedDisplay = useMemo(() => {
    if (researchStatus !== "running" || researchElapsedSeconds === null) {
      return null;
    }
    const clientElapsedSeconds =
      researchElapsedLoadedAt === null
        ? 0
        : Math.max(0, Math.floor((nowMs - researchElapsedLoadedAt) / 1000));
    return formatElapsedDuration(researchElapsedSeconds + clientElapsedSeconds);
  }, [
    nowMs,
    researchElapsedLoadedAt,
    researchElapsedSeconds,
    researchStatus,
  ]);

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
    isCancellingRunRef.current = false;
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
          if (progress.current_step) {
            emitRunAllStepStarted(progress.current_step, runId);
          }
          pollRunStatus(runId);
          return;
        }
        resetRunUiState();
        void refreshResearchSettings();
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

    source.addEventListener("snapshot", (event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data) as RunAllStatusResponse;
        if (payload.final_status) {
          applySessionStatus(payload.final_status);
        }
        if (payload.status === "running" && payload.current_step) {
          emitRunAllStepStarted(payload.current_step, runId);
          if (payload.current_label && !isCancellingRunRef.current) {
            setStatus(`Läuft: ${payload.current_label}`);
          }
        }
      } catch (error) {
        logClientError("SessionMenu.snapshotEvent", error, { runId });
      }
    });

    source.addEventListener("step_started", (event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data) as RunStepStartedEvent;
        emitRunAllStepStarted(payload.key, runId);
        if (payload.label && !isCancellingRunRef.current) {
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
            emitRunAllStepStarted(inferredStep, runId);
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
      isCancellingRunRef.current = true;
      setIsCancellingRun(true);
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
        isCancellingRunRef.current = false;
        emitRunAllStepCleared();
        stopRunMonitoring();
        void refreshResearchSettings();
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
        isCancellingRunRef.current = false;
        emitRunAllStepCleared();
        stopRunMonitoring();
        void refreshResearchSettings();
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
        isCancellingRunRef.current = false;
        emitRunAllStepCleared();
        stopRunMonitoring();
        void refreshResearchSettings();
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
      if (isCancellingRunRef.current) {
        setStatus("Abbruch läuft bereits...");
        return;
      }
      try {
        isCancellingRunRef.current = true;
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
        isCancellingRunRef.current = false;
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
    isCancellingRunRef.current = false;
    setStatus("Schritte werden vorbereitet...");
    emitRunAllStepCleared();
    try {
      const { currentFilename, proposedFilename, llm } =
        await prepareSessionDocuments({
          appSessionId: state.appSessionId,
          selectedModel: state.selectedModel,
          availableModels: state.availableModels,
          availableRegulations: state.availableRegulations,
          selectedCurrentLaw: state.selectedCurrentLaw,
          selectedRegulation: state.selectedRegulation,
          pendingCurrent: {
            file: state.pendingCurrentUpload,
            desiredName: state.pendingCurrentUploadName,
          },
          pendingProposed: {
            file: state.pendingProposedUpload,
            desiredName: state.pendingProposedUploadName,
          },
          setSelectedCurrentLaw,
          setSelectedRegulation,
          setPendingCurrentUpload,
          setPendingProposedUpload,
          setPendingCurrentUploadName,
          setPendingProposedUploadName,
          setAvailableRegulations,
        });
      const start = await apiClient.startRunAllSteps({
        appSessionId: state.appSessionId,
        currentFilename,
        proposedFilename,
        model: llm.model,
        provider: llm.provider,
        keys: llm.keys,
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
      logSessionStartError("SessionMenu.startRunAll", error, {
        appSessionId: state.appSessionId,
      });
      setStatus(formatSessionStartError(error));
      setIsRunningAll(false);
      setCurrentRunId(null);
      setIsCancellingRun(false);
      isCancellingRunRef.current = false;
      emitRunAllStepCleared();
      stopRunMonitoring();
    }
  };

  const menuContent = (
    <div
      className="fixed z-[60] w-[360px] rounded-2xl border border-slate-200 bg-white p-4 text-xs text-slate-700 shadow-2xl"
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
        <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
          Session
        </div>
        <button
          onClick={handleNewSession}
          className="w-full rounded-xl bg-slate-900 px-3 py-2 text-left text-xs font-semibold text-white"
        >
          Neue Session starten
        </button>
        <button
          onClick={handleRunAllSteps}
          className={`w-full rounded-xl px-3 py-2 text-left text-xs font-semibold transition ${
            isRunningAll
              ? "border border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100"
              : isRunAllActionDisabled
                ? "cursor-not-allowed border border-slate-100 bg-slate-100 text-slate-400"
              : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
          }`}
          disabled={isRunAllActionDisabled}
        >
          {isRunningAll
            ? isCancellingRun
              ? "Abbruch wird ausgeführt..."
              : "Ausführung abbrechen"
            : runAllActionLabel}
        </button>
        <button
          onClick={handleUndoLastStep}
          disabled={!lastStepLabel || isUndoing || hasActiveWorkflowRun}
          className={`w-full rounded-xl px-3 py-2 text-left text-xs font-semibold transition ${
            lastStepLabel && !isUndoing && !hasActiveWorkflowRun
              ? "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              : "cursor-not-allowed border border-slate-100 bg-slate-100 text-slate-400"
          }`}
        >
          {isUndoing
            ? "Bitte warten..."
            : `\"${lastStepLabel || "Letzten Schritt"}\" zurücksetzen`}
        </button>
      </div>
      <div className="mt-4 space-y-2 border-t border-slate-100 pt-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
              Fallzahlen
            </div>
            <div className="mt-1 font-semibold text-slate-900">
              Deep Research für Fallzahlen
            </div>
            <div className="mt-1 text-[11px] text-slate-500">
              Status: {researchStatus}
              {researchElapsedDisplay ? ` · läuft seit ${researchElapsedDisplay}` : ""}
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={researchEnabled}
            disabled={
              researchLocked || isUpdatingResearch || hasActiveWorkflowRun
            }
            onClick={handleToggleDeepResearch}
            className={`relative mt-1 h-6 w-14 rounded-full border p-0.5 text-[10px] font-bold leading-none transition disabled:cursor-not-allowed disabled:opacity-50 ${
              researchEnabled
                ? "border-slate-900 bg-slate-900 text-white"
                : "border-slate-300 bg-slate-100 text-slate-500"
            }`}
          >
            <span
              className={`absolute top-1/2 -translate-y-1/2 ${
                researchEnabled ? "left-2" : "right-2"
              }`}
            >
              {researchEnabled ? "An" : "Aus"}
            </span>
            <span
              className={`block h-4 w-4 rounded-full bg-white shadow-sm transition ${
                researchEnabled ? "translate-x-8" : "translate-x-0"
              }`}
            />
          </button>
        </div>
        <button
          onClick={handleDownloadDeepResearchReport}
          disabled={isDownloadingResearch || researchStatus !== "parsed"}
          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-left text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
        >
          {isDownloadingResearch
            ? "Bericht wird geladen..."
            : "Deep-Research-Bericht herunterladen"}
        </button>
      </div>
      <div className="mt-4 space-y-2 border-t border-slate-100 pt-3">
        <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
          Export
        </div>
        <button
          onClick={handleExportSession}
          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-left text-xs font-semibold text-slate-700 hover:bg-slate-50"
        >
          Sessiongraph exportieren (Mermaid)
        </button>
        <button
          onClick={handleDownloadComplianceExport}
          disabled={
            isDownloadingComplianceExport ||
            isRunningAll ||
            !state.totalCostReady
          }
          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-left text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
        >
          {isDownloadingComplianceExport
            ? "Vorblatt/Begründung wird geladen..."
            : "Vorblatt/Begründung exportieren"}
        </button>
        {isComplianceEditChoiceVisible && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-[11px] text-amber-900">
            <div className="font-semibold">
              Bearbeitete EA-Werte vorhanden.
            </div>
            <div className="mt-1 text-amber-800">
              Der Export verwendet immer den aktuell sichtbaren EA-Stand. Wenn du Modellwerte exportieren möchtest, setze die EA-Werte zuerst in „EA bearbeiten“ zurück.
            </div>
            <div className="mt-2 space-y-1">
              <button
                type="button"
                onClick={() => handleComplianceEditChoice("use_user_edits")}
                disabled={isDownloadingComplianceExport}
                className="w-full rounded-lg bg-amber-900 px-2 py-1.5 text-left font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                Bearbeitete EA-Werte verwenden
              </button>
              <button
                type="button"
                onClick={() => handleComplianceEditChoice(null)}
                disabled={isDownloadingComplianceExport}
                className="w-full rounded-lg px-2 py-1.5 text-left font-semibold text-amber-800 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Abbrechen
              </button>
            </div>
          </div>
        )}
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
            disabled={!hasPendingSessionSwitch}
            className={`rounded-xl px-4 py-2 text-xs font-semibold transition ${
              hasPendingSessionSwitch
                ? "bg-slate-900 text-white hover:bg-slate-800"
                : "cursor-not-allowed border border-slate-200 bg-slate-100 text-slate-400"
            }`}
          >
            {hasPendingSessionSwitch ? "Session wechseln" : "Aktuelle Session"}
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
