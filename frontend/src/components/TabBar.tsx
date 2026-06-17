"use client";

import { useState } from "react";
import { createPortal } from "react-dom";

import { useApp } from "@/contexts/AppContext";
import LlmMonitorConsole from "@/components/LlmMonitorConsole";
import { isLlmConsoleEnabled } from "@/lib/llmConsoleConfig";
import { useMounted } from "@/lib/useMounted";

const tabs: Array<{ id: number; label: string; shortLabel: string }> = [
  { id: 0, label: "Gesetz auswählen", shortLabel: "Upload" },
  { id: 1, label: "Vorgaben identifizieren", shortLabel: "Vorgaben" },
  { id: 2, label: "Prozesse bündeln", shortLabel: "Prozesse" },
  { id: 3, label: "Fallgruppen entwickeln", shortLabel: "Fälle" },
  { id: 4, label: "Prozessschritte bestimmen", shortLabel: "Schritte" },
  { id: 5, label: "Aufwand quantifizieren", shortLabel: "Aufwand" },
  { id: 6, label: "Gesamtkosten berechnen", shortLabel: "Kosten" },
];

type TabState = {
  summaryReady: boolean;
  regulationsReady: boolean;
  processesReady: boolean;
  caseGroupsReady: boolean;
  processStepsReady: boolean;
  effortReady: boolean;
  totalCostReady: boolean;
};

function isTabDisabled(tabId: number, state: TabState): boolean {
  if (tabId === 0) return state.summaryReady;
  if (tabId === 1) return !state.summaryReady || state.regulationsReady;
  if (tabId === 2) return !state.regulationsReady || state.processesReady;
  if (tabId === 3) return !state.processesReady || state.caseGroupsReady;
  if (tabId === 4) return !state.caseGroupsReady || state.processStepsReady;
  if (tabId === 5) return !state.processStepsReady || state.effortReady;
  if (tabId === 6) return !state.effortReady;
  return false;
}

export default function TabBar() {
  const { state, setCurrentTab } = useApp();
  const [llmConsoleOpen, setLlmConsoleOpen] = useState(false);
  const isMounted = useMounted();
  const showLlmConsole = isLlmConsoleEnabled();

  return (
    <div className="border-b border-white/30 bg-white/70 backdrop-blur-lg">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="hidden grid-cols-7 gap-2 py-3 lg:grid">
          {tabs.map((tab) => {
            const isActive = tab.id === state.currentTab;
            const isCompletedFinalStep = tab.id === 6 && state.totalCostReady;
            const shouldHighlight = isActive && !isCompletedFinalStep;
            const isDisabled = isTabDisabled(tab.id, state);
            const isVisuallyMuted = isDisabled || isCompletedFinalStep;
            return (
              <button
                key={tab.id}
                onClick={() => setCurrentTab(tab.id)}
                disabled={isDisabled}
                className={`flex min-h-12 w-full min-w-0 items-center gap-2 rounded-2xl border px-3 py-2 text-left text-[13px] font-semibold transition-all ${
                  shouldHighlight
                    ? "border-slate-700 bg-slate-800 text-white shadow-lg"
                    : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50"
                } ${isVisuallyMuted ? "opacity-50" : ""} ${
                  isDisabled ? "cursor-not-allowed" : ""
                }`}
              >
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs ${
                    shouldHighlight
                      ? "bg-white text-slate-900"
                      : "bg-slate-100 text-slate-700"
                  }`}
                >
                  {tab.id + 1}
                </span>
                <span className="min-w-0 leading-tight">{tab.label}</span>
              </button>
            );
          })}
        </div>
        <div className="flex gap-2 overflow-x-auto py-3 lg:hidden">
          {tabs.map((tab) => {
            const isActive = tab.id === state.currentTab;
            const isCompletedFinalStep = tab.id === 6 && state.totalCostReady;
            const shouldHighlight = isActive && !isCompletedFinalStep;
            const isDisabled = isTabDisabled(tab.id, state);
            const isVisuallyMuted = isDisabled || isCompletedFinalStep;
            return (
              <button
                key={tab.id}
                onClick={() => setCurrentTab(tab.id)}
                disabled={isDisabled}
                className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                  shouldHighlight
                    ? "border-slate-700 bg-slate-800 text-white"
                    : "border-slate-200 bg-white text-slate-600"
                } ${isVisuallyMuted ? "opacity-50" : ""} ${
                  isDisabled ? "cursor-not-allowed" : ""
                }`}
              >
                {tab.shortLabel}
              </button>
            );
          })}
        </div>
      </div>
      {showLlmConsole &&
        isMounted &&
        createPortal(
          <button
            type="button"
            onClick={() => setLlmConsoleOpen((prev) => !prev)}
            className="llm-console-fab"
            data-open={llmConsoleOpen ? "true" : "false"}
            title={llmConsoleOpen ? "LLM Konsole schließen" : "LLM Konsole öffnen"}
            aria-label={llmConsoleOpen ? "LLM Konsole schließen" : "LLM Konsole öffnen"}
          >
            <span>LLM</span>
          </button>,
          document.body
        )}
      <LlmMonitorConsole
        open={llmConsoleOpen}
        onClose={() => setLlmConsoleOpen(false)}
      />
    </div>
  );
}
