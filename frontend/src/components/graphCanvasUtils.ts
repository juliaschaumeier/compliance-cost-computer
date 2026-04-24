import { Tile } from "@/types";

export type Viewport = { x: number; y: number; zoom: number };
export type Lane = { key: string; label: string; startCol: number; width: number };

const COLUMN_LABELS = [
  "Gesetz",
  "Vorgaben",
  "Prozesse",
  "Fallgruppen",
  "Schritte",
  "Aufwand",
  "Kosten",
] as const;

export function collectChangedTiles(original: Tile[], updated: Tile[]): Tile[] {
  const changed = updated.filter((tile, idx) => tile.column !== original[idx]?.column);
  return Array.from(new Map(changed.map((tile) => [tile.id, tile])).values());
}

export function findColumnRange(
  tiles: Tile[],
  prefix: string,
): { min: number | null; max: number | null } {
  const cols = tiles
    .filter((tile) => tile.id.startsWith(prefix))
    .map((tile) => tile.column);
  return {
    min: cols.length ? Math.min(...cols) : null,
    max: cols.length ? Math.max(...cols) : null,
  };
}

export function buildLanes(
  tiles: Tile[],
): { lanes: Lane[]; visibleLanes: Lane[]; maxColumn: number } {
  const lawColumn = tiles.find((tile) => tile.id === "law_tile")?.column ?? 0;
  const maxColumn = tiles.length
    ? Math.max(...tiles.map((tile) => tile.column))
    : lawColumn;
  const regulationRange = findColumnRange(tiles, "regulation_");
  const processRange = findColumnRange(tiles, "process_");
  const caseGroupRange = findColumnRange(tiles, "case_group_");
  const stepRange = findColumnRange(tiles, "step_");
  const vorgabenCol = regulationRange.min ?? lawColumn + 1;
  const prozesseCol = processRange.min ?? vorgabenCol + 1;
  const fallgruppenCol = caseGroupRange.min ?? prozesseCol + 1;
  const schritteStartCol = stepRange.min ?? fallgruppenCol + 1;
  const schritteEndCol = stepRange.max ?? schritteStartCol;
  const schritteWidth = Math.max(1, schritteEndCol - schritteStartCol + 1);
  const lanes: Lane[] = [
    { key: "law", label: COLUMN_LABELS[0], startCol: lawColumn, width: 1 },
    { key: "regulations", label: COLUMN_LABELS[1], startCol: vorgabenCol, width: 1 },
    { key: "processes", label: COLUMN_LABELS[2], startCol: prozesseCol, width: 1 },
    { key: "case_groups", label: COLUMN_LABELS[3], startCol: fallgruppenCol, width: 1 },
    { key: "steps", label: COLUMN_LABELS[4], startCol: schritteStartCol, width: schritteWidth },
    { key: "effort", label: COLUMN_LABELS[5], startCol: schritteEndCol + 1, width: 1 },
    { key: "costs", label: COLUMN_LABELS[6], startCol: schritteEndCol + 2, width: 1 },
  ];
  return {
    lanes,
    visibleLanes: lanes.filter((lane) => lane.startCol <= maxColumn),
    maxColumn,
  };
}

export function laneTitle(tiles: Tile[], lane: Lane): string {
  if (lane.key === "law" || lane.key === "effort") {
    return lane.label;
  }
  const count = tiles.filter(
    (tile) => tile.column >= lane.startCol && tile.column < lane.startCol + lane.width
  ).length;
  return `${count} ${lane.label}`;
}
