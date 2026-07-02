"use client";

import { formatNumber } from "@/components/ea_edit/utils";

export type ReviewDiffRow = {
  entityId: number | string;
  entityLabel: string;
  groupId?: number | string | null;
  groupLabel?: string | null;
  fieldKey: string;
  fieldLabel: string;
  modelValue: number | null;
  activeValue: number | null;
  newValue: number | null;
};

type ReviewDiffTableProps = {
  entityHeader: string;
  rows: ReviewDiffRow[];
  emptyMessage?: string;
  containerClassName?: string;
};

export default function ReviewDiffTable({
  entityHeader,
  rows,
  emptyMessage = "Keine Änderungen gefunden.",
  containerClassName = "max-h-[52vh] overflow-auto rounded-lg border border-slate-200",
}: ReviewDiffTableProps) {
  const groupedCount = new Map<string, number>();
  for (const row of rows) {
    const group = row.groupLabel?.trim() || null;
    if (!group) {
      continue;
    }
    const groupKey = row.groupId !== undefined && row.groupId !== null
      ? `id:${row.groupId}`
      : `label:${group}`;
    groupedCount.set(groupKey, (groupedCount.get(groupKey) || 0) + 1);
  }

  let lastGroupKey: string | null = null;
  return (
    <div className={containerClassName}>
      <table className="min-w-full border-collapse text-xs">
        <thead className="sticky top-0 bg-white">
          <tr className="border-b border-slate-200 text-left text-slate-600">
            <th className="px-2 py-2">{entityHeader}</th>
            <th className="px-2 py-2">Geändertes Feld</th>
            <th className="px-2 py-2">Modell</th>
            <th className="px-2 py-2">Aktiv</th>
            <th className="px-2 py-2">Neu</th>
          </tr>
        </thead>
        <tbody>
          {rows.flatMap((row, index) => {
            const currentGroup = row.groupLabel?.trim() || null;
            const currentGroupKey =
              currentGroup && row.groupId !== undefined && row.groupId !== null
                ? `id:${row.groupId}`
                : currentGroup
                  ? `label:${currentGroup}`
                  : null;
            const groupHeaderNeeded =
              currentGroupKey !== null && currentGroupKey !== lastGroupKey;
            lastGroupKey = currentGroupKey;
            const renderedRows: JSX.Element[] = [];
            if (groupHeaderNeeded && currentGroup !== null) {
              renderedRows.push(
                <tr
                  key={`group-${currentGroupKey}-${index}`}
                  className="border-b border-slate-200 bg-slate-100"
                >
                  <td
                    className="px-2 py-2 text-[11px] font-semibold text-slate-700"
                    colSpan={5}
                  >
                    {currentGroup} · {groupedCount.get(currentGroupKey || "") || 0} Änderungen
                  </td>
                </tr>
              );
            }
            renderedRows.push(
              <tr
                key={`${row.entityId}-${row.fieldKey}`}
                className="ea-review-cell border-b border-slate-100 bg-amber-50"
              >
                <td className="px-2 py-2 align-top font-semibold text-slate-800">
                  {row.entityLabel}
                </td>
                <td className="px-2 py-2 align-top text-slate-800">{row.fieldLabel}</td>
                <td className="px-2 py-2 align-top text-slate-700">
                  {formatNumber(row.modelValue)}
                </td>
                <td className="px-2 py-2 align-top text-slate-700">
                  {formatNumber(row.activeValue)}
                </td>
                <td className="px-2 py-2 align-top font-semibold text-slate-900">
                  {formatNumber(row.newValue)}
                </td>
              </tr>
            );
            return renderedRows;
          })}
          {rows.length === 0 && (
            <tr className="border-b border-slate-100">
              <td className="px-2 py-3 text-slate-500" colSpan={5}>
                {emptyMessage}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
