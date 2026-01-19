"use client";

import React, { createContext, useContext, useState } from "react";
import { Model } from "@/types";

interface AppState {
  currentTab: number;
  selectedModel: string;
  availableModels: Model[];
}

interface AppContextValue {
  state: AppState;
  setCurrentTab: (tab: number) => void;
  setSelectedModel: (model: string) => void;
  setAvailableModels: (models: Model[]) => void;
}

const AppContext = createContext<AppContextValue | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [currentTab, setCurrentTab] = useState(0);
  const [selectedModel, setSelectedModel] = useState("");
  const [availableModels, setAvailableModels] = useState<Model[]>([]);

  return (
    <AppContext.Provider
      value={{
        state: { currentTab, selectedModel, availableModels },
        setCurrentTab,
        setSelectedModel,
        setAvailableModels,
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
