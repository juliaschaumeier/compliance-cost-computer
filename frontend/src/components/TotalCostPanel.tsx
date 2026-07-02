"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";
import { formatCompactCurrency, formatCompactHours } from "@/lib/compactNumberFormat";
import { formatActionErrorMessage, logClientError } from "@/lib/errorFeedback";
import { useRunAllStepCancel } from "@/lib/useRunAllStepCancel";
import { getWorkflowStepActionButtonState } from "@/lib/workflowStepActionButton";
import StepRunButton from "@/components/StepRunButton";
import WorkflowControls from "@/components/WorkflowControls";
import { NormAddressee, TotalCostResponse, TotalCostSummaryResponse } from "@/types";

type CostSummary = Partial<Record<NormAddressee, TotalCostResponse>>;
const INCOMPLETE_COST_SUMMARY_STATUS =
  "Kostenübersicht ist unvollständig. Bitte Gesamtkosten erneut berechnen.";
const COST_SUMMARY_ADDRESSEES: NormAddressee[] = [
  "administration",
  "business",
  "citizens",
];

function normalizeCostSummary(summary: TotalCostSummaryResponse): CostSummary | null {
  const hasAnyPersistedEntry = COST_SUMMARY_ADDRESSEES.some(
    (addressee) => summary[addressee] != null
  );
  if (!hasAnyPersistedEntry) {
    return null;
  }
  const normalized = COST_SUMMARY_ADDRESSEES.reduce<CostSummary>(
    (next, addressee) => {
      const row = summary[addressee];
      if (row) {
        next[addressee] = row;
      }
      return next;
    },
    {}
  );
  return normalized;
}

function isCompleteCostSummary(summary: CostSummary): boolean {
  return COST_SUMMARY_ADDRESSEES.every((addressee) => summary[addressee]);
}

function formatCostValue(
  value: number | null | undefined,
  options: { zeroWhenMissing?: boolean } = {}
): string {
  if (typeof value !== "number") {
    return options.zeroWhenMissing ? "0 €" : "n. v.";
  }
  if (value === 0) {
    return "0 €";
  }
  return formatCompactCurrency(value);
}

function formatCitizenCostValue(row: TotalCostResponse | undefined): string {
  const hours =
    typeof row?.total_time_hours === "number"
      ? formatCompactHours(row.total_time_hours)
      : "0 h";
  const expenses = formatCostValue(row?.total_expenses, { zeroWhenMissing: true });
  return `${hours} · ${expenses}`;
}

function buildCostSummaryCells(summary: CostSummary): {
  totalCell: { label: string; value: string };
  addresseeCells: {
    label: string;
    value: string;
    sub?: { label: string; value: string };
  }[];
} {
  const administration = summary.administration?.total_cost ?? 0;
  const business = summary.business?.total_cost ?? 0;
  return {
    totalCell: {
      label: "Gesamt",
      value: formatCostValue(administration + business),
    },
    addresseeCells: [
      { label: "Bürger:innen", value: formatCitizenCostValue(summary.citizens) },
      {
        label: "Wirtschaft",
        value: formatCostValue(summary.business?.total_cost, { zeroWhenMissing: true }),
        // Bürokratiekosten aus Informationspflichten als "davon"-Anteil der Wirtschaft.
        sub: {
          label: "davon IP",
          value: formatCostValue(summary.business?.bureaucracy_cost, {
            zeroWhenMissing: true,
          }),
        },
      },
      {
        label: "Verwaltung",
        value: formatCostValue(summary.administration?.total_cost, { zeroWhenMissing: true }),
      },
    ],
  };
}

function buildCostSummaryLabel(summary: CostSummary): string {
  const { totalCell, addresseeCells } = buildCostSummaryCells(summary);
  return [
    `${totalCell.label} ${totalCell.value}`,
    ...addresseeCells.map((cell) =>
      cell.sub
        ? `${cell.label} ${cell.value} (${cell.sub.label} ${cell.sub.value})`
        : `${cell.label} ${cell.value}`
    ),
  ].join(" · ");
}

function CostSummaryStrip({ summary }: { summary: CostSummary }) {
  const { totalCell, addresseeCells } = buildCostSummaryCells(summary);

  return (
    <div
      className="w-fit max-w-full overflow-x-auto rounded-xl border border-slate-300 bg-white px-4 py-2 shadow-sm ring-1 ring-slate-100"
      aria-label={`Kostenübersicht: ${buildCostSummaryLabel(summary)}`}
    >
      <div className="flex min-w-max items-start">
        <div className="w-[120px] shrink-0">
          <div className="text-xs font-bold uppercase tracking-wide text-slate-500">
            Jährlicher
          </div>
          <div className="mt-1 text-xs font-bold uppercase tracking-wide text-slate-500">
            Aufwand
          </div>
        </div>
        <div className="shrink-0">
          <div className="text-xs font-semibold text-slate-500">{totalCell.label}</div>
          <div
            className="mt-1 whitespace-nowrap text-[17px] font-semibold text-slate-950"
            title={totalCell.value}
          >
            {totalCell.value}
          </div>
        </div>
        <div aria-hidden="true" className="w-[60px] shrink-0" />
        <div
          data-testid="cost-summary-addressee-group"
          className="flex shrink-0 items-start gap-10"
        >
          {addresseeCells.map((cell) => (
            <div key={cell.label} className="shrink-0">
              <div className="text-xs font-semibold text-slate-500">
                {cell.label}
              </div>
              <div
                className="mt-1 whitespace-nowrap text-[15px] font-semibold text-slate-800"
                title={cell.value}
              >
                {cell.value}
              </div>
              {cell.sub && (
                <div
                  className="mt-0.5 whitespace-nowrap text-[11px] font-medium text-slate-500"
                  title={`${cell.sub.label} ${cell.sub.value}`}
                >
                  {cell.sub.label} {cell.sub.value}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function TotalCostPanel() {
  const { state, setCurrentTab, setTotalCostReady } = useApp();
  const [status, setStatus] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [costSummary, setCostSummary] = useState<CostSummary | null>(null);
  const costSummaryRef = useRef<CostSummary | null>(null);
  const costSummaryLoadId = useRef(0);
  const costSummaryMutationId = useRef(0);
  const totalCostReadyRef = useRef(state.totalCostReady);
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

  useEffect(() => {
    totalCostReadyRef.current = state.totalCostReady;
    if (!state.totalCostReady) {
      costSummaryLoadId.current += 1;
      updateCostSummary(null);
      setStatus((current) =>
        current === INCOMPLETE_COST_SUMMARY_STATUS ? null : current
      );
    }
  }, [state.totalCostReady, updateCostSummary]);

  const loadCostSummary = useCallback(async () => {
    if (!state.appSessionId || !state.totalCostReady) {
      costSummaryLoadId.current += 1;
      updateCostSummary(null);
      setStatus((current) =>
        current === INCOMPLETE_COST_SUMMARY_STATUS ? null : current
      );
      return;
    }
    const loadId = ++costSummaryLoadId.current;
    const mutationId = costSummaryMutationId.current;
    const computingAtStart = isComputingCostSummary.current;
    try {
      const summary = await apiClient.getTotalCostSummary(state.appSessionId);
      if (
        loadId !== costSummaryLoadId.current ||
        mutationId !== costSummaryMutationId.current ||
        !totalCostReadyRef.current
      ) {
        return;
      }
      const normalized = normalizeCostSummary(summary);
      if (normalized) {
        updateCostSummary(normalized);
        const isCompleteSummary = isCompleteCostSummary(normalized);
        if (!isCompleteSummary && !computingAtStart) {
          setStatus(INCOMPLETE_COST_SUMMARY_STATUS);
        } else if (isCompleteSummary) {
          setStatus((current) =>
            current === INCOMPLETE_COST_SUMMARY_STATUS ? null : current
          );
        }
      } else if (!computingAtStart && costSummaryRef.current) {
        updateCostSummary(null);
        setStatus(INCOMPLETE_COST_SUMMARY_STATUS);
      } else if (!computingAtStart) {
        setStatus(INCOMPLETE_COST_SUMMARY_STATUS);
      }
    } catch (error) {
      logClientError("TotalCostPanel.loadCostSummary", error, {
        appSessionId: state.appSessionId,
      });
    }
  }, [state.appSessionId, state.totalCostReady, updateCostSummary]);

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
      await runAllCancel.cancelRunAllForStep();
      return;
    }
    if (!canRun) {
      return;
    }
    setStatus(null);
    setIsRunning(true);
    costSummaryMutationId.current += 1;
    isComputingCostSummary.current = true;
    const addressees = ["administration", "business", "citizens"] as const;
    const labels: Record<(typeof addressees)[number], string> = {
      administration: "Verwaltung",
      business: "Wirtschaft",
      citizens: "Bürger",
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
        setStatus(null);
        setCurrentTab(6);
      } else if (successes.length === 0) {
        updateCostSummary(null);
        setStatus(
          `Gesamtkosten konnten für keinen Normadressaten berechnet werden.${failureLines.join("")}`
        );
      } else {
        // Teilweiser Erfolg: totalCostReady bleibt false, damit der Nutzer
        // den fehlenden NA gezielt nachziehen kann.
        updateCostSummary(null);
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
          <div
            className={`min-w-0 flex-1 ${
              shouldShowCostSummary ? "max-w-full" : "max-w-[820px]"
            }`}
          >
            {shouldShowCostSummary ? (
              <CostSummaryStrip summary={costSummary} />
            ) : (
              <div className="flex flex-wrap items-center gap-x-3 gap-y-3">
                <p className="max-w-xl text-xs leading-5 text-slate-600">
                  In diesem Schritt werden Schritt-, Fallgruppen- und Prozesskosten
                  je Normadressat berechnet und als Kostenübersicht zusammengeführt.
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

        {status && (
          <div
            className="ccc-status-warning rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800"
          >
            {status}
          </div>
        )}
      </div>
    </section>
  );
}
