"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  Controls,
  type Node,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";

import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";
import { normalizeAndAlignTiles } from "@/lib/graphLayout";
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
  useEffect(() => {
    if (nodeTypesRef.current?.tile !== TileNode) {
      console.warn("[GraphCanvas] nodeTypes tile changed", {
        prev: nodeTypesRef.current?.tile,
        next: TileNode,
      });
    }
  }, [nodeTypes]);
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
    return () => {
      nodeObservers.current.forEach((observer) => observer.disconnect());
      nodeObservers.current.clear();
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
      setError(null);
      return;
    }
    try {
      setLoading(true);
      const response = await apiClient.fetchTiles();
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
            Array.from(deduped.values()).map((tile) => apiClient.upsertTile(tile))
          );
        }
      } else {
        const normalized = normalizeAndAlignTiles(response.tiles);
        setTiles(normalized.updated);
        const changed = [...normalized.changed];
        if (changed.length) {
          const deduped = new Map(changed.map((tile) => [tile.id, tile]));
          await Promise.all(
            Array.from(deduped.values()).map((tile) => apiClient.upsertTile(tile))
          );
        }
      }
      setError(null);
    } catch (err) {
      setError("Tiles konnten nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  }, [state.summaryReady]);

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
        await apiClient.deleteTile(tileId);
        setTiles((prev) => prev.filter((tile) => tile.id !== tileId));
      } catch (err) {
        setError("Tile konnte nicht gelöscht werden.");
      }
    },
    []
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
    const rowHeights = new Map<number, number>();
    tiles.forEach((tile) => {
      const height = tileHeights[tile.id] ?? TILE_HEIGHT;
      const current = rowHeights.get(tile.row) ?? 0;
      if (height > current) {
        rowHeights.set(tile.row, height);
      }
    });
    const sortedRows = Array.from(rowHeights.keys()).sort((a, b) => a - b);
    const rowOffsets = new Map<number, number>();
    let y = 0;
    let maxBottom = 0;
    sortedRows.forEach((row) => {
      rowOffsets.set(row, y);
      const height = rowHeights.get(row) ?? TILE_HEIGHT;
      maxBottom = Math.max(maxBottom, y + height);
      y += height + TILE_GAP;
    });
    tiles.forEach((tile) => {
      const height = tileHeights[tile.id] ?? TILE_HEIGHT;
      const yPos = rowOffsets.get(tile.row);
      positions.set(tile.id, {
        x: tile.column * COLUMN_WIDTH,
        y: yPos ?? tile.row * ROW_HEIGHT,
        height,
      });
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
          text: tile.text,
          deletable: tile.deletable,
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

  const edges = useMemo(() => {
    const highlightEnabled = Boolean(focusedNodeId);
    return tiles.flatMap((tile) =>
      tile.link_from_tile.map((sourceId) => {
        const isActive =
          !highlightEnabled ||
          sourceId === focusedNodeId ||
          tile.id === focusedNodeId;
        const strokeColor = highlightEnabled
          ? isActive
            ? "#0f766e"
            : "#94a3b8"
          : "#0f172a";
        return {
          id: `e-${sourceId}-${tile.id}`,
          source: sourceId,
          target: tile.id,
          style: {
            stroke: strokeColor,
            strokeWidth: highlightEnabled ? (isActive ? 2.5 : 1) : 2,
            opacity: highlightEnabled ? (isActive ? 1 : 0.25) : 1,
            strokeLinecap: "round",
            strokeLinejoin: "round",
          },
        };
      })
    );
  }, [tiles, focusedNodeId]);

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
        await apiClient.upsertTile(updatedTile);
      } catch (err) {
        setError("Tile-Position konnte nicht gespeichert werden.");
      }
    },
    [tiles]
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

  const handleMove = useCallback(
    (_event: unknown, nextViewport: { x: number; y: number; zoom: number }) => {
      setViewport(nextViewport);
    },
    []
  );

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
    { label: COLUMN_LABELS[0], startCol: lawColumn, width: 1 },
    { label: COLUMN_LABELS[1], startCol: vorgabenCol, width: 1 },
    { label: COLUMN_LABELS[2], startCol: prozesseCol, width: 1 },
    { label: COLUMN_LABELS[3], startCol: fallgruppenCol, width: 1 },
    {
      label: COLUMN_LABELS[4],
      startCol: schritteStartCol,
      width: schritteWidth,
    },
    { label: COLUMN_LABELS[5], startCol: schritteEndCol + 1, width: 1 },
    { label: COLUMN_LABELS[6], startCol: schritteEndCol + 2, width: 1 },
  ];
  const visibleLanes = lanes.filter((lane) => lane.startCol <= maxColumn);
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
        {loading ? (
          <div className="flex h-full items-center justify-center text-sm text-slate-500">
            Daten werden geladen...
          </div>
        ) : (
          <ReactFlowProvider>
              <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                edgeTypes={edgeTypes}
                nodesDraggable={false}
                onNodeDragStop={handleNodeDragStop}
                onNodeClick={handleNodeClick}
                onPaneClick={handlePaneClick}
                onMove={handleMove}
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
                      key={lane.label}
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
                        {lane.label}
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
                        key={lane.label}
                        className="absolute"
                        style={{ left, width }}
                      >
                        <div
                          className="px-4 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500"
                          style={{ paddingTop: labelPadding }}
                        >
                          {lane.label}
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
        )}

      </div>
    </section>
  );
}
