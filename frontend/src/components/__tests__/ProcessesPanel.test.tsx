import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ProcessesPanel from "@/components/ProcessesPanel";
import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";
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
const mockStartStepRun = apiClient.startStepRun as jest.Mock;
const mockGetStepRunStatus = apiClient.getStepRunStatus as jest.Mock;

describe("ProcessesPanel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    emitRunAllStepCleared();
    mockStartStepRun.mockResolvedValue({
      run_id: "run-processes",
      started: true,
      status: "running",
    });
    mockGetStepRunStatus.mockReturnValue(new Promise(() => undefined));
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

  it("hides a persisted failed Step 3 message while Step 3 is running again", async () => {
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
        lastFailedMessage: "Der Schritt wurde abgebrochen. Bitte führen Sie ihn erneut aus.",
      },
      setCurrentTab: jest.fn(),
      setProcessesReady: jest.fn(),
    });
    const user = userEvent.setup();
    render(<ProcessesPanel />);

    expect(screen.getByText(/der schritt wurde abgebrochen/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /ausführen/i }));

    await waitFor(() => expect(mockStartStepRun).toHaveBeenCalled());
    expect(screen.queryByText(/der schritt wurde abgebrochen/i)).not.toBeInTheDocument();
  });
});
