"use client";

import { useCallback } from "react";
import { Handle, type NodeProps, Position } from "@xyflow/react";
import { ChangeStatus, getChangeStatusLabel } from "@/lib/changeStatus";
import { TileMetricTable } from "@/components/tileMetrics";

export interface TileNodeData {
  title: string;
  text: string;
  headerMetricLeft?: string | null;
  headerMetricRight?: string | null;
  metricTable?: TileMetricTable | null;
  onBodyRef: (id: string, element: HTMLParagraphElement | null) => void;
  onNodeRef: (id: string, element: HTMLDivElement | null) => void;
  onToggleExpand: () => void;
  isExpanded: boolean;
  textHasOverflow: boolean;
  isFocused: boolean;
  isNeighbor: boolean;
  changeStatus?: ChangeStatus | null;
  // Dezentes "IP"-Pill fuer Business-Informationspflichten; wird ausschliesslich
  // in der Wirtschaft-Sicht bei gesetztem Flag angezeigt (Gating in GraphCanvas).
  showIpBadge?: boolean;
}

export function TileNode({ data, id }: NodeProps<TileNodeData>) {
  const isLawTile = id === "law_tile";
  const bodyText = data.text;
  const isExpanded = isLawTile || data.isExpanded;
  const metricTable = data.metricTable;
  const summaryMetric = metricTable?.variant === "summary" ? metricTable : null;
  const tableMetric = metricTable?.variant === "table" ? metricTable : null;
  const metricTableAlwaysVisible = Boolean(summaryMetric?.alwaysVisible);
  const suppressTitle = Boolean(summaryMetric?.suppressTitle);
  const showHeaderMeta = Boolean(
    data.changeStatus ||
      data.showIpBadge ||
      data.headerMetricLeft ||
      data.headerMetricRight
  );
  const showTitle = Boolean(data.title) && !suppressTitle;
  const canExpand =
    !isLawTile &&
    !metricTableAlwaysVisible &&
    (Boolean(data.metricTable) || (Boolean(bodyText) && data.textHasOverflow));
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
      {(showHeaderMeta || showTitle) && (
        <div className="tile-header">
          {showHeaderMeta && (
            <div className="tile-meta-row">
              <div className="tile-meta-left">
                {data.changeStatus && (
                  <span className={`tile-status tile-status-${data.changeStatus}`}>
                    {getChangeStatusLabel(data.changeStatus)}
                  </span>
                )}
                {data.showIpBadge && (
                  <span
                    className="tile-ip"
                    title="Informationspflicht Wirtschaft"
                    aria-label="Informationspflicht Wirtschaft"
                  >
                    IP
                  </span>
                )}
              </div>
              {(data.headerMetricLeft || data.headerMetricRight) && (
                <div className="tile-actions">
                  {data.headerMetricLeft && (
                    <span className="tile-metric tile-metric-left">
                      {data.headerMetricLeft}
                    </span>
                  )}
                  {data.headerMetricRight && (
                    <span className="tile-metric tile-metric-right">
                      {data.headerMetricRight}
                    </span>
                  )}
                </div>
              )}
            </div>
          )}
          {showTitle && (
            <div className="tile-title-wrap">
              <h4>{data.title}</h4>
            </div>
          )}
        </div>
      )}
      {(bodyText || canExpand) && (
        <div className="tile-body-row">
          {bodyText ? (
            <p
              ref={setBodyRef}
              className={`tile-body-text ${
                isExpanded || isLawTile ? "is-expanded" : ""
              }`}
            >
              {bodyText}
            </p>
          ) : (
            <span className="tile-body-placeholder" />
          )}
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
      )}
      {summaryMetric && (metricTableAlwaysVisible || isExpanded || isLawTile) && (
        <div
          className={`tile-summary-strip ${
            summaryMetric.titleLikeLabels ? "tile-summary-strip-title-like" : ""
          }`}
          aria-label="Erfüllungsaufwand Übersicht"
        >
          {summaryMetric.items.map((item) => (
            <div key={item.label} className="tile-summary-item">
              <span className="tile-summary-label">{item.label}</span>
              <span
                className={`tile-summary-value ${
                  item.emphasis ? "tile-summary-value-emphasis" : ""
                }`}
              >
                {item.value}
              </span>
            </div>
          ))}
        </div>
      )}
      {tableMetric && (isExpanded || isLawTile) && (
        <div className="tile-data-table-wrap">
          <table className="tile-data-table">
            <thead>
              <tr>
                <th scope="col" />
                <th scope="col">Aktuell</th>
                <th scope="col">Entwurf</th>
              </tr>
            </thead>
            <tbody>
              {tableMetric.rows.map((row) => (
                <tr
                  key={row.label}
                  className={row.emphasizeTop ? "tile-data-table-row-break" : undefined}
                >
                  <th scope="row">{row.label}</th>
                  <td>{row.current}</td>
                  <td>{row.proposed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
