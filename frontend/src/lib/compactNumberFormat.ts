const WHOLE_NUMBER_FORMAT = new Intl.NumberFormat("de-DE", {
  maximumFractionDigits: 0,
});

type CompactUnit = {
  divisor: number;
  suffix: string;
};

const CURRENCY_UNITS: CompactUnit[] = [
  { divisor: 1_000_000_000, suffix: "Mrd." },
  { divisor: 1_000_000, suffix: "Mio." },
  { divisor: 1_000, suffix: "Tsd." },
];

const HOUR_UNITS: CompactUnit[] = [
  { divisor: 1_000_000, suffix: "Mio. h" },
  { divisor: 1_000, suffix: "Tsd. h" },
];

function resolveCompactUnit(value: number, units: CompactUnit[]): CompactUnit | null {
  const absolute = Math.abs(value);
  return units.find((unit) => absolute >= unit.divisor) ?? null;
}

function shouldPromoteAfterRounding(value: number, unit: CompactUnit): boolean {
  const scaled = Math.abs(value) / unit.divisor;
  return Math.round(scaled * 10) / 10 >= 1000;
}

function formatCompactUnit(value: number, unit: CompactUnit): string {
  const sign = value < 0 ? "-" : "";
  const scaled = Math.abs(value) / unit.divisor;
  const text = new Intl.NumberFormat("de-DE", {
    maximumFractionDigits: 1,
  }).format(scaled);
  return `${sign}${text} ${unit.suffix}`;
}

function formatSmallEuro(value: number): string {
  const text = new Intl.NumberFormat("de-DE", {
    minimumFractionDigits: Number.isInteger(value) ? 0 : 2,
    maximumFractionDigits: Number.isInteger(value) ? 0 : 2,
  }).format(value);
  return `${text} €`;
}

export function formatCompactCurrency(value: number): string {
  const unit = resolveCompactUnit(value, CURRENCY_UNITS);
  if (!unit) {
    return formatSmallEuro(value);
  }
  const unitIndex = CURRENCY_UNITS.indexOf(unit);
  const promotedUnit =
    shouldPromoteAfterRounding(value, unit) && unitIndex > 0
      ? CURRENCY_UNITS[unitIndex - 1]
      : unit;
  return `${formatCompactUnit(value, promotedUnit)} €`;
}

export function formatCompactHours(value: number): string {
  const unit = resolveCompactUnit(value, HOUR_UNITS);
  if (!unit) {
    return `${WHOLE_NUMBER_FORMAT.format(value)} h`;
  }
  const unitIndex = HOUR_UNITS.indexOf(unit);
  const promotedUnit =
    shouldPromoteAfterRounding(value, unit) && unitIndex > 0
      ? HOUR_UNITS[unitIndex - 1]
      : unit;
  return formatCompactUnit(value, promotedUnit);
}
