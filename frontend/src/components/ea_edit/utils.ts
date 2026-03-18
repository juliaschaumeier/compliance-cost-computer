export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }
  return new Intl.NumberFormat("de-DE", { maximumFractionDigits: 2 }).format(value);
}

export function toInputString(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "";
  }
  return String(value);
}

export function toLocalizedInputString(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "";
  }
  const raw = String(value);
  if (raw.includes("e") || raw.includes("E")) {
    return new Intl.NumberFormat("de-DE", {
      useGrouping: false,
      maximumFractionDigits: 20,
    }).format(value);
  }
  return raw.replace(".", ",");
}

export function parseNullableNumber(value: string): number | null {
  const compact = value.trim().replace(/\s+/g, "");
  if (!compact) {
    return null;
  }
  const germanPattern = /^(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?$/;
  if (!germanPattern.test(compact)) {
    return null;
  }
  const normalized = compact.replace(/\./g, "").replace(",", ".");
  const parsed = Number.parseFloat(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

export function isValidNullableNumberInput(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed) {
    return true;
  }
  return parseNullableNumber(value) !== null;
}

export function numberChanged(next: number | null, original: number | null): boolean {
  if (next === null && original === null) {
    return false;
  }
  if (next === null || original === null) {
    return true;
  }
  return Math.abs(next - original) > 1e-9;
}

export function normalizeEditedNumericInput(input: string, modelValue: number | null): number | null {
  const parsed = parseNullableNumber(input);
  return numberChanged(parsed, modelValue) ? parsed : null;
}

export function resolveEffectiveValue(
  modelValue: number | null,
  editedValue: number | null
): number | null {
  return editedValue ?? modelValue;
}

export function isZeroInputValue(input: string): boolean {
  const parsed = parseNullableNumber(input);
  return parsed !== null && Math.abs(parsed) <= 1e-9;
}
