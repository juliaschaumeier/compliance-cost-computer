import { Edge } from "@xyflow/react";

import { Tile } from "@/types";

const ACTIVE_EDGE_STROKE = "#3b82f6";
const DIMMED_EDGE_STROKE = "#94a3b8";
const DEFAULT_EDGE_STROKE = "#0f172a";

export const buildGraphEdges = (
  tiles: Tile[],
  focusedNodeId: string | null
): Edge[] => {
  const highlightEnabled = Boolean(focusedNodeId);
  const nodeIdSet = new Set(tiles.map((tile) => tile.id));
  const seenEdgeIds = new Set<string>();
  const edges: Edge[] = [];

  tiles.forEach((tile) => {
    tile.link_from_tile.forEach((sourceId) => {
      if (!nodeIdSet.has(sourceId) || !nodeIdSet.has(tile.id)) {
        return;
      }
      const edgeId = `e-${sourceId}-${tile.id}`;
      if (seenEdgeIds.has(edgeId)) {
        return;
      }
      seenEdgeIds.add(edgeId);
      const isActive =
        !highlightEnabled || sourceId === focusedNodeId || tile.id === focusedNodeId;
      const strokeColor = highlightEnabled
        ? isActive
          ? ACTIVE_EDGE_STROKE
          : DIMMED_EDGE_STROKE
        : DEFAULT_EDGE_STROKE;
      edges.push({
        id: edgeId,
        source: sourceId,
        target: tile.id,
        style: {
          stroke: strokeColor,
          strokeWidth: highlightEnabled ? (isActive ? 2.5 : 1) : 2,
          opacity: highlightEnabled ? (isActive ? 1 : 0.25) : 1,
          strokeLinecap: "round",
          strokeLinejoin: "round",
        },
      });
    });
  });

  return edges;
};
