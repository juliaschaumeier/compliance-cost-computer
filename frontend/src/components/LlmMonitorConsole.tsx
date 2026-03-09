"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";
import {
  LlmMonitorEvent,
  LlmMonitorPendingCall,
  LlmMonitorRecentCall,
  LlmMonitorSnapshotResponse,
  LlmMonitorStreamAttempt,
} from "@/types";

type LlmMonitorConsoleProps = {
  open: boolean;
  onClose: () => void;
};

type MonitorTab = "overview" | "stream";

type LlmEventEnvelope = {
  event?: LlmMonitorEvent;
  pending?: LlmMonitorPendingCall[];
  stream_attempt?: LlmMonitorStreamAttempt | null;
};

const MAX_EVENT_ROWS = 180;
const MAX_RECENT_ROWS = 140;
const MAX_STREAM_ATTEMPTS = 160;

function formatClockFromMs(value?: number | null): string {
  if (!value || !Number.isFinite(value)) {
    return "-";
  }
  return new Date(value).toLocaleTimeString("de-DE", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatClockFromIso(value?: string | null): string {
  if (!value) {
    return "-";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleTimeString("de-DE", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatDurationMs(value?: number | null): string {
  if (!value || !Number.isFinite(value)) {
    return "-";
  }
  if (value < 1000) {
    return `${Math.round(value)} ms`;
  }
  return `${(value / 1000).toFixed(1)} s`;
}

function recentRowKey(row: LlmMonitorRecentCall): string {
  if (typeof row.answer_id === "number" && row.answer_id > 0) {
    return `answer:${row.answer_id}`;
  }
  return [
    "synthetic",
    row.attempt_id || "-",
    row.prompt_id || "-",
    row.answer_state || "-",
    row.state_reason || "-",
    row.created_at || "-",
  ].join(":");
}

function attemptKey(attempt: LlmMonitorStreamAttempt): string {
  return String(attempt.attempt_id || "");
}

function eventToRecentRow(event: LlmMonitorEvent): LlmMonitorRecentCall | null {
  const eventType = String(event.event_type || "");
  if (
    ![
      "llm_query_succeeded",
      "llm_query_failed",
      "llm_apply_succeeded",
      "llm_apply_failed",
    ].includes(eventType)
  ) {
    return null;
  }
  let answerState = "pending";
  let stateReason: string | null = "waiting_for_session_update";
  if (eventType === "llm_query_failed") {
    answerState = "invalid";
    stateReason = event.error_kind || event.error || "query_failed";
  } else if (eventType === "llm_apply_succeeded") {
    answerState = "active";
    stateReason = event.state_reason || "session_updated";
  } else if (eventType === "llm_apply_failed") {
    answerState = "invalid";
    stateReason = event.state_reason || event.error || "session_update_failed";
  }
  return {
    answer_id: event.answer_id ?? null,
    prompt_id: String(event.prompt_id || ""),
    model: String(event.model || ""),
    provider: event.provider || null,
    attempt_id: event.attempt_id || null,
    request_id: event.request_id || null,
    route_method: event.route_method || null,
    route_path: event.route_path || null,
    elapsed_ms: event.elapsed_ms ?? null,
    answer_state: answerState,
    state_reason: stateReason,
    input_tokens: event.input_tokens ?? null,
    output_tokens: event.output_tokens ?? null,
    hidden_thinking_tokens: event.hidden_thinking_tokens ?? null,
    estimated_cost_usd: event.estimated_cost_usd ?? null,
    error_kind: event.error_kind || null,
    error_status_code: event.error_status_code ?? null,
    error: event.error || null,
    created_at: event.timestamp_ms ? new Date(event.timestamp_ms).toISOString() : null,
  };
}

function mergeRecentRows(
  previous: LlmMonitorRecentCall[],
  incoming: LlmMonitorRecentCall[]
): LlmMonitorRecentCall[] {
  const merged = [...incoming, ...previous];
  const seen = new Set<string>();
  const deduped: LlmMonitorRecentCall[] = [];
  for (const row of merged) {
    const key = recentRowKey(row);
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    deduped.push(row);
    if (deduped.length >= MAX_RECENT_ROWS) {
      break;
    }
  }
  return deduped;
}

function mergeStreamAttemptRows(
  previous: LlmMonitorStreamAttempt[],
  incoming: LlmMonitorStreamAttempt[]
): LlmMonitorStreamAttempt[] {
  const merged = [...incoming, ...previous];
  const byId = new Map<string, LlmMonitorStreamAttempt>();
  for (const row of merged) {
    const key = attemptKey(row);
    if (!key) {
      continue;
    }
    if (!byId.has(key)) {
      byId.set(key, row);
      continue;
    }
    byId.set(key, { ...byId.get(key), ...row });
  }
  return Array.from(byId.values())
    .sort((a, b) => (Number(b.updated_at_ms || 0) - Number(a.updated_at_ms || 0)))
    .slice(0, MAX_STREAM_ATTEMPTS);
}

function resolvePendingElapsedMs(call: LlmMonitorPendingCall, nowMs: number): number | null {
  if (typeof call.elapsed_ms === "number" && Number.isFinite(call.elapsed_ms)) {
    return call.elapsed_ms;
  }
  if (
    typeof call.started_at_ms === "number" &&
    Number.isFinite(call.started_at_ms) &&
    nowMs >= call.started_at_ms
  ) {
    return nowMs - call.started_at_ms;
  }
  return null;
}

function selectedAttemptTranscript(attempt: LlmMonitorStreamAttempt | null): string {
  if (!attempt) {
    return "";
  }
  if (typeof attempt.text === "string" && attempt.text.length > 0) {
    return attempt.text;
  }
  const chunks = Array.isArray(attempt.chunks) ? attempt.chunks : [];
  return chunks.map((chunk) => chunk?.delta_text || "").join("");
}

export default function LlmMonitorConsole({ open, onClose }: LlmMonitorConsoleProps) {
  const { state } = useApp();
  const sourceRef = useRef<EventSource | null>(null);
  const selectedAttemptIdRef = useRef<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [tab, setTab] = useState<MonitorTab>("overview");
  const [pending, setPending] = useState<LlmMonitorPendingCall[]>([]);
  const [recent, setRecent] = useState<LlmMonitorRecentCall[]>([]);
  const [events, setEvents] = useState<LlmMonitorEvent[]>([]);
  const [streamAttempts, setStreamAttempts] = useState<LlmMonitorStreamAttempt[]>([]);
  const [selectedAttemptId, setSelectedAttemptId] = useState<string | null>(null);
  const [selectedAttempt, setSelectedAttempt] = useState<LlmMonitorStreamAttempt | null>(
    null
  );
  const [showRawChunks, setShowRawChunks] = useState(false);
  const [nowMs, setNowMs] = useState<number>(() => Date.now());

  useEffect(() => {
    selectedAttemptIdRef.current = selectedAttemptId;
  }, [selectedAttemptId]);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (!open) {
      return;
    }
    const timer = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [open]);

  useEffect(() => {
    if (!open) {
      if (sourceRef.current) {
        sourceRef.current.close();
        sourceRef.current = null;
      }
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setStreamError(null);

    const applySnapshot = (snapshot: LlmMonitorSnapshotResponse) => {
      setPending(snapshot.pending || []);
      setRecent((snapshot.recent || []).slice(0, MAX_RECENT_ROWS));
      setEvents((snapshot.events || []).slice(0, MAX_EVENT_ROWS));
      const streamRows = (snapshot.stream_attempts || []).slice(0, MAX_STREAM_ATTEMPTS);
      setStreamAttempts(streamRows);
      if (!selectedAttemptIdRef.current && streamRows.length > 0) {
        setSelectedAttemptId(String(streamRows[0].attempt_id || ""));
        setSelectedAttempt(streamRows[0]);
      }
    };

    const loadSnapshot = async () => {
      try {
        const snapshot = await apiClient.getLlmMonitorSnapshot({
          appSessionId: state.appSessionId,
          limit: MAX_RECENT_ROWS,
        });
        if (!cancelled) {
          applySnapshot(snapshot);
        }
      } catch (error) {
        logClientError("LlmMonitorConsole.loadSnapshot", error, {
          appSessionId: state.appSessionId,
        });
        if (!cancelled) {
          setStreamError("Snapshot konnte nicht geladen werden.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    loadSnapshot();

    const source = new EventSource(
      apiClient.getLlmMonitorEventsUrl({
        appSessionId: state.appSessionId,
        limit: MAX_RECENT_ROWS,
      })
    );
    sourceRef.current = source;

    source.addEventListener("snapshot", (event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data) as LlmMonitorSnapshotResponse;
        applySnapshot(payload);
        setStreamError(null);
      } catch (error) {
        logClientError("LlmMonitorConsole.snapshotEvent", error, {
          appSessionId: state.appSessionId,
        });
      }
    });

    source.addEventListener("llm_event", (event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data) as LlmEventEnvelope;
        if (Array.isArray(payload.pending)) {
          setPending(payload.pending);
        }
        if (payload.event) {
          setEvents((prev) => [payload.event!, ...prev].slice(0, MAX_EVENT_ROWS));
          const syntheticRecent = eventToRecentRow(payload.event);
          if (syntheticRecent) {
            setRecent((prev) => mergeRecentRows(prev, [syntheticRecent]));
          }
        }
        if (payload.stream_attempt) {
          setStreamAttempts((prev) => mergeStreamAttemptRows(prev, [payload.stream_attempt!]));
          const key = String(payload.stream_attempt.attempt_id || "");
          if (selectedAttemptIdRef.current && key === selectedAttemptIdRef.current) {
            setSelectedAttempt((prev) => ({ ...(prev || {}), ...payload.stream_attempt }));
          }
          if (!selectedAttemptIdRef.current && key) {
            setSelectedAttemptId(key);
            setSelectedAttempt(payload.stream_attempt);
          }
        }
        setStreamError(null);
      } catch (error) {
        logClientError("LlmMonitorConsole.llmEvent", error, {
          appSessionId: state.appSessionId,
        });
      }
    });

    source.onerror = () => {
      if (!cancelled) {
        setStreamError("Event-Stream unterbrochen. Versuche Wiederverbindung...");
      }
    };

    return () => {
      cancelled = true;
      source.close();
      if (sourceRef.current === source) {
        sourceRef.current = null;
      }
    };
  }, [open, state.appSessionId]);

  useEffect(() => {
    if (!open || !selectedAttemptId) {
      return;
    }
    let cancelled = false;
    const loadAttempt = async () => {
      try {
        const payload = await apiClient.getLlmMonitorStreamAttempt({
          appSessionId: state.appSessionId,
          attemptId: selectedAttemptId,
        });
        if (cancelled) {
          return;
        }
        setSelectedAttempt(payload.attempt);
        setStreamAttempts((prev) => mergeStreamAttemptRows(prev, [payload.attempt]));
      } catch (error) {
        logClientError("LlmMonitorConsole.loadAttempt", error, {
          appSessionId: state.appSessionId,
          attemptId: selectedAttemptId,
        });
      }
    };
    loadAttempt();
    return () => {
      cancelled = true;
    };
  }, [open, selectedAttemptId, state.appSessionId]);

  const pendingRows = useMemo(() => {
    return pending.map((call) => ({
      ...call,
      elapsedMs: resolvePendingElapsedMs(call, nowMs),
    }));
  }, [pending, nowMs]);

  const streamTranscript = useMemo(
    () => selectedAttemptTranscript(selectedAttempt),
    [selectedAttempt]
  );

  if (!isMounted || !open) {
    return null;
  }

  return createPortal(
    <div className="fixed inset-0 z-[90] flex items-end justify-end bg-slate-900/30 p-3 sm:p-4">
      <section className="flex h-[80vh] w-full max-w-[1150px] flex-col overflow-hidden rounded-2xl border border-slate-300 bg-white shadow-2xl">
        <header className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3">
          <div>
            <div className="text-sm font-semibold text-slate-900">LLM Konsole</div>
            <div className="text-[11px] text-slate-600">
              Session {state.appSessionId} · Pending {pending.length} · Recent {recent.length}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`rounded-full px-2 py-1 text-[10px] font-semibold ${
                streamError ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"
              }`}
            >
              {streamError ? "Reconnecting" : "Live"}
            </span>
            <button
              type="button"
              onClick={() => {
                setEvents([]);
                setRecent([]);
              }}
              className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-50"
            >
              Log leeren
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-50"
            >
              Schließen
            </button>
          </div>
        </header>

        <div className="border-b border-slate-200 bg-white px-4 py-2">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setTab("overview")}
              className={`rounded-lg px-3 py-1 text-xs font-semibold ${
                tab === "overview"
                  ? "bg-slate-900 text-white"
                  : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              Overview
            </button>
            <button
              type="button"
              onClick={() => setTab("stream")}
              className={`rounded-lg px-3 py-1 text-xs font-semibold ${
                tab === "stream"
                  ? "bg-slate-900 text-white"
                  : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              Stream Debug
            </button>
          </div>
        </div>

        {streamError && (
          <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs font-semibold text-amber-800">
            {streamError}
          </div>
        )}

        {tab === "overview" ? (
          <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-2">
            <section className="min-h-0 border-b border-slate-200 lg:border-b-0 lg:border-r">
              <div className="border-b border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700">
                Pending Calls
              </div>
              <div className="h-[30vh] overflow-auto px-3 py-2 text-xs">
                {isLoading ? (
                  <div className="text-slate-500">Lade Snapshot...</div>
                ) : pendingRows.length === 0 ? (
                  <div className="text-slate-500">Keine laufenden LLM-Calls.</div>
                ) : (
                  pendingRows.map((row) => (
                    <div
                      key={String(row.attempt_id || `${row.prompt_id}-${row.started_at_ms}`)}
                      className="mb-2 rounded-lg border border-slate-200 bg-white p-2"
                    >
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-slate-800">{row.prompt_id || "-"}</div>
                        <div className="font-mono text-[11px] text-slate-600">
                          {formatDurationMs(row.elapsedMs)}
                        </div>
                      </div>
                      <div className="mt-1 text-[11px] text-slate-600">
                        {formatClockFromMs(row.started_at_ms)} · {row.provider || "?"} ·{" "}
                        {row.model || "?"}
                      </div>
                      <div className="mt-1 font-mono text-[10px] text-slate-500">
                        {(row.route_method || "?").toUpperCase()} {row.route_path || "-"}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>

            <section className="min-h-0 border-b border-slate-200">
              <div className="border-b border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700">
                Recent Calls
              </div>
              <div className="h-[30vh] overflow-auto px-3 py-2 text-xs">
                {recent.length === 0 ? (
                  <div className="text-slate-500">Noch keine abgeschlossenen Calls.</div>
                ) : (
                  recent.map((row) => (
                    <div key={recentRowKey(row)} className="mb-2 rounded-lg border border-slate-200 bg-white p-2">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-slate-800">{row.prompt_id || "-"}</div>
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                            row.answer_state === "invalid"
                              ? "bg-rose-100 text-rose-800"
                              : row.answer_state === "active"
                                ? "bg-emerald-100 text-emerald-800"
                                : "bg-slate-100 text-slate-700"
                          }`}
                        >
                          {row.answer_state || "-"}
                        </span>
                      </div>
                      <div className="mt-1 text-[11px] text-slate-600">
                        {formatClockFromIso(row.created_at)} · {row.provider || "?"} ·{" "}
                        {row.model || "?"}
                      </div>
                      <div className="mt-1 font-mono text-[10px] text-slate-500">
                        Dauer {formatDurationMs(row.elapsed_ms)} · in {row.input_tokens ?? "-"} /
                        out {row.output_tokens ?? "-"}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>

            <section className="min-h-0 lg:col-span-2">
              <div className="border-b border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700">
                Live Event Log
              </div>
              <div className="h-[28vh] overflow-auto px-3 py-2 text-xs">
                {events.length === 0 ? (
                  <div className="text-slate-500">Noch keine Live-Events.</div>
                ) : (
                  events.map((row) => (
                    <div
                      key={`${row.sequence || 0}-${row.attempt_id || row.answer_id || row.event_type}`}
                      className="mb-1 rounded border border-slate-200 bg-white px-2 py-1"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] text-slate-500">
                          {formatClockFromMs(row.timestamp_ms)}
                        </span>
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-700">
                          {row.event_type}
                        </span>
                        <span className="text-[11px] font-semibold text-slate-800">
                          {row.prompt_id || "-"}
                        </span>
                        <span className="font-mono text-[10px] text-slate-500">
                          {formatDurationMs(row.elapsed_ms)}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>
        ) : (
          <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[320px_1fr]">
            <aside className="min-h-0 border-b border-slate-200 lg:border-b-0 lg:border-r">
              <div className="border-b border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700">
                Stream Attempts
              </div>
              <div className="h-full overflow-auto px-2 py-2">
                {streamAttempts.length === 0 ? (
                  <div className="px-2 text-xs text-slate-500">Noch keine Stream-Daten.</div>
                ) : (
                  streamAttempts.map((attempt) => {
                    const key = attemptKey(attempt);
                    const isActive = key && key === selectedAttemptId;
                    return (
                      <button
                        key={key || `${attempt.prompt_id}-${attempt.started_at_ms}`}
                        type="button"
                        onClick={() => {
                          if (!key) {
                            return;
                          }
                          setSelectedAttemptId(key);
                          setSelectedAttempt(attempt);
                        }}
                        className={`mb-2 w-full rounded-lg border px-2 py-2 text-left text-xs ${
                          isActive
                            ? "border-slate-800 bg-slate-900 text-white"
                            : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                        }`}
                      >
                        <div className="font-semibold">{attempt.prompt_id || "-"}</div>
                        <div className="mt-0.5 text-[10px] opacity-80">
                          {attempt.provider || "?"} · {attempt.model || "?"}
                        </div>
                        <div className="mt-0.5 text-[10px] opacity-80">
                          {attempt.status || "-"} · {formatClockFromMs(attempt.started_at_ms)}
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            </aside>

            <section className="min-h-0">
              <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-3 py-2">
                <div className="text-xs font-semibold text-slate-700">Stream Transcript</div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setShowRawChunks((prev) => !prev)}
                    className="rounded border border-slate-200 bg-white px-2 py-1 text-[10px] font-semibold text-slate-700 hover:bg-slate-50"
                  >
                    {showRawChunks ? "Text View" : "Raw Chunks"}
                  </button>
                </div>
              </div>
              <div className="h-full overflow-auto p-3">
                {!selectedAttempt ? (
                  <div className="text-xs text-slate-500">Bitte einen Attempt links auswählen.</div>
                ) : (
                  <div className="space-y-3">
                    <div className="rounded border border-slate-200 bg-white p-2 text-xs text-slate-700">
                      <div>
                        <span className="font-semibold">Prompt:</span> {selectedAttempt.prompt_id || "-"}
                      </div>
                      <div>
                        <span className="font-semibold">Status:</span> {selectedAttempt.status || "-"}
                      </div>
                      <div>
                        <span className="font-semibold">Started:</span>{" "}
                        {formatClockFromMs(selectedAttempt.started_at_ms)} ·{" "}
                        <span className="font-semibold">Elapsed:</span>{" "}
                        {formatDurationMs(selectedAttempt.elapsed_ms)}
                      </div>
                      <div>
                        <span className="font-semibold">Route:</span>{" "}
                        {(selectedAttempt.route_method || "?").toUpperCase()}{" "}
                        {selectedAttempt.route_path || "-"}
                      </div>
                    </div>

                    {showRawChunks ? (
                      <pre className="max-h-[45vh] overflow-auto rounded border border-slate-200 bg-slate-950 p-3 text-[11px] leading-relaxed text-slate-100">
                        {JSON.stringify(selectedAttempt.chunks || [], null, 2)}
                      </pre>
                    ) : (
                      <pre className="max-h-[45vh] overflow-auto whitespace-pre-wrap rounded border border-slate-200 bg-slate-950 p-3 text-[12px] leading-relaxed text-slate-100">
                        {streamTranscript || "(Kein Stream-Text erfasst)"}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            </section>
          </div>
        )}
      </section>
    </div>,
    document.body
  );
}
