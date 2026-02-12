import { Tile } from "@/types";

type TileUpdate = {
  updated: Tile[];
  changed: Tile[];
};

export const normalizeRows = (input: Tile[]): TileUpdate => {
  const byColumn = new Map<number, Tile[]>();
  input.forEach((tile) => {
    const list = byColumn.get(tile.column) || [];
    list.push(tile);
    byColumn.set(tile.column, list);
  });
  const updated: Tile[] = [];
  const changed: Tile[] = [];
  for (const [, columnTiles] of byColumn.entries()) {
    const usedRows = new Set<number>();
    const sorted = [...columnTiles].sort((a, b) => {
      if (a.row !== b.row) {
        return a.row - b.row;
      }
      return a.id.localeCompare(b.id);
    });
    for (const tile of sorted) {
      let nextRow = tile.row;
      while (usedRows.has(nextRow)) {
        nextRow += 1;
      }
      usedRows.add(nextRow);
      if (nextRow !== tile.row) {
        const adjusted = { ...tile, row: nextRow };
        updated.push(adjusted);
        changed.push(adjusted);
      } else {
        updated.push(tile);
      }
    }
  }
  return { updated, changed };
};

export const alignStepsToCaseGroups = (input: Tile[]): TileUpdate => {
  const caseGroupRows = new Map<number, number>();
  input.forEach((tile) => {
    if (!tile.id.startsWith("case_group_")) {
      return;
    }
    const caseGroupId = tile.meta_information?.case_group_id;
    if (typeof caseGroupId === "number") {
      caseGroupRows.set(caseGroupId, tile.row);
    }
  });
  const updated: Tile[] = [];
  const changed: Tile[] = [];
  input.forEach((tile) => {
    if (!tile.id.startsWith("step_")) {
      updated.push(tile);
      return;
    }
    const caseGroupId = tile.meta_information?.case_group_id;
    if (typeof caseGroupId !== "number") {
      updated.push(tile);
      return;
    }
    const targetRow = caseGroupRows.get(caseGroupId);
    if (targetRow === undefined || targetRow === tile.row) {
      updated.push(tile);
      return;
    }
    const adjusted = { ...tile, row: targetRow };
    updated.push(adjusted);
    changed.push(adjusted);
  });
  return { updated, changed };
};

export const normalizeAndAlignTiles = (input: Tile[]): TileUpdate => {
  const normalized = normalizeRows(input);
  const aligned = alignStepsToCaseGroups(normalized.updated);
  const dedupedChanged = new Map(
    [...normalized.changed, ...aligned.changed].map((tile) => [tile.id, tile])
  );
  return {
    updated: aligned.updated,
    changed: Array.from(dedupedChanged.values()),
  };
};
