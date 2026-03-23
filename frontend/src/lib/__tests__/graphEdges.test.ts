import { buildGraphEdges } from "@/lib/graphEdges";
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

describe("graphEdges", () => {
  it("deduplicates edges by source-target pair", () => {
    const tiles: Tile[] = [
      makeTile({ id: "law_tile" }),
      makeTile({
        id: "regulation_1",
        link_from_tile: ["law_tile", "law_tile"],
      }),
    ];

    const edges = buildGraphEdges(tiles, null);

    expect(edges).toHaveLength(1);
    expect(edges[0]?.id).toBe("e-law_tile-regulation_1");
    expect(edges[0]?.source).toBe("law_tile");
    expect(edges[0]?.target).toBe("regulation_1");
  });

  it("drops edges when source or target node is missing", () => {
    const tiles: Tile[] = [
      makeTile({
        id: "regulation_1",
        link_from_tile: ["ghost_source"],
      }),
    ];

    const edges = buildGraphEdges(tiles, null);

    expect(edges).toHaveLength(0);
  });

  it("applies highlight styles to active and dimmed edges", () => {
    const tiles: Tile[] = [
      makeTile({ id: "law_tile" }),
      makeTile({ id: "regulation_1", link_from_tile: ["law_tile"] }),
      makeTile({ id: "regulation_2", link_from_tile: ["law_tile"] }),
      makeTile({ id: "process_1", link_from_tile: ["regulation_1"] }),
    ];

    const edges = buildGraphEdges(tiles, "regulation_1");
    const byId = new Map(edges.map((edge) => [edge.id, edge]));
    const activeIncoming = byId.get("e-law_tile-regulation_1");
    const activeOutgoing = byId.get("e-regulation_1-process_1");
    const dimmed = byId.get("e-law_tile-regulation_2");

    expect(activeIncoming?.style?.stroke).toBe("#3b82f6");
    expect(activeOutgoing?.style?.stroke).toBe("#3b82f6");
    expect(dimmed?.style?.stroke).toBe("#94a3b8");
    expect(dimmed?.style?.opacity).toBe(0.25);
  });
});
