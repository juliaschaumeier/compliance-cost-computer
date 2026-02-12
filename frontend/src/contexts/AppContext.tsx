"use client";

import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { apiClient } from "@/lib/api";
import { Model } from "@/types";

interface AppState {
  currentTab: number;
  sessionId: string;
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
}

interface AppContextValue {
  state: AppState;
  setCurrentTab: (tab: number) => void;
  setSessionId: (sessionId: string) => void;
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
}

const AppContext = createContext<AppContextValue | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [currentTab, setCurrentTab] = useState(0);
  const [sessionId, setSessionId] = useState("");
  const [isFreshSessionId, setIsFreshSessionId] = useState(false);
  const [selectedModel, setSelectedModel] = useState(() => {
    if (typeof window === "undefined") {
      return "";
    }
    return localStorage.getItem("selected_model") || "";
  });
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
  const sessionIdAttempts = useRef(0);

  const generateSessionId = () => {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    return Array.from({ length: 6 }, () =>
      chars[Math.floor(Math.random() * chars.length)]
    ).join("");
  };

  const setNewSessionId = () => {
    const generated = generateSessionId();
    sessionIdAttempts.current += 1;
    setSessionId(generated);
    setIsFreshSessionId(true);
  };

  useEffect(() => {
    const storedSessionId = sessionStorage.getItem("session_id");
    if (storedSessionId && /^[A-Z0-9]{6}$/.test(storedSessionId)) {
      setSessionId(storedSessionId);
      setIsFreshSessionId(false);
      return;
    }
    setNewSessionId();
  }, []);

  useEffect(() => {
    if (!sessionId) {
      return;
    }
    sessionStorage.setItem("session_id", sessionId);
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) {
      return;
    }
    let cancelled = false;
    const deriveTab = (status: {
      summary_ready: boolean;
      regulations_ready: boolean;
      processes_ready: boolean;
      case_groups_ready: boolean;
      process_steps_ready: boolean;
      effort_ready: boolean;
      total_cost_ready: boolean;
    }) => {
      if (!status.summary_ready) return 0;
      if (!status.regulations_ready) return 1;
      if (!status.processes_ready) return 2;
      if (!status.case_groups_ready) return 3;
      if (!status.process_steps_ready) return 4;
      if (!status.effort_ready) return 5;
      return 6;
    };
    const syncStatus = async () => {
      try {
        const status = await apiClient.getSessionStatus(sessionId);
        if (cancelled) {
          return;
        }
        setSummaryReady(status.summary_ready);
        setRegulationsReady(status.regulations_ready);
        setProcessesReady(status.processes_ready);
        setCaseGroupsReady(status.case_groups_ready);
        setProcessStepsReady(status.process_steps_ready);
        setEffortReady(status.effort_ready);
        setTotalCostReady(status.total_cost_ready);
        const targetTab = deriveTab(status);
        setCurrentTab((prev) => (prev > targetTab ? targetTab : prev));
      } catch {
        // Best-effort sync; keep sessionStorage state if backend is unavailable.
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
  }, [sessionId]);

  useEffect(() => {
    const storedRegulation = sessionStorage.getItem("selected_regulation") || "";
    if (storedRegulation) {
      setSelectedRegulation(storedRegulation);
    }
  }, []);

  useEffect(() => {
    if (selectedModel) {
      localStorage.setItem("selected_model", selectedModel);
    } else {
      localStorage.removeItem("selected_model");
    }
  }, [selectedModel]);

  useEffect(() => {
    const storedCurrentLaw = sessionStorage.getItem("selected_current_law") || "";
    if (storedCurrentLaw) {
      setSelectedCurrentLaw(storedCurrentLaw);
    }
  }, []);

  useEffect(() => {
    if (selectedRegulation) {
      sessionStorage.setItem("selected_regulation", selectedRegulation);
    } else {
      sessionStorage.removeItem("selected_regulation");
    }
  }, [selectedRegulation]);

  useEffect(() => {
    if (selectedCurrentLaw) {
      sessionStorage.setItem("selected_current_law", selectedCurrentLaw);
    } else {
      sessionStorage.removeItem("selected_current_law");
    }
  }, [selectedCurrentLaw]);

  useEffect(() => {
    const storedSummaryReady = sessionStorage.getItem("summary_ready") === "true";
    if (storedSummaryReady) {
      setSummaryReady(true);
    }
  }, []);

  useEffect(() => {
    const storedRegulationsReady =
      sessionStorage.getItem("regulations_ready") === "true";
    if (storedRegulationsReady) {
      setRegulationsReady(true);
    }
  }, []);

  useEffect(() => {
    const storedProcessesReady =
      sessionStorage.getItem("processes_ready") === "true";
    if (storedProcessesReady) {
      setProcessesReady(true);
    }
  }, []);

  useEffect(() => {
    const storedCaseGroupsReady =
      sessionStorage.getItem("case_groups_ready") === "true";
    if (storedCaseGroupsReady) {
      setCaseGroupsReady(true);
    }
  }, []);

  useEffect(() => {
    const storedProcessStepsReady =
      sessionStorage.getItem("process_steps_ready") === "true";
    if (storedProcessStepsReady) {
      setProcessStepsReady(true);
    }
  }, []);

  useEffect(() => {
    const storedEffortReady = sessionStorage.getItem("effort_ready") === "true";
    if (storedEffortReady) {
      setEffortReady(true);
    }
  }, []);

  useEffect(() => {
    const storedTotalCostReady =
      sessionStorage.getItem("total_cost_ready") === "true";
    if (storedTotalCostReady) {
      setTotalCostReady(true);
    }
  }, []);

  useEffect(() => {
    if (summaryReady) {
      sessionStorage.setItem("summary_ready", "true");
    } else {
      sessionStorage.removeItem("summary_ready");
    }
  }, [summaryReady]);

  useEffect(() => {
    if (regulationsReady) {
      sessionStorage.setItem("regulations_ready", "true");
    } else {
      sessionStorage.removeItem("regulations_ready");
    }
  }, [regulationsReady]);

  useEffect(() => {
    if (processesReady) {
      sessionStorage.setItem("processes_ready", "true");
    } else {
      sessionStorage.removeItem("processes_ready");
    }
  }, [processesReady]);

  useEffect(() => {
    if (caseGroupsReady) {
      sessionStorage.setItem("case_groups_ready", "true");
    } else {
      sessionStorage.removeItem("case_groups_ready");
    }
  }, [caseGroupsReady]);

  useEffect(() => {
    if (processStepsReady) {
      sessionStorage.setItem("process_steps_ready", "true");
    } else {
      sessionStorage.removeItem("process_steps_ready");
    }
  }, [processStepsReady]);

  useEffect(() => {
    if (effortReady) {
      sessionStorage.setItem("effort_ready", "true");
    } else {
      sessionStorage.removeItem("effort_ready");
    }
  }, [effortReady]);

  useEffect(() => {
    if (totalCostReady) {
      sessionStorage.setItem("total_cost_ready", "true");
    } else {
      sessionStorage.removeItem("total_cost_ready");
    }
  }, [totalCostReady]);

  useEffect(() => {
    if (summaryReady && currentTab === 0) {
      setCurrentTab(1);
    }
  }, [summaryReady, currentTab]);

  useEffect(() => {
    if (regulationsReady && currentTab <= 1) {
      setCurrentTab(2);
    }
  }, [regulationsReady, currentTab]);

  useEffect(() => {
    if (processesReady && currentTab <= 2) {
      setCurrentTab(3);
    }
  }, [processesReady, currentTab]);

  useEffect(() => {
    if (caseGroupsReady && currentTab <= 3) {
      setCurrentTab(4);
    }
  }, [caseGroupsReady, currentTab]);

  useEffect(() => {
    if (processStepsReady && currentTab <= 4) {
      setCurrentTab(5);
    }
  }, [processStepsReady, currentTab]);

  useEffect(() => {
    if (effortReady && currentTab <= 5) {
      setCurrentTab(6);
    }
  }, [effortReady, currentTab]);

  useEffect(() => {
    if (!summaryReady && regulationsReady) {
      setRegulationsReady(false);
    }
  }, [summaryReady, regulationsReady]);

  useEffect(() => {
    if (!regulationsReady && processesReady) {
      setProcessesReady(false);
    }
  }, [regulationsReady, processesReady]);

  useEffect(() => {
    if (!processesReady && caseGroupsReady) {
      setCaseGroupsReady(false);
    }
  }, [processesReady, caseGroupsReady]);

  useEffect(() => {
    if (!caseGroupsReady && processStepsReady) {
      setProcessStepsReady(false);
    }
  }, [caseGroupsReady, processStepsReady]);

  useEffect(() => {
    if (!processStepsReady && effortReady) {
      setEffortReady(false);
    }
  }, [processStepsReady, effortReady]);

  useEffect(() => {
    if (!effortReady && totalCostReady) {
      setTotalCostReady(false);
    }
  }, [effortReady, totalCostReady]);

  useEffect(() => {
    if (!sessionId || !selectedModel) {
      return;
    }
    let cancelled = false;
    const syncSession = async () => {
      try {
        const { created } = await apiClient.upsertSession(sessionId, selectedModel);
        if (cancelled) {
          return;
        }
        if (created) {
          sessionIdAttempts.current = 0;
          setIsFreshSessionId(false);
          return;
        }
        if (isFreshSessionId && sessionIdAttempts.current < 5) {
          setNewSessionId();
          return;
        }
        setIsFreshSessionId(false);
      } catch {
        // Session persistence is best-effort; ignore failures for now.
      }
    };
    syncSession();
    return () => {
      cancelled = true;
    };
  }, [sessionId, selectedModel, isFreshSessionId]);

  return (
    <AppContext.Provider
      value={{
        state: {
          currentTab,
          sessionId,
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
        },
        setCurrentTab,
        setSessionId,
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
