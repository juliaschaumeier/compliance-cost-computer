import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ProcessesPanel from "@/components/ProcessesPanel";
import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";
import { emitRunAllStepCleared, emitRunAllStepStarted } from "@/lib/runAllStepEvents";

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
  const baseContextActions = {
    setCurrentTab: jest.fn(),
    setProcessesReady: jest.fn(),
    setLastFailedStep: jest.fn(),
    setLastFailedLabel: jest.fn(),
    setLastFailedMessage: jest.fn(),
  };

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
      ...baseContextActions,
    });

    render(<ProcessesPanel />);

    expect(
      screen.getByText("Vorgabe 295 linked to multiple processes")
    ).toBeInTheDocument();
  });

  it("hides a persisted failed Step 3 message while Step 3 is running again", async () => {
    const actions = {
      ...baseContextActions,
      setLastFailedStep: jest.fn(),
      setLastFailedLabel: jest.fn(),
      setLastFailedMessage: jest.fn(),
    };
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
      ...actions,
    });
    const user = userEvent.setup();
    render(<ProcessesPanel />);

    expect(screen.getByText(/der schritt wurde abgebrochen/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /ausführen/i }));

    expect(actions.setLastFailedStep).toHaveBeenCalledWith(null);
    expect(actions.setLastFailedLabel).toHaveBeenCalledWith(null);
    expect(actions.setLastFailedMessage).toHaveBeenCalledWith(null);
    await waitFor(() => expect(mockStartStepRun).toHaveBeenCalled());
    expect(screen.queryByText(/der schritt wurde abgebrochen/i)).not.toBeInTheDocument();
  });

  it("hides a persisted failed Step 3 message while run-all is retrying Step 3", async () => {
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
      ...baseContextActions,
    });
    render(<ProcessesPanel />);

    expect(screen.getByText(/der schritt wurde abgebrochen/i)).toBeInTheDocument();

    act(() => {
      emitRunAllStepStarted("processes", "run-all-1", "run_all", "Prozesse bündeln");
    });

    expect(screen.queryByText(/der schritt wurde abgebrochen/i)).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /abbrechen/i })
    ).toBeInTheDocument();
  });
});
