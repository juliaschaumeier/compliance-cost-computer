"use client";

import { useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { apiClient, buildLlmRequestOptions } from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";

export default function CaseGroupsPanel() {
  const { state, setCurrentTab, setCaseGroupsReady } = useApp();
  const [status, setStatus] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const canRun = state.processesReady && !state.caseGroupsReady && !isRunning;

  const handleDevelop = async () => {
    if (!canRun) {
      return;
    }
    setStatus(null);
    setIsRunning(true);
    const llm = buildLlmRequestOptions({
      selectedModel: state.selectedModel,
      availableModels: state.availableModels,
    });
    try {
      await apiClient.developCaseGroups({
        appSessionId: state.appSessionId,
        model: llm.model,
        provider: llm.provider,
        keys: llm.keys,
      });
      window.dispatchEvent(new Event("tiles-updated"));
      setCaseGroupsReady(true);
      setCurrentTab(4);
    } catch (error) {
      logClientError("CaseGroupsPanel.developCaseGroups", error, {
        appSessionId: state.appSessionId,
      });
      setStatus("Fallgruppen konnten nicht entwickelt werden.");
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <section className="w-full border-b border-white/60 bg-white/80 px-6 py-4 backdrop-blur">
      <div className="mx-auto max-w-6xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="text-xs text-slate-600">
            <span className="block">
              Wenn Prozesse auf unterschiedlichen Wegen erfüllt werden, werden
              Fallgruppen gebildet.
            </span>
            <span className="block">
              Jede Fallgruppe beschreibt eine typische Ausprägung der Ausführung,
              damit der Erfüllungsaufwand getrennt ermittelt werden kann.
            </span>
          </p>
          <button
            onClick={handleDevelop}
            disabled={!canRun}
            className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
              canRun
                ? "bg-slate-900 text-white"
                : "cursor-not-allowed bg-slate-200 text-slate-500"
            }`}
          >
            {isRunning ? "Bitte warten..." : "Fallgruppen entwickeln"}
          </button>
        </div>

        {status && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
            {status}
          </div>
        )}
      </div>
    </section>
  );
}
