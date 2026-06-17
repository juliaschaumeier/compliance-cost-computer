"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";
import { formatActionErrorMessage, logClientError } from "@/lib/errorFeedback";
import { useRunAllStepCancel } from "@/lib/useRunAllStepCancel";
import { getWorkflowStepActionButtonState } from "@/lib/workflowStepActionButton";
import StepRunButton from "@/components/StepRunButton";
import WorkflowControls from "@/components/WorkflowControls";
import { NormAddressee, TotalCostResponse, TotalCostSummaryResponse } from "@/types";

type CostSummary = Partial<Record<NormAddressee, TotalCostResponse>>;
const COST_SUMMARY_ADDRESSEES: NormAddressee[] = [
  "administration",
  "business",
  "citizens",
];

function normalizeCostSummary(summary: TotalCostSummaryResponse): CostSummary | null {
  const hasAnyPersistedEntry = COST_SUMMARY_ADDRESSEES.some(
    (addressee) => summary[addressee] !== undefined
  );
  if (!hasAnyPersistedEntry) {
    return null;
  }
  const normalized = COST_SUMMARY_ADDRESSEES.reduce<CostSummary>(
    (next, addressee) => {
      const row = summary[addressee];
      next[addressee] =
        row ?? {
          norm_addressee: addressee,
          total_cost: null,
          bureaucracy_cost: null,
          total_time_hours: null,
          total_expenses: null,
        };
      return next;
    },
    {}
  );
  return normalized;
}

function isCompleteCostSummary(summary: CostSummary): boolean {
  return COST_SUMMARY_ADDRESSEES.every((addressee) => summary[addressee]);
}

function formatThousandEuro(
  value: number | null | undefined,
  options: { zeroWhenMissing?: boolean } = {}
): string {
  if (typeof value !== "number") {
    return options.zeroWhenMissing ? "0 €" : "n. v.";
  }
  if (value === 0) {
    return "0 €";
  }
  return `${Math.round(value / 1000).toLocaleString("de-DE")} Tsd. €`;
}

function formatHours(value: number | null | undefined): string {
  if (typeof value !== "number") {
    return "n. v.";
  }
  if (Math.abs(value) >= 1_000_000) {
    return `${(value / 1_000_000).toLocaleString("de-DE", {
      maximumFractionDigits: 1,
    })} Mio. h`;
  }
  return `${Math.round(value).toLocaleString("de-DE")} h`;
}

function formatCitizenCostValue(row: TotalCostResponse | undefined): string {
  const hours =
    typeof row?.total_time_hours === "number" ? formatHours(row.total_time_hours) : "0 h";
  const expenses = formatThousandEuro(row?.total_expenses, { zeroWhenMissing: true });
  return `${hours} · ${expenses}`;
}

function buildCostSummaryLabel(summary: CostSummary): string {
  const administration = summary.administration?.total_cost ?? 0;
  const business = summary.business?.total_cost ?? 0;
  const total = [administration, business].reduce((sum, value) => sum + value, 0);
  return [
    `Gesamt ${formatThousandEuro(total)}`,
    `Bürger:innen ${formatCitizenCostValue(summary.citizens)}`,
    `Wirtschaft ${formatThousandEuro(summary.business?.total_cost, { zeroWhenMissing: true })}`,
    `Verwaltung ${formatThousandEuro(summary.administration?.total_cost, { zeroWhenMissing: true })}`,
  ].join(" · ");
}

function CostSummaryStrip({ summary }: { summary: CostSummary }) {
  const administration = summary.administration?.total_cost ?? 0;
  const business = summary.business?.total_cost ?? 0;
  const total = administration + business;
  const citizenValue = formatCitizenCostValue(summary.citizens);

  const cells = [
    { label: "Gesamt", value: formatThousandEuro(total), emphasis: true },
    { label: "Bürger:innen", value: citizenValue },
    {
      label: "Wirtschaft",
      value: formatThousandEuro(summary.business?.total_cost, { zeroWhenMissing: true }),
    },
    {
      label: "Verwaltung",
      value: formatThousandEuro(summary.administration?.total_cost, { zeroWhenMissing: true }),
    },
  ];

  return (
    <div
      className="rounded-xl border border-slate-300 bg-white px-4 py-2 shadow-sm ring-1 ring-slate-100"
      aria-label={`Kostenübersicht: ${buildCostSummaryLabel(summary)}`}
    >
      <div className="grid grid-cols-[92px_minmax(105px,0.9fr)_minmax(175px,1.35fr)_minmax(105px,0.9fr)_minmax(105px,0.9fr)] items-center gap-x-4 gap-y-1">
        <div className="text-xs font-bold uppercase tracking-wide text-slate-500">
          Kosten
        </div>
        {cells.map((cell) => (
          <div
            key={cell.label}
            className="truncate text-xs font-semibold text-slate-500"
          >
            {cell.label}
          </div>
        ))}
        <div className="text-xs text-slate-400">jährlich</div>
        {cells.map((cell) => (
          <div
            key={cell.label}
            className={`truncate ${
              cell.emphasis
                ? "text-[17px] font-semibold text-slate-950"
                : "text-[15px] font-semibold text-slate-800"
            }`}
            title={cell.value}
          >
            {cell.value}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function TotalCostPanel() {
  const { state, setCurrentTab, setTotalCostReady } = useApp();
  const [status, setStatus] = useState<string | null>(null);
  const [statusTone, setStatusTone] = useState<"success" | "error">("success");
  const [isRunning, setIsRunning] = useState(false);
  const [costSummary, setCostSummary] = useState<CostSummary | null>(null);
  const costSummaryRef = useRef<CostSummary | null>(null);
  const costSummaryLoadId = useRef(0);
  const costSummaryMutationId = useRef(0);
  const isComputingCostSummary = useRef(false);
  const runAllCancel = useRunAllStepCancel({
    stepKey: "total_cost",
    appSessionId: state.appSessionId,
    setStatus,
    logScope: "TotalCostPanel.cancelRunAll",
  });
  const isRunAllBusy = runAllCancel.isRunAllBusy;
  const isBusy = isRunning || isRunAllBusy;
  const shouldShowCostSummary =
    state.totalCostReady && costSummary ? isCompleteCostSummary(costSummary) : false;

  const updateCostSummary = useCallback((summary: CostSummary | null) => {
    costSummaryRef.current = summary;
    setCostSummary(summary);
  }, []);

  const loadCostSummary = useCallback(async () => {
    if (!state.appSessionId || !state.totalCostReady) {
      updateCostSummary(null);
      return;
    }
    const loadId = ++costSummaryLoadId.current;
    const mutationId = costSummaryMutationId.current;
    const computingAtStart = isComputingCostSummary.current;
    try {
      const summary = await apiClient.getTotalCostSummary(state.appSessionId);
      if (
        loadId !== costSummaryLoadId.current ||
        mutationId !== costSummaryMutationId.current
      ) {
        return;
      }
      const normalized = normalizeCostSummary(summary);
      if (normalized) {
        updateCostSummary(normalized);
      } else if (!computingAtStart && costSummaryRef.current) {
        updateCostSummary(null);
      }
    } catch (error) {
      logClientError("TotalCostPanel.loadCostSummary", error, {
        appSessionId: state.appSessionId,
      });
    }
  }, [state.appSessionId, state.totalCostReady, updateCostSummary]);

  useEffect(() => {
    if (runAllCancel.isCancellingRunAll) {
      setStatusTone("error");
    }
  }, [runAllCancel.isCancellingRunAll]);

  useEffect(() => {
    costSummaryMutationId.current += 1;
    updateCostSummary(null);
  }, [state.appSessionId, updateCostSummary]);

  useEffect(() => {
    void loadCostSummary();
  }, [loadCostSummary]);

  useEffect(() => {
    const refreshSummary = () => {
      void loadCostSummary();
    };
    window.addEventListener("tiles-updated", refreshSummary);
    return () => {
      window.removeEventListener("tiles-updated", refreshSummary);
    };
  }, [loadCostSummary]);

  const canRun =
    state.processStepsReady &&
    state.effortReady &&
    !state.totalCostReady &&
    !isBusy;

  const buttonState = getWorkflowStepActionButtonState({
    idleLabel: state.totalCostReady ? "Alles berechnet" : "Ausführen",
    canRun,
    isManualRunning: isRunning,
    manualRunningLabel: "Bitte warten...",
    canCancelManualRun: false,
    isRunAllBusy,
    isRunAllCancelling: runAllCancel.isCancellingRunAll,
    runAllRunId: runAllCancel.runAllRunId,
  });

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
    costSummaryMutationId.current += 1;
    isComputingCostSummary.current = true;
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
      const successes: {
        na: (typeof addressees)[number];
        result: Awaited<ReturnType<typeof apiClient.computeTotalCost>>;
      }[] = [];
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

      const successLines = successes.map(({ na }) => ` ${labels[na]}: berechnet.`);

      const failureLines = failures.map(
        ({ na, error }) =>
          ` ${labels[na]}: Fehler (${formatActionErrorMessage("Berechnung fehlgeschlagen", error)})`
      );

      if (failures.length === 0) {
        updateCostSummary(
          successes.reduce<CostSummary>((summary, { na, result }) => {
            summary[na] = result;
            return summary;
          }, {})
        );
        setTotalCostReady(true);
        setStatusTone("success");
        setStatus("Kosten fuer Verwaltung, Wirtschaft und Buerger berechnet.");
        setCurrentTab(6);
      } else if (successes.length === 0) {
        updateCostSummary(null);
        setStatusTone("error");
        setStatus(
          `Gesamtkosten konnten fuer keinen Normadressaten berechnet werden.${failureLines.join("")}`
        );
      } else {
        // Teilweiser Erfolg: totalCostReady bleibt false, damit der Nutzer
        // den fehlenden NA gezielt nachziehen kann.
        updateCostSummary(null);
        setStatusTone("error");
        setStatus(
          `Teilweise berechnet.${successLines.join("")}${failureLines.join("")}`
        );
      }
    } finally {
      isComputingCostSummary.current = false;
      setIsRunning(false);
    }
  };

  return (
    <section className="w-full border-b border-white/60 bg-white/80 py-4 backdrop-blur">
      <div className="mx-auto max-w-7xl space-y-4 px-4 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-3">
          <div className="min-w-0 max-w-[820px] flex-1">
            {shouldShowCostSummary ? (
              <CostSummaryStrip summary={costSummary} />
            ) : (
              <div className="flex flex-wrap items-center gap-x-3 gap-y-3">
                <p className="max-w-xl text-xs leading-5 text-slate-600">
                  Beim Klick auf „Gesamtkosten berechnen“ werden Schritt-,
                  Fallgruppen- und Prozesskosten je Normadressat berechnet.
                </p>
                <StepRunButton
                  onClick={handleCompute}
                  disabled={buttonState.disabled}
                  className={buttonState.className}
                  isRunning={buttonState.isRunning}
                  showIcon={!state.totalCostReady}
                >
                  {buttonState.label}
                </StepRunButton>
              </div>
            )}
          </div>
          <div className="xl:ml-auto">
            <WorkflowControls />
          </div>
        </div>

        {status && !(shouldShowCostSummary && statusTone === "success") && (
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
