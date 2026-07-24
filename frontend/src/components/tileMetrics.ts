import { getColumnLabel } from "@/lib/effortLabels";
import { normalizeChangeStatus } from "@/lib/changeStatus";
import {
  formatCompactCount,
  formatCompactCurrency,
  formatCompactHours,
} from "@/lib/compactNumberFormat";
import { NormAddressee, Tile } from "@/types";

export type TileTableRow = {
  label: string;
  current: string;
  proposed: string;
  emphasizeTop?: boolean;
};

export type TileSummaryItem = {
  label: string;
  value: string;
  emphasis?: boolean;
};

export type TileMetricTable =
  | {
      variant: "table";
      rows: TileTableRow[];
    }
  | {
      variant: "summary";
      items: TileSummaryItem[];
      alwaysVisible?: boolean;
      suppressTitle?: boolean;
      titleLikeLabels?: boolean;
    };

type ParsedLegacyTable = {
  description: string;
  rows: TileTableRow[];
};

type CitizenTotalValues = {
  totalHours: number | null;
  totalExpenses: number | null;
};

type CitizenTotalSummary = {
  items: TileSummaryItem[];
};

type TileSummaryOptions = {
  alwaysVisible?: boolean;
  suppressTitle?: boolean;
  titleLikeLabels?: boolean;
};

export function toFiniteNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const normalized = value.trim().replace(/\./g, "").replace(",", ".");
    const parsed = Number.parseFloat(normalized);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return null;
}

function formatCount(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return new Intl.NumberFormat("de-DE", {
    maximumFractionDigits: Number.isInteger(value) ? 0 : 2,
  }).format(value);
}

function formatMinutes(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return `${formatCount(value)} min`;
}

function formatMinutesDeltaCompact(value: number): string {
  const prefix = value > 0 ? "+" : "";
  const absolute = Math.abs(value);
  if (absolute >= 60) {
    return `${prefix}${formatCompactHours(value / 60)}`;
  }
  return `${prefix}${formatMinutes(value)}`;
}

function formatEuro(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: Number.isInteger(value) ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function resolveDeltaValues(
  currentRaw: unknown,
  proposedRaw: unknown,
  changeStatusRaw: unknown,
): { current: number; proposed: number } | null {
  const current = toFiniteNumber(currentRaw);
  const proposed = toFiniteNumber(proposedRaw);
  if (current !== null && proposed !== null) {
    return { current, proposed };
  }

  const changeStatus = normalizeChangeStatus(changeStatusRaw);
  if (changeStatus === "eingefuehrt" && proposed !== null) {
    return { current: 0, proposed };
  }
  if (changeStatus === "abgeschafft" && current !== null) {
    return { current, proposed: 0 };
  }
  return null;
}

function normalizeStepLabel(raw: string): string | null {
  const lower = raw.trim().toLowerCase();
  if (!lower) {
    return null;
  }
  if (lower.includes("kosten")) {
    return "Kosten/Jahr";
  }
  if (lower.includes("sachaufwand")) {
    return "Sachaufwand";
  }
  const compact = lower.replace(/\s/g, "");
  if (compact.includes("ed/md") || compact.includes("edmd")) {
    return "eD/mD";
  }
  if (compact === "gd" || lower.includes("gehobener dienst")) {
    return "gD";
  }
  if (compact === "hd" || lower.includes("höherer dienst") || lower.includes("hoeherer dienst")) {
    return "hD";
  }
  if (compact === "ø" || compact === "o" || lower.includes("durchschnitt")) {
    return "Ø";
  }
  return null;
}

function normalizeCaseLabel(raw: string): string | null {
  const lower = raw.trim().toLowerCase();
  if (!lower) {
    return null;
  }
  if (lower.startsWith("betroffene")) {
    return "Betroffene";
  }
  if (lower.startsWith("häufigkeit/jahr") || lower.startsWith("haeufigkeit/jahr")) {
    return "Häufigkeit/Jahr";
  }
  if (lower.startsWith("fälle/jahr") || lower.startsWith("faelle/jahr")) {
    return "Fälle/Jahr";
  }
  return null;
}

function parseLegacyStepText(text: string): ParsedLegacyTable {
  const lines = text.split("\n").map((line) => line.trim());
  const rowRegex = /^([^:]+):\s*(.*?)\s*\|\s*(.*?)$/;
  const rows: TileTableRow[] = [];
  const descriptionLines: string[] = [];

  for (const line of lines) {
    if (!line) {
      continue;
    }
    const lower = line.toLowerCase();
    if (
      ((lower.includes("gültig") && lower.includes("vorschlag")) ||
        (lower.includes("aktuell") && lower.includes("entwurf"))) &&
      line.includes("|")
    ) {
      continue;
    }
    const match = line.match(rowRegex);
    if (match) {
      const label = normalizeStepLabel(match[1]);
      if (label) {
        rows.push({
          label,
          current: (match[2] || "-").trim() || "-",
          proposed: (match[3] || "-").trim() || "-",
          emphasizeTop: label === "Kosten/Jahr",
        });
        continue;
      }
    }
    descriptionLines.push(line);
  }

  return {
    description: descriptionLines.join("\n").trim(),
    rows,
  };
}

function parseLegacyCaseText(text: string): ParsedLegacyTable {
  const lines = text.split("\n").map((line) => line.trim());
  const descriptionLines: string[] = [];
  const currentValues = new Map<string, string>();
  const proposedValues = new Map<string, string>();
  let section: "none" | "current" | "proposed" = "none";
  const stepStyleRegex = /^([^:]+):\s*(.*?)\s*\|\s*(.*?)$/;

  for (const line of lines) {
    if (!line) {
      continue;
    }
    const lower = line.toLowerCase();
    if (lower === "gültig:" || lower === "gueltig:" || lower === "aktuell:") {
      section = "current";
      continue;
    }
    if (lower === "vorschlag:" || lower === "entwurf:") {
      section = "proposed";
      continue;
    }

    const stepStyle = line.match(stepStyleRegex);
    if (stepStyle) {
      const label = normalizeCaseLabel(stepStyle[1]);
      if (label) {
        currentValues.set(label, (stepStyle[2] || "-").trim() || "-");
        proposedValues.set(label, (stepStyle[3] || "-").trim() || "-");
        continue;
      }
    }

    const separator = line.indexOf(":");
    if (separator >= 0 && section !== "none") {
      const label = normalizeCaseLabel(line.slice(0, separator));
      if (label) {
        const value = line.slice(separator + 1).trim() || "-";
        if (section === "current") {
          currentValues.set(label, value);
        } else {
          proposedValues.set(label, value);
        }
        continue;
      }
    }
    descriptionLines.push(line);
  }

  const orderedLabels = ["Betroffene", "Häufigkeit/Jahr", "Fälle/Jahr"] as const;
  const rows: TileTableRow[] = orderedLabels
    .map((label) => {
      const current = currentValues.get(label) ?? "-";
      const proposed = proposedValues.get(label) ?? "-";
      if (current === "-" && proposed === "-") {
        return null;
      }
      return {
        label,
        current,
        proposed,
        emphasizeTop: label === "Fälle/Jahr",
      };
    })
    .filter((row): row is TileTableRow => Boolean(row));

  return {
    description: descriptionLines.join("\n").trim(),
    rows,
  };
}

function mergeRows(primary: TileTableRow[], fallback: TileTableRow[]): TileTableRow[] {
  const merged = primary.map((row) => ({ ...row }));
  const byLabel = new Map(merged.map((row) => [row.label, row]));

  for (const row of fallback) {
    const existing = byLabel.get(row.label);
    if (!existing) {
      const clone = { ...row };
      merged.push(clone);
      byLabel.set(clone.label, clone);
      continue;
    }
    if (existing.current === "-" && row.current !== "-") {
      existing.current = row.current;
    }
    if (existing.proposed === "-" && row.proposed !== "-") {
      existing.proposed = row.proposed;
    }
    existing.emphasizeTop = Boolean(existing.emphasizeTop || row.emphasizeTop);
  }
  return merged;
}

function orderRows(rows: TileTableRow[], order: readonly string[]): TileTableRow[] {
  const rank = new Map(order.map((label, index) => [label, index]));
  return [...rows].sort((a, b) => {
    const aRank = rank.get(a.label);
    const bRank = rank.get(b.label);
    if (aRank === undefined && bRank === undefined) {
      return 0;
    }
    if (aRank === undefined) {
      return 1;
    }
    if (bRank === undefined) {
      return -1;
    }
    return aRank - bRank;
  });
}

function parseLegacyTable(tile: Tile): ParsedLegacyTable {
  if (tile.id.startsWith("step_")) {
    return parseLegacyStepText(tile.text || "");
  }
  if (tile.id.startsWith("case_group_")) {
    return parseLegacyCaseText(tile.text || "");
  }
  return { description: tile.text || "", rows: [] };
}

function getCitizenTotalValues(tile: Tile): CitizenTotalValues {
  const meta = tile.meta_information || {};
  const totalTimeMinutes = toFiniteNumber(meta.total_time_minutes);
  const totalHours =
    toFiniteNumber(meta.total_time_hours) ??
    (totalTimeMinutes !== null ? totalTimeMinutes / 60 : null);
  return {
    totalHours,
    totalExpenses: toFiniteNumber(meta.total_expenses),
  };
}

function buildCitizenTotalSummary(tile: Tile): CitizenTotalSummary | null {
  const values = getCitizenTotalValues(tile);
  const items: TileSummaryItem[] = [];
  if (values.totalHours !== null) {
    items.push({
      label: "Jährlicher Zeitaufwand",
      value: formatCompactHours(values.totalHours),
      emphasis: true,
    });
  }
  if (values.totalExpenses !== null) {
    items.push({
      label: "Jährliche Sachkosten",
      value: formatCompactCurrency(values.totalExpenses),
    });
  }
  return items.length > 0 ? { items } : null;
}

function buildSummaryMetricTable(
  items: TileSummaryItem[],
  options: TileSummaryOptions = {},
): TileMetricTable {
  return {
    variant: "summary",
    items,
    ...options,
  };
}

function buildTableMetricTable(rows: TileTableRow[]): TileMetricTable {
  return {
    variant: "table",
    rows,
  };
}

export function buildTileBodyText(tile: Tile): string {
  if (tile.id === "total_cost") {
    if (buildCitizenTotalSummary(tile) !== null) {
      return "";
    }
    const totalCost = toFiniteNumber(tile.meta_information?.total_cost);
    return totalCost === null ? "" : formatCompactCurrency(totalCost);
  }
  if (
    (tile.id.startsWith("step_") || tile.id.startsWith("case_group_")) &&
    typeof tile.meta_information?.description === "string"
  ) {
    const parsed = parseLegacyTable({
      ...tile,
      text: tile.meta_information.description,
    });
    return parsed.description;
  }
  if (tile.id.startsWith("step_") || tile.id.startsWith("case_group_")) {
    return parseLegacyTable(tile).description;
  }
  return tile.text;
}

export function buildTileHeaderMetrics(
  tile: Tile,
  normAddressee: NormAddressee = "administration",
): { left: string | null; right: string | null } {
  const meta = tile.meta_information || {};
  if (tile.id.startsWith("process_")) {
    const processCost = toFiniteNumber(meta.cost);
    return {
      left: processCost === null ? null : `Σ ${formatCompactCurrency(processCost)}`,
      right: null,
    };
  }
  if (tile.id.startsWith("step_")) {
    if (normAddressee === "citizens") {
      const timeCurrent = meta.time_required_current as Record<string, unknown> | undefined;
      const timeProposed = meta.time_required_proposed as Record<string, unknown> | undefined;
      const timeValues = resolveDeltaValues(
        timeCurrent?.a,
        timeProposed?.a,
        meta.change_status,
      );
      const costValues = resolveDeltaValues(
        meta.cost_current,
        meta.cost_proposed,
        meta.change_status,
      );
      const timeDelta = timeValues ? timeValues.proposed - timeValues.current : null;
      const costDelta = costValues ? costValues.proposed - costValues.current : null;
      return {
        left: timeDelta === null ? null : `Δ ${formatMinutesDeltaCompact(timeDelta)}`,
        right:
          costDelta === null || costDelta === 0
            ? null
            : `Δ ${formatCompactCurrency(costDelta)}`,
      };
    }
    const deltaValues = resolveDeltaValues(
      meta.cost_current,
      meta.cost_proposed,
      meta.change_status,
    );
    if (!deltaValues) {
      return { left: null, right: null };
    }
    return {
      left: `Δ ${formatCompactCurrency(deltaValues.proposed - deltaValues.current)}`,
      right: null,
    };
  }
  if (tile.id.startsWith("case_group_")) {
    const deltaValues = resolveDeltaValues(
      meta.cases_current,
      meta.cases_proposed,
      meta.change_status,
    );
    if (!deltaValues) {
      return { left: null, right: null };
    }
    const delta = deltaValues.proposed - deltaValues.current;
    const prefix = delta > 0 ? "+" : "";
    return {
      left: `Δ ${prefix}${formatCompactCount(delta)}`,
      right: null,
    };
  }
  return { left: null, right: null };
}

export function buildTileMetricTable(
  tile: Tile,
  normAddressee: NormAddressee = "administration",
): TileMetricTable | null {
  const meta = tile.meta_information || {};
  if (tile.id === "total_cost" && normAddressee === "citizens") {
    const summary = buildCitizenTotalSummary(tile);
    return summary
      ? buildSummaryMetricTable(summary.items, {
          alwaysVisible: true,
          suppressTitle: true,
          titleLikeLabels: true,
        })
      : null;
  }

  if (tile.id.startsWith("case_group_")) {
    const addresseesCurrent = toFiniteNumber(meta.addressees_current);
    const annualFrequencyCurrent = toFiniteNumber(meta.annual_frequency_current);
    const casesCurrent = toFiniteNumber(meta.cases_current);
    const addresseesProposed = toFiniteNumber(meta.addressees_proposed);
    const annualFrequencyProposed = toFiniteNumber(meta.annual_frequency_proposed);
    const casesProposed = toFiniteNumber(meta.cases_proposed);

    const rows: TileTableRow[] = [];
    if (addresseesCurrent !== null || addresseesProposed !== null) {
      rows.push({
        label: "Betroffene",
        current: formatCount(addresseesCurrent),
        proposed: formatCount(addresseesProposed),
      });
    }
    if (annualFrequencyCurrent !== null || annualFrequencyProposed !== null) {
      rows.push({
        label: "Häufigkeit/Jahr",
        current: formatCount(annualFrequencyCurrent),
        proposed: formatCount(annualFrequencyProposed),
      });
    }
    if (casesCurrent !== null || casesProposed !== null) {
      rows.push({
        label: "Fälle/Jahr",
        current: formatCount(casesCurrent),
        proposed: formatCount(casesProposed),
        emphasizeTop: true,
      });
    }
    const fallbackRows = parseLegacyCaseText(tile.text || "").rows;
    const mergedRows = orderRows(
      mergeRows(rows, fallbackRows),
      ["Betroffene", "Häufigkeit/Jahr", "Fälle/Jahr"]
    );
    return mergedRows.length > 0 ? buildTableMetricTable(mergedRows) : null;
  }

  if (tile.id.startsWith("step_")) {
    // Row-based model: personnel rows carry their wage provenance as the label
    // (e.g. "Laender - Gehobener Dienst") and the effective minutes per period.
    // The slot-based path stays as the fallback for citizens / legacy steps.
    const personnelRows = meta.personnel_rows;
    const usePersonnel = Array.isArray(personnelRows) && personnelRows.length > 0;

    const rows: TileTableRow[] = [];
    let timeLabels: string[];
    if (usePersonnel) {
      (personnelRows as Array<Record<string, unknown>>).forEach((entry) => {
        const current = toFiniteNumber(entry.current_min);
        const proposed = toFiniteNumber(entry.proposed_min);
        if (current === null && proposed === null) {
          return;
        }
        rows.push({
          label: typeof entry.label === "string" ? entry.label : "",
          current: formatMinutes(current),
          proposed: formatMinutes(proposed),
        });
      });
      timeLabels = rows.map((row) => row.label);
    } else {
      const timeCurrent =
        (meta.time_required_current as Record<string, unknown> | undefined) || {};
      const timeProposed =
        (meta.time_required_proposed as Record<string, unknown> | undefined) || {};
      const rowDefs: Array<{ key: "a" | "b" | "c" | "d"; label: string }> = [
        { key: "a", label: getColumnLabel(normAddressee, "a") },
        { key: "b", label: getColumnLabel(normAddressee, "b") },
        { key: "c", label: getColumnLabel(normAddressee, "c") },
        { key: "d", label: getColumnLabel(normAddressee, "d") },
      ];
      rowDefs.forEach(({ key, label }) => {
        const current = toFiniteNumber(timeCurrent[key]);
        const proposed = toFiniteNumber(timeProposed[key]);
        if (current === null && proposed === null) {
          return;
        }
        rows.push({
          label,
          current: formatMinutes(current),
          proposed: formatMinutes(proposed),
        });
      });
      timeLabels = rowDefs.map((row) => row.label);
    }

    const expensesCurrent = toFiniteNumber(meta.expenses_current);
    const expensesProposed = toFiniteNumber(meta.expenses_proposed);
    if (expensesCurrent !== null || expensesProposed !== null) {
      rows.push({
        label: "Sachaufwand",
        current: formatEuro(expensesCurrent),
        proposed: formatEuro(expensesProposed),
      });
    }

    const costCurrent = toFiniteNumber(meta.cost_current);
    const costProposed = toFiniteNumber(meta.cost_proposed);
    if (costCurrent !== null || costProposed !== null) {
      rows.push({
        label: "Kosten/Jahr",
        current: formatEuro(costCurrent),
        proposed: formatEuro(costProposed),
        emphasizeTop: true,
      });
    }

    const order = [...timeLabels, "Sachaufwand", "Kosten/Jahr"];
    if (usePersonnel) {
      // Meta is authoritative here; do not merge the free-text fallback.
      const orderedRows = orderRows(rows, order);
      return orderedRows.length > 0 ? buildTableMetricTable(orderedRows) : null;
    }
    const fallbackRows = parseLegacyStepText(tile.text || "").rows;
    const mergedRows = orderRows(mergeRows(rows, fallbackRows), order);
    return mergedRows.length > 0 ? buildTableMetricTable(mergedRows) : null;
  }

  return null;
}
