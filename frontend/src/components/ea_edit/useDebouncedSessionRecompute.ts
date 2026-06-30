"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiClient } from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";
import { NormAddressee } from "@/types";

type UseDebouncedSessionRecomputeOptions = {
  appSessionId: string;
  // Required: without it /costs/compute silently defaults to administration, so an
  // edit of another addressee would recompute the wrong total. Enforced, not optional.
  normAddressee: NormAddressee;
  eaActivityId: string | null;
  debounceMs?: number;
};

export function useDebouncedSessionRecompute({
  appSessionId,
  normAddressee,
  eaActivityId,
  debounceMs = 400,
}: UseDebouncedSessionRecomputeOptions) {
  const [recomputeStatus, setRecomputeStatus] = useState<string | null>(null);
  const debounceTimerRef = useRef<number | null>(null);
  const debouncePromiseRef = useRef<Promise<void> | null>(null);
  const debounceResolveRef = useRef<(() => void) | null>(null);
  const recomputeInFlightRef = useRef<Promise<void> | null>(null);

  useEffect(() => {
    return () => {
      if (debounceTimerRef.current !== null) {
        window.clearTimeout(debounceTimerRef.current);
      }
      if (debounceResolveRef.current) {
        debounceResolveRef.current();
      }
    };
  }, []);

  const waitForDebounce = useCallback(async () => {
    if (!debouncePromiseRef.current) {
      debouncePromiseRef.current = new Promise<void>((resolve) => {
        debounceResolveRef.current = resolve;
      });
    }
    if (debounceTimerRef.current !== null) {
      window.clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = window.setTimeout(() => {
      debounceTimerRef.current = null;
      const resolve = debounceResolveRef.current;
      debounceResolveRef.current = null;
      debouncePromiseRef.current = null;
      if (resolve) {
        resolve();
      }
    }, debounceMs);
    await debouncePromiseRef.current;
  }, [debounceMs]);

  const runAutoRecompute = useCallback(async () => {
    setRecomputeStatus(null);
    await waitForDebounce();
    if (recomputeInFlightRef.current) {
      await recomputeInFlightRef.current;
      return;
    }
    const request = (async () => {
      await apiClient.computeTotalCost({
        appSessionId,
        normAddressee,
        eaActivityId: eaActivityId ?? undefined,
      });
      window.dispatchEvent(new Event("tiles-updated"));
    })();
    recomputeInFlightRef.current = request;
    try {
      await request;
    } catch (error) {
      logClientError("useDebouncedSessionRecompute.runAutoRecompute", error, {
        appSessionId,
      });
      setRecomputeStatus("Automatische Neuberechnung der Gesamtkosten ist fehlgeschlagen.");
      throw error;
    } finally {
      recomputeInFlightRef.current = null;
    }
  }, [appSessionId, normAddressee, eaActivityId, waitForDebounce]);

  return {
    recomputeStatus,
    runAutoRecompute,
  };
}
