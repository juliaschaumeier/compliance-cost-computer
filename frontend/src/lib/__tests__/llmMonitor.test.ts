import { selectVisibleRecent } from "@/lib/llmMonitor";
import { LlmMonitorRecentCall } from "@/types";

function call(overrides: Partial<LlmMonitorRecentCall>): LlmMonitorRecentCall {
  return {
    prompt_id: "process_step_analysis",
    model: "test-model",
    answer_state: "active",
    ...overrides,
  };
}

describe("selectVisibleRecent (#64 P7)", () => {
  it("blendet einen ueberholten invalid-Versuch aus, wenn ein neuerer folgt", () => {
    // newest-first: aktiver Retry (answer_id 2) verdraengt alten Fehlversuch (1).
    const recent = [
      call({ answer_id: 2, answer_state: "active" }),
      call({ answer_id: 1, answer_state: "invalid" }),
    ];

    const { visibleRecent, staleRecentCount } = selectVisibleRecent(recent, true);

    expect(visibleRecent.map((row) => row.answer_id)).toEqual([2]);
    expect(staleRecentCount).toBe(1);
  });

  it("behaelt die ueberholte Zeile, wenn hideStale false ist", () => {
    const recent = [
      call({ answer_id: 2, answer_state: "active" }),
      call({ answer_id: 1, answer_state: "invalid" }),
    ];

    const { visibleRecent, staleRecentCount } = selectVisibleRecent(recent, false);

    expect(visibleRecent.map((row) => row.answer_id)).toEqual([2, 1]);
    expect(staleRecentCount).toBe(1);
  });

  it("haelt aktuelle Fehler und unterscheidet Normadressaten", () => {
    // Zwei invalid-Zeilen, aber verschiedene Adressaten -> keiner verdraengt den
    // anderen, beide bleiben sichtbar.
    const recent = [
      call({ answer_id: 3, norm_addressee: "administration", answer_state: "invalid" }),
      call({ answer_id: 2, norm_addressee: "business", answer_state: "invalid" }),
    ];

    const { visibleRecent, staleRecentCount } = selectVisibleRecent(recent, true);

    expect(visibleRecent.map((row) => row.answer_id)).toEqual([3, 2]);
    expect(staleRecentCount).toBe(0);
  });
});
