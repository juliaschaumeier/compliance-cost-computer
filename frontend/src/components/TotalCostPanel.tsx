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

    const successLines = successes.map(({ na, result }) => {
      if (na === "citizens") {
        const timePart =
          typeof result.total_time_hours === "number"
            ? `Zeit ${result.total_time_hours.toFixed(2)} Std.`
            : null;
        const expensesPart =
          typeof result.total_expenses === "number"
            ? `Sachaufwand ${result.total_expenses.toFixed(2)} EUR`
            : null;
        const detail =
          timePart || expensesPart
            ? [timePart, expensesPart].filter(Boolean).join(", ")
            : "Aufwand berechnet";
        return ` ${labels[na]}: ${detail}.`;
      }
      return ` ${labels[na]}: ${formatEuro(result.total_cost)}.`;
    });

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
