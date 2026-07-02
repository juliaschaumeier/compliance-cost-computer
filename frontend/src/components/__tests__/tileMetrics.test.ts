import {
  buildTileBodyText,
  buildTileHeaderMetrics,
  buildTileMetricTable,
} from "@/components/tileMetrics";
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
  it("renders case group delta pills for introduced groups with missing current cases", () => {
    const tile = buildTile({
      id: "case_group_11",
      meta_information: {
        change_status: "eingefuehrt",
        cases_current: null,
        cases_proposed: 16,
      },
    });

    expect(buildTileHeaderMetrics(tile)).toEqual({
      left: "Δ +16",
      right: null,
    });
  });

  it("renders case group delta pills for removed groups with missing proposed cases", () => {
    const tile = buildTile({
      id: "case_group_12",
      meta_information: {
        change_status: "abgeschafft",
        cases_current: 16,
        cases_proposed: null,
      },
    });

    expect(buildTileHeaderMetrics(tile)).toEqual({
      left: "Δ -16",
      right: null,
    });
  });

  it("does not render case group delta pills for changed groups with incomplete cases", () => {
    const tile = buildTile({
      id: "case_group_13",
      meta_information: {
        change_status: "geaendert",
        cases_current: null,
        cases_proposed: 16,
      },
    });

    expect(buildTileHeaderMetrics(tile)).toEqual({
      left: null,
      right: null,
    });
  });

  it("renders step delta pills for introduced steps with missing current cost", () => {
    const tile = buildTile({
      id: "step_22",
      meta_information: {
        change_status: "eingefuehrt",
        cost_current: null,
        cost_proposed: 2937.6,
      },
    });

    expect(buildTileHeaderMetrics(tile)).toEqual({
      left: "Δ 2,9 Tsd. €",
      right: null,
    });
  });

  it("renders step delta pills for removed steps with missing proposed cost", () => {
    const tile = buildTile({
      id: "step_23",
      meta_information: {
        change_status: "abgeschafft",
        cost_current: 2937.6,
        cost_proposed: null,
      },
    });

    expect(buildTileHeaderMetrics(tile)).toEqual({
      left: "Δ -2,9 Tsd. €",
      right: null,
    });
  });

  it("does not render step delta pills for changed steps with incomplete costs", () => {
    const tile = buildTile({
      id: "step_24",
      meta_information: {
        change_status: "geaendert",
        cost_current: null,
        cost_proposed: 2937.6,
      },
    });

    expect(buildTileHeaderMetrics(tile)).toEqual({
      left: null,
      right: null,
    });
  });

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
    expect(table).toMatchObject({
      variant: "table",
      rows: [
        { label: "Betroffene" },
        { label: "Häufigkeit/Jahr" },
      ],
    });
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
    expect(table).toMatchObject({
      variant: "table",
      rows: [
        { label: "eD/mD" },
        { label: "Sachaufwand" },
        { label: "Kosten/Jahr" },
      ],
    });
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
    expect(table).toMatchObject({
      variant: "table",
      rows: [
        { label: "Niedrig" },
        { label: "Mittel" },
        { label: "Hoch" },
        { label: "Ø" },
        { label: "Kosten/Jahr" },
      ],
    });
  });

  it("formats citizen total-cost tiles as compact annual effort summaries", () => {
    const tile = buildTile({
      id: "total_cost",
      title: "Jährlicher Erfüllungsaufwand",
      text: "Zeit: -32706666.6667 Std.\nSachaufwand: 0 €",
      meta_information: {
        total_time_hours: -32706666.6667,
        total_expenses: 0,
      },
    });

    expect(buildTileBodyText(tile)).toBe("");
    expect(buildTileMetricTable(tile, "citizens")).toEqual({
      variant: "summary",
      alwaysVisible: true,
      suppressTitle: true,
      titleLikeLabels: true,
      items: [
        {
          label: "Jährlicher Zeitaufwand",
          value: "-32,7 Mio. h",
          emphasis: true,
        },
        {
          label: "Jährliche Sachkosten",
          value: "0 €",
        },
      ],
    });
  });

  it("formats non-citizen total-cost tile text from metadata instead of stored backend text", () => {
    const tile = buildTile({
      id: "total_cost",
      title: "Jährliche Kosten",
      text: "-1,66 Mrd. €",
      meta_information: {
        total_cost: -1655330000,
      },
    });

    expect(buildTileBodyText(tile)).toBe("-1,7 Mrd. €");
  });

  it("ignores stored backend text for total-cost tiles without numeric metadata", () => {
    const tile = buildTile({
      id: "total_cost",
      title: "Jährliche Kosten",
      text: "-1,66 Mrd. €",
      meta_information: {},
    });

    expect(buildTileBodyText(tile)).toBe("");
  });

  it("formats explicit zero citizen totals as zero time and zero Sachkosten", () => {
    const tile = buildTile({
      id: "total_cost",
      title: "Jährliche Kosten",
      meta_information: {
        total_time_minutes: 0,
        total_expenses: 0,
      },
    });

    expect(buildTileMetricTable(tile, "citizens")).toEqual({
      variant: "summary",
      alwaysVisible: true,
      suppressTitle: true,
      titleLikeLabels: true,
      items: [
        {
          label: "Jährlicher Zeitaufwand",
          value: "0 h",
          emphasis: true,
        },
        {
          label: "Jährliche Sachkosten",
          value: "0 €",
        },
      ],
    });
  });

  it("shows citizen step tile time deltas without a zero-euro header metric", () => {
    const tile = buildTile({
      id: "step_44",
      meta_information: {
        time_required_current: { a: 10, b: null, c: null, d: null },
        time_required_proposed: { a: 12, b: null, c: null, d: null },
        cost_current: 0,
        cost_proposed: 0,
      },
    });

    expect(buildTileHeaderMetrics(tile, "citizens")).toEqual({
      left: "Δ +2 min",
      right: null,
    });
  });

  it("keeps citizen step tile euro deltas when Sachaufwand changes", () => {
    const tile = buildTile({
      id: "step_44",
      meta_information: {
        time_required_current: { a: 10, b: null, c: null, d: null },
        time_required_proposed: { a: 12, b: null, c: null, d: null },
        cost_current: 5,
        cost_proposed: 9,
      },
    });

    expect(buildTileHeaderMetrics(tile, "citizens")).toEqual({
      left: "Δ +2 min",
      right: "Δ 4 €",
    });
  });

  it("uses personnel_rows with wage provenance for step metrics", () => {
    const tile = buildTile({
      id: "step_55",
      meta_information: {
        personnel_rows: [
          { label: "Länder - gD", current_min: 12, proposed_min: 8 },
          { label: "Bund - hD", current_min: 5, proposed_min: null },
        ],
        cost_current: 100,
        cost_proposed: 80,
      },
    });

    const table = buildTileMetricTable(tile);
    expect(table?.rows.map((row) => row.label)).toEqual([
      "Länder - gD",
      "Bund - hD",
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
    expect(table).toMatchObject({
      variant: "table",
      rows: [
        {
          label: "hD",
          current: "-",
          proposed: "240 min",
        },
        { label: "Sachaufwand" },
        { label: "Kosten/Jahr" },
      ],
    });
  });
});
