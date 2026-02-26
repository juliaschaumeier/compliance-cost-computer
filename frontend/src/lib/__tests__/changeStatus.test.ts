import { getChangeStatusLabel, normalizeChangeStatus } from "@/lib/changeStatus";

describe("changeStatus helpers", () => {
  it("normalizes supported aliases", () => {
    expect(normalizeChangeStatus("eingeführt")).toBe("eingefuehrt");
    expect(normalizeChangeStatus("changed")).toBe("geaendert");
    expect(normalizeChangeStatus("removed")).toBe("abgeschafft");
  });

  it("returns null for unknown values", () => {
    expect(normalizeChangeStatus("foo")).toBeNull();
    expect(normalizeChangeStatus(null)).toBeNull();
  });

  it("maps status labels", () => {
    expect(getChangeStatusLabel("eingefuehrt")).toBe("Neu");
    expect(getChangeStatusLabel("geaendert")).toBe("Geändert");
    expect(getChangeStatusLabel("abgeschafft")).toBe("Abgeschafft");
  });
});
