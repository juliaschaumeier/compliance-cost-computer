"use client";

import { useApp } from "@/contexts/AppContext";

const tabs = [
  { id: 0, label: "Gesetz hochladen", shortLabel: "Upload" },
  { id: 1, label: "Regelungen identifizieren", shortLabel: "Regeln" },
  { id: 2, label: "Prozesse bündeln", shortLabel: "Prozesse" },
  { id: 3, label: "Fallgruppen entwickeln", shortLabel: "Fälle" },
  { id: 4, label: "Prozessschritte", shortLabel: "Schritte" },
  { id: 5, label: "Aufwand berechnen", shortLabel: "Aufwand" },
  { id: 6, label: "Gesamtkosten", shortLabel: "Kosten" },
];

export default function TabBar() {
  const { state, setCurrentTab } = useApp();

  return (
    <div className="border-b border-white/30 bg-white/70 backdrop-blur-lg">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="hidden gap-2 overflow-x-auto py-4 lg:flex">
          {tabs.map((tab) => {
            const isActive = tab.id === state.currentTab;
            return (
              <button
                key={tab.id}
                onClick={() => setCurrentTab(tab.id)}
                className={`rounded-full border px-4 py-2 text-sm font-semibold transition-all ${
                  isActive
                    ? "border-slate-800 bg-slate-900 text-white shadow-lg"
                    : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                {tab.id + 1}. {tab.label}
              </button>
            );
          })}
        </div>
        <div className="flex gap-2 overflow-x-auto py-3 lg:hidden">
          {tabs.map((tab) => {
            const isActive = tab.id === state.currentTab;
            return (
              <button
                key={tab.id}
                onClick={() => setCurrentTab(tab.id)}
                className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                  isActive
                    ? "border-slate-800 bg-slate-900 text-white"
                    : "border-slate-200 bg-white text-slate-600"
                }`}
              >
                {tab.shortLabel}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
