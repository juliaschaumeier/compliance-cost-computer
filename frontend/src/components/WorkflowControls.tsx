"use client";

import { useEffect, useState } from "react";

import EaEditDrawerShell from "@/components/ea_edit/EaEditDrawerShell";
import { useApp } from "@/contexts/AppContext";
import { NormAddressee } from "@/types";

const normAddresseeLabels: Record<NormAddressee, string> = {
  citizens: "Bürger:innen",
  business: "Wirtschaft",
  administration: "Verwaltung",
};

const workflowControlBase =
  "h-10 rounded-xl border border-slate-200 bg-white text-[13px] font-medium text-slate-800 transition hover:border-slate-300 hover:bg-slate-50";
const workflowControlDisabled =
  "cursor-not-allowed border-slate-100 bg-slate-50 text-slate-400 opacity-60 shadow-none hover:border-slate-100 hover:bg-slate-50";

export default function WorkflowControls() {
  const { state, setSelectedNormAddressee } = useApp();
  const [eaEditOpen, setEaEditOpen] = useState(false);
  const canOpenEditor = state.totalCostReady;
  const selectedNormAddressee =
    state.selectedNormAddressee ?? "administration";

  useEffect(() => {
    if (!canOpenEditor) {
      setEaEditOpen(false);
    }
  }, [canOpenEditor]);

  return (
    <>
      <div className="flex items-center gap-2">
        <label className="sr-only" htmlFor="norm-addressee-view">
          Normadressat-Ansicht auswählen
        </label>
        <div className="relative w-40 shrink-0">
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            className="pointer-events-none absolute left-3 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-slate-500"
          >
            <path
              d="M3 12s3.4-5 9-5 9 5 9 5-3.4 5-9 5-9-5-9-5Z"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="1.7"
            />
            <circle
              cx="12"
              cy="12"
              r="2.4"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
            />
          </svg>
          <select
            id="norm-addressee-view"
            value={selectedNormAddressee}
            onChange={(event) =>
              setSelectedNormAddressee?.(
                event.target.value as NormAddressee
              )
            }
            className={`${workflowControlBase} w-full appearance-none py-2 pl-9 pr-8`}
          >
            {(Object.keys(normAddresseeLabels) as NormAddressee[]).map(
              (value) => (
                <option key={value} value={value}>
                  {normAddresseeLabels[value]}
                </option>
              )
            )}
          </select>
          <span
            aria-hidden="true"
            className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500"
          >
            ⌄
          </span>
        </div>
        <button
          type="button"
          onClick={() => setEaEditOpen(true)}
          disabled={!canOpenEditor}
          className={`inline-flex min-w-36 items-center justify-center gap-2 px-3 ${workflowControlBase} ${
            canOpenEditor ? "" : workflowControlDisabled
          }`}
          title={
            canOpenEditor
              ? "EA-Editor öffnen"
              : "EA-Editor ist nach Gesamtkosten-Berechnung verfügbar"
          }
        >
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            className="h-4 w-4 shrink-0"
          >
            <path
              d="M12 20h9"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="1.8"
            />
            <path
              d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5Z"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="1.8"
            />
          </svg>
          <span>EA bearbeiten</span>
        </button>
      </div>
      <EaEditDrawerShell
        open={eaEditOpen}
        onClose={() => setEaEditOpen(false)}
      />
    </>
  );
}
