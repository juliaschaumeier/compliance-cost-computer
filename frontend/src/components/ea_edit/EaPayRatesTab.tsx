"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { apiClient } from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";
import { NormAddressee, SessionWageRateRow } from "@/types";

import { useEaReviewSave } from "./useEaReviewSave";
import {
  formatNumber,
  isValidNullableNumberInput,
  parseNullableNumber,
} from "./utils";

type EaPayRatesTabProps = {
  open: boolean;
  active: boolean;
  appSessionId: string;
  normAddressee: NormAddressee;
  eaActivityId?: string | null;
  readOnly?: boolean;
  runAutoRecompute: () => Promise<void>;
  onDirtyChange?: (dirty: boolean) => void;
};

const NORM_ADDRESSEE_LABELS: Record<NormAddressee, string> = {
  administration: "Verwaltung",
  business: "Wirtschaft",
  citizens: "Bürgerinnen und Bürger",
};

// Short labels for the economic-section source (Lohnkostentabelle Wirtschaft,
// WZ sections A-S + gesamtwirtschaft).
const WZ_SECTION_LABELS: Record<string, string> = {
  A: "Land- und Forstwirtschaft, Fischerei",
  B: "Bergbau",
  C: "Verarbeitendes Gewerbe",
  D: "Energieversorgung",
  E: "Wasser-/Abfallwirtschaft",
  F: "Baugewerbe",
  G: "Handel; Kfz-Reparatur",
  H: "Verkehr und Lagerei",
  I: "Gastgewerbe",
  J: "Information und Kommunikation",
  K: "Finanz- und Versicherungsdienstleistungen",
  L: "Grundstücks- und Wohnungswesen",
  M: "Freiberufliche/wiss./techn. Dienstleistungen",
  N: "Sonstige wirtschaftliche Dienstleistungen",
  P: "Erziehung und Unterricht",
  Q: "Gesundheits- und Sozialwesen",
  R: "Kunst, Unterhaltung und Erholung",
  S: "Sonstige Dienstleistungen",
  gesamtwirtschaft: "Gesamtwirtschaft (A-S ohne O)",
};

const VERWALTUNGSEBENE_LABELS: Record<string, string> = {
  bund: "Bund",
  laender: "Länder",
  kommunen: "Kommunen",
  sozialversicherung: "Sozialversicherung",
  durchschnitt: "Durchschnitt über Verwaltungsebenen",
};

const QUALIFICATION_LABELS: Record<string, string> = {
  einfacher_und_mittlerer_dienst: "Einfacher/Mittlerer Dienst (eD/mD)",
  gehobener_dienst: "Gehobener Dienst (gD)",
  hoeherer_dienst: "Höherer Dienst (hD)",
  niedrig: "Niedrig",
  mittel: "Mittel",
  hoch: "Hoch",
  durchschnitt: "Durchschnitt (Ø)",
};

function sourceLabel(kind: string, value: string): string {
  if (kind === "wirtschaftsabschnitt") {
    const detail = WZ_SECTION_LABELS[value];
    if (!detail) {
      return value;
    }
    return value === "gesamtwirtschaft" ? detail : `${value} · ${detail}`;
  }
  return VERWALTUNGSEBENE_LABELS[value] ?? value;
}

function qualificationLabel(qualification: string): string {
  return QUALIFICATION_LABELS[qualification] ?? qualification;
}

function rowKey(row: {
  wage_source_kind: string;
  wage_source_value: string;
  qualification: string;
}): string {
  return `${row.wage_source_kind}|${row.wage_source_value}|${row.qualification}`;
}

export default function EaPayRatesTab({
  open,
  active,
  appSessionId,
  normAddressee,
  eaActivityId = null,
  readOnly = false,
  runAutoRecompute,
  onDirtyChange,
}: EaPayRatesTabProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [rows, setRows] = useState<SessionWageRateRow[]>([]);
  const [editedInputs, setEditedInputs] = useState<Record<string, string>>({});
  const [loadedKey, setLoadedKey] = useState<string | null>(null);
  const { isSaving, status, setStatus, runSave } = useEaReviewSave({
    logLabel: "EaPayRatesTab.save",
    logContext: { appSessionId },
  });

  const loadKey = `${appSessionId}::${normAddressee}`;

  const hasInvalidInput = Object.values(editedInputs).some(
    (value) => !isValidNullableNumberInput(value)
  );

  // A row is dirty when its "Neu" input is non-empty and differs from the stored
  // override. An empty input keeps the current override (cleared via reset).
  const dirtyRows = useMemo(() => {
    if (hasInvalidInput) {
      return [];
    }
    return rows.filter((row) => {
      const input = editedInputs[rowKey(row)] ?? "";
      if (input.trim() === "") {
        return false;
      }
      return parseNullableNumber(input) !== row.hourly_rate_edited;
    });
  }, [rows, editedInputs, hasInvalidInput]);

  const hasActiveEdited = useMemo(
    () => rows.some((row) => row.hourly_rate_edited !== null),
    [rows]
  );

  useEffect(() => {
    onDirtyChange?.(!readOnly && dirtyRows.length > 0);
  }, [dirtyRows, onDirtyChange, readOnly]);

  useEffect(() => {
    if (!readOnly) {
      return;
    }
    setEditedInputs({});
  }, [readOnly]);

  const loadRows = useCallback(async () => {
    setIsLoading(true);
    setStatus(null);
    try {
      const payload = await apiClient.getSessionWageRates({ appSessionId, normAddressee });
      setRows(payload.rows);
      setEditedInputs({});
      setLoadedKey(loadKey);
    } catch (error) {
      logClientError("EaPayRatesTab.load", error, { appSessionId, normAddressee });
      setStatus("Lohnsätze konnten nicht geladen werden.");
    } finally {
      setIsLoading(false);
    }
  }, [appSessionId, normAddressee, loadKey, setStatus]);

  useEffect(() => {
    setRows([]);
    setEditedInputs({});
    setLoadedKey(null);
    setStatus(null);
  }, [appSessionId, normAddressee, setStatus]);

  useEffect(() => {
    if (!open || !active) {
      return;
    }
    if (normAddressee === "citizens") {
      return;
    }
    if (loadedKey === loadKey) {
      return;
    }
    loadRows();
  }, [open, active, normAddressee, loadRows, loadedKey, loadKey]);

  const handleSave = async () => {
    if (readOnly || dirtyRows.length === 0 || hasInvalidInput) {
      return;
    }
    try {
      await runSave(
        async () => {
          for (const row of dirtyRows) {
            await apiClient.updateSessionWageRate({
              appSessionId,
              normAddressee,
              eaActivityId: eaActivityId ?? undefined,
              wageSourceKind: row.wage_source_kind,
              wageSourceValue: row.wage_source_value,
              qualification: row.qualification,
              hourlyRateEdited: parseNullableNumber(editedInputs[rowKey(row)] ?? ""),
            });
          }
          await runAutoRecompute();
          await loadRows();
        },
        {
          successMessage:
            "Lohnsätze gespeichert. Gesamtkosten wurden automatisch neu berechnet.",
          errorMessage: "Speichern fehlgeschlagen. Bitte Eingaben prüfen und erneut versuchen.",
        }
      );
    } catch {
      // Status handling is centralized in useEaReviewSave.
    }
  };

  const handleResetEdited = async () => {
    if (readOnly || !hasActiveEdited) {
      return;
    }
    try {
      await runSave(
        async () => {
          for (const row of rows.filter((r) => r.hourly_rate_edited !== null)) {
            await apiClient.updateSessionWageRate({
              appSessionId,
              normAddressee,
              eaActivityId: eaActivityId ?? undefined,
              wageSourceKind: row.wage_source_kind,
              wageSourceValue: row.wage_source_value,
              qualification: row.qualification,
              hourlyRateEdited: null,
            });
          }
          await runAutoRecompute();
          await loadRows();
        },
        {
          successMessage:
            "Bearbeitete Lohnsätze zurückgesetzt. Gesamtkosten wurden automatisch neu berechnet.",
          errorMessage: "Zurücksetzen fehlgeschlagen. Bitte erneut versuchen.",
        }
      );
    } catch {
      // Status handling is centralized in useEaReviewSave.
    }
  };

  if (!active) {
    return null;
  }

  if (normAddressee === "citizens") {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-700">
        <p className="font-semibold text-slate-800">
          Lohnsätze sind für Bürgerinnen und Bürger nicht anwendbar.
        </p>
        <p className="mt-2">
          Für diesen Normadressaten werden nur Zeitaufwand (in Minuten) und
          Sachaufwand (in Euro) berücksichtigt. Eine Monetarisierung der Zeit
          erfolgt nicht.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
        Lohnsätze werden geladen...
      </div>
    );
  }

  const groups: Array<{ kind: string; value: string; rows: SessionWageRateRow[] }> = [];
  const groupIndex = new Map<string, number>();
  for (const row of rows) {
    const gk = `${row.wage_source_kind}|${row.wage_source_value}`;
    let idx = groupIndex.get(gk);
    if (idx === undefined) {
      idx = groups.length;
      groupIndex.set(gk, idx);
      groups.push({ kind: row.wage_source_kind, value: row.wage_source_value, rows: [] });
    }
    groups[idx].rows.push(row);
  }

  const inputClass = (value: string) =>
    `w-24 rounded px-2 py-1 ${
      isValidNullableNumberInput(value)
        ? "border border-slate-300"
        : "border border-red-400 bg-red-50"
    }`;

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
        Normadressat:{" "}
        <span className="font-semibold">{NORM_ADDRESSEE_LABELS[normAddressee]}</span>
      </div>
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-[11px] text-slate-500">
        Je genutzter Lohnquelle eine Tabelle mit allen Qualifikationen. „Lohn­kosten­tabelle“
        zeigt den Modell-Standardsatz; überschreiben Sie ihn pro Quelle und Qualifikation
        unter „Neu“. Zahlenformat: z. B. 1.234,56 (de-DE).
      </div>
      {groups.length === 0 && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
          Noch keine genutzten Lohnquellen in dieser Session.
        </div>
      )}
      {groups.map((group) => (
        <div
          key={`${group.kind}|${group.value}`}
          className="overflow-hidden rounded-lg border border-slate-200"
        >
          <div className="bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700">
            {sourceLabel(group.kind, group.value)}
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-600">
                  <th className="px-2 py-2">Qualifikation</th>
                  <th className="px-2 py-2">Lohnkostentabelle</th>
                  <th className="px-2 py-2">Aktiv</th>
                  <th className="px-2 py-2">Neu</th>
                </tr>
              </thead>
              <tbody>
                {group.rows.map((row) => {
                  const key = rowKey(row);
                  const activeRate = row.hourly_rate_edited ?? row.model_hourly_rate;
                  return (
                    <tr key={key} className="border-b border-slate-100">
                      <td className="px-2 py-2 font-semibold text-slate-800">
                        {qualificationLabel(row.qualification)}
                      </td>
                      <td className="px-2 py-2">{formatNumber(row.model_hourly_rate)} €</td>
                      <td className="px-2 py-2 font-semibold text-slate-900">
                        {formatNumber(activeRate)} €
                      </td>
                      <td className="px-2 py-2">
                        <input
                          value={editedInputs[key] ?? ""}
                          placeholder={
                            row.hourly_rate_edited !== null
                              ? formatNumber(row.hourly_rate_edited)
                              : ""
                          }
                          onChange={(event) => {
                            if (readOnly) {
                              return;
                            }
                            setStatus(null);
                            setEditedInputs((prev) => ({
                              ...prev,
                              [key]: event.target.value,
                            }));
                          }}
                          disabled={readOnly}
                          className={inputClass(editedInputs[key] ?? "")}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ))}
      <div className="flex justify-end gap-2">
        <button
          onClick={handleResetEdited}
          disabled={isSaving || readOnly || !eaActivityId || !hasActiveEdited}
          className="rounded-full border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Auf Modellwerte zurücksetzen
        </button>
        <button
          onClick={handleSave}
          disabled={isSaving || readOnly || !eaActivityId || hasInvalidInput || dirtyRows.length === 0}
          className="rounded-full bg-slate-900 px-4 py-2 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {isSaving ? "Speichert..." : "Lohnsätze speichern"}
        </button>
      </div>
      {hasInvalidInput && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-800">
          Bitte ungültige Zahlenformate korrigieren.
        </div>
      )}
      {status && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
          {status}
        </div>
      )}
    </div>
  );
}
