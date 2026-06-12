import { buildTileBodyText, buildTileMetricTable } from "@/components/tileMetrics";
import { Tile } from "@/types";

function buildTile(overrides: Partial<Tile>): Tile {
  return {
    id: "case_group_1",
    title: "Tile",
    text: "",
    meta_information: {},
    column: 0,
    row: 0,
    deletable: false,
    link_from_tile: [],
    ...overrides,
  };
}

describe("tileMetrics", () => {
  it("omits 'Fälle/Jahr' row when both values are missing", () => {
    const tile = buildTile({
      id: "case_group_11",
      meta_information: {
        addressees_current: 20,
        annual_frequency_current: 2,
        addressees_proposed: 25,
        annual_frequency_proposed: 3,
        cases_current: null,
        cases_proposed: null,
      },
    });

    const table = buildTileMetricTable(tile);
    expect(table?.rows.map((row) => row.label)).toEqual([
      "Betroffene",
      "Häufigkeit/Jahr",
    ]);
  });

  it("adds 'Kosten/Jahr' for step metrics when costs exist", () => {
    const tile = buildTile({
      id: "step_22",
      meta_information: {
        time_required_current: { a: 10, b: null, c: null, d: null },
        time_required_proposed: { a: 12, b: null, c: null, d: null },
        expenses_current: 1,
        expenses_proposed: 2,
        cost_current: 120,
        cost_proposed: 150.5,
      },
    });

    const table = buildTileMetricTable(tile);
    expect(table?.rows.map((row) => row.label)).toEqual([
      "eD/mD",
      "Sachaufwand",
      "Kosten/Jahr",
    ]);
  });

  it("uses business labels for step metrics when norm addressee is business", () => {
    const tile = buildTile({
      id: "step_44",
      meta_information: {
        time_required_current: { a: 5, b: 10, c: 15, d: 10 },
        time_required_proposed: { a: 6, b: 12, c: 18, d: 12 },
        cost_current: 100,
        cost_proposed: 120,
      },
    });

    const table = buildTileMetricTable(tile, "business");
    expect(table?.rows.map((row) => row.label)).toEqual([
      "Niedrig",
      "Mittel",
      "Hoch",
      "Ø",
      "Kosten/Jahr",
    ]);
  });

  it("uses personnel_rows with wage provenance for step metrics", () => {
    const tile = buildTile({
      id: "step_55",
      meta_information: {
        personnel_rows: [
          { label: "Laender - Gehobener Dienst", current_min: 12, proposed_min: 8 },
          { label: "Bund - Hoeherer Dienst", current_min: 5, proposed_min: null },
        ],
        cost_current: 100,
        cost_proposed: 80,
      },
    });

    const table = buildTileMetricTable(tile);
    expect(table?.rows.map((row) => row.label)).toEqual([
      "Laender - Gehobener Dienst",
      "Bund - Hoeherer Dienst",
      "Kosten/Jahr",
    ]);
  });

  it("prefers personnel_rows over stale slot time on the step metric table", () => {
    const tile = buildTile({
      id: "step_56",
      meta_information: {
        // Stale slot time from before a row edit; must be ignored.
        time_required_current: { a: 999, b: null, c: null, d: null },
        time_required_proposed: { a: 999, b: null, c: null, d: null },
        personnel_rows: [
          { label: "R - Mittel", current_min: 12, proposed_min: 8 },
        ],
      },
    });

    const table = buildTileMetricTable(tile, "business");
    expect(table?.rows.map((row) => row.label)).toEqual(["R - Mittel"]);
    expect(table?.rows[0].current).toContain("12");
    expect(table?.rows[0].current).not.toContain("999");
  });

  it("falls back to legacy step text rows when structured meta rows are missing", () => {
    const tile = buildTile({
      id: "step_33",
      text: [
        "Analyse der wirtschaftlichen Komponenten",
        "Gültig | Vorschlag",
        "hD: - | 240 min",
        "Sachaufwand: - | 0 €",
      ].join("\n"),
      meta_information: {
        description: [
          "Analyse der wirtschaftlichen Komponenten",
          "Gültig | Vorschlag",
          "hD: - | 240 min",
          "Sachaufwand: - | 0 €",
        ].join("\n"),
        cost_current: 0,
        cost_proposed: 240,
      },
    });

    const body = buildTileBodyText(tile);
    expect(body).toBe("Analyse der wirtschaftlichen Komponenten");

    const table = buildTileMetricTable(tile);
    expect(table?.rows.map((row) => row.label)).toEqual([
      "hD",
      "Sachaufwand",
      "Kosten/Jahr",
    ]);
    expect(table?.rows.find((row) => row.label === "hD")).toMatchObject({
      label: "hD",
      current: "-",
      proposed: "240 min",
    });
  });
});
