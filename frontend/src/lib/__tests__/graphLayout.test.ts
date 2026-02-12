import { alignStepsToCaseGroups, normalizeAndAlignTiles } from "@/lib/graphLayout";
import { Tile } from "@/types";

const makeTile = (overrides: Partial<Tile>): Tile => ({
  id: "tile",
  title: "Title",
  text: "Text",
  meta_information: {},
  column: 0,
  row: 0,
  deletable: false,
  link_from_tile: [],
  ...overrides,
});

describe("graphLayout", () => {
  it("aligns step tiles to their case group row after normalization", () => {
    const tiles: Tile[] = [
      makeTile({
        id: "case_group_1",
        column: 3,
        row: 2,
        meta_information: { case_group_id: 1 },
      }),
      makeTile({
        id: "case_group_2",
        column: 3,
        row: 5,
        meta_information: { case_group_id: 2 },
      }),
      makeTile({
        id: "step_10",
        column: 4,
        row: 0,
        meta_information: { case_group_id: 1 },
      }),
      makeTile({
        id: "step_11",
        column: 5,
        row: 1,
        meta_information: { case_group_id: 1 },
      }),
      makeTile({
        id: "step_20",
        column: 4,
        row: 0,
        meta_information: { case_group_id: 2 },
      }),
    ];

    const result = normalizeAndAlignTiles(tiles);
    const step10 = result.updated.find((tile) => tile.id === "step_10");
    const step11 = result.updated.find((tile) => tile.id === "step_11");
    const step20 = result.updated.find((tile) => tile.id === "step_20");

    expect(step10?.row).toBe(2);
    expect(step11?.row).toBe(2);
    expect(step20?.row).toBe(5);
    expect(result.changed.map((tile) => tile.id).sort()).toEqual(
      ["step_10", "step_11", "step_20"].sort()
    );
  });

  it("keeps step rows when the case group row is unavailable", () => {
    const tiles: Tile[] = [
      makeTile({
        id: "step_99",
        column: 4,
        row: 3,
        meta_information: { case_group_id: 99 },
      }),
    ];

    const result = alignStepsToCaseGroups(tiles);

    expect(result.updated[0].row).toBe(3);
    expect(result.changed).toHaveLength(0);
  });
});
