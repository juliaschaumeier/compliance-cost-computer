"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { apiClient } from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";
import { SessionPayRatesResponse } from "@/types";

import { useEaReviewSave } from "./useEaReviewSave";
import {
  formatNumber,
  isValidNullableNumberInput,
  parseNullableNumber,
} from "./utils";

type EaPayRatesTabProps = {
  open: boolean;
  active: boolean;
  appSessionId: string;
  runAutoRecompute: () => Promise<void>;
  onDirtyChange?: (dirty: boolean) => void;
};

type PayGradeKey = "a" | "b" | "c" | "d";

const PAY_GRADE_ROWS: Array<{ key: PayGradeKey; label: string }> = [
  { key: "a", label: "Einfacher/Mittlerer Dienst (eD/mD)" },
  { key: "b", label: "Gehobener Dienst (gD)" },
  { key: "c", label: "Höherer Dienst (hD)" },
  { key: "d", label: "Durchschnitt über Laufbahnen (Ø)" },
];

const EMPTY_EDITED_INPUTS: Record<PayGradeKey, string> = {
  a: "",
  b: "",
  c: "",
  d: "",
};

export default function EaPayRatesTab({
  open,
  active,
  appSessionId,
  runAutoRecompute,
  onDirtyChange,
}: EaPayRatesTabProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [payRates, setPayRates] = useState<SessionPayRatesResponse | null>(null);
  const [payEditedInputs, setPayEditedInputs] =
    useState<Record<PayGradeKey, string>>(EMPTY_EDITED_INPUTS);
  const [loadedSessionKey, setLoadedSessionKey] = useState<string | null>(null);
  const { isSaving, status, setStatus, runSave } = useEaReviewSave({
    logLabel: "EaPayRatesTab.save",
    logContext: { appSessionId },
  });
  const hasInvalidInput = Object.values(payEditedInputs).some(
    (value) => !isValidNullableNumberInput(value)
  );
  const parsedEdited = useMemo<Record<PayGradeKey, number | null>>(
    () => ({
      a: parseNullableNumber(payEditedInputs.a),
      b: parseNullableNumber(payEditedInputs.b),
      c: parseNullableNumber(payEditedInputs.c),
      d: parseNullableNumber(payEditedInputs.d),
    }),
    [payEditedInputs]
  );
  const nextEdited = useMemo<Record<PayGradeKey, number | null>>(() => {
    if (!payRates) {
      return { a: null, b: null, c: null, d: null };
    }
    return {
      a:
        payEditedInputs.a.trim() === ""
          ? payRates.edited.a
          : parsedEdited.a,
      b:
        payEditedInputs.b.trim() === ""
          ? payRates.edited.b
          : parsedEdited.b,
      c:
        payEditedInputs.c.trim() === ""
          ? payRates.edited.c
          : parsedEdited.c,
      d:
        payEditedInputs.d.trim() === ""
          ? payRates.edited.d
          : parsedEdited.d,
    };
  }, [payRates, payEditedInputs, parsedEdited]);

  const hasDirtyEdited = useMemo(() => {
    if (!payRates || hasInvalidInput) {
      return false;
    }
    return (
      nextEdited.a !== payRates.edited.a ||
      nextEdited.b !== payRates.edited.b ||
      nextEdited.c !== payRates.edited.c ||
      nextEdited.d !== payRates.edited.d
    );
  }, [hasInvalidInput, nextEdited, payRates]);
  const hasActiveEdited = useMemo(() => {
    if (!payRates) {
      return false;
    }
    return Object.values(payRates.edited).some((value) => value !== null);
  }, [payRates]);

  useEffect(() => {
    onDirtyChange?.(hasDirtyEdited);
  }, [hasDirtyEdited, onDirtyChange]);

  const loadPayRates = useCallback(async () => {
    setIsLoading(true);
    setStatus(null);
    try {
      const payload = await apiClient.getSessionPayRates({ appSessionId });
      setPayRates(payload);
      setLoadedSessionKey(appSessionId);
      setPayEditedInputs(EMPTY_EDITED_INPUTS);
    } catch (error) {
      logClientError("EaPayRatesTab.load", error, { appSessionId });
      setStatus("Lohnsätze konnten nicht geladen werden.");
    } finally {
      setIsLoading(false);
    }
  }, [appSessionId, setStatus]);

  useEffect(() => {
    setPayRates(null);
    setPayEditedInputs(EMPTY_EDITED_INPUTS);
    setLoadedSessionKey(null);
    setStatus(null);
  }, [appSessionId, setStatus]);

  useEffect(() => {
    if (!open || !active) {
      return;
    }
    if (loadedSessionKey === appSessionId && payRates) {
      return;
    }
    loadPayRates();
  }, [open, active, loadPayRates, loadedSessionKey, appSessionId, payRates]);

  const handleSave = async () => {
    if (!payRates || !hasDirtyEdited || hasInvalidInput) {
      return;
    }
    try {
      await runSave(
        async () => {
          const response = await apiClient.updateSessionPayRates({
            appSessionId,
            administrationLevel: payRates.administration_level || "bund",
            editedA: nextEdited.a,
            editedB: nextEdited.b,
            editedC: nextEdited.c,
            editedD: nextEdited.d,
          });
          await runAutoRecompute();
          setPayRates(response);
          setPayEditedInputs(EMPTY_EDITED_INPUTS);
        },
        {
          successMessage: "Lohnsätze gespeichert. Gesamtkosten wurden automatisch neu berechnet.",
          errorMessage: "Speichern fehlgeschlagen. Bitte Eingaben prüfen und erneut versuchen.",
        }
      );
    } catch {
      // Status handling is centralized in useEaReviewSave.
    }
  };

  const handleResetEdited = async () => {
    if (!payRates || !hasActiveEdited) {
      return;
    }
    try {
      await runSave(
        async () => {
          const response = await apiClient.updateSessionPayRates({
            appSessionId,
            administrationLevel: payRates.administration_level || "bund",
            editedA: null,
            editedB: null,
            editedC: null,
            editedD: null,
          });
          await runAutoRecompute();
          setPayRates(response);
          setPayEditedInputs(EMPTY_EDITED_INPUTS);
        },
        {
          successMessage:
            "Bearbeitete Lohnsätze zurückgesetzt. Gesamtkosten wurden automatisch neu berechnet.",
          errorMessage: "Zurücksetzen fehlgeschlagen. Bitte erneut versuchen.",
        }
      );
    } catch {
      // Status handling is centralized in useEaReviewSave.
    }
  };

  if (!active) {
    return null;
  }

  if (isLoading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
        Lohnsätze werden geladen...
      </div>
    );
  }

  const inputClass = (value: string) =>
    `w-24 rounded px-2 py-1 ${
      isValidNullableNumberInput(value)
        ? "border border-slate-300"
        : "border border-red-400 bg-red-50"
    }`;

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
        Verwaltungsebene:{" "}
        <span className="font-semibold uppercase">
          {payRates?.administration_level || "bund"}
        </span>
      </div>
      <div className="text-[11px] text-slate-500">
        Zahlenformat: z. B. 1.234,56 (de-DE).
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate-600">
              <th className="px-2 py-2">Qualifikation</th>
              <th className="px-2 py-2">Modell</th>
              <th className="px-2 py-2">Aktiv</th>
              <th className="px-2 py-2">Neu</th>
            </tr>
          </thead>
          <tbody>
            {PAY_GRADE_ROWS.map((row) => (
              <tr key={row.key} className="border-b border-slate-100">
                <td className="px-2 py-2 font-semibold text-slate-800">{row.label}</td>
                <td className="px-2 py-2">
                  {formatNumber(payRates?.defaults?.[row.key] ?? null)} €
                </td>
                <td className="px-2 py-2 font-semibold text-slate-900">
                  {formatNumber(
                    payRates?.active?.[row.key] ??
                      payRates?.defaults?.[row.key] ??
                      null
                  )}{" "}
                  €
                </td>
                <td className="px-2 py-2">
                  <input
                    value={payEditedInputs[row.key] ?? ""}
                    onChange={(event) =>
                      setPayEditedInputs((prev) => ({
                        ...prev,
                        [row.key]: event.target.value,
                      }))
                    }
                    className={inputClass(payEditedInputs[row.key] ?? "")}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex justify-end gap-2">
        <button
          onClick={handleResetEdited}
          disabled={isSaving || !hasActiveEdited}
          className="rounded-full border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Auf Modellwerte zurücksetzen
        </button>
        <button
          onClick={handleSave}
          disabled={isSaving || hasInvalidInput || !hasDirtyEdited}
          className="rounded-full bg-slate-900 px-4 py-2 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {isSaving ? "Speichert..." : "Lohnsätze speichern"}
        </button>
      </div>
      {hasInvalidInput && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-800">
          Bitte ungültige Zahlenformate korrigieren.
        </div>
      )}
      {status && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
          {status}
        </div>
      )}
    </div>
  );
}
