import { render, screen } from "@testing-library/react";

import ProcessesPanel from "@/components/ProcessesPanel";
import { useApp } from "@/contexts/AppContext";
import { emitRunAllStepCleared } from "@/lib/runAllStepEvents";

jest.mock("@/contexts/AppContext", () => ({
  useApp: jest.fn(),
}));

jest.mock("@/lib/api", () => ({
  apiClient: {
    startStepRun: jest.fn(),
    getStepRunStatus: jest.fn(),
    cancelStepRun: jest.fn(),
    cancelRunAll: jest.fn(),
  },
  buildLlmRequestOptions: jest.fn(() => ({
    model: "test-model",
    provider: "gemini",
    keys: {},
  })),
}));

const mockUseApp = useApp as jest.Mock;

describe("ProcessesPanel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    emitRunAllStepCleared();
  });

  it("shows a persisted failed Step 3 message from session status", () => {
    mockUseApp.mockReturnValue({
      state: {
        appSessionId: "PRIDJF",
        selectedNormAddressee: "administration",
        selectedModel: "gemini-3.5-flash",
        availableModels: [],
        summaryReady: true,
        regulationsReady: true,
        processesReady: false,
        caseGroupsReady: false,
        processStepsReady: false,
        effortReady: false,
        totalCostReady: false,
        lastFailedStep: "processes",
        lastFailedLabel: "Prozesse bündeln",
        lastFailedMessage: "Vorgabe 295 linked to multiple processes",
      },
      setCurrentTab: jest.fn(),
      setProcessesReady: jest.fn(),
    });

    render(<ProcessesPanel />);

    expect(
      screen.getByText("Vorgabe 295 linked to multiple processes")
    ).toBeInTheDocument();
  });
});
