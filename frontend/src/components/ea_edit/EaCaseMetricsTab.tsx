"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import EditorMetricsTable from "@/components/ea_edit/components/EditorMetricsTable";
import ReviewDiffTable, { ReviewDiffRow } from "@/components/ea_edit/components/ReviewDiffTable";
import { apiClient } from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";
import { EditableCaseGroupRow, NormAddressee } from "@/types";

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
  normAddressee: NormAddressee;
  eaActivityId?: string | null;
  readOnly?: boolean;
  runAutoRecompute: () => Promise<void>;
  onDirtyChange?: (dirty: boolean) => void;
};

const CASE_FIELDS = [
  {
    key: "addressees_current",
    editedKey: "addressees_current_edited",
    effectiveKey: "addressees_current_effective",
    side: "current",
    researchKey: "anzahl_betroffene_gueltig",
    columnLabel: "Betroffene",
    reviewLabel: "Aktuelles Gesetz Betroffene",
  },
  {
    key: "annual_frequency_current",
    editedKey: "annual_frequency_current_edited",
    effectiveKey: "annual_frequency_current_effective",
    side: "current",
    researchKey: "haeufigkeit_pro_jahr_gueltig",
    columnLabel: "Häufigkeit",
    reviewLabel: "Aktuelles Gesetz Häufigkeit",
  },
  {
    key: "addressees_proposed",
    editedKey: "addressees_proposed_edited",
    effectiveKey: "addressees_proposed_effective",
    side: "proposed",
    researchKey: "anzahl_betroffene_vorschlag",
    columnLabel: "Betroffene",
    reviewLabel: "Gesetzesentwurf Betroffene",
  },
  {
    key: "annual_frequency_proposed",
    editedKey: "annual_frequency_proposed_edited",
    effectiveKey: "annual_frequency_proposed_effective",
    side: "proposed",
    researchKey: "haeufigkeit_pro_jahr_vorschlag",
    columnLabel: "Häufigkeit",
    reviewLabel: "Gesetzesentwurf Häufigkeit",
  },
] as const;

type CaseField = (typeof CASE_FIELDS)[number];
type CaseFieldKey = CaseField["key"];
type CaseDraftRow = Record<CaseFieldKey, string>;
type CaseDraft = Record<number, CaseDraftRow>;
type CaseParsedValues = Record<CaseFieldKey, number | null>;
type CaseChangedCells = Record<CaseFieldKey, boolean>;
type ResearchEvidence = {
  confidence?: string;
  explanation?: string;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function parseResearchMetadata(
  raw: EditableCaseGroupRow["case_metric_research_json"]
): Record<string, ResearchEvidence> {
  const parsed = typeof raw === "string" ? safeJsonParse(raw) : raw;
  const metadata = asRecord(parsed);
  if (!metadata) {
    return {};
  }
  const confidence = asRecord(metadata.confidence);
  const explanations = asRecord(metadata.erklaerungen);
  const result: Record<string, ResearchEvidence> = {};
  for (const field of CASE_FIELDS) {
    const key = field.researchKey;
    const explanation = explanations?.[key];
    const confidenceValue = confidence?.[key];
    result[key] = {
      confidence: typeof confidenceValue === "string" ? confidenceValue : undefined,
      explanation: typeof explanation === "string" ? explanation : undefined,
    };
  }
  return result;
}

function safeJsonParse(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function EvidenceDisclosure({
  evidence,
  dimmed,
}: {
  evidence?: ResearchEvidence;
  dimmed: boolean;
}) {
  if (!evidence?.confidence && !evidence?.explanation) {
    return null;
  }
  const confidence = evidence.confidence || "unbekannt";
  return (
    <details className={`mt-1 text-[10px] ${dimmed ? "opacity-40" : ""}`}>
      <summary className="inline-flex cursor-pointer list-none items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 font-semibold text-slate-600">
        <span>{confidence}</span>
        <span aria-hidden="true">▾</span>
      </summary>
      {evidence.explanation && (
        <div className="mt-1 max-w-[13rem] rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 leading-snug text-slate-600">
          {dimmed && (
            <div className="mb-1 font-semibold text-slate-500">
              Hinweis zum Modellwert
            </div>
          )}
          {evidence.explanation}
        </div>
      )}
    </details>
  );
}

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
  normAddressee,
  eaActivityId = null,
  readOnly = false,
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

  const loadKey = `${appSessionId}::${normAddressee}`;

  const loadRows = useCallback(async () => {
    setIsLoading(true);
    setStatus(null);
    try {
      const payload = await apiClient.getEditableCaseGroups({ appSessionId });
      setRows(payload.rows.filter((row) => row.norm_addressee === normAddressee));
      setLoadedSessionKey(loadKey);
    } catch (error) {
      logClientError("EaCaseMetricsTab.load", error, { appSessionId, normAddressee });
      setStatus("Fallzahlen konnten nicht geladen werden.");
    } finally {
      setIsLoading(false);
    }
  }, [appSessionId, normAddressee, loadKey, setStatus]);

  useEffect(() => {
    setRows([]);
    setDraft({});
    setLoadedSessionKey(null);
    setReviewMode(false);
    setStatus(null);
    setIsLoading(false);
  }, [appSessionId, normAddressee, setStatus, setReviewMode]);

  useEffect(() => {
    if (!open || !active) {
      return;
    }
    if (loadedSessionKey === loadKey) {
      return;
    }
    loadRows();
  }, [open, active, loadRows, loadedSessionKey, loadKey]);

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
    onDirtyChange?.(!readOnly && changes.length > 0);
  }, [changes.length, onDirtyChange, readOnly]);

  useEffect(() => {
    if (!readOnly) {
      return;
    }
    setDraft({});
    setReviewMode(false);
  }, [readOnly, setReviewMode]);

  const handleSave = async () => {
    if (readOnly || changes.length === 0 || invalidCellCount > 0) {
      return;
    }
    try {
      await runSave(
        async () => {
          await apiClient.bulkUpdateCaseGroups({
            appSessionId,
            eaActivityId: eaActivityId ?? undefined,
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
    if (readOnly || rows.length === 0 || !hasEditedOverrides) {
      return;
    }
    try {
      await runSave(
        async () => {
          await apiClient.bulkUpdateCaseGroups({
            appSessionId,
            eaActivityId: eaActivityId ?? undefined,
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
                  Aktuelles Gesetz
                </th>
                <th
                  className="border-l border-slate-200 bg-emerald-50 px-2 py-2 text-emerald-900"
                  colSpan={3}
                >
                  Gesetzesentwurf
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
                const researchEvidence = parseResearchMetadata(row.case_metric_research_json);
                const inputClass = (value: string) =>
                  `w-24 rounded px-2 py-1 ${
                    isValidNullableNumberInput(value)
                      ? `border border-slate-300 ${
                          isZeroInputValue(value) ? "text-slate-400" : "text-slate-900"
                        }`
                      : "border border-red-400 bg-red-50"
                  }`;
                const updateField = (fieldKey: CaseFieldKey, value: string) => {
                  if (readOnly) {
                    return;
                  }
                  setStatus(null);
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
                          disabled={readOnly}
                          className={inputClass(draftRow[field.key])}
                        />
                        <EvidenceDisclosure
                          evidence={researchEvidence[field.researchKey]}
                          dimmed={Boolean(changedCellsByField?.[field.key])}
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
                          disabled={readOnly}
                          className={inputClass(draftRow[field.key])}
                        />
                        <EvidenceDisclosure
                          evidence={researchEvidence[field.researchKey]}
                          dimmed={Boolean(changedCellsByField?.[field.key])}
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
              disabled={
                isSaving || readOnly || !eaActivityId || rows.length === 0 || !hasEditedOverrides
              }
              className="rounded-full border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Auf Modellwerte zurücksetzen
            </button>
            <button
              onClick={() => setReviewMode(true)}
              disabled={readOnly || !eaActivityId || changes.length === 0 || invalidCellCount > 0}
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
              disabled={
                isSaving ||
                readOnly ||
                !eaActivityId ||
                changes.length === 0 ||
                invalidCellCount > 0
              }
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
