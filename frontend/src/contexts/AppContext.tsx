"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { apiClient } from "@/lib/api";
import { deriveTabFromStatus } from "@/lib/sessionStatus";
import { Model } from "@/types";

interface AppState {
  currentTab: number;
  appSessionId: string;
  selectedModel: string;
  availableModels: Model[];
  selectedCurrentLaw: string;
  selectedRegulation: string;
  availableRegulations: string[];
  summaryReady: boolean;
  regulationsReady: boolean;
  processesReady: boolean;
  caseGroupsReady: boolean;
  processStepsReady: boolean;
  effortReady: boolean;
  totalCostReady: boolean;
  lastCompletedStep: string | null;
  lastCompletedLabel: string | null;
}

interface AppContextValue {
  state: AppState;
  setCurrentTab: (tab: number) => void;
  setAppSessionId: (appSessionId: string) => void;
  setSelectedModel: (model: string) => void;
  setAvailableModels: (models: Model[]) => void;
  setSelectedCurrentLaw: (law: string) => void;
  setSelectedRegulation: (regulation: string) => void;
  setAvailableRegulations: (regulations: string[]) => void;
  setSummaryReady: (ready: boolean) => void;
  setRegulationsReady: (ready: boolean) => void;
  setProcessesReady: (ready: boolean) => void;
  setCaseGroupsReady: (ready: boolean) => void;
  setProcessStepsReady: (ready: boolean) => void;
  setEffortReady: (ready: boolean) => void;
  setTotalCostReady: (ready: boolean) => void;
  setLastCompletedStep: (step: string | null) => void;
  setLastCompletedLabel: (label: string | null) => void;
}

const AppContext = createContext<AppContextValue | undefined>(undefined);
const APP_SESSION_STORAGE_KEY = "app_session_id";
const LEGACY_SESSION_STORAGE_KEY = "session_id";
const READINESS_STORAGE_KEYS = [
  "summary_ready",
  "regulations_ready",
  "processes_ready",
  "case_groups_ready",
  "process_steps_ready",
  "effort_ready",
  "total_cost_ready",
] as const;
type ReadinessStorageKey = (typeof READINESS_STORAGE_KEYS)[number];

export function AppProvider({ children }: { children: React.ReactNode }) {
  const logDebug = useCallback((message: string, details?: Record<string, unknown>) => {
    if (process.env.NODE_ENV !== "production") {
      console.debug(message, details);
    }
  }, []);

  const [currentTab, setCurrentTab] = useState(0);
  const [appSessionId, setAppSessionIdState] = useState("");
  const [isFreshAppSessionId, setIsFreshAppSessionId] = useState(false);
  const [selectedModel, setSelectedModel] = useState("");
  const [selectedModelHydrated, setSelectedModelHydrated] = useState(false);
  const [availableModels, setAvailableModels] = useState<Model[]>([]);
  const [selectedCurrentLaw, setSelectedCurrentLaw] = useState("");
  const [selectedRegulation, setSelectedRegulation] = useState("");
  const [availableRegulations, setAvailableRegulations] = useState<string[]>([]);
  const [summaryReady, setSummaryReady] = useState(false);
  const [regulationsReady, setRegulationsReady] = useState(false);
  const [processesReady, setProcessesReady] = useState(false);
  const [caseGroupsReady, setCaseGroupsReady] = useState(false);
  const [processStepsReady, setProcessStepsReady] = useState(false);
  const [effortReady, setEffortReady] = useState(false);
  const [totalCostReady, setTotalCostReady] = useState(false);
  const [lastCompletedStep, setLastCompletedStep] = useState<string | null>(null);
  const [lastCompletedLabel, setLastCompletedLabel] = useState<string | null>(null);
  const appSessionIdAttempts = useRef(0);
  const readinessSetters = useMemo<
    Record<ReadinessStorageKey, (value: boolean) => void>
  >(
    () => ({
      summary_ready: setSummaryReady,
      regulations_ready: setRegulationsReady,
      processes_ready: setProcessesReady,
      case_groups_ready: setCaseGroupsReady,
      process_steps_ready: setProcessStepsReady,
      effort_ready: setEffortReady,
      total_cost_ready: setTotalCostReady,
    }),
    []
  );
  const readinessValues = useMemo<Record<ReadinessStorageKey, boolean>>(
    () => ({
      summary_ready: summaryReady,
      regulations_ready: regulationsReady,
      processes_ready: processesReady,
      case_groups_ready: caseGroupsReady,
      process_steps_ready: processStepsReady,
      effort_ready: effortReady,
      total_cost_ready: totalCostReady,
    }),
    [
      summaryReady,
      regulationsReady,
      processesReady,
      caseGroupsReady,
      processStepsReady,
      effortReady,
      totalCostReady,
    ]
  );

  const generateAppSessionId = useCallback(() => {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    return Array.from({ length: 6 }, () =>
      chars[Math.floor(Math.random() * chars.length)]
    ).join("");
  }, []);

  const setNewAppSessionId = useCallback(() => {
    const generated = generateAppSessionId();
    appSessionIdAttempts.current += 1;
    setAppSessionIdState(generated);
    setIsFreshAppSessionId(true);
  }, [generateAppSessionId]);

  const setAppSessionId = useCallback((nextAppSessionId: string) => {
    setAppSessionIdState(nextAppSessionId);
    setIsFreshAppSessionId(false);
    appSessionIdAttempts.current = 0;
  }, []);

  useEffect(() => {
    const storedAppSessionId =
      sessionStorage.getItem(APP_SESSION_STORAGE_KEY) ||
      sessionStorage.getItem(LEGACY_SESSION_STORAGE_KEY);
    if (storedAppSessionId && /^[A-Z0-9]{6}$/.test(storedAppSessionId)) {
      setAppSessionIdState(storedAppSessionId);
      setIsFreshAppSessionId(false);
      sessionStorage.setItem(APP_SESSION_STORAGE_KEY, storedAppSessionId);
      sessionStorage.removeItem(LEGACY_SESSION_STORAGE_KEY);
      return;
    }
    setNewAppSessionId();
  }, [setNewAppSessionId]);

  useEffect(() => {
    if (!appSessionId) {
      return;
    }
    sessionStorage.setItem(APP_SESSION_STORAGE_KEY, appSessionId);
    sessionStorage.removeItem(LEGACY_SESSION_STORAGE_KEY);
  }, [appSessionId, readinessSetters, logDebug]);

  useEffect(() => {
    if (!appSessionId) {
      return;
    }
    let cancelled = false;
    const syncStatus = async () => {
      try {
        const status = await apiClient.getSessionStatus(appSessionId);
        if (cancelled) {
          return;
        }
        for (const storageKey of READINESS_STORAGE_KEYS) {
          readinessSetters[storageKey](status[storageKey]);
        }
        setLastCompletedStep(status.last_completed_step ?? null);
        setLastCompletedLabel(status.last_completed_label ?? null);
      } catch (error) {
        const status =
          typeof (error as { status?: unknown })?.status === "number"
            ? ((error as { status: number }).status as number)
            : undefined;
        // New app session IDs are created client-side first and may not exist
        // server-side until the first upsert completes.
        if (status === 404) {
          return;
        }
        logDebug("[AppContext] Failed to sync session status", {
          appSessionId,
          error,
        });
      }
    };
    syncStatus();
    const handleTilesUpdate = () => {
      syncStatus();
    };
    window.addEventListener("tiles-updated", handleTilesUpdate);
    return () => {
      cancelled = true;
      window.removeEventListener("tiles-updated", handleTilesUpdate);
    };
  }, [appSessionId, logDebug, readinessSetters]);

  useEffect(() => {
    const localStorageKeys: Array<[string, (value: string) => void]> = [
      ["selected_regulation", setSelectedRegulation],
      ["selected_current_law", setSelectedCurrentLaw],
    ];
    for (const [storageKey, setter] of localStorageKeys) {
      const storedValue = sessionStorage.getItem(storageKey) || "";
      if (storedValue) {
        setter(storedValue);
      }
    }
  }, []);

  useEffect(() => {
    const storedSelectedModel = localStorage.getItem("selected_model") || "";
    if (storedSelectedModel) {
      setSelectedModel(storedSelectedModel);
    }
    setSelectedModelHydrated(true);
  }, []);

  useEffect(() => {
    if (!selectedModelHydrated) {
      return;
    }
    if (selectedModel) {
      localStorage.setItem("selected_model", selectedModel);
    } else {
      localStorage.removeItem("selected_model");
    }
  }, [selectedModel, selectedModelHydrated]);

  useEffect(() => {
    const localStorageValues: Array<[string, string]> = [
      ["selected_regulation", selectedRegulation],
      ["selected_current_law", selectedCurrentLaw],
    ];
    for (const [storageKey, value] of localStorageValues) {
      if (value) {
        sessionStorage.setItem(storageKey, value);
      } else {
        sessionStorage.removeItem(storageKey);
      }
    }
  }, [selectedRegulation, selectedCurrentLaw]);

  useEffect(() => {
    for (const storageKey of READINESS_STORAGE_KEYS) {
      const setter = readinessSetters[storageKey];
      setter(sessionStorage.getItem(storageKey) === "true");
    }
  }, [readinessSetters]);

  useEffect(() => {
    for (const storageKey of READINESS_STORAGE_KEYS) {
      const ready = readinessValues[storageKey];
      if (ready) {
        sessionStorage.setItem(storageKey, "true");
      } else {
        sessionStorage.removeItem(storageKey);
      }
    }
  }, [readinessValues]);

  useEffect(() => {
    const normalizedStatus = {
      summary_ready: readinessValues.summary_ready,
      regulations_ready:
        readinessValues.summary_ready && readinessValues.regulations_ready,
      processes_ready:
        readinessValues.summary_ready &&
        readinessValues.regulations_ready &&
        readinessValues.processes_ready,
      case_groups_ready:
        readinessValues.summary_ready &&
        readinessValues.regulations_ready &&
        readinessValues.processes_ready &&
        readinessValues.case_groups_ready,
      process_steps_ready:
        readinessValues.summary_ready &&
        readinessValues.regulations_ready &&
        readinessValues.processes_ready &&
        readinessValues.case_groups_ready &&
        readinessValues.process_steps_ready,
      effort_ready:
        readinessValues.summary_ready &&
        readinessValues.regulations_ready &&
        readinessValues.processes_ready &&
        readinessValues.case_groups_ready &&
        readinessValues.process_steps_ready &&
        readinessValues.effort_ready,
      total_cost_ready:
        readinessValues.summary_ready &&
        readinessValues.regulations_ready &&
        readinessValues.processes_ready &&
        readinessValues.case_groups_ready &&
        readinessValues.process_steps_ready &&
        readinessValues.effort_ready &&
        readinessValues.total_cost_ready,
    };

    for (const storageKey of READINESS_STORAGE_KEYS) {
      if (storageKey === "summary_ready") {
        continue;
      }
      if (normalizedStatus[storageKey] !== readinessValues[storageKey]) {
        readinessSetters[storageKey](normalizedStatus[storageKey]);
      }
    }

    setCurrentTab(deriveTabFromStatus(normalizedStatus));
  }, [readinessSetters, readinessValues]);

  useEffect(() => {
    if (!appSessionId || !selectedModel) {
      return;
    }
    let cancelled = false;
    const syncSession = async () => {
      try {
        const { created } = await apiClient.upsertSession(appSessionId, selectedModel);
        if (cancelled) {
          return;
        }
        if (created) {
          appSessionIdAttempts.current = 0;
          setIsFreshAppSessionId(false);
          return;
        }
        if (isFreshAppSessionId && appSessionIdAttempts.current < 5) {
          setNewAppSessionId();
          return;
        }
        setIsFreshAppSessionId(false);
      } catch (error) {
        logDebug("[AppContext] Failed to upsert session", {
          appSessionId,
          selectedModel,
          error,
        });
      }
    };
    syncSession();
    return () => {
      cancelled = true;
    };
  }, [appSessionId, selectedModel, isFreshAppSessionId, setNewAppSessionId, logDebug]);

  return (
    <AppContext.Provider
      value={{
        state: {
          currentTab,
          appSessionId,
          selectedModel,
          availableModels,
          selectedCurrentLaw,
          selectedRegulation,
          availableRegulations,
          summaryReady,
          regulationsReady,
          processesReady,
          caseGroupsReady,
          processStepsReady,
          effortReady,
          totalCostReady,
          lastCompletedStep,
          lastCompletedLabel,
        },
        setCurrentTab,
        setAppSessionId,
        setSelectedModel,
        setAvailableModels,
        setSelectedCurrentLaw,
        setSelectedRegulation,
        setAvailableRegulations,
        setSummaryReady,
        setRegulationsReady,
        setProcessesReady,
        setCaseGroupsReady,
        setProcessStepsReady,
        setEffortReady,
        setTotalCostReady,
        setLastCompletedStep,
        setLastCompletedLabel,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within AppProvider");
  }
  return context;
}
