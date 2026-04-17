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
import { AUTOMATED_NORM_ADDRESSEES, Model, NormAddressee } from "@/types";

type AddresseeReadiness = {
  processesReady: boolean;
  caseGroupsReady: boolean;
  processStepsReady: boolean;
  effortReady: boolean;
  totalCostReady: boolean;
};

const EMPTY_ADDRESSEE_READINESS: AddresseeReadiness = {
  processesReady: false,
  caseGroupsReady: false,
  processStepsReady: false,
  effortReady: false,
  totalCostReady: false,
};

function createDefaultAddresseeReadiness(): Record<NormAddressee, AddresseeReadiness> {
  return {
    administration: { ...EMPTY_ADDRESSEE_READINESS },
    business: { ...EMPTY_ADDRESSEE_READINESS },
    citizens: { ...EMPTY_ADDRESSEE_READINESS },
  };
}

function setAllAddresseesField(
  prev: Record<NormAddressee, AddresseeReadiness>,
  field: keyof AddresseeReadiness,
  value: boolean
): Record<NormAddressee, AddresseeReadiness> {
  return AUTOMATED_NORM_ADDRESSEES.reduce(
    (next, addressee) => ({
      ...next,
      [addressee]: {
        ...(prev[addressee] ?? EMPTY_ADDRESSEE_READINESS),
        [field]: value,
      },
    }),
    { ...prev }
  );
}

interface AppState {
  currentTab: number;
  appSessionId: string;
  selectedNormAddressee: NormAddressee;
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
  setSelectedNormAddressee: (normAddressee: NormAddressee) => void;
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
const SELECTED_NORM_ADDRESSEE_STORAGE_KEY = "selected_norm_addressee";

// Lazy-Initializer fuer selectedNormAddressee: liest den zuletzt gewaehlten
// Adressaten aus SessionStorage, damit nach Reload keine Verwaltung-Flash
// entsteht und die Anzeige konsistent mit dem vorherigen User-Zustand ist.
function readStoredNormAddressee(): NormAddressee {
  if (typeof window === "undefined") {
    return "administration";
  }
  try {
    const stored = sessionStorage.getItem(SELECTED_NORM_ADDRESSEE_STORAGE_KEY);
    if (stored === "administration" || stored === "business" || stored === "citizens") {
      return stored;
    }
  } catch {
    // SessionStorage kann in privaten Browsing-Modi oder SSR unzugaenglich
    // sein - dann faellt das Feature auf den Default zurueck.
  }
  return "administration";
}
const NORM_ADDRESSEE_READINESS_STORAGE_KEY = "norm_addressee_readiness";
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
  const [selectedNormAddressee, setSelectedNormAddresseeState] =
    useState<NormAddressee>(readStoredNormAddressee);
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
  const [addresseeReadiness, setAddresseeReadiness] = useState<
    Record<NormAddressee, AddresseeReadiness>
  >(createDefaultAddresseeReadiness);
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

  const setSelectedNormAddressee = useCallback((normAddressee: NormAddressee) => {
    setSelectedNormAddresseeState(normAddressee);
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
    const stored = sessionStorage.getItem(SELECTED_NORM_ADDRESSEE_STORAGE_KEY);
    if (stored === "administration" || stored === "business" || stored === "citizens") {
      setSelectedNormAddresseeState(stored);
    }
    const storedReadiness = sessionStorage.getItem(NORM_ADDRESSEE_READINESS_STORAGE_KEY);
    if (!storedReadiness) {
      return;
    }
    try {
      const parsed = JSON.parse(storedReadiness) as Partial<
        Record<NormAddressee, Partial<AddresseeReadiness>>
      >;
      setAddresseeReadiness({
        administration: {
          ...EMPTY_ADDRESSEE_READINESS,
          ...(parsed.administration ?? {}),
        },
        business: {
          ...EMPTY_ADDRESSEE_READINESS,
          ...(parsed.business ?? {}),
        },
        citizens: {
          ...EMPTY_ADDRESSEE_READINESS,
          ...(parsed.citizens ?? {}),
        },
      });
    } catch {
      sessionStorage.removeItem(NORM_ADDRESSEE_READINESS_STORAGE_KEY);
    }
  }, []);

  useEffect(() => {
    if (!appSessionId) {
      return;
    }
    sessionStorage.setItem(APP_SESSION_STORAGE_KEY, appSessionId);
    sessionStorage.removeItem(LEGACY_SESSION_STORAGE_KEY);
  }, [appSessionId, readinessSetters, logDebug]);

  useEffect(() => {
    sessionStorage.setItem(
      SELECTED_NORM_ADDRESSEE_STORAGE_KEY,
      selectedNormAddressee
    );
  }, [selectedNormAddressee]);

  useEffect(() => {
    sessionStorage.setItem(
      NORM_ADDRESSEE_READINESS_STORAGE_KEY,
      JSON.stringify(addresseeReadiness)
    );
  }, [addresseeReadiness]);

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
        // Wenn das Backend keine by_addressee-Maps liefert, rutschen
        // Business/Citizens auf den Legacy-Pfad mit stummem "false"
        // zurueck. Das ist nur im Uebergangszustand zulaessig - wir
        // loggen einen Warnhinweis, damit solche Faelle im Audit
        // auffindbar bleiben.
        const missingByAddresseeKeys: string[] = [];
        if (!status.processes_ready_by_addressee) missingByAddresseeKeys.push("processes_ready_by_addressee");
        if (!status.case_groups_ready_by_addressee) missingByAddresseeKeys.push("case_groups_ready_by_addressee");
        if (!status.process_steps_ready_by_addressee) missingByAddresseeKeys.push("process_steps_ready_by_addressee");
        if (!status.effort_ready_by_addressee) missingByAddresseeKeys.push("effort_ready_by_addressee");
        if (!status.total_cost_ready_by_addressee) missingByAddresseeKeys.push("total_cost_ready_by_addressee");
        if (missingByAddresseeKeys.length > 0) {
          logDebug(
            "[AppContext] event=addressee_readiness_fallback Backend lieferte keine by_addressee-Maps",
            { appSessionId, missing: missingByAddresseeKeys }
          );
        }
        setAddresseeReadiness((prev) =>
          AUTOMATED_NORM_ADDRESSEES.reduce(
            (next, addressee) => ({
              ...next,
              [addressee]: {
                processesReady:
                  status.processes_ready_by_addressee?.[addressee] ??
                  (addressee === "administration" ? status.processes_ready : false),
                caseGroupsReady:
                  status.case_groups_ready_by_addressee?.[addressee] ??
                  (addressee === "administration" ? status.case_groups_ready : false),
                processStepsReady:
                  status.process_steps_ready_by_addressee?.[addressee] ??
                  (addressee === "administration" ? status.process_steps_ready : false),
                effortReady:
                  status.effort_ready_by_addressee?.[addressee] ??
                  (addressee === "administration" ? status.effort_ready : false),
                totalCostReady:
                  status.total_cost_ready_by_addressee?.[addressee] ??
                  (addressee === "administration" ? status.total_cost_ready : false),
              },
            }),
            { ...prev }
          )
        );
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
    const aggregateReadiness = {
      processesReady: AUTOMATED_NORM_ADDRESSEES.every(
        (addressee) => addresseeReadiness[addressee]?.processesReady
      ),
      caseGroupsReady: AUTOMATED_NORM_ADDRESSEES.every(
        (addressee) => addresseeReadiness[addressee]?.caseGroupsReady
      ),
      processStepsReady: AUTOMATED_NORM_ADDRESSEES.every(
        (addressee) => addresseeReadiness[addressee]?.processStepsReady
      ),
      effortReady: AUTOMATED_NORM_ADDRESSEES.every(
        (addressee) => addresseeReadiness[addressee]?.effortReady
      ),
      totalCostReady: AUTOMATED_NORM_ADDRESSEES.every(
        (addressee) => addresseeReadiness[addressee]?.totalCostReady
      ),
    };
    const normalizedStatus = {
      summary_ready: readinessValues.summary_ready,
      regulations_ready:
        readinessValues.summary_ready && readinessValues.regulations_ready,
      processes_ready:
        readinessValues.summary_ready &&
        readinessValues.regulations_ready &&
        aggregateReadiness.processesReady,
      case_groups_ready:
        readinessValues.summary_ready &&
        readinessValues.regulations_ready &&
        aggregateReadiness.processesReady &&
        aggregateReadiness.caseGroupsReady,
      process_steps_ready:
        readinessValues.summary_ready &&
        readinessValues.regulations_ready &&
        aggregateReadiness.processesReady &&
        aggregateReadiness.caseGroupsReady &&
        aggregateReadiness.processStepsReady,
      effort_ready:
        readinessValues.summary_ready &&
        readinessValues.regulations_ready &&
        aggregateReadiness.processesReady &&
        aggregateReadiness.caseGroupsReady &&
        aggregateReadiness.processStepsReady &&
        aggregateReadiness.effortReady,
      total_cost_ready:
        readinessValues.summary_ready &&
        readinessValues.regulations_ready &&
        aggregateReadiness.processesReady &&
        aggregateReadiness.caseGroupsReady &&
        aggregateReadiness.processStepsReady &&
        aggregateReadiness.effortReady &&
        aggregateReadiness.totalCostReady,
    };

    setProcessesReady(normalizedStatus.processes_ready);
    setCaseGroupsReady(normalizedStatus.case_groups_ready);
    setProcessStepsReady(normalizedStatus.process_steps_ready);
    setEffortReady(normalizedStatus.effort_ready);
    setTotalCostReady(normalizedStatus.total_cost_ready);

    setCurrentTab(deriveTabFromStatus(normalizedStatus));
  }, [addresseeReadiness, readinessValues]);

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
          selectedNormAddressee,
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
        setSelectedNormAddressee,
        setSelectedModel,
        setAvailableModels,
        setSelectedCurrentLaw,
        setSelectedRegulation,
        setAvailableRegulations,
        setSummaryReady: (ready: boolean) => {
          setSummaryReady(ready);
          if (!ready) {
            setRegulationsReady(false);
            setAddresseeReadiness(createDefaultAddresseeReadiness());
          }
        },
        setRegulationsReady: (ready: boolean) => {
          setRegulationsReady(ready);
          if (!ready) {
            setAddresseeReadiness(createDefaultAddresseeReadiness());
          }
        },
        setProcessesReady: (ready: boolean) =>
          setAddresseeReadiness((prev) => {
            const next = setAllAddresseesField(prev, "processesReady", ready);
            if (!ready) {
              return AUTOMATED_NORM_ADDRESSEES.reduce(
                (acc, addressee) => ({
                  ...acc,
                  [addressee]: {
                    ...acc[addressee],
                    caseGroupsReady: false,
                    processStepsReady: false,
                    effortReady: false,
                    totalCostReady: false,
                  },
                }),
                next
              );
            }
            return next;
          }),
        setCaseGroupsReady: (ready: boolean) =>
          setAddresseeReadiness((prev) => {
            const next = setAllAddresseesField(prev, "caseGroupsReady", ready);
            if (!ready) {
              return AUTOMATED_NORM_ADDRESSEES.reduce(
                (acc, addressee) => ({
                  ...acc,
                  [addressee]: {
                    ...acc[addressee],
                    processStepsReady: false,
                    effortReady: false,
                    totalCostReady: false,
                  },
                }),
                next
              );
            }
            return next;
          }),
        setProcessStepsReady: (ready: boolean) =>
          setAddresseeReadiness((prev) => {
            const next = setAllAddresseesField(prev, "processStepsReady", ready);
            if (!ready) {
              return AUTOMATED_NORM_ADDRESSEES.reduce(
                (acc, addressee) => ({
                  ...acc,
                  [addressee]: {
                    ...acc[addressee],
                    effortReady: false,
                    totalCostReady: false,
                  },
                }),
                next
              );
            }
            return next;
          }),
        setEffortReady: (ready: boolean) =>
          setAddresseeReadiness((prev) => {
            const next = setAllAddresseesField(prev, "effortReady", ready);
            if (!ready) {
              return AUTOMATED_NORM_ADDRESSEES.reduce(
                (acc, addressee) => ({
                  ...acc,
                  [addressee]: {
                    ...acc[addressee],
                    totalCostReady: false,
                  },
                }),
                next
              );
            }
            return next;
          }),
        setTotalCostReady: (ready: boolean) =>
          setAddresseeReadiness((prev) =>
            setAllAddresseesField(prev, "totalCostReady", ready)
          ),
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
