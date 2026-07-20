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
import { createAuthenticatedEventSource } from "@/lib/eventSource";
import { useAnchoredPopoverPosition } from "@/lib/useAnchoredPopoverPosition";
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
import { RunAllStatusResponse, SessionStatus, SessionSummary } from "@/types";

type SessionMenuProps = {
  variant?: "default" | "header";
};

type SessionStepResult = { status: string; message?: string };
type RunStepStartedEvent = { key?: string; label?: string };
type RunStepStatusEvent = {
  session_status?: SessionStatus;
  step?: SessionStepResult;
  message?: string;
};
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

const RUN_ALL_STEP_LABELS: Record<RunAllStepKey, string> = {
  summary: "Gesetz auswählen",
  regulations: "Vorgaben identifizieren",
  processes: "Prozesse bündeln",
  case_groups: "Fallgruppen entwickeln",
  process_steps: "Prozessschritte bestimmen",
  effort: "Aufwand quantifizieren",
  total_cost: "Gesamtkosten berechnen",
};

function getRunAllStepLabel(
  key?: string | null,
  label?: string | null
): string | null {
  if (label) {
    return label;
  }
  if (key && key in RUN_ALL_STEP_LABELS) {
    return RUN_ALL_STEP_LABELS[key as RunAllStepKey];
  }
  return null;
}

function formatElapsedDuration(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")} min`;
}

function getApiDetailMessage(error: unknown): string | null {
  const details = (error as ApiClientError | undefined)?.details;
  if (typeof details !== "object" || details === null || Array.isArray(details)) {
    return null;
  }
  const message = (details as Record<string, unknown>).message;
  return typeof message === "string" && message.trim() ? message : null;
}

const isLikelyValidApiKey = (value: string | null) =>
  Boolean(value && value.trim().length > 10);

const menuSectionLabelClass =
  "text-[10px] font-semibold uppercase tracking-wide text-slate-400";
const menuButtonBaseClass =
  "w-full rounded-xl px-3 py-2 text-left text-xs font-semibold transition";
const menuPrimaryButtonClass =
  `${menuButtonBaseClass} bg-slate-800 text-white`;
const menuSecondaryButtonClass =
  `${menuButtonBaseClass} border border-slate-200 bg-white text-slate-700 hover:bg-slate-50`;
const menuRunningButtonClass =
  `${menuButtonBaseClass} flex items-center gap-2 border border-slate-300 bg-slate-50 text-slate-700 hover:bg-slate-100`;
const menuCancellingButtonClass =
  `${menuButtonBaseClass} flex cursor-not-allowed items-center gap-2 border border-slate-200 bg-slate-100 text-slate-400`;
const menuDisabledButtonClass =
  `${menuButtonBaseClass} cursor-not-allowed border border-slate-100 bg-slate-100 text-slate-400`;
const menuExportButtonClass = `${menuSecondaryButtonClass} disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400`;

function isTransientWorkflowStatus(status: string | null): boolean {
  if (!status) {
    return false;
  }
  return [
    "Abbruch angefordert",
    "Abbruch läuft bereits",
    "Alle Schritte sind bereits abgeschlossen",
    "Alle Schritte wurden ausgeführt",
    "Ausführung abgebrochen",
    "Lauf beendet",
    "Lauf läuft bereits",
    "Letzter Schritt zurückgesetzt",
    "Läuft:",
    "Schritte werden ausgeführt",
    "Schritte werden vorbereitet",
  ].some((prefix) => status.startsWith(prefix));
}

export default function SessionMenu({ variant = "default" }: SessionMenuProps) {
  const {
    state,
    setAvailableRegulations,
    setAppSessionId,
    setSelectedModel,
    setSelectedCurrentLaw,
    setSelectedRegulation,
    setPendingCurrentUpload,
    setPendingProposedUpload,
    setPendingCurrentUploadName,
    setPendingProposedUploadName,
    setIsComplianceExportRunning,
    applySessionStatus,
  } = useApp();
  const [isOpen, setIsOpen] = useState(false);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedSession, setSelectedSession] = useState("");
  const [isLoadingSession, setIsLoadingSession] = useState(false);
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
  const [
    pendingComplianceExportSessionId,
    setPendingComplianceExportSessionId,
  ] = useState<string | null>(null);
  const [isRunningAll, setIsRunningAll] = useState(false);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [currentRunLabel, setCurrentRunLabel] = useState<string | null>(null);
  const [isCancellingRun, setIsCancellingRun] = useState(false);
  const isCancellingRunRef = useRef(false);
  const activeWorkflowRun = useActiveWorkflowRun();
  const runEventSourceRef = useRef<EventSource | null>(null);
  const runPollTimerRef = useRef<number | null>(null);
  const [isMounted, setIsMounted] = useState(false);
  const triggerRef = useRef<HTMLDivElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const { position: menuPos } = useAnchoredPopoverPosition({
    open: isOpen,
    triggerRef,
    width: 360,
    align: "right",
    offset: 8,
    padding: 16,
    fallbackPosition: { top: 96, left: 16 },
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
  }, [isOpen, state.appSessionId]);

  useEffect(() => {
    resetStatus();
    setIsComplianceEditChoiceVisible(false);
    setPendingComplianceExportSessionId(null);
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

  const getSessionModel = (appSessionId: string): string | null =>
    sessions.find((session) => session.app_session_id === appSessionId)?.llm_model || null;

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
  const isRunAllComplete = state.totalCostReady;
  const runAllIdleLabel = hasAnyCompletedWorkflowStep
    ? "Verbleibende Schritte ausführen"
    : "Alle Schritte ausführen";
  const runAllButtonLabel = isRunningAll
    ? isCancellingRun
      ? "Abbruch wird ausgeführt..."
      : `\"${currentRunLabel || "Schritte"}\" abbrechen`
    : isRunAllComplete
      ? "Alle Schritte abgeschlossen"
      : runAllIdleLabel;
  const isRunAllActionDisabled =
    (!isRunningAll && (isRunAllComplete || isSingleStepWorkflowRunning)) ||
    (isRunningAll && isCancellingRun);
  const otherStatus = status && !isTransientWorkflowStatus(status) ? status : null;

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (menuRef.current?.contains(target) || triggerRef.current?.contains(target)) {
        return;
      }
      setIsOpen(false);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const handleNewSession = () => {
    sessionStorage.clear();
    window.location.reload();
  };

  const handleLoadSession = async (targetSession: string) => {
    if (!targetSession || targetSession === state.appSessionId || isLoadingSession) {
      return;
    }
    try {
      resetStatus();
      setIsLoadingSession(true);
      const sessionStatus = await apiClient.getSessionStatus(targetSession);
      await apiClient.rebuildTiles(
        targetSession,
        state.selectedNormAddressee
      );
      const sessionModel = getSessionModel(targetSession);
      setAppSessionId(targetSession);
      if (sessionModel) {
        setSelectedModel(sessionModel);
      }
      applySessionMenuStatus(sessionStatus);
      setIsOpen(false);
    } catch (error) {
      logClientError("SessionMenu.loadSession", error, {
        selectedSession: targetSession,
      });
      setSelectedSession(state.appSessionId);
      setStatus("Session konnte nicht geladen werden.");
    } finally {
      setIsLoadingSession(false);
    }
  };

  const handleSessionSelect = (targetSession: string) => {
    setSelectedSession(targetSession);
    void handleLoadSession(targetSession);
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
      applySessionMenuStatus(sessionStatus);
      window.dispatchEvent(new Event("tiles-updated"));
      setStatus(
        result.message ||
          `Letzter Schritt zurückgesetzt: ${result.undone_label || lastStepLabel}`
      );
    } catch (error) {
      logClientError("SessionMenu.undoLastStep", error, {
        appSessionId: state.appSessionId,
        lastStepLabel,
      });
      setStatus(
        getApiDetailMessage(error) ||
          "Letzter Schritt konnte nicht zurückgesetzt werden."
      );
    } finally {
      setIsUndoing(false);
    }
  };

  const handleToggleDeepResearch = async () => {
    if (isUpdatingResearch || researchLocked || hasActiveWorkflowRun) {
      return;
    }
    if (!researchEnabled && !isLikelyValidApiKey(localStorage.getItem("gemini_api_key"))) {
      setStatus(
        "Deep Research benötigt einen Gemini API Key. Bitte in der LLM-Auswahl hinterlegen."
      );
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
      setStatus("Vorblatt und Begründung können erst nach Abschluss aller Schritte exportiert werden.");
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
      setPendingComplianceExportSessionId(null);
      setIsDownloadingComplianceExport(true);
      setIsComplianceExportRunning(true);
      await downloadComplianceExport("reject_if_user_edits", exportSessionId);
      setStatus("Vorblatt und Begründung exportiert.");
    } catch (error) {
      if (getErrorStatus(error) === 409 && getDetailError(error) === "user_edits_present") {
        setPendingComplianceExportSessionId(exportSessionId);
        setIsComplianceEditChoiceVisible(true);
        setStatus("Es gibt bearbeitete EA-Werte. Bitte Exportvariante auswählen.");
      } else {
        logClientError("SessionMenu.downloadComplianceExport", error, {
          appSessionId: exportSessionId,
        });
        setStatus("Export von Vorblatt und Begründung fehlgeschlagen.");
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
      setPendingComplianceExportSessionId(null);
      setStatus("Export von Vorblatt und Begründung abgebrochen.");
      return;
    }
    const exportSessionId = pendingComplianceExportSessionId || state.appSessionId;
    try {
      resetStatus();
      setIsDownloadingComplianceExport(true);
      setIsComplianceEditChoiceVisible(false);
      setIsComplianceExportRunning(true);
      await downloadComplianceExport(userEditPolicy, exportSessionId);
      setStatus(
        userEditPolicy === "use_user_edits"
          ? "Vorblatt und Begründung mit bearbeiteten EA-Werten exportiert."
          : "Vorblatt und Begründung exportiert."
      );
    } catch (error) {
      logClientError("SessionMenu.downloadComplianceExport.retry", error, {
        appSessionId: exportSessionId,
      });
      setStatus("Export von Vorblatt und Begründung fehlgeschlagen.");
    } finally {
      setIsDownloadingComplianceExport(false);
      setIsComplianceExportRunning(false);
      setPendingComplianceExportSessionId(null);
    }
  };

  const applySessionMenuStatus = (sessionStatus: SessionStatus) => {
    applySessionStatus(sessionStatus);
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
    setCurrentRunLabel(null);
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
      applySessionMenuStatus(sessionStatus);
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
          applySessionMenuStatus(progress.final_status);
        }
        if (progress.status === "running") {
          if (progress.current_step) {
            const label = getRunAllStepLabel(progress.current_step);
            setCurrentRunLabel(label);
            emitRunAllStepStarted(progress.current_step, runId, "run_all", label);
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
    const source = createAuthenticatedEventSource(apiClient.getRunAllEventsUrl(runId));
    runEventSourceRef.current = source;

    source.addEventListener("snapshot", (event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data) as RunAllStatusResponse;
        if (payload.final_status) {
          applySessionMenuStatus(payload.final_status);
        }
        if (payload.status === "running" && payload.current_step) {
          const label = getRunAllStepLabel(
            payload.current_step,
            payload.current_label
          );
          setCurrentRunLabel(label);
          emitRunAllStepStarted(payload.current_step, runId, "run_all", label);
          if (label && !isCancellingRunRef.current) {
            setStatus(`Läuft: ${label}`);
          }
        }
      } catch (error) {
        logClientError("SessionMenu.snapshotEvent", error, { runId });
      }
    });

    source.addEventListener("step_started", (event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data) as RunStepStartedEvent;
        const label = getRunAllStepLabel(payload.key, payload.label);
        setCurrentRunLabel(label);
        emitRunAllStepStarted(payload.key, runId, "run_all", label);
        if (label && !isCancellingRunRef.current) {
          setStatus(`Läuft: ${label}`);
        }
      } catch (error) {
        logClientError("SessionMenu.stepStartedEvent", error, { runId });
        // Ignore malformed progress event.
      }
    });

    const applyStepSessionStatus = (payload: RunStepStatusEvent) => {
      if (!payload.session_status) {
        return;
      }
      applySessionMenuStatus(payload.session_status);
      const inferredStep = deriveRunAllStepKeyFromStatus(payload.session_status);
      if (inferredStep) {
        const label = getRunAllStepLabel(inferredStep);
        setCurrentRunLabel(label);
        emitRunAllStepStarted(inferredStep, runId, "run_all", label);
      }
    };

    const applyEventStatus = (event: Event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data) as RunStepStatusEvent;
        applyStepSessionStatus(payload);
      } catch (error) {
        logClientError("SessionMenu.stepStatusEvent", error, { runId });
        // Ignore malformed status event.
      }
    };

    const handleStepFailed = (event: Event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data) as RunStepStatusEvent;
        applyStepSessionStatus(payload);
        setStatus(
          payload.step?.message ||
            payload.message ||
            "Schritte konnten nicht vollständig ausgeführt werden."
        );
      } catch (error) {
        logClientError("SessionMenu.stepFailedEvent", error, { runId });
        setStatus("Schritte konnten nicht vollständig ausgeführt werden.");
      } finally {
        resetRunUiState();
        void refreshResearchSettings();
      }
    };

    source.addEventListener("step_completed", applyEventStatus);
    source.addEventListener("step_skipped", applyEventStatus);
    source.addEventListener("step_failed", handleStepFailed);
    source.addEventListener("run_cancelling", () => {
      isCancellingRunRef.current = true;
      setIsCancellingRun(true);
      setStatus("Abbruch angefordert...");
    });

    source.addEventListener("run_completed", (event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data) as RunCompletedEvent;
        if (payload.final_status) {
          applySessionMenuStatus(payload.final_status);
        }
        setStatus(payload.ok ? "Alle Schritte wurden ausgeführt." : "Lauf beendet.");
      } catch (error) {
        logClientError("SessionMenu.runCompletedEvent", error, { runId });
        setStatus("Alle Schritte wurden ausgeführt.");
      } finally {
        setIsRunningAll(false);
        setCurrentRunId(null);
        setCurrentRunLabel(null);
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
          applySessionMenuStatus(payload.final_status);
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
        setCurrentRunLabel(null);
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
          applySessionMenuStatus(payload.final_status);
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
        setCurrentRunLabel(null);
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
    setCurrentRunLabel(null);
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
      setCurrentRunLabel(null);
      setIsCancellingRun(false);
      beginRunEventStream(start.run_id);
    } catch (error) {
      logSessionStartError("SessionMenu.startRunAll", error, {
        appSessionId: state.appSessionId,
      });
      setStatus(formatSessionStartError(error));
      setIsRunningAll(false);
      setCurrentRunId(null);
      setCurrentRunLabel(null);
      setIsCancellingRun(false);
      isCancellingRunRef.current = false;
      emitRunAllStepCleared();
      stopRunMonitoring();
    }
  };

  const menuContent = (
    <div
      ref={menuRef}
      className="fixed z-[60] w-[360px] rounded-2xl border border-slate-200 bg-white p-4 text-xs text-slate-700 shadow-2xl"
      style={{ top: menuPos.top, left: menuPos.left }}
    >
      <div className="flex items-center justify-between">
        <div className="font-semibold text-slate-900">Session Aktionen</div>
        <button
          onClick={() => setIsOpen(false)}
          className="flex h-7 w-7 items-center justify-center rounded-full text-sm font-semibold text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
          aria-label="Session Aktionsmenü schließen"
        >
          ×
        </button>
      </div>
      <div className="mt-4 space-y-2">
        <div className={menuSectionLabelClass}>
          Session
        </div>
        <button
          onClick={handleNewSession}
          className={menuPrimaryButtonClass}
        >
          Neue Session starten
        </button>
        <select
          value={selectedSession}
          onChange={(event) => handleSessionSelect(event.target.value)}
          disabled={isLoadingSession}
          className="w-full rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 disabled:cursor-wait disabled:bg-slate-100 disabled:text-slate-400"
          aria-label="Session wechseln"
        >
          <option value="">Session auswählen</option>
          {formattedSessions.map((session) => (
            <option key={session.app_session_id} value={session.app_session_id}>
              {session.label}
            </option>
          ))}
        </select>
      </div>
      <div className="mt-4 space-y-2 border-t border-slate-100 pt-3">
        <div className={menuSectionLabelClass}>
          Ablauf
        </div>
        <button
          onClick={handleRunAllSteps}
          className={
            isRunningAll
              ? isCancellingRun
                ? menuCancellingButtonClass
                : menuRunningButtonClass
              : isRunAllActionDisabled
                ? menuDisabledButtonClass
                : menuSecondaryButtonClass
          }
          disabled={isRunAllActionDisabled}
        >
          {isRunningAll && (
            <span className="h-3 w-3 shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent" />
          )}
          <span>{runAllButtonLabel}</span>
        </button>
        <button
          onClick={handleUndoLastStep}
          disabled={!lastStepLabel || isUndoing || hasActiveWorkflowRun}
          className={
            lastStepLabel && !isUndoing && !hasActiveWorkflowRun
              ? menuSecondaryButtonClass
              : menuDisabledButtonClass
          }
        >
          {isUndoing
            ? "Bitte warten..."
            : `\"${lastStepLabel || "Letzten Schritt"}\" zurücksetzen`}
        </button>
      </div>
      <div className="mt-4 space-y-2 border-t border-slate-100 pt-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className={menuSectionLabelClass}>
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
                ? "border-slate-700 bg-slate-800 text-white"
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
      </div>
      <div className="mt-4 space-y-2 border-t border-slate-100 pt-3">
        <div className={menuSectionLabelClass}>
          Export
        </div>
        <button
          onClick={handleDownloadComplianceExport}
          disabled={
            isDownloadingComplianceExport ||
            isRunningAll ||
            !state.totalCostReady
          }
          className={menuExportButtonClass}
        >
          {isDownloadingComplianceExport
            ? "Vorblatt und Begründung werden geladen..."
            : "Vorblatt und Begründung exportieren"}
        </button>
        <button
          onClick={handleDownloadDeepResearchReport}
          disabled={isDownloadingResearch || researchStatus !== "parsed"}
          className={menuExportButtonClass}
        >
          {isDownloadingResearch
            ? "Bericht wird geladen..."
            : "Deep-Research-Bericht herunterladen"}
        </button>
        {isComplianceEditChoiceVisible && (
          <div className="ccc-status-warning rounded-xl border border-amber-200 bg-amber-50 p-3 text-[11px] text-amber-900">
            <div className="font-semibold">
              Bearbeitete EA-Werte vorhanden.
            </div>
            <div className="mt-1">
              Der Export verwendet immer den aktuell sichtbaren EA-Stand. Wenn du Modellwerte exportieren möchtest, setze die EA-Werte zuerst in „EA bearbeiten“ zurück.
            </div>
            <div className="mt-2 space-y-1">
              <button
                type="button"
                onClick={() => handleComplianceEditChoice("use_user_edits")}
                disabled={isDownloadingComplianceExport}
                className="w-full rounded-lg bg-[var(--ccc-status-review-text)] px-2 py-1.5 text-left font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                Bearbeitete EA-Werte verwenden
              </button>
              <button
                type="button"
                onClick={() => handleComplianceEditChoice(null)}
                disabled={isDownloadingComplianceExport}
                className="w-full rounded-lg px-2 py-1.5 text-left font-semibold text-[var(--ccc-status-review-text)] hover:bg-[var(--ccc-status-review-bg)] disabled:cursor-not-allowed disabled:opacity-60"
              >
                Abbrechen
              </button>
            </div>
          </div>
        )}
      </div>
      {otherStatus && (
        <div className="ccc-status-warning mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] font-semibold text-amber-800">
          {otherStatus}
        </div>
      )}
    </div>
  );

  return (
    <div ref={triggerRef} className="relative">
      <div
        className={`flex h-10 items-center overflow-hidden rounded-xl border font-semibold shadow-sm ${
          variant === "header"
            ? "border-white/30 bg-white/10 text-white"
            : "border-slate-200 bg-white text-slate-700"
        } text-sm`}
      >
        <div className="flex items-center gap-2 px-4 py-2">
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            className="h-5 w-6 shrink-0"
          >
            <ellipse
              cx="12"
              cy="5"
              rx="8.8"
              ry="3"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="1.8"
            />
            <path
              d="M3.2 5v14c0 1.7 3.9 3 8.8 3s8.8-1.3 8.8-3V5"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="1.8"
            />
            <path
              d="M3.2 12c0 1.7 3.9 3 8.8 3s8.8-1.3 8.8-3"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="1.8"
            />
          </svg>
          <span>Session</span>
          <span className="select-text font-mono">{state.appSessionId}</span>
        </div>
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          title="Session Aktionen"
          aria-label={isOpen ? "Session Aktionen schließen" : "Session Aktionen öffnen"}
          aria-expanded={isOpen}
          className={`h-full border-l px-3 py-2 transition ${
            variant === "header"
              ? "border-white/20 hover:bg-white/10"
              : "border-slate-200 hover:bg-slate-50"
          }`}
        >
          {isOpen ? "⌃" : "⌄"}
        </button>
      </div>
      {isOpen && isMounted ? createPortal(menuContent, document.body) : null}
    </div>
  );
}
