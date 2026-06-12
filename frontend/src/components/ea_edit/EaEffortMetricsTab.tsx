"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import EditorMetricsTable from "@/components/ea_edit/components/EditorMetricsTable";
import ReviewDiffTable, { ReviewDiffRow } from "@/components/ea_edit/components/ReviewDiffTable";
import { apiClient } from "@/lib/api";
import {
  PayGradeSlot as SharedPayGradeSlot,
  getColumnLabel as sharedGetColumnLabel,
} from "@/lib/effortLabels";
import { logClientError } from "@/lib/errorFeedback";
import {
  EditableCaseGroupRow,
  EditableProcessStepRow,
  NormAddressee,
  PersonnelEffortEntry,
} from "@/types";

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

type PayGradeSlot = SharedPayGradeSlot;

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

const getColumnLabel = sharedGetColumnLabel;

function getReviewLabel(
  normAddressee: NormAddressee,
  slot: PayGradeSlot,
  side: "current" | "proposed",
): string {
  const sidePrefix = side === "current" ? "Aktuelles Gesetz" : "Gesetzesentwurf";
  if (slot === "expenses") {
    return `${sidePrefix} Sachaufwand`;
  }
  return `${sidePrefix} Zeit ${getColumnLabel(normAddressee, slot)}`;
}

type StepField = (typeof STEP_FIELDS)[number];
type StepFieldKey = StepField["key"];
type StepDraftRow = Record<string, string>;
type StepDraft = Record<number, StepDraftRow>;

// One editable value in the step table. Steps WITH personnel rows edit times on
// the row-based model (saved via /process-steps/personnel-effort-edit); steps
// without (legacy/old sessions, citizens) keep the slot-based fields. Expenses
// stay step-level for both. Mirrors the cost engine's "rows authoritative when
// present" rule.
type EditableCell = {
  key: string;
  side: "current" | "proposed";
  slot: PayGradeSlot;
  model: number | null;
  edited: number | null;
  effective: number | null;
  sourceTag?: string;
  save:
    | { type: "bulk"; fieldKey: StepFieldKey }
    | {
        type: "personnel";
        period: "current" | "proposed";
        qualification: string;
        wageSourceKind: string;
        wageSourceValue: string;
      };
};

// Qualification -> table column (Julia's qualification order = slot order a..d).
const QUALIFICATION_SLOT: Record<string, Exclude<PayGradeSlot, "expenses">> = {
  einfacher_und_mittlerer_dienst: "a",
  gehobener_dienst: "b",
  hoeherer_dienst: "c",
  niedrig: "a",
  mittel: "b",
  hoch: "c",
  durchschnitt: "d",
};

const SOURCE_TAGS: Record<string, string> = {
  bund: "Bund",
  laender: "Länder",
  kommunen: "Kommunen",
  sozialversicherung: "SV",
  durchschnitt: "Ø",
  gesamtwirtschaft: "Gesamt",
};

function sourceTagOf(value: string): string {
  return SOURCE_TAGS[value] ?? value;
}

// All qualifications of an addressee in canonical (slot) order. Lets the user add
// effort for a qualification the LLM did not assign (Julia: move minutes between
// qualifications), matching the pre-redesign editor.
const QUALIFICATIONS_BY_ADDRESSEE: Record<string, string[]> = {
  administration: [
    "einfacher_und_mittlerer_dienst",
    "gehobener_dienst",
    "hoeherer_dienst",
    "durchschnitt",
  ],
  business: ["niedrig", "mittel", "hoch", "durchschnitt"],
};

function distinctSources(
  entries: PersonnelEffortEntry[]
): Array<{ kind: string; value: string }> {
  const seen = new Set<string>();
  const out: Array<{ kind: string; value: string }> = [];
  for (const entry of entries) {
    const key = `${entry.wage_source_kind}|${entry.wage_source_value}`;
    if (!seen.has(key)) {
      seen.add(key);
      out.push({ kind: entry.wage_source_kind, value: entry.wage_source_value });
    }
  }
  return out;
}

// The wage source under which empty qualification cells of a period are editable:
// the period's single source, or (when the period has no rows yet) the other
// period's single source. Null when ambiguous (mixed sources) -> only existing
// rows are shown.
function fillSourceForPeriod(
  row: EditableProcessStepRow,
  period: "current" | "proposed"
): { kind: string; value: string } | null {
  const here =
    (period === "current" ? row.personnel_effort_current : row.personnel_effort_proposed) ?? [];
  const hereSources = distinctSources(here);
  if (hereSources.length === 1) {
    return hereSources[0];
  }
  if (hereSources.length > 1) {
    return null;
  }
  const other =
    (period === "current" ? row.personnel_effort_proposed : row.personnel_effort_current) ?? [];
  const otherSources = distinctSources(other);
  return otherSources.length === 1 ? otherSources[0] : null;
}

function stepUsesPersonnelRows(row: EditableProcessStepRow): boolean {
  return (
    (row.personnel_effort_current?.length ?? 0) +
      (row.personnel_effort_proposed?.length ?? 0) >
    0
  );
}

function buildStepCells(row: EditableProcessStepRow): EditableCell[] {
  const personnel = stepUsesPersonnelRows(row);
  const cells: EditableCell[] = [];
  for (const field of STEP_FIELDS) {
    if (personnel && field.slot !== "expenses") {
      continue;
    }
    cells.push({
      key: field.key,
      side: field.side,
      slot: field.slot,
      model: row[field.key],
      edited: row[field.editedKey],
      effective: row[field.effectiveKey],
      save: { type: "bulk", fieldKey: field.key },
    });
  }
  if (!personnel) {
    return cells;
  }
  const qualifications = QUALIFICATIONS_BY_ADDRESSEE[row.norm_addressee] ?? [];
  for (const side of ["current", "proposed"] as const) {
    const entries =
      (side === "current" ? row.personnel_effort_current : row.personnel_effort_proposed) ?? [];
    const source = fillSourceForPeriod(row, side);
    if (source && qualifications.length > 0) {
      // Render every qualification under the step's source (Julia's order =
      // slot order); empty ones are blank and create a row on edit.
      for (const qualification of qualifications) {
        const entry = entries.find(
          (e) =>
            e.qualification === qualification &&
            e.wage_source_kind === source.kind &&
            e.wage_source_value === source.value
        );
        cells.push({
          key: `pe:${side}:${qualification}:${source.kind}:${source.value}`,
          side,
          slot: QUALIFICATION_SLOT[qualification] ?? "d",
          model: entry?.time_required_in_min ?? null,
          edited: entry?.time_required_in_min_edited ?? null,
          effective: entry?.time_required_in_min_edited ?? entry?.time_required_in_min ?? null,
          sourceTag: sourceTagOf(source.value),
          save: {
            type: "personnel",
            period: side,
            qualification,
            wageSourceKind: source.kind,
            wageSourceValue: source.value,
          },
        });
      }
      continue;
    }
    // Ambiguous (mixed sources): conservatively edit only existing rows.
    for (const entry of entries) {
      cells.push({
        key: `pe:${side}:${entry.qualification}:${entry.wage_source_kind}:${entry.wage_source_value}`,
        side,
        slot: QUALIFICATION_SLOT[entry.qualification] ?? "d",
        model: entry.time_required_in_min,
        edited: entry.time_required_in_min_edited,
        effective: entry.time_required_in_min_edited ?? entry.time_required_in_min,
        sourceTag: sourceTagOf(entry.wage_source_value),
        save: {
          type: "personnel",
          period: side,
          qualification: entry.qualification,
          wageSourceKind: entry.wage_source_kind,
          wageSourceValue: entry.wage_source_value,
        },
      });
    }
  }
  return cells;
}

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
  const draft: StepDraftRow = {};
  for (const cell of buildStepCells(row)) {
    draft[cell.key] = toLocalizedInputString(cell.effective);
  }
  return draft;
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
      items: Array<{ cell: EditableCell; next: number | null }>;
    }> = [];
    for (const row of stepRowsForChanges) {
      const draftRow = draft[row.step_id] || buildStepDraftRow(row);
      const items: Array<{ cell: EditableCell; next: number | null }> = [];
      for (const cell of buildStepCells(row)) {
        const input = draftRow[cell.key] ?? toLocalizedInputString(cell.effective);
        const next = normalizeEditedNumericInput(input, cell.model);
        if (numberChanged(next, cell.edited)) {
          items.push({ cell, next });
        }
      }
      if (items.length > 0) {
        changedRows.push({ row, items });
      }
    }
    return changedRows;
  }, [stepRowsForChanges, draft]);

  const changedCellCount = useMemo(
    () => changes.reduce((acc, item) => acc + item.items.length, 0),
    [changes]
  );
  const changedStepCount = changes.length;
  const changedCaseGroupCount = useMemo(
    () => new Set(changes.map((item) => item.row.case_group_id)).size,
    [changes]
  );
  const changedByStepId = useMemo(
    () =>
      new Map(
        changes.map((item) => [
          item.row.step_id,
          new Set(item.items.map(({ cell }) => cell.key)),
        ])
      ),
    [changes]
  );
  const reviewRows = useMemo<ReviewDiffRow[]>(() => {
    const result: ReviewDiffRow[] = [];
    for (const item of changes) {
      const caseGroupLabel =
        caseGroupLabelById.get(item.row.case_group_id) ||
        `Fallgruppe ${item.row.case_group_id}`;
      for (const { cell, next } of item.items) {
        result.push({
          entityId: item.row.step_id,
          entityLabel: item.row.step,
          groupId: item.row.case_group_id,
          groupLabel: caseGroupLabel,
          fieldKey: cell.key,
          fieldLabel:
            getReviewLabel(normAddressee, cell.slot, cell.side) +
            (cell.sourceTag ? ` · ${cell.sourceTag}` : ""),
          modelValue: cell.model,
          activeValue: resolveEffectiveValue(cell.model, cell.edited),
          newValue: resolveEffectiveValue(cell.model, next),
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
          Object.values(rowDraft).filter((value) => !isValidNullableNumberInput(value)).length
        );
      }, 0),
    [draft]
  );
  const hasEditedOverrides = useMemo(
    () =>
      stepRowsForChanges.some((row) =>
        buildStepCells(row).some((cell) => cell.edited !== null)
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
          // Step-level changes (slot times for legacy steps, expenses for all)
          // go through the bulk update; personnel time changes go per row to the
          // row-based endpoint.
          const bulkRows: Array<{ step_id: number } & Record<StepFieldKey, number | null>> = [];
          const personnelEdits: Array<{
            row: EditableProcessStepRow;
            save: Extract<EditableCell["save"], { type: "personnel" }>;
            next: number | null;
          }> = [];
          for (const item of changes) {
            const bulkChanged = new Map<StepFieldKey, number | null>();
            for (const { cell, next } of item.items) {
              if (cell.save.type === "bulk") {
                bulkChanged.set(cell.save.fieldKey, next);
              } else {
                personnelEdits.push({ row: item.row, save: cell.save, next });
              }
            }
            if (bulkChanged.size > 0) {
              const payloadRow = { step_id: item.row.step_id } as {
                step_id: number;
              } & Record<StepFieldKey, number | null>;
              for (const field of STEP_FIELDS) {
                payloadRow[field.key] = bulkChanged.has(field.key)
                  ? bulkChanged.get(field.key) ?? null
                  : item.row[field.editedKey];
              }
              bulkRows.push(payloadRow);
            }
          }
          if (bulkRows.length > 0) {
            await apiClient.bulkUpdateProcessSteps({ appSessionId, rows: bulkRows });
          }
          for (const edit of personnelEdits) {
            await apiClient.updatePersonnelEffortTime({
              appSessionId,
              normAddressee: edit.row.norm_addressee,
              stepId: edit.row.step_id,
              period: edit.save.period,
              qualification: edit.save.qualification,
              wageSourceKind: edit.save.wageSourceKind,
              wageSourceValue: edit.save.wageSourceValue,
              timeRequiredInMinEdited: edit.next,
            });
          }
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
          const hasBulkEdited = stepRowsForChanges.some((row) =>
            STEP_FIELDS.some((field) => row[field.editedKey] !== null)
          );
          if (hasBulkEdited) {
            await apiClient.bulkUpdateProcessSteps({
              appSessionId,
              rows: stepRowsForChanges.map((row) => {
                const payloadRow = { step_id: row.step_id } as {
                  step_id: number;
                } & Record<StepFieldKey, number | null>;
                for (const field of STEP_FIELDS) {
                  payloadRow[field.key] = null;
                }
                return payloadRow;
              }),
            });
          }
          for (const row of stepRowsForChanges) {
            for (const cell of buildStepCells(row)) {
              if (cell.save.type !== "personnel" || cell.edited === null) {
                continue;
              }
              await apiClient.updatePersonnelEffortTime({
                appSessionId,
                normAddressee: row.norm_addressee,
                stepId: row.step_id,
                period: cell.save.period,
                qualification: cell.save.qualification,
                wageSourceKind: cell.save.wageSourceKind,
                wageSourceValue: cell.save.wageSourceValue,
                timeRequiredInMinEdited: null,
              });
            }
          }
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
    setStatus(null);
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
                  Aktuelles Gesetz
                </th>
                <th
                  className="border-l border-slate-200 bg-emerald-50 px-2 py-2 text-emerald-900"
                  colSpan={proposedFields.length}
                >
                  Gesetzesentwurf
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
                const cells = buildStepCells(row);
                const draftRow = draft[row.step_id] || buildStepDraftRow(row);
                const changedKeys = changedByStepId.get(row.step_id);
                const inputClass = (value: string) =>
                  `w-14 rounded px-1 py-1 ${
                    isValidNullableNumberInput(value)
                      ? `border border-slate-300 ${
                          isZeroInputValue(value) ? "text-slate-400" : "text-slate-900"
                        }`
                      : "border border-red-400 bg-red-50"
                  }`;
                const updateField = (cellKey: string, value: string) => {
                  setStatus(null);
                  setDraft((prev) => ({
                    ...prev,
                    [row.step_id]: { ...draftRow, [cellKey]: value },
                  }));
                };
                const renderColumn = (field: StepField, extraClass: string) => {
                  const columnCells = cells.filter(
                    (cell) => cell.side === field.side && cell.slot === field.slot
                  );
                  const changed = columnCells.some((cell) => changedKeys?.has(cell.key));
                  return (
                    <td
                      key={`${row.step_id}-${field.key}`}
                      className={`px-2 py-2 ${changed ? "bg-amber-50" : ""} ${extraClass}`}
                    >
                      {columnCells.length === 0 ? (
                        <span className="text-slate-300">–</span>
                      ) : (
                        <div className="space-y-1">
                          {columnCells.map((cell) => (
                            <div key={cell.key} className="flex items-center gap-1">
                              <input
                                value={draftRow[cell.key] ?? ""}
                                onChange={(event) => updateField(cell.key, event.target.value)}
                                className={inputClass(draftRow[cell.key] ?? "")}
                              />
                              {columnCells.length > 1 && cell.sourceTag && (
                                <span className="whitespace-nowrap text-[10px] text-slate-500">
                                  {cell.sourceTag}
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </td>
                  );
                };
                const stepSources = distinctSources([
                  ...(row.personnel_effort_current ?? []),
                  ...(row.personnel_effort_proposed ?? []),
                ]);
                return (
                  <tr key={row.step_id} className="border-b border-slate-100">
                    <td className="px-2 py-2 font-semibold text-slate-800">
                      {row.step}
                      {stepSources.length === 1 && (
                        <span className="ml-1 font-normal text-[10px] text-slate-500">
                          · {sourceTagOf(stepSources[0].value)}
                        </span>
                      )}
                    </td>
                    {currentFields.map((field) => renderColumn(field, ""))}
                    {proposedFields.map((field) =>
                      renderColumn(
                        field,
                        field === proposedFields[0] ? "border-l border-slate-200" : ""
                      )
                    )}
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
