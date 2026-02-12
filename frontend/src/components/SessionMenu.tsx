"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";
import { SessionSummary } from "@/types";

type SessionMenuProps = {
  compact?: boolean;
};

export default function SessionMenu({ compact }: SessionMenuProps) {
  const {
    state,
    setCurrentTab,
    setSessionId,
    setSummaryReady,
    setRegulationsReady,
    setProcessesReady,
    setCaseGroupsReady,
    setProcessStepsReady,
    setEffortReady,
    setTotalCostReady,
  } = useApp();
  const [isOpen, setIsOpen] = useState(false);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedSession, setSelectedSession] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [isUndoing, setIsUndoing] = useState(false);
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
      } catch {
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
      return {
        ...session,
        label: `${session.app_session_id} · ${label}`,
      };
    });
  }, [sessions]);

  const resetStatus = () => setStatus(null);

  const lastStepLabel = useMemo(() => {
    if (state.totalCostReady) return "Gesamtkosten berechnen";
    if (state.effortReady) return "Aufwand berechnen";
    if (state.processStepsReady) return "Prozessschritte bestimmen";
    if (state.caseGroupsReady) return "Fallgruppen entwickeln";
    if (state.processesReady) return "Prozesse bündeln";
    if (state.regulationsReady) return "Vorgaben bestimmen";
    if (state.summaryReady) return "CCC starten";
    return null;
  }, [
    state.totalCostReady,
    state.effortReady,
    state.processStepsReady,
    state.caseGroupsReady,
    state.processesReady,
    state.regulationsReady,
    state.summaryReady,
  ]);

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
      await apiClient.rebuildTiles(state.sessionId);
      window.dispatchEvent(new Event("tiles-updated"));
      setStatus("Tiles der Session wurden neu geladen.");
    } catch {
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
      setSessionId(selectedSession);
      setSummaryReady(sessionStatus.summary_ready);
      setRegulationsReady(sessionStatus.regulations_ready);
      setProcessesReady(sessionStatus.processes_ready);
      setCaseGroupsReady(sessionStatus.case_groups_ready);
      setProcessStepsReady(sessionStatus.process_steps_ready);
      setEffortReady(sessionStatus.effort_ready);
      setTotalCostReady(sessionStatus.total_cost_ready);
      setCurrentTab(0);
      await apiClient.rebuildTiles(selectedSession);
      window.dispatchEvent(new Event("tiles-updated"));
      setIsOpen(false);
    } catch {
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
      const result = await apiClient.undoLastStep(state.sessionId);
      if (result.status === "no-op") {
        setStatus("Kein Schritt zum Zurücksetzen vorhanden.");
        return;
      }
      await apiClient.rebuildTiles(state.sessionId);
      window.dispatchEvent(new Event("tiles-updated"));
      setStatus(`Letzter Schritt zurückgesetzt: ${result.undone_label || lastStepLabel}`);
    } catch {
      setStatus("Letzter Schritt konnte nicht zurückgesetzt werden.");
    } finally {
      setIsUndoing(false);
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
          {state.sessionId}
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
