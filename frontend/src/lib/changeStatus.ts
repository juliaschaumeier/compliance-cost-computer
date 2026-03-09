export type ChangeStatus =
  | "eingefuehrt"
  | "geaendert"
  | "abgeschafft"
  | "unveraendert";

export function normalizeChangeStatus(value: unknown): ChangeStatus | null {
  if (typeof value !== "string") {
    return null;
  }
  const raw = value.trim().toLowerCase();
  if (
    raw === "unveraendert" ||
    raw === "unverändert" ||
    raw === "gleich" ||
    raw === "gleichbleibend" ||
    raw === "unchanged" ||
    raw === "same" ||
    raw === "no change" ||
    raw === "no_change"
  ) {
    return "unveraendert";
  }
  if (raw === "eingefuehrt" || raw === "eingeführt" || raw === "introduced" || raw === "new") {
    return "eingefuehrt";
  }
  if (
    raw === "abgeschafft" ||
    raw === "entfallen" ||
    raw === "entfaellt" ||
    raw === "obsolete" ||
    raw === "deleted" ||
    raw === "removed"
  ) {
    return "abgeschafft";
  }
  if (raw === "geaendert" || raw === "geändert" || raw === "changed" || raw === "updated") {
    return "geaendert";
  }
  return null;
}

export function getChangeStatusLabel(status: ChangeStatus): string {
  if (status === "eingefuehrt") {
    return "Neu";
  }
  if (status === "abgeschafft") {
    return "Abgeschafft";
  }
  if (status === "unveraendert") {
    return "Unverändert";
  }
  return "Geändert";
}
