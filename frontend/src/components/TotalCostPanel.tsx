"use client";

import { useEffect, useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";
import { formatActionErrorMessage, logClientError } from "@/lib/errorFeedback";
import { useRunAllStepCancel } from "@/lib/useRunAllStepCancel";

export default function TotalCostPanel() {
  const { state, setCurrentTab, setTotalCostReady } = useApp();
  const [status, setStatus] = useState<string | null>(null);
  const [statusTone, setStatusTone] = useState<"success" | "error">("success");
  const [isRunning, setIsRunning] = useState(false);
  const runAllCancel = useRunAllStepCancel({
    stepKey: "total_cost",
    appSessionId: state.appSessionId,
    setStatus,
    logScope: "TotalCostPanel.cancelRunAll",
  });
  const isRunAllBusy = runAllCancel.isRunAllBusy;
  const isBusy = isRunning || isRunAllBusy;

  useEffect(() => {
    if (runAllCancel.isCancellingRunAll) {
      setStatusTone("error");
    }
  }, [runAllCancel.isCancellingRunAll]);

  const canRun =
    state.processStepsReady &&
    state.effortReady &&
    !state.totalCostReady &&
    !isBusy;

  const label = state.totalCostReady
    ? "Bereits berechnet"
    : isRunAllBusy
      ? runAllCancel.isCancellingRunAll
        ? "Abbruch wird ausgeführt..."
        : "Abbrechen"
      : isRunning
        ? "Bitte warten..."
      : "Gesamtkosten berechnen";

  const handleCompute = async () => {
    if (isRunAllBusy) {
      setStatusTone("error");
      await runAllCancel.cancelRunAllForStep();
      return;
    }
    if (!canRun) {
      return;
    }
    setStatus(null);
    setStatusTone("success");
    setIsRunning(true);
    const addressees = ["administration", "business", "citizens"] as const;
    const labels: Record<(typeof addressees)[number], string> = {
      administration: "Verwaltung",
      business: "Wirtschaft",
      citizens: "Buerger",
    };
    try {
      const settled = await Promise.allSettled(
        addressees.map((na) =>
          apiClient.computeTotalCost({
            appSessionId: state.appSessionId,
            normAddressee: na,
          })
        )
      );
    const successes: { na: (typeof addressees)[number]; result: Awaited<ReturnType<typeof apiClient.computeTotalCost>> }[] = [];
    const failures: { na: (typeof addressees)[number]; error: unknown }[] = [];
    settled.forEach((outcome, idx) => {
      const na = addressees[idx];
      if (outcome.status === "fulfilled") {
        successes.push({ na, result: outcome.value });
      } else {
        failures.push({ na, error: outcome.reason });
        logClientError(`TotalCostPanel.computeTotalCost[${na}]`, outcome.reason, {
          appSessionId: state.appSessionId,
        });
      }
    });

    window.dispatchEvent(new Event("tiles-updated"));

    // Bewusst ohne konkrete Beträge: die maßgebliche, stets aktuelle Summe steht
    // in der total_cost-Kachel (Single Source of Truth). Eine Zahl hier würde nach
    // späteren EA-Edits (Löhne/Fallzahlen) veralten (PR #35, Kommentar Julia).
    const successLines = successes.map(({ na }) => ` ${labels[na]}: berechnet.`);

    const failureLines = failures.map(
      ({ na, error }) =>
        ` ${labels[na]}: Fehler (${formatActionErrorMessage("Berechnung fehlgeschlagen", error)})`
    );

      if (failures.length === 0) {
        setTotalCostReady(true);
        setStatusTone("success");
        setStatus(
          `Kosten fuer Verwaltung, Wirtschaft und Buerger berechnet.${successLines.join("")}`
        );
        setCurrentTab(6);
      } else if (successes.length === 0) {
        setStatusTone("error");
        setStatus(
          `Gesamtkosten konnten fuer keinen Normadressaten berechnet werden.${failureLines.join("")}`
        );
      } else {
        // Teilweiser Erfolg: totalCostReady bleibt false, damit der Nutzer
        // den fehlenden NA gezielt nachziehen kann.
        setStatusTone("error");
        setStatus(
          `Teilweise berechnet.${successLines.join("")}${failureLines.join("")}`
        );
      }
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <section className="w-full border-b border-white/60 bg-white/80 px-6 py-4 backdrop-blur">
      <div className="mx-auto max-w-6xl space-y-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start">
          <p className="text-xs leading-5 text-slate-600">
            Beim Klick auf „Gesamtkosten berechnen“ werden Schritt-, Fallgruppen-
            und Prozesskosten in einem Durchgang für Verwaltung, Wirtschaft und
            Bürger berechnet, dabei aber je Normadressat eigene Kostensichten
            erzeugt. Der Umschalter zeigt die Sicht des ausgewählten Normadressaten.
          </p>
          <button
            onClick={handleCompute}
            disabled={
              runAllCancel.isCancellingRunAll ||
              (isRunAllBusy ? !runAllCancel.runAllRunId : !canRun)
            }
            className={`inline-flex items-center gap-2 justify-self-start whitespace-nowrap rounded-full px-4 py-2 text-sm font-semibold transition sm:justify-self-end ${
              isRunAllBusy
                ? runAllCancel.isCancellingRunAll
                  ? "cursor-not-allowed border border-rose-100 bg-rose-100 text-rose-400"
                  : "border border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100"
                : canRun
                  ? "bg-slate-900 text-white"
                  : "cursor-not-allowed bg-slate-200 text-slate-500"
            }`}
          >
            {isRunAllBusy && (
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
            )}
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
