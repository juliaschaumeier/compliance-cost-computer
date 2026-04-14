"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { useApp } from "@/contexts/AppContext";
import { useMounted } from "@/lib/useMounted";

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

const TAB_COPY: Record<EditorTab, { title: string; hint: string }> = {
  pay_rates: {
    title: "Globale Lohnsätze",
    hint: "Lege die aktiven Lohnsätze für diese Session fest. Werte gelten für alle Schritte.",
  },
  case_metrics: {
    title: "Fallzahlen",
    hint: "Bearbeite Betroffene und Häufigkeit je Fallgruppe für Gültig und Vorschlag.",
  },
  effort_metrics: {
    title: "Schrittkosten",
    hint: "Bearbeite Zeitaufwand und Sachaufwand je Prozessschritt für Gültig und Vorschlag.",
  },
};

export default function EaEditDrawerShell({ open, onClose }: EaEditDrawerShellProps) {
  const isMounted = useMounted();
  const { state } = useApp();
  const [activeTab, setActiveTab] = useState<EditorTab>("pay_rates");
  const continueEditingRef = useRef<HTMLButtonElement | null>(null);
  const { recomputeStatus, runAutoRecompute } = useDebouncedSessionRecompute({
    appSessionId: state.appSessionId,
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

  if (!isMounted || !open) {
    return null;
  }

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
              <div className="text-sm font-semibold text-slate-900">EA bearbeiten</div>
              <button
                onClick={requestClose}
                className="rounded-full border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-700"
              >
                Schließen
              </button>
            </div>
            <div className="mt-3 flex gap-2">
              {(["pay_rates", "case_metrics", "effort_metrics"] as EditorTab[]).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
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
              <div className="mt-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
                {closeGuardHint}
              </div>
            )}
          </header>
          <div className="h-[calc(100%-140px)] overflow-auto px-4 py-4">
            <EaPayRatesTab
              open={open}
              active={activeTab === "pay_rates"}
              appSessionId={state.appSessionId}
              runAutoRecompute={runAutoRecompute}
              onDirtyChange={(dirty) => markTabDirty("pay_rates", dirty)}
            />
            <EaCaseMetricsTab
              open={open}
              active={activeTab === "case_metrics"}
              appSessionId={state.appSessionId}
              normAddressee={state.selectedNormAddressee}
              runAutoRecompute={runAutoRecompute}
              onDirtyChange={(dirty) => markTabDirty("case_metrics", dirty)}
            />
            <EaEffortMetricsTab
              open={open}
              active={activeTab === "effort_metrics"}
              appSessionId={state.appSessionId}
              normAddressee={state.selectedNormAddressee}
              runAutoRecompute={runAutoRecompute}
              onDirtyChange={(dirty) => markTabDirty("effort_metrics", dirty)}
            />
            {recomputeStatus && (
              <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
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
                    className="rounded-full border border-rose-300 px-3 py-1.5 text-xs font-semibold text-rose-700"
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
        </section>
      </div>
    </div>
  );

  return createPortal(body, document.body);
}
