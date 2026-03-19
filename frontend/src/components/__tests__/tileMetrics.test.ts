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
