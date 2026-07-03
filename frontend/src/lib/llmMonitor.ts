import { LlmMonitorRecentCall } from "@/types";

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
