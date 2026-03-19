"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import EditorMetricsTable from "@/components/ea_edit/components/EditorMetricsTable";
import ReviewDiffTable, { ReviewDiffRow } from "@/components/ea_edit/components/ReviewDiffTable";
import { apiClient } from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";
import { EditableCaseGroupRow } from "@/types";

import {
  formatNumber,
  isValidNullableNumberInput,
  isZeroInputValue,
  normalizeEditedNumericInput,
  numberChanged,
  resolveEffectiveValue,
  toLocalizedInputString,
} from "./utils";
import { useEaReviewSave } from "./useEaReviewSave";

type EaCaseMetricsTabProps = {
  open: boolean;
  active: boolean;
  appSessionId: string;
  runAutoRecompute: () => Promise<void>;
  onDirtyChange?: (dirty: boolean) => void;
};

const CASE_FIELDS = [
  {
    key: "addressees_current",
    editedKey: "addressees_current_edited",
    effectiveKey: "addressees_current_effective",
    side: "current",
    columnLabel: "Betroffene",
    reviewLabel: "Gültig Betroffene",
  },
  {
    key: "annual_frequency_current",
    editedKey: "annual_frequency_current_edited",
    effectiveKey: "annual_frequency_current_effective",
    side: "current",
    columnLabel: "Häufigkeit",
    reviewLabel: "Gültig Häufigkeit",
  },
  {
    key: "addressees_proposed",
    editedKey: "addressees_proposed_edited",
    effectiveKey: "addressees_proposed_effective",
    side: "proposed",
    columnLabel: "Betroffene",
    reviewLabel: "Vorschlag Betroffene",
  },
  {
    key: "annual_frequency_proposed",
    editedKey: "annual_frequency_proposed_edited",
    effectiveKey: "annual_frequency_proposed_effective",
    side: "proposed",
    columnLabel: "Häufigkeit",
    reviewLabel: "Vorschlag Häufigkeit",
  },
] as const;

type CaseField = (typeof CASE_FIELDS)[number];
type CaseFieldKey = CaseField["key"];
type CaseDraftRow = Record<CaseFieldKey, string>;
type CaseDraft = Record<number, CaseDraftRow>;
type CaseParsedValues = Record<CaseFieldKey, number | null>;
type CaseChangedCells = Record<CaseFieldKey, boolean>;

function buildCaseDraftRow(row: EditableCaseGroupRow): CaseDraftRow {
  const draft = {} as CaseDraftRow;
  for (const field of CASE_FIELDS) {
    draft[field.key] = toLocalizedInputString(row[field.effectiveKey]);
  }
  return draft;
}

export default function EaCaseMetricsTab({
  open,
  active,
  appSessionId,
  runAutoRecompute,
  onDirtyChange,
}: EaCaseMetricsTabProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [rows, setRows] = useState<EditableCaseGroupRow[]>([]);
  const [draft, setDraft] = useState<CaseDraft>({});
  const [loadedSessionKey, setLoadedSessionKey] = useState<string | null>(null);
  const { reviewMode, setReviewMode, isSaving, status, setStatus, runSave } =
    useEaReviewSave({
      logLabel: "EaCaseMetricsTab.save",
      logContext: { appSessionId },
    });

  const currentFields = useMemo(
    () => CASE_FIELDS.filter((field) => field.side === "current"),
    []
  );
  const proposedFields = useMemo(
    () => CASE_FIELDS.filter((field) => field.side === "proposed"),
    []
  );

  const loadRows = useCallback(async () => {
    setIsLoading(true);
    setStatus(null);
    try {
      const payload = await apiClient.getEditableCaseGroups({ appSessionId });
      setRows(payload.rows);
      setLoadedSessionKey(appSessionId);
    } catch (error) {
      logClientError("EaCaseMetricsTab.load", error, { appSessionId });
      setStatus("Fallzahlen konnten nicht geladen werden.");
    } finally {
      setIsLoading(false);
    }
  }, [appSessionId, setStatus]);

  useEffect(() => {
    setRows([]);
    setDraft({});
    setLoadedSessionKey(null);
    setReviewMode(false);
    setStatus(null);
    setIsLoading(false);
  }, [appSessionId, setStatus, setReviewMode]);

  useEffect(() => {
    if (!open || !active) {
      return;
    }
    if (loadedSessionKey === appSessionId) {
      return;
    }
    loadRows();
  }, [open, active, loadRows, loadedSessionKey, appSessionId]);

  const changes = useMemo(() => {
    const changedRows: Array<{
      row: EditableCaseGroupRow;
      next: CaseParsedValues;
      changedCellsByField: CaseChangedCells;
      changedCells: number;
    }> = [];
    for (const row of rows) {
      const draftRow = draft[row.case_group_id] || buildCaseDraftRow(row);
      const next = {} as CaseParsedValues;
      const changedCellsByField = {} as CaseChangedCells;
      let changedCells = 0;
      for (const field of CASE_FIELDS) {
        const normalized = normalizeEditedNumericInput(draftRow[field.key], row[field.key]);
        next[field.key] = normalized;
        const changed = numberChanged(normalized, row[field.editedKey]);
        changedCellsByField[field.key] = changed;
        if (changed) {
          changedCells += 1;
        }
      }
      if (changedCells > 0) {
        changedRows.push({ row, next, changedCellsByField, changedCells });
      }
    }
    return changedRows;
  }, [rows, draft]);

  const changedCellCount = useMemo(
    () => changes.reduce((acc, item) => acc + item.changedCells, 0),
    [changes]
  );
  const changedByCaseGroupId = useMemo(
    () => new Map(changes.map((item) => [item.row.case_group_id, item.changedCellsByField])),
    [changes]
  );
  const reviewRows = useMemo<ReviewDiffRow[]>(() => {
    const result: ReviewDiffRow[] = [];
    for (const item of changes) {
      for (const field of CASE_FIELDS) {
        if (!item.changedCellsByField[field.key]) {
          continue;
        }
        const modelValue = item.row[field.key];
        result.push({
          entityId: item.row.case_group_id,
          entityLabel: item.row.case_group,
          fieldKey: field.key,
          fieldLabel: field.reviewLabel,
          modelValue,
          activeValue: resolveEffectiveValue(modelValue, item.row[field.editedKey]),
          newValue: resolveEffectiveValue(modelValue, item.next[field.key]),
        });
      }
    }
    return result;
  }, [changes]);
  const invalidCellCount = useMemo(
    () =>
      Object.values(draft).reduce((count, rowDraft) => {
        return (
          count +
          CASE_FIELDS.filter((field) => !isValidNullableNumberInput(rowDraft[field.key])).length
        );
      }, 0),
    [draft]
  );
  const hasEditedOverrides = useMemo(
    () => rows.some((row) => CASE_FIELDS.some((field) => row[field.editedKey] !== null)),
    [rows]
  );

  useEffect(() => {
    onDirtyChange?.(changes.length > 0);
  }, [changes.length, onDirtyChange]);

  const handleSave = async () => {
    try {
      await runSave(
        async () => {
          await apiClient.bulkUpdateCaseGroups({
            appSessionId,
            rows: changes.map((item) => {
              const payloadRow = { case_group_id: item.row.case_group_id } as {
                case_group_id: number;
              } & CaseParsedValues;
              for (const field of CASE_FIELDS) {
                payloadRow[field.key] = item.next[field.key];
              }
              return payloadRow;
            }),
          });
          await runAutoRecompute();
          setDraft({});
          setReviewMode(false);
          await loadRows();
        },
        {
          successMessage:
            "Fallzahlen gespeichert. Gesamtkosten wurden automatisch neu berechnet.",
          errorMessage: "Speichern fehlgeschlagen. Bitte Eingaben prüfen und erneut versuchen.",
        }
      );
    } catch {
      // Status handling is centralized in useEaReviewSave.
    }
  };

  const handleResetToModelValues = async () => {
    if (rows.length === 0 || !hasEditedOverrides) {
      return;
    }
    try {
      await runSave(
        async () => {
          await apiClient.bulkUpdateCaseGroups({
            appSessionId,
            rows: rows.map((row) => {
              const payloadRow = { case_group_id: row.case_group_id } as {
                case_group_id: number;
              } & CaseParsedValues;
              for (const field of CASE_FIELDS) {
                payloadRow[field.key] = null;
              }
              return payloadRow;
            }),
          });
          await runAutoRecompute();
          setDraft({});
          setReviewMode(false);
          await loadRows();
        },
        {
          successMessage:
            "Fallzahlen auf Modellwerte zurückgesetzt. Gesamtkosten wurden automatisch neu berechnet.",
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
        Fallzahlen werden geladen...
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {!reviewMode ? (
        <>
          <div className="text-[11px] text-slate-500">
            Zahlenformat: z. B. 1.234,56 (de-DE).
          </div>
          <div className="text-[11px] font-semibold text-slate-600">
            Ungespeicherte Änderungen: {changes.length} Zeilen / {changedCellCount} Zellen
          </div>
          <EditorMetricsTable>
            <thead className="sticky top-0 bg-white">
              <tr className="border-b border-slate-200 text-left text-slate-600">
                <th className="px-2 py-2">Fallgruppe</th>
                <th className="bg-sky-50 px-2 py-2 text-sky-900" colSpan={3}>
                  Gültig
                </th>
                <th
                  className="border-l border-slate-200 bg-emerald-50 px-2 py-2 text-emerald-900"
                  colSpan={3}
                >
                  Vorschlag
                </th>
              </tr>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="px-2 py-2" />
                {currentFields.map((field) => (
                  <th key={field.key} className="bg-sky-50/70 px-2 py-2 text-sky-800">
                    {field.columnLabel}
                  </th>
                ))}
                <th className="bg-sky-50/70 px-2 py-2 text-sky-800">Fälle/Jahr</th>
                {proposedFields.map((field) => (
                  <th
                    key={field.key}
                    className={`bg-emerald-50/70 px-2 py-2 text-emerald-800 ${
                      field === proposedFields[0] ? "border-l border-slate-200" : ""
                    }`}
                  >
                    {field.columnLabel}
                  </th>
                ))}
                <th className="bg-emerald-50/70 px-2 py-2 text-emerald-800">Fälle/Jahr</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const draftRow = draft[row.case_group_id] || buildCaseDraftRow(row);
                const changedCellsByField = changedByCaseGroupId.get(row.case_group_id);
                const inputClass = (value: string) =>
                  `w-24 rounded px-2 py-1 ${
                    isValidNullableNumberInput(value)
                      ? `border border-slate-300 ${
                          isZeroInputValue(value) ? "text-slate-400" : "text-slate-900"
                        }`
                      : "border border-red-400 bg-red-50"
                  }`;
                const updateField = (fieldKey: CaseFieldKey, value: string) => {
                  setDraft((prev) => ({
                    ...prev,
                    [row.case_group_id]: { ...draftRow, [fieldKey]: value },
                  }));
                };
                return (
                  <tr key={row.case_group_id} className="border-b border-slate-100">
                    <td className="px-2 py-2 font-semibold text-slate-800">{row.case_group}</td>
                    {currentFields.map((field) => (
                      <td
                        key={`${row.case_group_id}-${field.key}`}
                        className={`px-2 py-2 ${
                          changedCellsByField?.[field.key] ? "bg-amber-50" : ""
                        }`}
                      >
                        <input
                          value={draftRow[field.key]}
                          onChange={(event) => updateField(field.key, event.target.value)}
                          className={inputClass(draftRow[field.key])}
                        />
                      </td>
                    ))}
                    <td
                      className={`px-2 py-2 ${
                        row.cases_current_effective === 0
                          ? "text-slate-400"
                          : "text-slate-700"
                      }`}
                    >
                      {formatNumber(row.cases_current_effective)}
                    </td>
                    {proposedFields.map((field) => (
                      <td
                        key={`${row.case_group_id}-${field.key}`}
                        className={`px-2 py-2 ${
                          changedCellsByField?.[field.key] ? "bg-amber-50" : ""
                        } ${field === proposedFields[0] ? "border-l border-slate-200" : ""}`}
                      >
                        <input
                          value={draftRow[field.key]}
                          onChange={(event) => updateField(field.key, event.target.value)}
                          className={inputClass(draftRow[field.key])}
                        />
                      </td>
                    ))}
                    <td
                      className={`px-2 py-2 ${
                        row.cases_proposed_effective === 0
                          ? "text-slate-400"
                          : "text-slate-700"
                      }`}
                    >
                      {formatNumber(row.cases_proposed_effective)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </EditorMetricsTable>
          <div className="flex justify-end gap-2">
            <button
              onClick={handleResetToModelValues}
              disabled={isSaving || rows.length === 0 || !hasEditedOverrides}
              className="rounded-full border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Auf Modellwerte zurücksetzen
            </button>
            <button
              onClick={() => setReviewMode(true)}
              disabled={changes.length === 0 || invalidCellCount > 0}
              className="rounded-full border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Prüfen
            </button>
          </div>
        </>
      ) : (
        <>
          <div className="text-[11px] font-semibold text-slate-600">
            Geänderte Einträge: {changes.length} Zeilen / {changedCellCount} Zellen
          </div>
          <ReviewDiffTable entityHeader="Fallgruppe" rows={reviewRows} />
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setReviewMode(false)}
              className="rounded-full border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700"
            >
              Zurück
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving || changes.length === 0 || invalidCellCount > 0}
              className="rounded-full bg-slate-900 px-4 py-2 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {isSaving ? "Speichert..." : "Änderungen speichern"}
            </button>
          </div>
        </>
      )}
      {invalidCellCount > 0 && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-800">
          Bitte ungültige Zahlenformate korrigieren ({invalidCellCount}).
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
