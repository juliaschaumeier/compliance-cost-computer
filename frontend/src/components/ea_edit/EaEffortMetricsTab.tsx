"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import EditorMetricsTable from "@/components/ea_edit/components/EditorMetricsTable";
import ReviewDiffTable, { ReviewDiffRow } from "@/components/ea_edit/components/ReviewDiffTable";
import { apiClient } from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";
import { EditableCaseGroupRow, EditableProcessStepRow, NormAddressee } from "@/types";

import {
  isValidNullableNumberInput,
  isZeroInputValue,
  normalizeEditedNumericInput,
  numberChanged,
  resolveEffectiveValue,
  toLocalizedInputString,
} from "./utils";
import { useEaReviewSave } from "./useEaReviewSave";

type EaEffortMetricsTabProps = {
  open: boolean;
  active: boolean;
  appSessionId: string;
  normAddressee: NormAddressee;
  runAutoRecompute: () => Promise<void>;
  onDirtyChange?: (dirty: boolean) => void;
};

type PayGradeSlot = "a" | "b" | "c" | "d" | "expenses";

const STEP_FIELDS = [
  {
    key: "time_required_in_min_a_current",
    editedKey: "time_required_in_min_a_current_edited",
    effectiveKey: "time_required_in_min_a_current_effective",
    side: "current",
    slot: "a" as PayGradeSlot,
  },
  {
    key: "time_required_in_min_b_current",
    editedKey: "time_required_in_min_b_current_edited",
    effectiveKey: "time_required_in_min_b_current_effective",
    side: "current",
    slot: "b" as PayGradeSlot,
  },
  {
    key: "time_required_in_min_c_current",
    editedKey: "time_required_in_min_c_current_edited",
    effectiveKey: "time_required_in_min_c_current_effective",
    side: "current",
    slot: "c" as PayGradeSlot,
  },
  {
    key: "time_required_in_min_d_current",
    editedKey: "time_required_in_min_d_current_edited",
    effectiveKey: "time_required_in_min_d_current_effective",
    side: "current",
    slot: "d" as PayGradeSlot,
  },
  {
    key: "expenses_current",
    editedKey: "expenses_current_edited",
    effectiveKey: "expenses_current_effective",
    side: "current",
    slot: "expenses" as PayGradeSlot,
  },
  {
    key: "time_required_in_min_a_proposed",
    editedKey: "time_required_in_min_a_proposed_edited",
    effectiveKey: "time_required_in_min_a_proposed_effective",
    side: "proposed",
    slot: "a" as PayGradeSlot,
  },
  {
    key: "time_required_in_min_b_proposed",
    editedKey: "time_required_in_min_b_proposed_edited",
    effectiveKey: "time_required_in_min_b_proposed_effective",
    side: "proposed",
    slot: "b" as PayGradeSlot,
  },
  {
    key: "time_required_in_min_c_proposed",
    editedKey: "time_required_in_min_c_proposed_edited",
    effectiveKey: "time_required_in_min_c_proposed_effective",
    side: "proposed",
    slot: "c" as PayGradeSlot,
  },
  {
    key: "time_required_in_min_d_proposed",
    editedKey: "time_required_in_min_d_proposed_edited",
    effectiveKey: "time_required_in_min_d_proposed_effective",
    side: "proposed",
    slot: "d" as PayGradeSlot,
  },
  {
    key: "expenses_proposed",
    editedKey: "expenses_proposed_edited",
    effectiveKey: "expenses_proposed_effective",
    side: "proposed",
    slot: "expenses" as PayGradeSlot,
  },
] as const;

const COLUMN_LABELS_BY_ADDRESSEE: Record<NormAddressee, Record<PayGradeSlot, string>> = {
  administration: {
    a: "eD/mD",
    b: "gD",
    c: "hD",
    d: "Ø",
    expenses: "Sach",
  },
  business: {
    a: "Niedrig",
    b: "Mittel",
    c: "Hoch",
    d: "Ø",
    expenses: "Sach",
  },
  citizens: {
    a: "Zeit",
    b: "Reserve B",
    c: "Reserve C",
    d: "Reserve D",
    expenses: "Sach",
  },
};

function getColumnLabel(normAddressee: NormAddressee, slot: PayGradeSlot): string {
  return COLUMN_LABELS_BY_ADDRESSEE[normAddressee][slot];
}

function getReviewLabel(
  normAddressee: NormAddressee,
  slot: PayGradeSlot,
  side: "current" | "proposed",
): string {
  const sidePrefix = side === "current" ? "Gültig" : "Vorschlag";
  if (slot === "expenses") {
    return `${sidePrefix} Sachaufwand`;
  }
  return `${sidePrefix} Zeit ${getColumnLabel(normAddressee, slot)}`;
}

type StepField = (typeof STEP_FIELDS)[number];
type StepFieldKey = StepField["key"];
type StepDraftRow = Record<StepFieldKey, string>;
type StepDraft = Record<number, StepDraftRow>;
type StepParsedValues = Record<StepFieldKey, number | null>;
type StepChangedCells = Record<StepFieldKey, boolean>;

function toCaseGroupOptionLabel(label: string, maxChars = 50): string {
  const compact = label.trim().replace(/\s+/g, " ");
  if (!compact) {
    return "Unbenannte Fallgruppe";
  }
  if (compact.length <= maxChars) {
    return compact;
  }
  return `${compact.slice(0, maxChars).trimEnd()}…`;
}

function buildStepDraftRow(row: EditableProcessStepRow): StepDraftRow {
  const draft = {} as StepDraftRow;
  for (const field of STEP_FIELDS) {
    draft[field.key] = toLocalizedInputString(row[field.effectiveKey]);
  }
  return draft;
}

function normalizeStepDraftRow(draftRow: StepDraftRow, row: EditableProcessStepRow): StepParsedValues {
  const parsed = {} as StepParsedValues;
  for (const field of STEP_FIELDS) {
    parsed[field.key] = normalizeEditedNumericInput(draftRow[field.key], row[field.key]);
  }
  return parsed;
}

export default function EaEffortMetricsTab({
  open,
  active,
  appSessionId,
  normAddressee,
  runAutoRecompute,
  onDirtyChange,
}: EaEffortMetricsTabProps) {
  const [isLoadingCaseGroups, setIsLoadingCaseGroups] = useState(false);
  const [isLoadingSteps, setIsLoadingSteps] = useState(false);
  const [caseGroups, setCaseGroups] = useState<EditableCaseGroupRow[]>([]);
  const [selectedCaseGroupId, setSelectedCaseGroupId] = useState<number | null>(null);
  const [selectionNotice, setSelectionNotice] = useState<string | null>(null);
  const selectedCaseGroupIdRef = useRef<number | null>(null);
  const [stepRows, setStepRows] = useState<EditableProcessStepRow[]>([]);
  const [cachedStepRowsById, setCachedStepRowsById] = useState<
    Record<number, EditableProcessStepRow>
  >({});
  const [cachedStepIdsByCaseGroup, setCachedStepIdsByCaseGroup] = useState<
    Record<number, number[]>
  >({});
  const cachedStepIdsByCaseGroupRef = useRef<Record<number, number[]>>({});
  const [loadedSessionKey, setLoadedSessionKey] = useState<string | null>(null);
  const [draft, setDraft] = useState<StepDraft>({});
  const { reviewMode, setReviewMode, isSaving, status, setStatus, runSave } =
    useEaReviewSave({
      logLabel: "EaEffortMetricsTab.save",
      logContext: { appSessionId, selectedCaseGroupId },
    });

  useEffect(() => {
    selectedCaseGroupIdRef.current = selectedCaseGroupId;
  }, [selectedCaseGroupId]);

  useEffect(() => {
    cachedStepIdsByCaseGroupRef.current = cachedStepIdsByCaseGroup;
  }, [cachedStepIdsByCaseGroup]);

  const currentFields = useMemo(
    () => STEP_FIELDS.filter((field) => field.side === "current"),
    []
  );
  const proposedFields = useMemo(
    () => STEP_FIELDS.filter((field) => field.side === "proposed"),
    []
  );

  const caseGroupOptions = useMemo(() => {
    const dedup = new Map<number, string>();
    for (const row of caseGroups) {
      if (!dedup.has(row.case_group_id)) {
        dedup.set(row.case_group_id, row.case_group);
      }
    }
    return Array.from(dedup.entries()).map(([id, label], index) => ({
      id,
      label,
      shortLabel: toCaseGroupOptionLabel(label),
      fallbackIndex: index + 1,
    }));
  }, [caseGroups]);

  const selectedIndex = useMemo(() => {
    if (selectedCaseGroupId === null) {
      return -1;
    }
    return caseGroupOptions.findIndex((option) => option.id === selectedCaseGroupId);
  }, [caseGroupOptions, selectedCaseGroupId]);

  const selectedCaseGroupLabel = useMemo(
    () => caseGroupOptions.find((option) => option.id === selectedCaseGroupId)?.label ?? null,
    [caseGroupOptions, selectedCaseGroupId]
  );
  const caseGroupLabelById = useMemo(() => {
    const map = new Map<number, string>();
    for (const row of caseGroups) {
      if (!map.has(row.case_group_id)) {
        map.set(row.case_group_id, row.case_group);
      }
    }
    return map;
  }, [caseGroups]);

  const loadKey = `${appSessionId}::${normAddressee}`;

  const loadCaseGroups = useCallback(async () => {
    setIsLoadingCaseGroups(true);
    setStatus(null);
    setSelectionNotice(null);
    try {
      const payload = await apiClient.getEditableCaseGroups({ appSessionId });
      const filteredRows = payload.rows.filter(
        (row) => row.norm_addressee === normAddressee
      );
      setCaseGroups(filteredRows);
      setLoadedSessionKey(loadKey);
      const validCaseGroupIds = new Set(filteredRows.map((row) => row.case_group_id));
      setCachedStepRowsById((prev) => {
        let changed = false;
        const next: Record<number, EditableProcessStepRow> = {};
        for (const [stepIdRaw, row] of Object.entries(prev)) {
          if (!validCaseGroupIds.has(row.case_group_id)) {
            changed = true;
            continue;
          }
          next[Number(stepIdRaw)] = row;
        }
        if (changed) {
          return next;
        }
        return prev;
      });
      setCachedStepIdsByCaseGroup((prev) => {
        let changed = false;
        const next: Record<number, number[]> = {};
        for (const [caseGroupIdRaw, stepIds] of Object.entries(prev)) {
          const caseGroupId = Number(caseGroupIdRaw);
          if (!validCaseGroupIds.has(caseGroupId)) {
            changed = true;
            continue;
          }
          next[caseGroupId] = stepIds;
        }
        return changed ? next : prev;
      });
      const previous = selectedCaseGroupIdRef.current;
      const firstId = filteredRows.length > 0 ? filteredRows[0].case_group_id : null;
      let nextSelection = previous;
      let nextNotice: string | null = null;
      if (filteredRows.length === 0) {
        if (previous !== null) {
          nextNotice = "Gewählte Fallgruppe ist nicht mehr verfügbar.";
        }
        nextSelection = null;
      } else if (previous === null) {
        nextSelection = firstId;
      } else if (!filteredRows.some((row) => row.case_group_id === previous)) {
        nextSelection = firstId;
        nextNotice =
          "Gewählte Fallgruppe ist nicht mehr verfügbar. Zur ersten Fallgruppe gewechselt.";
      }
      setSelectedCaseGroupId(nextSelection);
      setSelectionNotice(nextNotice);
    } catch (error) {
      logClientError("EaEffortMetricsTab.loadCaseGroups", error, {
        appSessionId,
        normAddressee,
      });
      setStatus("Fallgruppen konnten nicht geladen werden.");
    } finally {
      setIsLoadingCaseGroups(false);
    }
  }, [appSessionId, normAddressee, loadKey, setStatus]);

  useEffect(() => {
    setIsLoadingCaseGroups(false);
    setIsLoadingSteps(false);
    setCaseGroups([]);
    setSelectedCaseGroupId(null);
    setSelectionNotice(null);
    setStepRows([]);
    setCachedStepRowsById({});
    setCachedStepIdsByCaseGroup({});
    setDraft({});
    setReviewMode(false);
    setStatus(null);
    setLoadedSessionKey(null);
  }, [appSessionId, normAddressee, setStatus, setReviewMode]);

  const loadSteps = useCallback(
    async (caseGroupId: number | null) => {
      if (caseGroupId === null) {
        setStepRows([]);
        return;
      }
      setIsLoadingSteps(true);
      setStatus(null);
      try {
        const payload = await apiClient.getEditableProcessSteps({
          appSessionId,
          caseGroupId,
        });
        setStepRows(payload.rows);
        setCachedStepRowsById((prev) => {
          const next = { ...prev };
          const previousStepIds = cachedStepIdsByCaseGroupRef.current[caseGroupId] || [];
          previousStepIds.forEach((stepId) => {
            delete next[stepId];
          });
          payload.rows.forEach((row) => {
            next[row.step_id] = row;
          });
          return next;
        });
        setCachedStepIdsByCaseGroup((prev) => ({
          ...prev,
          [caseGroupId]: payload.rows.map((row) => row.step_id),
        }));
      } catch (error) {
        logClientError("EaEffortMetricsTab.loadSteps", error, {
          appSessionId,
          caseGroupId,
        });
        setStatus("Prozessschritte konnten nicht geladen werden.");
      } finally {
        setIsLoadingSteps(false);
      }
    },
    [appSessionId, setStatus]
  );

  useEffect(() => {
    if (!open || !active) {
      return;
    }
    if (loadedSessionKey === loadKey) {
      return;
    }
    loadCaseGroups();
  }, [open, active, loadCaseGroups, loadedSessionKey, loadKey]);

  useEffect(() => {
    if (!open || !active) {
      return;
    }
    if (selectedCaseGroupId === null) {
      setStepRows([]);
      return;
    }
    const hasCachedSelection = Object.prototype.hasOwnProperty.call(
      cachedStepIdsByCaseGroup,
      selectedCaseGroupId
    );
    if (loadedSessionKey === loadKey && hasCachedSelection) {
      const cachedStepIds = cachedStepIdsByCaseGroup[selectedCaseGroupId] || [];
      const cachedRows = cachedStepIds
        .map((stepId) => cachedStepRowsById[stepId])
        .filter((row): row is EditableProcessStepRow => Boolean(row));
      if (cachedRows.length === cachedStepIds.length) {
        setStepRows(cachedRows);
        return;
      }
    }
    loadSteps(selectedCaseGroupId);
  }, [
    open,
    active,
    selectedCaseGroupId,
    loadSteps,
    loadedSessionKey,
    loadKey,
    cachedStepIdsByCaseGroup,
    cachedStepRowsById,
  ]);

  useEffect(() => {
    const validStepIds = new Set(Object.keys(cachedStepRowsById).map((key) => Number(key)));
    setDraft((prev) => {
      let changed = false;
      const next: StepDraft = {};
      for (const [stepIdRaw, draftRow] of Object.entries(prev)) {
        const stepId = Number(stepIdRaw);
        if (!validStepIds.has(stepId)) {
          changed = true;
          continue;
        }
        next[stepId] = draftRow;
      }
      return changed ? next : prev;
    });
  }, [cachedStepRowsById]);

  const stepRowsForChanges = useMemo(() => {
    const ordered: EditableProcessStepRow[] = [];
    const seen = new Set<number>();
    for (const option of caseGroupOptions) {
      const stepIds = cachedStepIdsByCaseGroup[option.id] || [];
      for (const stepId of stepIds) {
        if (seen.has(stepId)) {
          continue;
        }
        const row = cachedStepRowsById[stepId];
        if (!row) {
          continue;
        }
        ordered.push(row);
        seen.add(stepId);
      }
    }
    const caseGroupRank = new Map(caseGroupOptions.map((option, index) => [option.id, index]));
    const leftovers = Object.values(cachedStepRowsById)
      .filter((row) => !seen.has(row.step_id))
      .sort((a, b) => {
        const aRank = caseGroupRank.get(a.case_group_id) ?? Number.MAX_SAFE_INTEGER;
        const bRank = caseGroupRank.get(b.case_group_id) ?? Number.MAX_SAFE_INTEGER;
        if (aRank !== bRank) {
          return aRank - bRank;
        }
        return a.step_id - b.step_id;
      });
    return [...ordered, ...leftovers];
  }, [cachedStepRowsById, cachedStepIdsByCaseGroup, caseGroupOptions]);

  const changes = useMemo(() => {
    const changedRows: Array<{
      row: EditableProcessStepRow;
      next: StepParsedValues;
      changedCellsByField: StepChangedCells;
      changedCells: number;
    }> = [];
    for (const row of stepRowsForChanges) {
      const draftRow = draft[row.step_id] || buildStepDraftRow(row);
      const next = normalizeStepDraftRow(draftRow, row);
      const changedCellsByField = {} as StepChangedCells;
      let changedCells = 0;
      for (const field of STEP_FIELDS) {
        const changed = numberChanged(next[field.key], row[field.editedKey]);
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
  }, [stepRowsForChanges, draft]);

  const changedCellCount = useMemo(
    () => changes.reduce((acc, item) => acc + item.changedCells, 0),
    [changes]
  );
  const changedStepCount = changes.length;
  const changedCaseGroupCount = useMemo(
    () => new Set(changes.map((item) => item.row.case_group_id)).size,
    [changes]
  );
  const changedByStepId = useMemo(
    () => new Map(changes.map((item) => [item.row.step_id, item.changedCellsByField])),
    [changes]
  );
  const reviewRows = useMemo<ReviewDiffRow[]>(() => {
    const result: ReviewDiffRow[] = [];
    for (const item of changes) {
      for (const field of STEP_FIELDS) {
        if (!item.changedCellsByField[field.key]) {
          continue;
        }
        const modelValue = item.row[field.key];
        const caseGroupLabel =
          caseGroupLabelById.get(item.row.case_group_id) ||
          `Fallgruppe ${item.row.case_group_id}`;
        result.push({
          entityId: item.row.step_id,
          entityLabel: item.row.step,
          groupId: item.row.case_group_id,
          groupLabel: caseGroupLabel,
          fieldKey: field.key,
          fieldLabel: getReviewLabel(normAddressee, field.slot, field.side),
          modelValue,
          activeValue: resolveEffectiveValue(modelValue, item.row[field.editedKey]),
          newValue: resolveEffectiveValue(modelValue, item.next[field.key]),
        });
      }
    }
    return result;
  }, [changes, caseGroupLabelById, normAddressee]);
  const invalidCellCount = useMemo(
    () =>
      Object.values(draft).reduce((count, rowDraft) => {
        return (
          count +
          STEP_FIELDS.filter((field) => !isValidNullableNumberInput(rowDraft[field.key])).length
        );
      }, 0),
    [draft]
  );
  const hasEditedOverrides = useMemo(
    () =>
      stepRowsForChanges.some((row) =>
        STEP_FIELDS.some((field) => row[field.editedKey] !== null)
      ),
    [stepRowsForChanges]
  );

  useEffect(() => {
    onDirtyChange?.(changes.length > 0);
  }, [changes.length, onDirtyChange]);

  const handleSave = async () => {
    try {
      await runSave(
        async () => {
          await apiClient.bulkUpdateProcessSteps({
            appSessionId,
            rows: changes.map((item) => {
              const payloadRow = { step_id: item.row.step_id } as { step_id: number } & StepParsedValues;
              for (const field of STEP_FIELDS) {
                payloadRow[field.key] = item.next[field.key];
              }
              return payloadRow;
            }),
          });
          await runAutoRecompute();
          setDraft({});
          setCachedStepRowsById({});
          setCachedStepIdsByCaseGroup({});
          setReviewMode(false);
          await loadSteps(selectedCaseGroupId);
        },
        {
          successMessage: "Schrittkosten gespeichert. Gesamtkosten wurden automatisch neu berechnet.",
          errorMessage: "Speichern fehlgeschlagen. Bitte Eingaben prüfen und erneut versuchen.",
        }
      );
    } catch {
      // Status handling is centralized in useEaReviewSave.
    }
  };

  const handleResetToModelValues = async () => {
    if (stepRowsForChanges.length === 0 || !hasEditedOverrides) {
      return;
    }
    try {
      await runSave(
        async () => {
          await apiClient.bulkUpdateProcessSteps({
            appSessionId,
            rows: stepRowsForChanges.map((row) => {
              const payloadRow = { step_id: row.step_id } as { step_id: number } & StepParsedValues;
              for (const field of STEP_FIELDS) {
                payloadRow[field.key] = null;
              }
              return payloadRow;
            }),
          });
          await runAutoRecompute();
          setDraft({});
          setCachedStepRowsById({});
          setCachedStepIdsByCaseGroup({});
          setReviewMode(false);
          await loadSteps(selectedCaseGroupId);
        },
        {
          successMessage:
            "Schrittkosten auf Modellwerte zurückgesetzt. Gesamtkosten wurden automatisch neu berechnet.",
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

  const handleSelectCaseGroup = (caseGroupId: number | null) => {
    setSelectionNotice(null);
    setSelectedCaseGroupId(caseGroupId);
  };

  const isLoading = isLoadingCaseGroups || isLoadingSteps;
  if (isLoading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
        Schrittdaten werden geladen...
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
          <div className="flex items-start gap-2">
            <div className="shrink-0 text-[11px] font-semibold text-slate-600">
              Ungespeicherte Änderungen: {changedCaseGroupCount} Fallgruppen /{" "}
              {changedStepCount} Schritte / {changedCellCount} Zellen
            </div>
            <div className="min-w-0 flex-1 text-xs">
              <div className="flex items-center justify-end gap-1.5">
                <button
                  disabled={selectedIndex <= 0}
                  onClick={() =>
                    handleSelectCaseGroup(caseGroupOptions[selectedIndex - 1]?.id ?? null)
                  }
                  className="rounded border border-slate-300 px-1.5 py-1 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  ← Vorherige
                </button>
                <select
                  value={selectedCaseGroupId ?? ""}
                  onChange={(event) => handleSelectCaseGroup(Number(event.target.value))}
                  className="w-96 max-w-full rounded border border-slate-300 px-2 py-1"
                >
                  {caseGroupOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.shortLabel || `Fallgruppe ${option.fallbackIndex}`}
                    </option>
                  ))}
                </select>
                <button
                  disabled={selectedIndex < 0 || selectedIndex >= caseGroupOptions.length - 1}
                  onClick={() =>
                    handleSelectCaseGroup(caseGroupOptions[selectedIndex + 1]?.id ?? null)
                  }
                  className="rounded border border-slate-300 px-1.5 py-1 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Nächste →
                </button>
              </div>
            </div>
          </div>
          {selectedCaseGroupLabel && (
            <div className="mt-4 text-left text-sm font-semibold leading-5 text-slate-700">
              {selectedCaseGroupLabel}
            </div>
          )}
          {selectionNotice && (
            <div className="rounded-xl border border-sky-200 bg-sky-50 px-3 py-2 text-xs font-semibold text-sky-800">
              {selectionNotice}
            </div>
          )}
          <EditorMetricsTable containerClassName="overflow-x-auto rounded-lg border border-slate-200">
            <thead className="sticky top-0 bg-white">
              <tr className="border-b border-slate-200 text-left text-slate-600">
                <th className="px-2 py-2">Schritt</th>
                <th className="bg-sky-50 px-2 py-2 text-sky-900" colSpan={currentFields.length}>
                  Gültig
                </th>
                <th
                  className="border-l border-slate-200 bg-emerald-50 px-2 py-2 text-emerald-900"
                  colSpan={proposedFields.length}
                >
                  Vorschlag
                </th>
              </tr>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="px-2 py-2" />
                {currentFields.map((field) => (
                  <th key={field.key} className="bg-sky-50/70 px-2 py-2 text-sky-800">
                    {getColumnLabel(normAddressee, field.slot)}
                  </th>
                ))}
                {proposedFields.map((field) => (
                  <th
                    key={field.key}
                    className={`bg-emerald-50/70 px-2 py-2 text-emerald-800 ${
                      field === proposedFields[0] ? "border-l border-slate-200" : ""
                    }`}
                  >
                    {getColumnLabel(normAddressee, field.slot)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {stepRows.map((row) => {
                const draftRow = draft[row.step_id] || buildStepDraftRow(row);
                const changedCellsByField = changedByStepId.get(row.step_id);
                const inputClass = (value: string) =>
                  `w-16 rounded px-1 py-1 ${
                    isValidNullableNumberInput(value)
                      ? `border border-slate-300 ${
                          isZeroInputValue(value) ? "text-slate-400" : "text-slate-900"
                        }`
                      : "border border-red-400 bg-red-50"
                  }`;
                const updateField = (fieldKey: StepFieldKey, value: string) => {
                  setDraft((prev) => ({
                    ...prev,
                    [row.step_id]: { ...draftRow, [fieldKey]: value },
                  }));
                };
                return (
                  <tr key={row.step_id} className="border-b border-slate-100">
                    <td className="px-2 py-2 font-semibold text-slate-800">{row.step}</td>
                    {currentFields.map((field) => (
                      <td
                        key={`${row.step_id}-${field.key}`}
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
                    {proposedFields.map((field) => (
                      <td
                        key={`${row.step_id}-${field.key}`}
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
                  </tr>
                );
              })}
            </tbody>
          </EditorMetricsTable>
          <div className="flex justify-end">
            <button
              onClick={handleResetToModelValues}
              disabled={isSaving || stepRowsForChanges.length === 0 || !hasEditedOverrides}
              className="rounded-full border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Auf Modellwerte zurücksetzen
            </button>
          </div>
          <div className="flex justify-end">
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
            Geänderte Einträge: {changedCaseGroupCount} Fallgruppen / {changedStepCount} Schritte /{" "}
            {changedCellCount} Zellen
          </div>
          <ReviewDiffTable entityHeader="Schritt" rows={reviewRows} />
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
