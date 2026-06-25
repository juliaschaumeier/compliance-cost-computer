"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import EaEditDrawerShell from "@/components/ea_edit/EaEditDrawerShell";
import { useApp } from "@/contexts/AppContext";
import { useAnchoredPopoverPosition } from "@/lib/useAnchoredPopoverPosition";
import { NormAddressee } from "@/types";

const normAddresseeLabels: Record<NormAddressee, string> = {
  citizens: "Bürger:innen",
  business: "Wirtschaft",
  administration: "Verwaltung",
};

const normAddresseeOptions: NormAddressee[] = [
  "citizens",
  "business",
  "administration",
];

const workflowControlBase =
  "h-10 rounded-xl border border-slate-200 bg-white text-[13px] font-medium text-slate-800 transition hover:border-slate-300 hover:bg-slate-50";
const workflowControlDisabled =
  "cursor-not-allowed border-slate-100 bg-slate-50 text-slate-400 opacity-60 shadow-none hover:border-slate-100 hover:bg-slate-50";
const viewMenuWidth = 176;

export default function WorkflowControls() {
  const { state, setSelectedNormAddressee } = useApp();
  const [eaEditOpen, setEaEditOpen] = useState(false);
  const [viewMenuOpen, setViewMenuOpen] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const viewButtonRef = useRef<HTMLButtonElement | null>(null);
  const viewMenuRef = useRef<HTMLDivElement | null>(null);
  const canOpenEditor = state.totalCostReady;
  const selectedNormAddressee =
    state.selectedNormAddressee ?? "administration";

  useEffect(() => {
    if (!canOpenEditor) {
      setEaEditOpen(false);
    }
  }, [canOpenEditor]);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const { position: viewMenuPos, updatePosition: updateViewMenuPosition } =
    useAnchoredPopoverPosition({
      open: viewMenuOpen,
      triggerRef: viewButtonRef,
      width: viewMenuWidth,
      align: "left",
      offset: 8,
      padding: 12,
    });

  useEffect(() => {
    if (!viewMenuOpen) {
      return;
    }
    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (
        viewButtonRef.current?.contains(target) ||
        viewMenuRef.current?.contains(target)
      ) {
        return;
      }
      setViewMenuOpen(false);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setViewMenuOpen(false);
        viewButtonRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [viewMenuOpen]);

  const handleSelectNormAddressee = (value: NormAddressee) => {
    setSelectedNormAddressee?.(value);
    setViewMenuOpen(false);
    viewButtonRef.current?.focus();
  };

  const viewMenu =
    viewMenuOpen && isMounted
      ? createPortal(
          <div
            ref={viewMenuRef}
            role="listbox"
            aria-label="Normadressat-Ansicht auswählen"
            className="fixed z-[70] rounded-2xl border border-slate-200 bg-white p-1.5 text-sm text-slate-700 shadow-2xl"
            style={{
              top: viewMenuPos.top,
              left: viewMenuPos.left,
              width: viewMenuWidth,
            }}
          >
            {normAddresseeOptions.map((value) => {
              const isSelected = value === selectedNormAddressee;
              return (
                <button
                  key={value}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => handleSelectNormAddressee(value)}
                  className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-left transition ${
                    isSelected
                      ? "bg-slate-100 font-semibold text-slate-950"
                      : "font-medium text-slate-700 hover:bg-slate-50 hover:text-slate-950"
                  }`}
                >
                  <span>{normAddresseeLabels[value]}</span>
                  {isSelected ? (
                    <svg
                      aria-hidden="true"
                      viewBox="0 0 24 24"
                      className="h-4 w-4 text-slate-700"
                    >
                      <path
                        d="m5 12 4 4L19 6"
                        fill="none"
                        stroke="currentColor"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                      />
                    </svg>
                  ) : null}
                </button>
              );
            })}
          </div>,
          document.body
        )
      : null;

  return (
    <>
      <div className="flex items-center gap-2">
        <div className="relative w-40 shrink-0">
          <button
            ref={viewButtonRef}
            type="button"
            id="norm-addressee-view"
            aria-label="Normadressat-Ansicht auswählen"
            aria-haspopup="listbox"
            aria-expanded={viewMenuOpen}
            onClick={() => {
              updateViewMenuPosition();
              setViewMenuOpen((open) => !open);
            }}
            className={`${workflowControlBase} inline-flex w-full items-center gap-2 px-3`}
            title="Normadressat-Ansicht auswählen"
          >
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              className="h-[18px] w-[18px] shrink-0 text-slate-500"
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
            <span className="min-w-0 flex-1 truncate text-left">
              {normAddresseeLabels[selectedNormAddressee]}
            </span>
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              className={`h-3.5 w-3.5 shrink-0 text-slate-500 transition ${
                viewMenuOpen ? "rotate-180" : ""
              }`}
            >
              <path
                d="m6 9 6 6 6-6"
                fill="none"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
              />
            </svg>
          </button>
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
      {viewMenu}
    </>
  );
}
