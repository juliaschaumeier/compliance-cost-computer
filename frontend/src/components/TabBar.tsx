"use client";

import { useState } from "react";
import { createPortal } from "react-dom";

import { useApp } from "@/contexts/AppContext";
import LlmMonitorConsole from "@/components/LlmMonitorConsole";
import { isLlmConsoleEnabled } from "@/lib/llmConsoleConfig";
import { useMounted } from "@/lib/useMounted";
import SessionMenu from "@/components/SessionMenu";

const tabs: Array<{ id: number; label: string; shortLabel: string }> = [
  { id: 0, label: "Gesetz auswählen", shortLabel: "Upload" },
  { id: 1, label: "Regelungen identifizieren", shortLabel: "Regeln" },
  { id: 2, label: "Prozesse bündeln", shortLabel: "Prozesse" },
  { id: 3, label: "Fallgruppen entwickeln", shortLabel: "Fälle" },
  { id: 4, label: "Prozessschritte", shortLabel: "Schritte" },
  { id: 5, label: "Aufwand berechnen", shortLabel: "Aufwand" },
  { id: 6, label: "Gesamtkosten", shortLabel: "Kosten" },
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
        <div className="hidden items-center gap-2 overflow-x-auto py-4 lg:flex">
          {tabs.map((tab) => {
            const isActive = tab.id === state.currentTab;
            const isDisabled = isTabDisabled(tab.id, state);
            return (
              <button
                key={tab.id}
                onClick={() => setCurrentTab(tab.id)}
                disabled={isDisabled}
                className={`rounded-full border px-4 py-2 text-sm font-semibold transition-all ${
                  isActive
                    ? "border-slate-800 bg-slate-900 text-white shadow-lg"
                    : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50"
                } ${isDisabled ? "cursor-not-allowed opacity-50" : ""}`}
              >
                {tab.id + 1}. {tab.label}
              </button>
            );
          })}
          <div className="relative ml-4 shrink-0">
            <SessionMenu />
          </div>
        </div>
        <div className="flex gap-2 overflow-x-auto py-3 lg:hidden">
          {tabs.map((tab) => {
            const isActive = tab.id === state.currentTab;
            const isDisabled = isTabDisabled(tab.id, state);
            return (
              <button
                key={tab.id}
                onClick={() => setCurrentTab(tab.id)}
                disabled={isDisabled}
                className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                  isActive
                    ? "border-slate-800 bg-slate-900 text-white"
                    : "border-slate-200 bg-white text-slate-600"
                } ${isDisabled ? "cursor-not-allowed opacity-50" : ""}`}
              >
                {tab.shortLabel}
              </button>
            );
          })}
        </div>
        <div className="flex items-center justify-end pb-3 lg:hidden">
          <SessionMenu compact />
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
