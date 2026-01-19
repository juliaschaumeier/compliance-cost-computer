"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  Node,
  NodeProps,
  ReactFlowProvider,
} from "reactflow";

import { apiClient } from "@/lib/api";
import { Tile } from "@/types";

const COLUMN_WIDTH = 320;
const ROW_HEIGHT = 220;

function TileNode({ data }: NodeProps<TileNodeData>) {
  return (
    <div className="tile-node">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4>{data.title}</h4>
          <p>{data.text || "Keine Beschreibung"}</p>
        </div>
        {data.deletable && (
          <div className="tile-actions">
            <button onClick={data.onDelete}>×</button>
          </div>
        )}
      </div>
    </div>
  );
}

interface TileNodeData {
  title: string;
  text: string;
  deletable: boolean;
  onDelete: () => void;
}

export default function GraphCanvas() {
  const [tiles, setTiles] = useState<Tile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newTileTitle, setNewTileTitle] = useState("");
  const [newTileText, setNewTileText] = useState("");

  const refreshTiles = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.fetchTiles();
      setTiles(response.tiles);
      setError(null);
    } catch (err) {
      setError("Tiles konnten nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshTiles();
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

  const nodes: Node[] = useMemo(() => {
    return tiles.map((tile) => ({
      id: tile.id,
      position: {
        x: tile.column * COLUMN_WIDTH,
        y: tile.row * ROW_HEIGHT,
      },
      data: {
        title: tile.title,
        text: tile.text,
        deletable: tile.deletable,
        onDelete: () => handleDelete(tile.id),
      },
      type: "tile",
    }));
  }, [tiles, handleDelete]);

  const edges = useMemo(() => {
    return tiles.flatMap((tile) =>
      tile.link_from_tile.map((sourceId) => ({
        id: `e-${sourceId}-${tile.id}`,
        source: sourceId,
        target: tile.id,
        markerEnd: { type: MarkerType.ArrowClosed },
        style: { stroke: "#0f172a", strokeWidth: 2 },
      }))
    );
  }, [tiles]);

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

  const handleSeed = useCallback(async () => {
    try {
      await apiClient.seedTiles();
      await refreshTiles();
    } catch (err) {
      setError("Seed konnte nicht geladen werden.");
    }
  }, [refreshTiles]);

  const handleAddTile = useCallback(async () => {
    if (!newTileTitle.trim()) {
      return;
    }
    const newTile: Tile = {
      id: crypto.randomUUID(),
      title: newTileTitle.trim(),
      text: newTileText.trim(),
      meta_information: {},
      column: 0,
      row: tiles.length,
      deletable: true,
      link_from_tile: [],
    };
    try {
      await apiClient.upsertTile(newTile);
      setTiles((prev) => [...prev, newTile]);
      setNewTileTitle("");
      setNewTileText("");
    } catch (err) {
      setError("Tile konnte nicht gespeichert werden.");
    }
  }, [newTileTitle, newTileText, tiles.length]);

  return (
    <section className="relative overflow-hidden rounded-[28px] border border-white/60 bg-white/70 p-4 shadow-2xl backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">
            Prozessgrafik
          </h2>
          <p className="text-sm text-slate-600">
            Der Graph bleibt bestehen, während die Tabs den Fortschritt steuern.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={refreshTiles}
            className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold"
          >
            Aktualisieren
          </button>
          <button
            onClick={handleSeed}
            className="rounded-full border border-slate-200 bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
          >
            Seed laden
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="relative h-[640px] overflow-hidden rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-50 to-slate-100">
        {loading ? (
          <div className="flex h-full items-center justify-center text-sm text-slate-500">
            Daten werden geladen...
          </div>
        ) : (
          <ReactFlowProvider>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={{ tile: TileNode }}
              onNodeDragStop={handleNodeDragStop}
              fitView
            >
              <Background gap={32} size={1.2} color="#e2e8f0" />
              <Controls />
            </ReactFlow>
          </ReactFlowProvider>
        )}

        <div className="absolute bottom-4 right-4 w-64 rounded-2xl border border-slate-200 bg-white/95 p-4 shadow-xl">
          <h3 className="text-sm font-semibold text-slate-800">Neues Tile</h3>
          <input
            value={newTileTitle}
            onChange={(event) => setNewTileTitle(event.target.value)}
            placeholder="Titel"
            className="mt-3 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
          />
          <textarea
            value={newTileText}
            onChange={(event) => setNewTileText(event.target.value)}
            placeholder="Kurzbeschreibung"
            rows={2}
            className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
          />
          <button
            onClick={handleAddTile}
            className="mt-3 w-full rounded-xl bg-teal-600 px-3 py-2 text-sm font-semibold text-white"
          >
            Tile hinzufügen
          </button>
        </div>
      </div>
    </section>
  );
}
