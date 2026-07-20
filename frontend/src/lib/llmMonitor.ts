import { LlmMonitorRecentCall } from "@/types";

const SQLITE_TIMESTAMP_PATTERN = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/;

export function parseMonitorTimestampMs(value?: string | null): number {
  if (!value) {
    return 0;
  }
  const normalized = SQLITE_TIMESTAMP_PATTERN.test(value)
    ? `${value.replace(" ", "T")}Z`
    : value;
  const parsed = Date.parse(normalized);
  return Number.isNaN(parsed) ? 0 : parsed;
}

export function formatMonitorClock(value?: string | null): string {
  const parsed = parseMonitorTimestampMs(value);
  if (!parsed) {
    return value || "-";
  }
  return new Date(parsed).toLocaleTimeString("de-DE", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function sortRecentCallsNewestFirst(
  recent: LlmMonitorRecentCall[]
): LlmMonitorRecentCall[] {
  return [...recent].sort((a, b) => {
    const timestampDelta =
      parseMonitorTimestampMs(b.created_at) - parseMonitorTimestampMs(a.created_at);
    if (timestampDelta !== 0) {
      return timestampDelta;
    }
    return Number(b.answer_id || 0) - Number(a.answer_id || 0);
  });
}

/**
 * #64 (P7): Ueberholte (superseded) Fehlversuche im Debug-Monitor herausfiltern.
 *
 * `recent` ist newest-first. Taucht dasselbe `(prompt_id, norm_addressee)`
 * erneut auf, ist die aeltere `invalid`-Zeile durch den spaeteren Versuch
 * ueberholt. Solche Zeilen werden bei `hideStale` ausgeblendet; der neueste
 * Eintrag je Gruppe und alle aktiven Zeilen bleiben immer sichtbar. `hideStale`
 * beeinflusst nur die Anzeige, `staleRecentCount` zaehlt unabhaengig davon.
 */
export function selectVisibleRecent(
  recent: LlmMonitorRecentCall[],
  hideStale: boolean
): { visibleRecent: LlmMonitorRecentCall[]; staleRecentCount: number } {
  const seenKeys = new Set<string>();
  const visibleRecent: LlmMonitorRecentCall[] = [];
  let staleRecentCount = 0;
  for (const row of recent) {
    const key = `${row.prompt_id || "-"}::${(
      row.norm_addressee || ""
    ).toLowerCase()}`;
    const isSuperseded = seenKeys.has(key) && row.answer_state === "invalid";
    seenKeys.add(key);
    if (isSuperseded) {
      staleRecentCount += 1;
      if (hideStale) {
        continue;
      }
    }
    visibleRecent.push(row);
  }
  return { visibleRecent, staleRecentCount };
}
