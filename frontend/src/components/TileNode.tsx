"use client";

import { useCallback } from "react";
import { Handle, type NodeProps, Position } from "@xyflow/react";
import { ChangeStatus, getChangeStatusLabel } from "@/lib/changeStatus";

export interface TileNodeData {
  title: string;
  text: string;
  deletable: boolean;
  headerMetricLeft?: string | null;
  headerMetricRight?: string | null;
  onBodyRef: (id: string, element: HTMLParagraphElement | null) => void;
  onNodeRef: (id: string, element: HTMLDivElement | null) => void;
  onDelete: () => void;
  onToggleExpand: () => void;
  isExpanded: boolean;
  textHasOverflow: boolean;
  isFocused: boolean;
  isNeighbor: boolean;
  changeStatus?: ChangeStatus | null;
}

export function TileNode({ data, id }: NodeProps<TileNodeData>) {
  const isLawTile = id === "law_tile";
  const isExpanded = isLawTile || data.isExpanded;
  const canExpand = !isLawTile && data.text && data.textHasOverflow;
  const { onNodeRef, onBodyRef } = data;
  const setNodeRef = useCallback(
    (element: HTMLDivElement | null) => {
      onNodeRef(id, element);
    },
    [onNodeRef, id]
  );
  const setBodyRef = useCallback(
    (element: HTMLParagraphElement | null) => {
      onBodyRef(id, element);
    },
    [onBodyRef, id]
  );
  const highlightClass = data.isFocused
    ? "is-focused"
    : data.isNeighbor
      ? "is-neighbor"
      : "";
  return (
    <div ref={setNodeRef} className={`tile-node ${highlightClass}`}>
      <Handle type="target" position={Position.Left} />
      <div className="tile-header">
        {(data.changeStatus || data.deletable || data.headerMetricLeft || data.headerMetricRight) && (
          <div className="tile-meta-row">
            {data.changeStatus ? (
              <span className={`tile-status tile-status-${data.changeStatus}`}>
                {getChangeStatusLabel(data.changeStatus)}
              </span>
            ) : (
              <span />
            )}
            {(data.deletable || data.headerMetricLeft || data.headerMetricRight) && (
              <div className="tile-actions">
                {data.headerMetricLeft && (
                  <span className="tile-metric tile-metric-left">{data.headerMetricLeft}</span>
                )}
                <button
                  onClick={(event) => {
                    event.stopPropagation();
                    data.onDelete();
                  }}
                  disabled={!data.deletable}
                >
                  ×
                </button>
                {data.headerMetricRight && (
                  <span className="tile-metric tile-metric-right">{data.headerMetricRight}</span>
                )}
              </div>
            )}
          </div>
        )}
        <div className="tile-title-wrap">
          <h4>{data.title}</h4>
        </div>
      </div>
      <div className="tile-body-row">
        <p
          ref={setBodyRef}
          className={`tile-body-text ${
            isExpanded || isLawTile ? "is-expanded" : ""
          }`}
        >
          {data.text || "Keine Beschreibung"}
        </p>
        {canExpand && (
          <button
            className="tile-expand-inline"
            onClick={(event) => {
              event.stopPropagation();
              data.onToggleExpand();
            }}
            aria-expanded={isExpanded}
            title={isExpanded ? "Text einklappen" : "Text ausklappen"}
          >
            {isExpanded ? "▴" : "▾"}
          </button>
        )}
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
