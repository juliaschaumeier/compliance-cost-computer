"use client";

import { useState } from "react";

import { useApp } from "@/contexts/AppContext";
import LlmMonitorConsole from "./LlmMonitorConsole";
import SessionMenu from "@/components/SessionMenu";

const tabs = [
  { id: 0, label: "Gesetz auswählen", shortLabel: "Upload" },
  { id: 1, label: "Regelungen identifizieren", shortLabel: "Regeln" },
  { id: 2, label: "Prozesse bündeln", shortLabel: "Prozesse" },
  { id: 3, label: "Fallgruppen entwickeln", shortLabel: "Fälle" },
  { id: 4, label: "Prozessschritte", shortLabel: "Schritte" },
  { id: 5, label: "Aufwand berechnen", shortLabel: "Aufwand" },
  { id: 6, label: "Gesamtkosten", shortLabel: "Kosten" },
];

export default function TabBar() {
  const { state, setCurrentTab } = useApp();
  const [llmConsoleOpen, setLlmConsoleOpen] = useState(false);

  return (
    <div className="border-b border-white/30 bg-white/70 backdrop-blur-lg">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="hidden items-center gap-2 overflow-x-auto py-4 lg:flex">
          {tabs.map((tab) => {
            const isActive = tab.id === state.currentTab;
            const isDisabled =
              (tab.id === 0 && state.summaryReady) ||
              (tab.id === 1 && (!state.summaryReady || state.regulationsReady)) ||
              (tab.id === 2 && (!state.regulationsReady || state.processesReady)) ||
              (tab.id === 3 && (!state.processesReady || state.caseGroupsReady)) ||
              (tab.id === 4 && (!state.caseGroupsReady || state.processStepsReady)) ||
              (tab.id === 5 &&
                (!state.processStepsReady || state.effortReady)) ||
              (tab.id === 6 && !state.effortReady);
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
          <button
            type="button"
            onClick={() => setLlmConsoleOpen(true)}
            className="ml-2 rounded-full border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-900 hover:bg-amber-100"
          >
            LLM Konsole
          </button>
          <div className="relative ml-4 shrink-0">
            <SessionMenu />
          </div>
        </div>
        <div className="flex gap-2 overflow-x-auto py-3 lg:hidden">
          {tabs.map((tab) => {
            const isActive = tab.id === state.currentTab;
            const isDisabled =
              (tab.id === 0 && state.summaryReady) ||
              (tab.id === 1 && (!state.summaryReady || state.regulationsReady)) ||
              (tab.id === 2 && (!state.regulationsReady || state.processesReady)) ||
              (tab.id === 3 && (!state.processesReady || state.caseGroupsReady)) ||
              (tab.id === 4 && (!state.caseGroupsReady || state.processStepsReady)) ||
              (tab.id === 5 &&
                (!state.processStepsReady || state.effortReady)) ||
              (tab.id === 6 && !state.effortReady);
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
          <button
            type="button"
            onClick={() => setLlmConsoleOpen(true)}
            className="mr-2 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-900"
          >
            LLM Konsole
          </button>
          <SessionMenu compact />
        </div>
      </div>
      <LlmMonitorConsole
        open={llmConsoleOpen}
        onClose={() => setLlmConsoleOpen(false)}
      />
    </div>
  );
}
