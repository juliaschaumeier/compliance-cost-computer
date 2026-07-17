import { LlmMonitorRecentCall } from "@/types";

export type ResponseFormatBadgeInfo = {
  label: "Schema" | "JSON" | "No format";
  variant: "neutral" | "warning";
};

const RESPONSE_FORMAT_LABELS: Record<string, ResponseFormatBadgeInfo["label"]> = {
  json_schema: "Schema",
  json_object: "JSON",
  none: "No format",
};

export function resolveResponseFormatBadge(row: {
  response_format_used?: string | null;
  response_format_downgraded?: boolean | null;
}): ResponseFormatBadgeInfo | null {
  const used = row.response_format_used;
  if (used === undefined || used === null) {
    return null;
  }
  const label = RESPONSE_FORMAT_LABELS[used];
  if (!label) {
    return null;
  }
  return {
    label,
    variant: row.response_format_downgraded ? "warning" : "neutral",
  };
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
