"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { apiClient } from "@/lib/api";
import { deriveTabFromStatus } from "@/lib/sessionStatus";
import { AUTOMATED_NORM_ADDRESSEES, Model, NormAddressee, SessionStatus } from "@/types";

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

function buildAddresseeReadinessFromStatus(
  status: SessionStatus,
  previous: Record<NormAddressee, AddresseeReadiness>
): Record<NormAddressee, AddresseeReadiness> {
  return AUTOMATED_NORM_ADDRESSEES.reduce(
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
    { ...previous }
  );
}

function buildAggregateStatus(
  summaryReady: boolean,
  regulationsReady: boolean,
  readiness: Record<NormAddressee, AddresseeReadiness>
) {
  const aggregateReadiness = {
    processesReady: AUTOMATED_NORM_ADDRESSEES.every(
      (addressee) => readiness[addressee]?.processesReady
    ),
    caseGroupsReady: AUTOMATED_NORM_ADDRESSEES.every(
      (addressee) => readiness[addressee]?.caseGroupsReady
    ),
    processStepsReady: AUTOMATED_NORM_ADDRESSEES.every(
      (addressee) => readiness[addressee]?.processStepsReady
    ),
    effortReady: AUTOMATED_NORM_ADDRESSEES.every(
      (addressee) => readiness[addressee]?.effortReady
    ),
    totalCostReady: AUTOMATED_NORM_ADDRESSEES.every(
      (addressee) => readiness[addressee]?.totalCostReady
    ),
  };

  return {
    summary_ready: summaryReady,
    regulations_ready: summaryReady && regulationsReady,
    processes_ready:
      summaryReady && regulationsReady && aggregateReadiness.processesReady,
    case_groups_ready:
      summaryReady &&
      regulationsReady &&
      aggregateReadiness.processesReady &&
      aggregateReadiness.caseGroupsReady,
    process_steps_ready:
      summaryReady &&
      regulationsReady &&
      aggregateReadiness.processesReady &&
      aggregateReadiness.caseGroupsReady &&
      aggregateReadiness.processStepsReady,
    effort_ready:
      summaryReady &&
      regulationsReady &&
      aggregateReadiness.processesReady &&
      aggregateReadiness.caseGroupsReady &&
      aggregateReadiness.processStepsReady &&
      aggregateReadiness.effortReady,
    total_cost_ready:
      summaryReady &&
      regulationsReady &&
      aggregateReadiness.processesReady &&
      aggregateReadiness.caseGroupsReady &&
      aggregateReadiness.processStepsReady &&
      aggregateReadiness.effortReady &&
      aggregateReadiness.totalCostReady,
  };
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
  pendingCurrentUpload: File | null;
  pendingProposedUpload: File | null;
  pendingCurrentUploadName: string;
  pendingProposedUploadName: string;
  summaryReady: boolean;
  regulationsReady: boolean;
  processesReady: boolean;
  caseGroupsReady: boolean;
  processStepsReady: boolean;
  effortReady: boolean;
  totalCostReady: boolean;
  lastCompletedStep: string | null;
  lastCompletedLabel: string | null;
  lastFailedStep: string | null;
  lastFailedLabel: string | null;
  lastFailedMessage: string | null;
  isComplianceExportRunning: boolean;
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
  setPendingCurrentUpload: (file: File | null) => void;
  setPendingProposedUpload: (file: File | null) => void;
  setPendingCurrentUploadName: (name: string) => void;
  setPendingProposedUploadName: (name: string) => void;
  setSummaryReady: (ready: boolean) => void;
  setRegulationsReady: (ready: boolean) => void;
  setProcessesReady: (ready: boolean) => void;
  setCaseGroupsReady: (ready: boolean) => void;
  setProcessStepsReady: (ready: boolean) => void;
  setEffortReady: (ready: boolean) => void;
  setTotalCostReady: (ready: boolean) => void;
  setLastCompletedStep: (step: string | null) => void;
  setLastCompletedLabel: (label: string | null) => void;
  setLastFailedStep: (step: string | null) => void;
  setLastFailedLabel: (label: string | null) => void;
  setLastFailedMessage: (message: string | null) => void;
  setIsComplianceExportRunning: (running: boolean) => void;
  applySessionStatus: (sessionStatus: SessionStatus) => void;
}

const AppContext = createContext<AppContextValue | undefined>(undefined);
const APP_SESSION_STORAGE_KEY = "app_session_id";
const LEGACY_SESSION_STORAGE_KEY = "session_id";
const SELECTED_NORM_ADDRESSEE_STORAGE_KEY = "selected_norm_addressee";

function readStoredNormAddressee(): NormAddressee {
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

export function AppProvider({ children }: { children: React.ReactNode }) {
  const logDebug = useCallback((message: string, details?: Record<string, unknown>) => {
    if (process.env.NODE_ENV === "development") {
      console.debug(message, details);
    }
  }, []);

  const [currentTab, setCurrentTab] = useState(0);
  const [appSessionId, setAppSessionIdState] = useState("");
  const [selectedNormAddressee, setSelectedNormAddresseeState] =
    useState<NormAddressee>("administration");
  const [selectedModel, setSelectedModel] = useState("");
  const [selectedModelHydrated, setSelectedModelHydrated] = useState(false);
  const [availableModels, setAvailableModels] = useState<Model[]>([]);
  const [selectedCurrentLaw, setSelectedCurrentLaw] = useState("");
  const [selectedRegulation, setSelectedRegulation] = useState("");
  const [availableRegulations, setAvailableRegulations] = useState<string[]>([]);
  const [pendingCurrentUpload, setPendingCurrentUpload] = useState<File | null>(null);
  const [pendingProposedUpload, setPendingProposedUpload] = useState<File | null>(null);
  const [pendingCurrentUploadName, setPendingCurrentUploadName] = useState("");
  const [pendingProposedUploadName, setPendingProposedUploadName] = useState("");
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
  const [lastFailedStep, setLastFailedStep] = useState<string | null>(null);
  const [lastFailedLabel, setLastFailedLabel] = useState<string | null>(null);
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null);
  const [isComplianceExportRunning, setIsComplianceExportRunning] = useState(false);

  const setAppSessionId = useCallback((nextAppSessionId: string) => {
    setAppSessionIdState(nextAppSessionId);
  }, []);

  const setSelectedNormAddressee = useCallback((normAddressee: NormAddressee) => {
    setSelectedNormAddresseeState(normAddressee);
  }, []);

  const applySessionStatus = useCallback(
    (status: SessionStatus) => {
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

      const nextReadiness = buildAddresseeReadinessFromStatus(
        status,
        createDefaultAddresseeReadiness()
      );
      const normalizedStatus = buildAggregateStatus(
        status.summary_ready,
        status.regulations_ready,
        nextReadiness
      );
      setAddresseeReadiness(nextReadiness);
      setSummaryReady(normalizedStatus.summary_ready);
      setRegulationsReady(normalizedStatus.regulations_ready);
      setProcessesReady(normalizedStatus.processes_ready);
      setCaseGroupsReady(normalizedStatus.case_groups_ready);
      setProcessStepsReady(normalizedStatus.process_steps_ready);
      setEffortReady(normalizedStatus.effort_ready);
      setTotalCostReady(normalizedStatus.total_cost_ready);
      setCurrentTab(deriveTabFromStatus(normalizedStatus));
      setLastCompletedStep(status.last_completed_step ?? null);
      setLastCompletedLabel(status.last_completed_label ?? null);
      setLastFailedStep(status.last_failed_step ?? null);
      setLastFailedLabel(status.last_failed_label ?? null);
      setLastFailedMessage(status.last_failed_message ?? null);
    },
    [appSessionId, logDebug]
  );

  useEffect(() => {
    const storedAppSessionId =
      sessionStorage.getItem(APP_SESSION_STORAGE_KEY) ||
      sessionStorage.getItem(LEGACY_SESSION_STORAGE_KEY);
    if (storedAppSessionId && /^[A-Za-z0-9_-]{1,64}$/.test(storedAppSessionId)) {
      setAppSessionIdState(storedAppSessionId);
      sessionStorage.setItem(APP_SESSION_STORAGE_KEY, storedAppSessionId);
      sessionStorage.removeItem(LEGACY_SESSION_STORAGE_KEY);
    }
    // When there is no stored session id, a new one is created server-side by
    // the syncSession effect once a model is selected (the server generates and
    // returns the app_session_id).
  }, []);

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
  }, [appSessionId]);

  useEffect(() => {
    const storedNormAddressee = readStoredNormAddressee();
    if (storedNormAddressee !== selectedNormAddressee) {
      setSelectedNormAddresseeState(storedNormAddressee);
    }
    // Only run after hydration. Reading sessionStorage in the state initializer
    // makes the first client render differ from the server-rendered header.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
        applySessionStatus(status);
      } catch (error) {
        const status =
          typeof (error as { status?: unknown })?.status === "number"
            ? ((error as { status: number }).status as number)
            : undefined;
        // A stored session id may no longer exist or may not be owned by the
        // current user (the backend returns 404 in that case).
        if (status === 404) {
          setAppSessionIdState("");
          sessionStorage.removeItem(APP_SESSION_STORAGE_KEY);
          sessionStorage.removeItem(LEGACY_SESSION_STORAGE_KEY);
          sessionStorage.removeItem(NORM_ADDRESSEE_READINESS_STORAGE_KEY);
          setSummaryReady(false);
          setRegulationsReady(false);
          setProcessesReady(false);
          setCaseGroupsReady(false);
          setProcessStepsReady(false);
          setEffortReady(false);
          setTotalCostReady(false);
          setAddresseeReadiness(createDefaultAddresseeReadiness());
          setCurrentTab(0);
          setLastCompletedStep(null);
          setLastCompletedLabel(null);
          setLastFailedStep(null);
          setLastFailedLabel(null);
          setLastFailedMessage(null);
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
  }, [appSessionId, applySessionStatus, logDebug]);

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
    const normalizedStatus = buildAggregateStatus(
      summaryReady,
      regulationsReady,
      addresseeReadiness
    );

    setProcessesReady(normalizedStatus.processes_ready);
    setCaseGroupsReady(normalizedStatus.case_groups_ready);
    setProcessStepsReady(normalizedStatus.process_steps_ready);
    setEffortReady(normalizedStatus.effort_ready);
    setTotalCostReady(normalizedStatus.total_cost_ready);

    setCurrentTab(deriveTabFromStatus(normalizedStatus));
  }, [addresseeReadiness, regulationsReady, summaryReady]);

  useEffect(() => {
    // A session id is only created server-side, on demand, once a model is
    // selected. The server generates the id and we adopt the returned value.
    if (appSessionId || !selectedModel) {
      return;
    }
    let cancelled = false;
    const createSession = async () => {
      try {
        const { app_session_id } = await apiClient.createSession(selectedModel);
        if (cancelled) {
          return;
        }
        setAppSessionIdState(app_session_id);
      } catch (error) {
        logDebug("[AppContext] Failed to create session", {
          selectedModel,
          error,
        });
      }
    };
    createSession();
    return () => {
      cancelled = true;
    };
  }, [appSessionId, selectedModel, logDebug]);

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
          pendingCurrentUpload,
          pendingProposedUpload,
          pendingCurrentUploadName,
          pendingProposedUploadName,
          summaryReady,
          regulationsReady,
          processesReady,
          caseGroupsReady,
          processStepsReady,
          effortReady,
          totalCostReady,
          lastCompletedStep,
          lastCompletedLabel,
          lastFailedStep,
          lastFailedLabel,
          lastFailedMessage,
          isComplianceExportRunning,
        },
        setCurrentTab,
        setAppSessionId,
        setSelectedNormAddressee,
        setSelectedModel,
        setAvailableModels,
        setSelectedCurrentLaw,
        setSelectedRegulation,
        setAvailableRegulations,
        setPendingCurrentUpload: (file: File | null) => {
          setPendingCurrentUpload(file);
          if (!file) {
            setPendingCurrentUploadName("");
          } else {
            setPendingCurrentUploadName(file.name);
          }
        },
        setPendingProposedUpload: (file: File | null) => {
          setPendingProposedUpload(file);
          if (!file) {
            setPendingProposedUploadName("");
          } else {
            setPendingProposedUploadName(file.name);
          }
        },
        setPendingCurrentUploadName,
        setPendingProposedUploadName,
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
        setLastFailedStep,
        setLastFailedLabel,
        setLastFailedMessage,
        setIsComplianceExportRunning,
        applySessionStatus,
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
