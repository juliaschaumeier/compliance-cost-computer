"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  Controls,
  type Node,
  type ReactFlowInstance,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";

import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";
import { normalizeChangeStatus } from "@/lib/changeStatus";
import { logClientError } from "@/lib/errorFeedback";
import { buildGraphEdges } from "@/lib/graphEdges";
import { normalizeAndAlignTiles } from "@/lib/graphLayout";
import {
  buildTileBodyText,
  buildTileHeaderMetrics,
  buildTileMetricTable,
} from "@/components/tileMetrics";
import { Tile } from "@/types";
import { TileNode } from "@/components/TileNode";

const COLUMN_WIDTH = 320;
const ROW_HEIGHT = 220;
const TILE_GAP = 64;
const TILE_HEIGHT = 160;
const COLUMN_LABELS = [
  "Gesetz",
  "Vorgaben",
  "Prozesse",
  "Fallgruppen",
  "Schritte",
  "Aufwand",
  "Kosten",
];
const LANE_HEIGHT = 2000;
const LANE_TOP_OFFSET = 56;

export default function GraphCanvas() {
  const { state } = useApp();
  const nodeTypesRef = useRef<{ tile: typeof TileNode } | null>(null);
  if (!nodeTypesRef.current || nodeTypesRef.current.tile !== TileNode) {
    nodeTypesRef.current = { tile: TileNode };
  }
  const nodeTypes = nodeTypesRef.current;
  const edgeTypesRef = useRef<Record<string, never> | null>(null);
  if (!edgeTypesRef.current) {
    edgeTypesRef.current = {};
  }
  const edgeTypes = edgeTypesRef.current;
  const [tiles, setTiles] = useState<Tile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [canvasHeight, setCanvasHeight] = useState<number | null>(null);
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);
  const [viewport, setViewport] = useState({ x: 0, y: 0, zoom: 1 });
  const [expandedNodeIds, setExpandedNodeIds] = useState<Record<string, boolean>>(
    {}
  );
  const [overflowIds, setOverflowIds] = useState<Set<string>>(new Set());
  const [tileHeights, setTileHeights] = useState<Record<string, number>>({});
  const containerRef = useRef<HTMLElement | null>(null);
  const bodyRefs = useRef<Map<string, HTMLParagraphElement | null>>(new Map());
  const nodeRefs = useRef<Map<string, HTMLDivElement | null>>(new Map());
  const nodeObservers = useRef<Map<string, ResizeObserver>>(new Map());
  const hasLoadedTilesRef = useRef(false);

  const registerBodyRef = useCallback(
    (id: string, element: HTMLParagraphElement | null) => {
      if (element) {
        bodyRefs.current.set(id, element);
      } else {
        bodyRefs.current.delete(id);
      }
    },
    []
  );

  const registerNodeRef = useCallback(
    (id: string, element: HTMLDivElement | null) => {
      if (!element) {
        nodeRefs.current.delete(id);
        const observer = nodeObservers.current.get(id);
        if (observer) {
          observer.disconnect();
          nodeObservers.current.delete(id);
        }
        setTileHeights((prev) => {
          if (!(id in prev)) {
            return prev;
          }
          const next = { ...prev };
          delete next[id];
          return next;
        });
        return;
      }
      const previous = nodeRefs.current.get(id);
      if (
        previous === element &&
        (nodeObservers.current.has(id) || typeof ResizeObserver === "undefined")
      ) {
        return;
      }
      nodeRefs.current.set(id, element);
      const existing = nodeObservers.current.get(id);
      if (existing) {
        existing.disconnect();
        nodeObservers.current.delete(id);
      }
      if (typeof ResizeObserver !== "undefined") {
        const observer = new ResizeObserver((entries) => {
          entries.forEach((entry) => {
            const nextHeight = Math.ceil(entry.contentRect.height);
            setTileHeights((prev) =>
              prev[id] === nextHeight ? prev : { ...prev, [id]: nextHeight }
            );
          });
        });
        observer.observe(element);
        nodeObservers.current.set(id, observer);
      }
      const nextHeight = Math.ceil(element.getBoundingClientRect().height);
      setTileHeights((prev) =>
        prev[id] === nextHeight ? prev : { ...prev, [id]: nextHeight }
      );
    },
    []
  );

  useEffect(() => {
    if (typeof ResizeObserver !== "undefined") {
      return;
    }
    if (typeof window === "undefined") {
      return;
    }
    const raf = window.requestAnimationFrame(() => {
      setTileHeights((prev) => {
        let changed = false;
        const next = { ...prev };
        nodeRefs.current.forEach((element, id) => {
          if (!element) {
            return;
          }
          const height = Math.ceil(element.getBoundingClientRect().height);
          if (next[id] !== height) {
            next[id] = height;
            changed = true;
          }
        });
        return changed ? next : prev;
      });
    });
    return () => window.cancelAnimationFrame(raf);
  }, [tiles, expandedNodeIds]);

  useEffect(() => {
    const observers = nodeObservers.current;
    return () => {
      observers.forEach((observer) => observer.disconnect());
      observers.clear();
    };
  }, []);

  useEffect(() => {
    const raf = window.requestAnimationFrame(() => {
      const next = new Set<string>();
      bodyRefs.current.forEach((element, id) => {
        if (!element || id === "law_tile") {
          return;
        }
        const visibleHeight = element.clientHeight;
        let hasOverflow = element.scrollHeight > visibleHeight + 1;
        if (visibleHeight > 0) {
          const clone = element.cloneNode(true) as HTMLParagraphElement;
          clone.style.position = "absolute";
          clone.style.visibility = "hidden";
          clone.style.pointerEvents = "none";
          clone.style.height = "auto";
          clone.style.maxHeight = "none";
          clone.style.overflow = "visible";
          clone.style.display = "block";
          clone.style.whiteSpace = "pre-line";
          clone.style.webkitLineClamp = "unset";
          clone.style.webkitBoxOrient = "vertical";
          clone.style.width = `${element.clientWidth}px`;
          document.body.appendChild(clone);
          const computed = window.getComputedStyle(clone);
          const fontSize = parseFloat(computed.fontSize || "0");
          const lineHeightValue = parseFloat(computed.lineHeight || "");
          const lineHeight =
            Number.isFinite(lineHeightValue) && lineHeightValue > 0
              ? lineHeightValue
              : fontSize > 0
                ? fontSize * 1.4
                : 18;
          const lineCount = lineHeight ? Math.ceil(clone.scrollHeight / lineHeight) : 0;
          hasOverflow = lineCount > 4;
          document.body.removeChild(clone);
        }
        if (hasOverflow) {
          next.add(id);
        }
      });
      setOverflowIds(next);
    });
    return () => window.cancelAnimationFrame(raf);
  }, [tiles, expandedNodeIds]);

  useEffect(() => {
    const ids = new Set(tiles.map((tile) => tile.id));
    setTileHeights((prev) => {
      let changed = false;
      const next = { ...prev };
      Object.keys(next).forEach((id) => {
        if (!ids.has(id)) {
          delete next[id];
          changed = true;
        }
      });
      return changed ? next : prev;
    });
  }, [tiles]);

  const refreshTiles = useCallback(async () => {
    if (!state.summaryReady) {
      setTiles([]);
      setLoading(false);
      hasLoadedTilesRef.current = true;
      setError(null);
      return;
    }
    try {
      if (!hasLoadedTilesRef.current) {
        setLoading(true);
      }
      const response = await apiClient.fetchTiles(state.appSessionId);
      const lawTile = response.tiles.find((tile) => tile.id === "law_tile");
      if (lawTile) {
        const updatedTiles = response.tiles.map((tile) => {
          if (!tile.id.startsWith("regulation_")) {
            return tile;
          }
          if (tile.column > lawTile.column) {
            return tile;
          }
          return { ...tile, column: lawTile.column + 1 };
        });
        const normalized = normalizeAndAlignTiles(updatedTiles);
        setTiles(normalized.updated);
        const columnChanged = updatedTiles.filter(
          (tile, idx) => tile.column !== response.tiles[idx].column
        );
        const changed = [...columnChanged, ...normalized.changed];
        if (changed.length) {
          const deduped = new Map(changed.map((tile) => [tile.id, tile]));
          await Promise.all(
            Array.from(deduped.values()).map((tile) =>
              apiClient.upsertTile(tile, state.appSessionId)
            )
          );
        }
      } else {
        const normalized = normalizeAndAlignTiles(response.tiles);
        setTiles(normalized.updated);
        const changed = [...normalized.changed];
        if (changed.length) {
          const deduped = new Map(changed.map((tile) => [tile.id, tile]));
          await Promise.all(
            Array.from(deduped.values()).map((tile) =>
              apiClient.upsertTile(tile, state.appSessionId)
            )
          );
        }
      }
      setError(null);
    } catch (err) {
      logClientError("GraphCanvas.refreshTiles", err, {
        appSessionId: state.appSessionId,
      });
      setError("Tiles konnten nicht geladen werden.");
    } finally {
      hasLoadedTilesRef.current = true;
      setLoading(false);
    }
  }, [state.summaryReady, state.appSessionId]);

  useEffect(() => {
    hasLoadedTilesRef.current = false;
  }, [state.appSessionId]);

  useEffect(() => {
    refreshTiles();
  }, [refreshTiles]);

  useEffect(() => {
    const updateHeight = () => {
      if (!containerRef.current) {
        return;
      }
      const rect = containerRef.current.getBoundingClientRect();
      setCanvasHeight(rect.height);
    };
    updateHeight();
    window.addEventListener("resize", updateHeight);
    return () => window.removeEventListener("resize", updateHeight);
  }, []);

  useEffect(() => {
    const handler = () => {
      refreshTiles();
    };
    window.addEventListener("tiles-updated", handler);
    return () => {
      window.removeEventListener("tiles-updated", handler);
    };
  }, [refreshTiles]);

  const handleDelete = useCallback(
    async (tileId: string) => {
      try {
        await apiClient.deleteTile(tileId, state.appSessionId);
        setTiles((prev) => prev.filter((tile) => tile.id !== tileId));
      } catch (err) {
        logClientError("GraphCanvas.deleteTile", err, {
          appSessionId: state.appSessionId,
          tileId,
        });
        setError("Tile konnte nicht gelöscht werden.");
      }
    },
    [state.appSessionId]
  );

  const relatedNodeIds = useMemo(() => {
    if (!focusedNodeId) {
      return new Set<string>();
    }
    const related = new Set<string>([focusedNodeId]);
    tiles.forEach((tile) => {
      tile.link_from_tile.forEach((sourceId) => {
        if (sourceId === focusedNodeId) {
          related.add(tile.id);
        }
        if (tile.id === focusedNodeId) {
          related.add(sourceId);
        }
      });
    });
    return related;
  }, [tiles, focusedNodeId]);

  const layout = useMemo(() => {
    const positions = new Map<
      string,
      { x: number; y: number; height: number }
    >();
    const columnBottoms = new Map<number, number>();
    const processYById = new Map<number, number>();
    let maxBottom = 0;

    const placeTile = (tile: Tile, y: number) => {
      const height = tileHeights[tile.id] ?? TILE_HEIGHT;
      const bottom = y + height;
      positions.set(tile.id, {
        x: tile.column * COLUMN_WIDTH,
        y,
        height,
      });
      maxBottom = Math.max(maxBottom, bottom);
      const prevColumnBottom = columnBottoms.get(tile.column) ?? 0;
      if (bottom > prevColumnBottom) {
        columnBottoms.set(tile.column, bottom);
      }
      if (tile.id.startsWith("process_")) {
        const parsed = Number.parseInt(tile.id.replace("process_", ""), 10);
        if (Number.isFinite(parsed)) {
          processYById.set(parsed, y);
        }
      }
      return height;
    };

    const parseCaseGroupId = (tile: Tile): number | null => {
      const fromMeta = tile.meta_information?.case_group_id;
      if (typeof fromMeta === "number") {
        return Number.isFinite(fromMeta) ? fromMeta : null;
      }
      if (typeof fromMeta === "string") {
        const parsed = Number.parseInt(fromMeta, 10);
        return Number.isFinite(parsed) ? parsed : null;
      }
      if (tile.id.startsWith("case_group_")) {
        const parsed = Number.parseInt(tile.id.replace("case_group_", ""), 10);
        return Number.isFinite(parsed) ? parsed : null;
      }
      return null;
    };

    const parseProcessId = (tile: Tile): number | null => {
      const fromMeta = tile.meta_information?.process_id;
      if (typeof fromMeta === "number") {
        return Number.isFinite(fromMeta) ? fromMeta : null;
      }
      if (typeof fromMeta === "string") {
        const parsed = Number.parseInt(fromMeta, 10);
        return Number.isFinite(parsed) ? parsed : null;
      }
      return null;
    };

    // 1) Lay out all non-step, non-case-group tiles per column independently.
    const regularTilesByColumn = new Map<number, Tile[]>();
    tiles.forEach((tile) => {
      if (tile.id.startsWith("case_group_") || tile.id.startsWith("step_")) {
        return;
      }
      const list = regularTilesByColumn.get(tile.column) || [];
      list.push(tile);
      regularTilesByColumn.set(tile.column, list);
    });
    regularTilesByColumn.forEach((columnTiles) => {
      const sorted = [...columnTiles].sort((a, b) =>
        a.row !== b.row ? a.row - b.row : a.id.localeCompare(b.id)
      );
      let y = 0;
      sorted.forEach((tile) => {
        const usedHeight = placeTile(tile, y);
        y += usedHeight + TILE_GAP;
      });
    });

    // 2) Lay out case-groups and their step rows with shared row heights.
    const caseGroupYById = new Map<number, number>();
    const caseGroupTiles = tiles
      .filter((tile) => tile.id.startsWith("case_group_"))
      .sort((a, b) => {
        const processYA = processYById.get(parseProcessId(a) ?? -1) ?? Number.MAX_SAFE_INTEGER;
        const processYB = processYById.get(parseProcessId(b) ?? -1) ?? Number.MAX_SAFE_INTEGER;
        if (processYA !== processYB) {
          return processYA - processYB;
        }
        if (a.row !== b.row) {
          return a.row - b.row;
        }
        return a.id.localeCompare(b.id);
      });
    const stepTiles = tiles
      .filter((tile) => tile.id.startsWith("step_"))
      .sort((a, b) =>
        a.column !== b.column
          ? a.column - b.column
          : a.row !== b.row
            ? a.row - b.row
            : a.id.localeCompare(b.id)
      );
    const stepTilesByCaseGroupId = new Map<number, Tile[]>();
    const orphanStepTiles: Tile[] = [];

    stepTiles.forEach((tile) => {
      const caseGroupId = parseCaseGroupId(tile);
      if (caseGroupId === null) {
        orphanStepTiles.push(tile);
        return;
      }
      const list = stepTilesByCaseGroupId.get(caseGroupId) || [];
      list.push(tile);
      stepTilesByCaseGroupId.set(caseGroupId, list);
    });

    let anchoredY = 0;
    caseGroupTiles.forEach((tile) => {
      const caseGroupId = parseCaseGroupId(tile);
      const processId = parseProcessId(tile);
      const processY = processId === null ? null : processYById.get(processId) ?? null;
      const linkedSteps =
        caseGroupId !== null ? (stepTilesByCaseGroupId.get(caseGroupId) ?? []) : [];
      const rowHeight = linkedSteps.reduce((maxHeight, stepTile) => {
        const stepHeight = tileHeights[stepTile.id] ?? TILE_HEIGHT;
        return Math.max(maxHeight, stepHeight);
      }, tileHeights[tile.id] ?? TILE_HEIGHT);

      const targetY = Math.max(anchoredY, processY ?? anchoredY);
      placeTile(tile, targetY);
      if (caseGroupId !== null) {
        caseGroupYById.set(caseGroupId, targetY);
      }
      linkedSteps.forEach((stepTile) => {
        placeTile(stepTile, targetY);
      });
      anchoredY = targetY + rowHeight + TILE_GAP;
    });

    // 3) Lay out orphan steps (without matching case-group) per column.
    stepTilesByCaseGroupId.forEach((linkedSteps, caseGroupId) => {
      if (caseGroupYById.has(caseGroupId)) {
        return;
      }
      orphanStepTiles.push(...linkedSteps);
    });
    orphanStepTiles
      .sort((a, b) =>
        a.column !== b.column
          ? a.column - b.column
          : a.row !== b.row
            ? a.row - b.row
            : a.id.localeCompare(b.id)
      )
      .forEach((tile) => {
        const currentBottom = columnBottoms.get(tile.column);
        const y = currentBottom === undefined ? 0 : currentBottom + TILE_GAP;
        placeTile(tile, y);
      });

    return { positions, maxBottom };
  }, [tiles, tileHeights]);

  const nodes: Node[] = useMemo(() => {
    const singleLawTile =
      tiles.length === 1 && tiles[0]?.id === "law_tile" && canvasHeight;
    const lawHeight =
      tiles.length === 1 ? tileHeights[tiles[0].id] ?? TILE_HEIGHT : TILE_HEIGHT;
    const centeredY = singleLawTile
      ? Math.max(0, (canvasHeight - lawHeight) / 2)
      : null;
    return tiles.map((tile) => {
      const layoutPos = layout.positions.get(tile.id);
      const metrics = buildTileHeaderMetrics(tile);
      return {
        id: tile.id,
        position: {
          x: layoutPos?.x ?? tile.column * COLUMN_WIDTH,
          y:
            singleLawTile && tile.id === "law_tile"
              ? centeredY ?? 0
              : layoutPos?.y ?? tile.row * ROW_HEIGHT,
        },
        data: {
          title: tile.title,
          text: buildTileBodyText(tile),
          deletable: tile.deletable,
          headerMetricLeft: metrics.left,
          headerMetricRight: metrics.right,
          metricTable: buildTileMetricTable(tile),
          onBodyRef: registerBodyRef,
          onNodeRef: registerNodeRef,
          onDelete: () => handleDelete(tile.id),
          onToggleExpand: () =>
            setExpandedNodeIds((prev) => ({
              ...prev,
              [tile.id]: !prev[tile.id],
            })),
          isExpanded: Boolean(expandedNodeIds[tile.id]),
          textHasOverflow:
            overflowIds.has(tile.id) || Boolean(expandedNodeIds[tile.id]),
          isFocused: focusedNodeId === tile.id,
          isNeighbor:
            Boolean(focusedNodeId) &&
            relatedNodeIds.has(tile.id) &&
            focusedNodeId !== tile.id,
          changeStatus: normalizeChangeStatus(tile.meta_information?.["change_status"]),
        },
        className: expandedNodeIds[tile.id] ? "node-expanded" : "",
        style: expandedNodeIds[tile.id] ? { zIndex: 5 } : undefined,
        type: "tile",
      };
    });
  }, [
    tiles,
    handleDelete,
    canvasHeight,
    focusedNodeId,
    relatedNodeIds,
    expandedNodeIds,
    registerBodyRef,
    registerNodeRef,
    overflowIds,
    layout,
    tileHeights,
  ]);

  const edges = useMemo(
    () => buildGraphEdges(tiles, focusedNodeId),
    [tiles, focusedNodeId]
  );

  const handleNodeDragStop = useCallback(
    async (_event: unknown, node: Node) => {
      const tile = tiles.find((item) => item.id === node.id);
      if (!tile) {
        return;
      }
      const nextColumn = Math.round(node.position.x / COLUMN_WIDTH);
      const nextRow = Math.round(node.position.y / ROW_HEIGHT);
      if (nextColumn === tile.column && nextRow === tile.row) {
        return;
      }
      const updatedTile: Tile = {
        ...tile,
        column: nextColumn,
        row: nextRow,
      };
      setTiles((prev) =>
        prev.map((item) => (item.id === node.id ? updatedTile : item))
      );
      try {
        await apiClient.upsertTile(updatedTile, state.appSessionId);
      } catch (err) {
        logClientError("GraphCanvas.saveTilePosition", err, {
          appSessionId: state.appSessionId,
          tileId: node.id,
          nextColumn,
          nextRow,
        });
        setError("Tile-Position konnte nicht gespeichert werden.");
      }
    },
    [tiles, state.appSessionId]
  );

  const handleNodeClick = useCallback(
    (_event: unknown, node: Node) => {
      setFocusedNodeId((prev) => (prev === node.id ? null : node.id));
    },
    []
  );

  const handlePaneClick = useCallback(() => {
    setFocusedNodeId(null);
  }, []);

  const handleViewportChange = useCallback(
    (nextViewport: { x: number; y: number; zoom: number }) => {
      setViewport(nextViewport);
    },
    []
  );

  const handleInit = useCallback((instance: ReactFlowInstance) => {
    setViewport(instance.getViewport());
  }, []);

  const disableFitView = tiles.length === 1 && tiles[0]?.id === "law_tile";
  const lawColumn = tiles.find((tile) => tile.id === "law_tile")?.column ?? 0;
  const maxColumn = tiles.length
    ? Math.max(...tiles.map((tile) => tile.column))
    : lawColumn;
  const minColForPrefix = (prefix: string) => {
    const cols = tiles
      .filter((tile) => tile.id.startsWith(prefix))
      .map((tile) => tile.column);
    return cols.length ? Math.min(...cols) : null;
  };
  const maxColForPrefix = (prefix: string) => {
    const cols = tiles
      .filter((tile) => tile.id.startsWith(prefix))
      .map((tile) => tile.column);
    return cols.length ? Math.max(...cols) : null;
  };
  const vorgabenCol = minColForPrefix("regulation_") ?? lawColumn + 1;
  const prozesseCol = minColForPrefix("process_") ?? vorgabenCol + 1;
  const fallgruppenCol = minColForPrefix("case_group_") ?? prozesseCol + 1;
  const schritteStartCol = minColForPrefix("step_") ?? fallgruppenCol + 1;
  const schritteEndCol = maxColForPrefix("step_") ?? schritteStartCol;
  const schritteWidth = Math.max(1, schritteEndCol - schritteStartCol + 1);
  const lanes = [
    { key: "law", label: COLUMN_LABELS[0], startCol: lawColumn, width: 1 },
    { key: "regulations", label: COLUMN_LABELS[1], startCol: vorgabenCol, width: 1 },
    { key: "processes", label: COLUMN_LABELS[2], startCol: prozesseCol, width: 1 },
    { key: "case_groups", label: COLUMN_LABELS[3], startCol: fallgruppenCol, width: 1 },
    {
      key: "steps",
      label: COLUMN_LABELS[4],
      startCol: schritteStartCol,
      width: schritteWidth,
    },
    { key: "effort", label: COLUMN_LABELS[5], startCol: schritteEndCol + 1, width: 1 },
    { key: "costs", label: COLUMN_LABELS[6], startCol: schritteEndCol + 2, width: 1 },
  ];
  const visibleLanes = lanes.filter((lane) => lane.startCol <= maxColumn);
  const laneTitle = (lane: { key: string; label: string; startCol: number; width: number }) => {
    if (lane.key === "law" || lane.key === "effort") {
      return lane.label;
    }
    const count = tiles.filter(
      (tile) =>
        tile.column >= lane.startCol &&
        tile.column < lane.startCol + lane.width
    ).length;
    return `${count} ${lane.label}`;
  };
  const lanesHeight = Math.max(
    LANE_HEIGHT,
    layout.maxBottom + TILE_GAP + LANE_TOP_OFFSET
  );
  const labelPadding = 8;
  const labelScreenTop =
    viewport.y + (-LANE_TOP_OFFSET + labelPadding) * viewport.zoom;
  const shouldStickLabels = labelScreenTop < 0;

  return (
    <section
      ref={containerRef}
      className="relative h-[calc(100vh-152px)] min-h-[640px] w-full overflow-hidden bg-gradient-to-br from-slate-50 to-slate-100"
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(14,165,164,0.12),transparent_55%),radial-gradient(circle_at_80%_20%,rgba(249,115,22,0.12),transparent_60%)]" />

      <div className="absolute inset-0">
        <ReactFlowProvider>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              edgeTypes={edgeTypes}
              nodesDraggable={false}
              onInit={handleInit}
              onNodeDragStop={handleNodeDragStop}
              onNodeClick={handleNodeClick}
              onPaneClick={handlePaneClick}
              onViewportChange={handleViewportChange}
              fitView={!disableFitView}
            >
              <div
                className="pointer-events-none absolute left-0"
                style={{
                  top: -LANE_TOP_OFFSET,
                  transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.zoom})`,
                  transformOrigin: "0 0",
                }}
              >
                <div
                  className="relative"
                  style={{
                    width: (maxColumn + 1) * COLUMN_WIDTH,
                    height: lanesHeight + LANE_TOP_OFFSET,
                  }}
                >
                  {visibleLanes.map((lane, index) => (
                    <div
                      key={lane.key}
                      className="absolute top-0 h-full"
                      style={{
                        left: lane.startCol * COLUMN_WIDTH,
                        width: lane.width * COLUMN_WIDTH,
                        background:
                          index % 2 === 0
                            ? "rgba(148, 163, 184, 0.08)"
                            : "rgba(148, 163, 184, 0.04)",
                        borderLeft:
                          index === 0
                            ? "none"
                            : "1px solid rgba(148, 163, 184, 0.2)",
                      }}
                    >
                      <div
                        className="px-4 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500"
                        style={{ paddingTop: labelPadding }}
                      >
                        {laneTitle(lane)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              {shouldStickLabels && (
                <div className="pointer-events-none absolute left-0 top-0 z-10">
                  {visibleLanes.map((lane) => {
                    const left =
                      lane.startCol * COLUMN_WIDTH * viewport.zoom + viewport.x;
                    const width = lane.width * COLUMN_WIDTH * viewport.zoom;
                    return (
                      <div
                        key={lane.key}
                        className="absolute"
                        style={{ left, width }}
                      >
                        <div
                          className="px-4 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500"
                          style={{ paddingTop: labelPadding }}
                        >
                          {laneTitle(lane)}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
              <Background gap={32} size={1.2} color="#e2e8f0" />
              <Controls />
          </ReactFlow>
        </ReactFlowProvider>
        {loading && (
          <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center text-sm text-slate-500">
            Daten werden geladen...
          </div>
        )}
        {error && !loading && (
          <div className="pointer-events-none absolute right-4 top-4 z-20 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
            {error}
          </div>
        )}

      </div>
    </section>
  );
}
