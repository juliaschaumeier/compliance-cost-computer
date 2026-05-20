import { getColumnLabel } from "@/lib/effortLabels";
import { NormAddressee, Tile } from "@/types";

export type TileTableRow = {
  label: string;
  current: string;
  proposed: string;
  emphasizeTop?: boolean;
};

export type TileMetricTable = {
  rows: TileTableRow[];
};

type ParsedLegacyTable = {
  description: string;
  rows: TileTableRow[];
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

function formatCurrencyCompact(value: number): string {
  const sign = value < 0 ? "-" : "";
  const absolute = Math.abs(value);
  const compact = (divisor: number, suffix: string): string => {
    const scaled = absolute / divisor;
    const digits = scaled >= 100 ? 0 : scaled >= 10 ? 1 : 2;
    const text = new Intl.NumberFormat("de-DE", {
      minimumFractionDigits: 0,
      maximumFractionDigits: digits,
    }).format(scaled);
    return `${sign}${text} ${suffix} €`;
  };

  if (absolute >= 1_000_000_000) {
    return compact(1_000_000_000, "Mrd.");
  }
  if (absolute >= 1_000_000) {
    return compact(1_000_000, "Mio.");
  }
  if (absolute >= 1_000) {
    return compact(1_000, "Tsd.");
  }
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: Number.isInteger(absolute) ? 0 : 2,
    maximumFractionDigits: Number.isInteger(absolute) ? 0 : 2,
  }).format(value);
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

export function buildTileBodyText(tile: Tile): string {
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
  tile: Tile
): { left: string | null; right: string | null } {
  const meta = tile.meta_information || {};
  if (tile.id.startsWith("process_")) {
    const processCost = toFiniteNumber(meta.cost);
    return {
      left: processCost === null ? null : `Σ ${formatCurrencyCompact(processCost)}`,
      right: null,
    };
  }
  if (tile.id.startsWith("step_")) {
    const current = toFiniteNumber(meta.cost_current);
    const proposed = toFiniteNumber(meta.cost_proposed);
    if (current === null || proposed === null) {
      return { left: null, right: null };
    }
    return {
      left: `Δ ${formatCurrencyCompact(proposed - current)}`,
      right: null,
    };
  }
  if (tile.id.startsWith("case_group_")) {
    const currentCases = toFiniteNumber(meta.cases_current);
    const proposedCases = toFiniteNumber(meta.cases_proposed);
    if (currentCases === null || proposedCases === null) {
      return { left: null, right: null };
    }
    const delta = proposedCases - currentCases;
    const prefix = delta > 0 ? "+" : "";
    return {
      left: `Δ ${prefix}${formatCount(delta)}`,
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
    return mergedRows.length > 0 ? { rows: mergedRows } : null;
  }

  if (tile.id.startsWith("step_")) {
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
    const rows: TileTableRow[] = [];
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
    const fallbackRows = parseLegacyStepText(tile.text || "").rows;
    const mergedRows = orderRows(
      mergeRows(rows, fallbackRows),
      [...rowDefs.map((r) => r.label), "Sachaufwand", "Kosten/Jahr"]
    );
    return mergedRows.length > 0 ? { rows: mergedRows } : null;
  }

  return null;
}
