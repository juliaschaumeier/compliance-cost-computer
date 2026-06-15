"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";
import type { ApiClientError } from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";
import { useMounted } from "@/lib/useMounted";
import type { NormAddressee } from "@/types";

import EaCaseMetricsTab from "./EaCaseMetricsTab";
import EaEffortMetricsTab from "./EaEffortMetricsTab";
import EaPayRatesTab from "./EaPayRatesTab";
import { useDebouncedSessionRecompute } from "./useDebouncedSessionRecompute";
import { useDrawerCloseGuard } from "./useDrawerCloseGuard";

type EaEditDrawerShellProps = {
  open: boolean;
  onClose: () => void;
};

type EditorTab = "pay_rates" | "case_metrics" | "effort_metrics";
type EaActivityState =
  | "idle"
  | "acquiring"
  | "owned"
  | "blocked_ea"
  | "blocked_workflow"
  | "unavailable";

const NORM_ADDRESSEE_LABELS: Record<NormAddressee, string> = {
  administration: "Verwaltung",
  business: "Wirtschaft",
  citizens: "Bürgerinnen und Bürger",
};

const TAB_COPY: Record<EditorTab, { title: string; hint: string }> = {
  pay_rates: {
    title: "Globale Lohnsätze",
    hint: "Lohnsätze für diese Session. Hier gesetzte Werte überschreiben die vom Modell genutzten Sätze für alle Schritte dieses Normadressaten. Ohne Eintrag gelten die Modellwerte.",
  },
  case_metrics: {
    title: "Fallzahlen",
    hint: "Bearbeite Betroffene und Häufigkeit je Fallgruppe für aktuelles Gesetz und Gesetzesentwurf.",
  },
  effort_metrics: {
    title: "Schrittkosten",
    hint: "Bearbeite Zeitaufwand in Minuten und Sachaufwand in Euro je Prozessschritt für aktuelles Gesetz und Gesetzesentwurf.",
  },
};

const EA_ACTIVITY_HEARTBEAT_MS = 30_000;

function detailRecord(error: unknown): Record<string, unknown> | null {
  const details = (error as ApiClientError | undefined)?.details;
  if (typeof details !== "object" || details === null || Array.isArray(details)) {
    return null;
  }
  return details as Record<string, unknown>;
}

function classifyEaActivityError(error: unknown): {
  state: EaActivityState;
  message: string;
} {
  const detail = detailRecord(error);
  if (detail?.error === "session_activity_conflict") {
    if (detail.active_type === "ea_edit") {
      return {
        state: "blocked_ea",
        message:
          "EA-Bearbeitung ist in dieser Session gerade in einem anderen Tab oder Fenster geöffnet. Bitte später erneut versuchen.",
      };
    }
    if (detail.active_type === "workflow") {
      return {
        state: "blocked_workflow",
        message:
          "EA-Bearbeitung ist während einer laufenden Ausführung in dieser Session gesperrt. Bitte warten Sie, bis der Lauf abgeschlossen ist.",
      };
    }
  }
  if (detail?.error === "session_activity_unavailable") {
    return {
      state: "unavailable",
      message:
        "EA-Bearbeitung ist nicht mehr aktiv. Bitte den Editor schließen und erneut öffnen.",
    };
  }
  return {
    state: "unavailable",
    message:
      "EA-Bearbeitung ist in dieser Session gerade nicht möglich. Bitte später erneut versuchen.",
  };
}

export default function EaEditDrawerShell({ open, onClose }: EaEditDrawerShellProps) {
  const isMounted = useMounted();
  const { state } = useApp();
  const [activeTab, setActiveTab] = useState<EditorTab>("pay_rates");
  const [activityState, setActivityState] = useState<EaActivityState>("idle");
  const [eaActivityId, setEaActivityId] = useState<string | null>(null);
  const [activityStatus, setActivityStatus] = useState<string | null>(null);
  const [resetConfirmOpen, setResetConfirmOpen] = useState(false);
  const [isResettingAllEaEdits, setIsResettingAllEaEdits] = useState(false);
  const [resetStatus, setResetStatus] = useState<string | null>(null);
  const [resetVersion, setResetVersion] = useState(0);
  const continueEditingRef = useRef<HTMLButtonElement | null>(null);
  const cancelResetRef = useRef<HTMLButtonElement | null>(null);
  const { recomputeStatus, runAutoRecompute } = useDebouncedSessionRecompute({
    appSessionId: state.appSessionId,
    normAddressee: state.selectedNormAddressee,
    eaActivityId,
    debounceMs: 400,
  });
  const {
    closeConfirmOpen,
    closeGuardHint,
    markTabDirty,
    requestClose,
    continueEditing,
    discardAndClose,
    leadToSave,
    resetDirtyState,
  } = useDrawerCloseGuard({
    open,
    sessionKey: state.appSessionId,
    tabs: TAB_COPY,
    onClose,
    onActivateTab: setActiveTab,
  });

  useEffect(() => {
    if (!closeConfirmOpen) {
      return;
    }
    continueEditingRef.current?.focus();
  }, [closeConfirmOpen]);

  useEffect(() => {
    if (!resetConfirmOpen) {
      return;
    }
    cancelResetRef.current?.focus();
  }, [resetConfirmOpen]);

  useEffect(() => {
    if (!open) {
      setResetConfirmOpen(false);
      setResetStatus(null);
      setActivityState("idle");
      return;
    }
    setResetStatus(null);
  }, [open, state.appSessionId]);

  useEffect(() => {
    if (activityState !== "owned") {
      resetDirtyState();
    }
  }, [activityState, resetDirtyState]);

  useEffect(() => {
    if (!open) {
      setEaActivityId(null);
      setActivityStatus(null);
      setActivityState("idle");
      return;
    }

    let cancelled = false;
    let acquiredActivityId: string | null = null;
    let heartbeatTimer: number | null = null;

    const stopHeartbeat = () => {
      if (heartbeatTimer !== null) {
        window.clearInterval(heartbeatTimer);
        heartbeatTimer = null;
      }
    };

    const release = (activityId: string | null) => {
      if (!activityId) {
        return;
      }
      void apiClient
        .releaseEaEditActivity({
          appSessionId: state.appSessionId,
          activityId,
        })
        .catch((error) => {
          logClientError("EaEditDrawerShell.releaseActivity", error, {
            appSessionId: state.appSessionId,
          });
        });
    };

    const heartbeat = async (activityId: string) => {
      try {
        await apiClient.heartbeatEaEditActivity({
          appSessionId: state.appSessionId,
          activityId,
        });
      } catch (error) {
        if (cancelled) {
          return;
        }
        stopHeartbeat();
        logClientError("EaEditDrawerShell.heartbeatActivity", error, {
          appSessionId: state.appSessionId,
        });
        setEaActivityId(null);
        setActivityState("unavailable");
        setActivityStatus(
          "EA-Bearbeitung ist nicht mehr aktiv. Bitte den Editor schließen und erneut öffnen."
        );
      }
    };

    setEaActivityId(null);
    setActivityState("acquiring");
    setActivityStatus("EA-Bearbeitung wird gesperrt...");
    apiClient
      .acquireEaEditActivity({ appSessionId: state.appSessionId })
      .then((payload) => {
        acquiredActivityId = payload.activity_id;
        if (cancelled) {
          release(acquiredActivityId);
          return;
        }
        setEaActivityId(payload.activity_id);
        setActivityState("owned");
        setActivityStatus(null);
        heartbeatTimer = window.setInterval(() => {
          void heartbeat(payload.activity_id);
        }, EA_ACTIVITY_HEARTBEAT_MS);
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        logClientError("EaEditDrawerShell.acquireActivity", error, {
          appSessionId: state.appSessionId,
        });
        setEaActivityId(null);
        const classified = classifyEaActivityError(error);
        setActivityState(classified.state);
        setActivityStatus(classified.message);
      });

    return () => {
      cancelled = true;
      stopHeartbeat();
      release(acquiredActivityId);
    };
  }, [open, state.appSessionId]);

  const ownsEaActivity = activityState === "owned" && Boolean(eaActivityId);
  const drawerReadOnly = !ownsEaActivity;

  const handleTabDirtyChange = (tab: EditorTab, dirty: boolean) => {
    if (drawerReadOnly) {
      markTabDirty(tab, false);
      return;
    }
    if (dirty) {
      setResetStatus(null);
    }
    markTabDirty(tab, dirty);
  };

  const handleResetAllEaEdits = async () => {
    if (drawerReadOnly || !eaActivityId) {
      return;
    }
    setIsResettingAllEaEdits(true);
    setResetStatus(null);
    try {
      await apiClient.resetSessionEaEdits({
        appSessionId: state.appSessionId,
        eaActivityId: eaActivityId ?? undefined,
      });
      setResetConfirmOpen(false);
      setResetVersion((value) => value + 1);
      window.dispatchEvent(new Event("tiles-updated"));
      setResetStatus(
        "Alle EA-Bearbeitungen wurden auf Modellwerte zurückgesetzt und die Gesamtkosten neu berechnet."
      );
    } catch (error) {
      logClientError("EaEditDrawerShell.resetAllEaEdits", error, {
        appSessionId: state.appSessionId,
      });
      setResetStatus("Zurücksetzen fehlgeschlagen. Bitte erneut versuchen.");
    } finally {
      setIsResettingAllEaEdits(false);
    }
  };

  if (!isMounted || !open) {
    return null;
  }

  const normAddresseeLabel = NORM_ADDRESSEE_LABELS[state.selectedNormAddressee];
  const activityStatusClass =
    activityState === "blocked_ea"
      ? "border-amber-300 bg-amber-100 text-amber-800"
      : "border-slate-200 bg-slate-100 text-slate-700";

  const body = (
    <div className="pointer-events-none fixed inset-0 z-[85]">
      <div className="absolute inset-0 bg-slate-900/25" />
      <div className="flex h-full items-stretch justify-end">
        <section
          className="pointer-events-auto relative h-full w-full max-w-[980px] border-l border-slate-300 bg-white shadow-2xl"
          onKeyDown={(event) => {
            if (event.key === "Escape" && closeConfirmOpen) {
              event.stopPropagation();
              continueEditing();
            }
          }}
        >
          <header className="border-b border-slate-200 bg-slate-50 px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold text-slate-900">
                Erfüllungsaufwand bearbeiten für {normAddresseeLabel}
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setResetConfirmOpen(true)}
                  disabled={
                    state.isComplianceExportRunning ||
                    isResettingAllEaEdits ||
                    drawerReadOnly ||
                    !eaActivityId
                  }
                  className="ccc-danger-outline rounded-full border border-rose-200 px-3 py-1 text-xs font-semibold text-rose-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Alle EA-Werte auf Modellwerte zurücksetzen
                </button>
                <button
                  onClick={requestClose}
                  className="rounded-full border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-700"
                >
                  Schließen
                </button>
              </div>
            </div>
            <div className="mt-3 flex gap-2">
              {(["pay_rates", "case_metrics", "effort_metrics"] as EditorTab[]).map((tab) => (
                <button
                  key={tab}
                  onClick={() => {
                    setResetStatus(null);
                    setActiveTab(tab);
                  }}
                  className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                    activeTab === tab
                      ? "border-slate-900 bg-slate-900 text-white"
                      : "border-slate-300 bg-white text-slate-700"
                  }`}
                >
                  {TAB_COPY[tab].title}
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs text-slate-600">{TAB_COPY[activeTab].hint}</p>
            {closeGuardHint && (
              <div className="ea-notice mt-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
                {closeGuardHint}
              </div>
            )}
            {state.isComplianceExportRunning && (
              <div className="mt-2 rounded-xl border border-slate-200 bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700">
                Vorblatt und Begründung werden gerade erzeugt. EA-Werte sind bis zum Abschluss gesperrt.
              </div>
            )}
            {activityStatus && (
              <div
                className={`mt-2 rounded-xl border px-3 py-2 text-xs font-semibold ${activityStatusClass}`}
              >
                {activityStatus}
              </div>
            )}
            {resetStatus && (
              <div className="ea-notice mt-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
                {resetStatus}
              </div>
            )}
          </header>
          <div className="h-[calc(100%-140px)] overflow-auto px-4 py-4">
            {state.isComplianceExportRunning ? (
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-700">
                Der Export verwendet einen Session-Snapshot. Bitte warte, bis die PDF-Erstellung abgeschlossen ist, bevor du EA-Werte änderst.
              </div>
            ) : (
              <>
                <EaPayRatesTab
                  key={`pay-rates-${resetVersion}`}
                  open={open}
                  active={activeTab === "pay_rates"}
                  appSessionId={state.appSessionId}
                  normAddressee={state.selectedNormAddressee}
                  eaActivityId={eaActivityId}
                  readOnly={drawerReadOnly}
                  runAutoRecompute={runAutoRecompute}
                  onDirtyChange={(dirty) => handleTabDirtyChange("pay_rates", dirty)}
                />
                <EaCaseMetricsTab
                  key={`case-metrics-${resetVersion}`}
                  open={open}
                  active={activeTab === "case_metrics"}
                  appSessionId={state.appSessionId}
                  normAddressee={state.selectedNormAddressee}
                  eaActivityId={eaActivityId}
                  readOnly={drawerReadOnly}
                  runAutoRecompute={runAutoRecompute}
                  onDirtyChange={(dirty) => handleTabDirtyChange("case_metrics", dirty)}
                />
                <EaEffortMetricsTab
                  key={`effort-metrics-${resetVersion}`}
                  open={open}
                  active={activeTab === "effort_metrics"}
                  appSessionId={state.appSessionId}
                  normAddressee={state.selectedNormAddressee}
                  eaActivityId={eaActivityId}
                  readOnly={drawerReadOnly}
                  runAutoRecompute={runAutoRecompute}
                  onDirtyChange={(dirty) => handleTabDirtyChange("effort_metrics", dirty)}
                />
              </>
            )}
            {recomputeStatus && (
              <div className="ea-notice mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
                {recomputeStatus}
              </div>
            )}
          </div>
          {closeConfirmOpen && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-900/30 p-4">
              <div
                role="dialog"
                aria-modal="true"
                aria-labelledby="ea-unsaved-title"
                className="w-full max-w-md rounded-2xl border border-slate-300 bg-white p-4 shadow-2xl"
              >
                <div id="ea-unsaved-title" className="text-sm font-semibold text-slate-900">
                  Ungespeicherte Änderungen
                </div>
                <p className="mt-2 text-xs text-slate-600">
                  Es gibt ungespeicherte Änderungen in diesem Editor.
                </p>
                <div className="mt-4 flex flex-wrap justify-end gap-2">
                  <button
                    ref={continueEditingRef}
                    type="button"
                    onClick={continueEditing}
                    className="rounded-full border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700"
                  >
                    Weiter bearbeiten
                  </button>
                  <button
                    type="button"
                    onClick={discardAndClose}
                    className="ccc-danger-outline rounded-full border border-rose-300 px-3 py-1.5 text-xs font-semibold text-rose-700"
                  >
                    Verwerfen & schließen
                  </button>
                  <button
                    type="button"
                    onClick={leadToSave}
                    className="rounded-full bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white"
                  >
                    Zum Speichern führen
                  </button>
                </div>
              </div>
            </div>
          )}
          {resetConfirmOpen && (
            <div className="absolute inset-0 z-20 flex items-center justify-center bg-slate-900/30 p-4">
              <div
                role="dialog"
                aria-modal="true"
                aria-labelledby="ea-reset-all-title"
                className="w-full max-w-lg rounded-2xl border border-slate-300 bg-white p-4 shadow-2xl"
              >
                <div id="ea-reset-all-title" className="text-sm font-semibold text-slate-900">
                  Alle EA-Werte auf Modellwerte zurücksetzen?
                </div>
                <p className="mt-2 text-xs text-slate-600">
                  Dies setzt Lohnsätze, Fallzahlen und Schrittkosten für alle Normadressaten dieser Session zurück. Anschließend werden die Gesamtkosten neu berechnet.
                </p>
                <div className="mt-4 flex flex-wrap justify-end gap-2">
                  <button
                    ref={cancelResetRef}
                    type="button"
                    onClick={() => setResetConfirmOpen(false)}
                    disabled={isResettingAllEaEdits}
                    className="rounded-full border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Abbrechen
                  </button>
                  <button
                    type="button"
                    onClick={handleResetAllEaEdits}
                    disabled={isResettingAllEaEdits}
                    className="ccc-danger-action rounded-full bg-rose-700 px-3 py-1.5 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:bg-rose-300"
                  >
                    {isResettingAllEaEdits ? "Wird zurückgesetzt..." : "Zurücksetzen"}
                  </button>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );

  return createPortal(body, document.body);
}
