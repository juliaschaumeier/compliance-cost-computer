"use client";

import { useApp } from "@/contexts/AppContext";
import RegulationsPanel from "@/components/RegulationsPanel";
import ProcessesPanel from "@/components/ProcessesPanel";
import CaseGroupsPanel from "@/components/CaseGroupsPanel";
import ProcessStepsPanel from "@/components/ProcessStepsPanel";
import EffortPanel from "@/components/EffortPanel";
import TotalCostPanel from "@/components/TotalCostPanel";

export default function TabPanels() {
  const { state } = useApp();

  if (state.currentTab === 0) {
    // Step 1 preparation lives in the sticky AppShell region.
    return null;
  }

  if (state.currentTab === 1) {
    return <RegulationsPanel />;
  }

  if (state.currentTab === 2) {
    return <ProcessesPanel />;
  }

  if (state.currentTab === 3) {
    return <CaseGroupsPanel />;
  }

  if (state.currentTab === 4) {
    return <ProcessStepsPanel />;
  }

  if (state.currentTab === 5) {
    return <EffortPanel />;
  }

  if (state.currentTab === 6) {
    return <TotalCostPanel />;
  }

  return null;
}
