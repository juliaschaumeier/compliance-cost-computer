"use client";

import { useEffect, useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";
import { formatActionErrorMessage, logClientError } from "@/lib/errorFeedback";
import { useRunAllStepCancel } from "@/lib/useRunAllStepCancel";
import StepRunButton from "@/components/StepRunButton";
import WorkflowControls from "@/components/WorkflowControls";

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
    ? "Alles berechnet"
    : isRunAllBusy
      ? runAllCancel.isCancellingRunAll
        ? "Abbruch wird ausgeführt..."
        : "Abbrechen"
      : isRunning
        ? "Bitte warten..."
      : "Ausführen";

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
        setStatus("Kosten fuer Verwaltung, Wirtschaft und Buerger berechnet.");
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
    <section className="w-full border-b border-white/60 bg-white/80 py-4 backdrop-blur">
      <div className="mx-auto max-w-7xl space-y-4 px-4 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-3">
          <p className="max-w-xl text-xs leading-5 text-slate-600">
            Beim Klick auf „Gesamtkosten berechnen“ werden Schritt-, Fallgruppen-
            und Prozesskosten je Normadressat berechnet.
          </p>
          <StepRunButton
            onClick={handleCompute}
            disabled={
              runAllCancel.isCancellingRunAll ||
              (isRunAllBusy ? !runAllCancel.runAllRunId : !canRun)
            }
            className={
              isRunAllBusy
                ? runAllCancel.isCancellingRunAll
                  ? "cursor-not-allowed border border-rose-100 bg-rose-100 text-rose-400"
                  : "border border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100"
                : canRun
                  ? "bg-slate-800 text-white"
                  : "cursor-not-allowed bg-slate-200 text-slate-500"
            }
            isRunning={isRunAllBusy || isRunning}
            showIcon={!state.totalCostReady}
          >
            {label}
          </StepRunButton>
          <div className="xl:ml-auto">
            <WorkflowControls />
          </div>
        </div>

        {status && (
          <div
            className={`rounded-xl px-3 py-2 text-xs font-semibold ${
              statusTone === "success"
                ? "ccc-status-success border border-emerald-200 bg-emerald-50 text-emerald-800"
                : "ccc-status-warning border border-amber-200 bg-amber-50 text-amber-800"
            }`}
          >
            {status}
          </div>
        )}
      </div>
    </section>
  );
}
