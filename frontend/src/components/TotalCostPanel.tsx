"use client";

import { useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";
import { formatActionErrorMessage, logClientError } from "@/lib/errorFeedback";
import { useRunAllStepBusy } from "@/lib/runAllStepEvents";

function formatEuro(value: number | null | undefined): string {
  return typeof value === "number" ? `${value.toFixed(2)} EUR` : "n. v.";
}

export default function TotalCostPanel() {
  const { state, setCurrentTab, setTotalCostReady } = useApp();
  const [status, setStatus] = useState<string | null>(null);
  const [statusTone, setStatusTone] = useState<"success" | "error">("success");
  const [isRunning, setIsRunning] = useState(false);
  const isRunAllBusy = useRunAllStepBusy("total_cost");
  const isBusy = isRunning || isRunAllBusy;

  const canRun =
    state.processStepsReady &&
    state.effortReady &&
    !state.totalCostReady &&
    !isBusy;

  const label = state.totalCostReady
    ? "Bereits berechnet"
    : isBusy
      ? "Bitte warten..."
      : "Gesamtkosten berechnen";

  const handleCompute = async () => {
    if (!canRun) {
      return;
    }
    setStatus(null);
    setStatusTone("success");
    setIsRunning(true);
    try {
      const [adminResult, businessResult, citizensResult] = await Promise.all([
        apiClient.computeTotalCost({
          appSessionId: state.appSessionId,
          normAddressee: "administration",
        }),
        apiClient.computeTotalCost({
          appSessionId: state.appSessionId,
          normAddressee: "business",
        }),
        apiClient.computeTotalCost({
          appSessionId: state.appSessionId,
          normAddressee: "citizens",
        }),
      ]);
      window.dispatchEvent(new Event("tiles-updated"));
      setTotalCostReady(true);
      const adminLine = ` Verwaltung: ${formatEuro(adminResult.total_cost)}.`;
      const businessLine = ` Wirtschaft: ${formatEuro(businessResult.total_cost)}.`;
      const citizensTimeLine =
        typeof citizensResult.total_time_hours === "number"
          ? ` Zeit ${citizensResult.total_time_hours.toFixed(2)} Std.`
          : null;
      const citizensExpensesLine =
        typeof citizensResult.total_expenses === "number"
          ? ` Sachaufwand ${citizensResult.total_expenses.toFixed(2)} EUR`
          : null;
      const citizensDetail =
        citizensTimeLine || citizensExpensesLine
          ? ` ${[citizensTimeLine, citizensExpensesLine].filter(Boolean).join(", ")}.`
          : " Aufwand berechnet.";
      const citizensLine = ` Buerger:${citizensDetail}`;
      setStatusTone("success");
      setStatus(
        `Kosten fuer Verwaltung, Wirtschaft und Buerger berechnet.${adminLine}${businessLine}${citizensLine}`
      );
      setCurrentTab(6);
    } catch (error) {
      logClientError("TotalCostPanel.computeTotalCost", error, {
        appSessionId: state.appSessionId,
      });
      setStatusTone("error");
      setStatus(formatActionErrorMessage("Gesamtkosten konnten nicht berechnet werden", error));
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <section className="w-full border-b border-white/60 bg-white/80 px-6 py-4 backdrop-blur">
      <div className="mx-auto max-w-6xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="text-xs text-slate-600">
            Beim Klick auf „Gesamtkosten berechnen“ werden Schritt-, Fallgruppen-
            und Prozesskosten in einem Durchgang für Verwaltung, Wirtschaft und
            Bürger berechnet, dabei aber je Normadressat eigene Kostensichten
            erzeugt. Der Umschalter zeigt die Sicht des ausgewählten Normadressaten.
          </p>
          <button
            onClick={handleCompute}
            disabled={!canRun}
            className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
              canRun
                ? "bg-slate-900 text-white"
                : "cursor-not-allowed bg-slate-200 text-slate-500"
            }`}
          >
            {label}
          </button>
        </div>

        {status && (
          <div
            className={`rounded-xl px-3 py-2 text-xs font-semibold ${
              statusTone === "success"
                ? "border border-emerald-200 bg-emerald-50 text-emerald-800"
                : "border border-amber-200 bg-amber-50 text-amber-800"
            }`}
          >
            {status}
          </div>
        )}
      </div>
    </section>
  );
}
