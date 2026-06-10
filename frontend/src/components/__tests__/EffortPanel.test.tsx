"use client";

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import EffortPanel from "@/components/EffortPanel";
import { apiClient } from "@/lib/api";
import { useApp } from "@/contexts/AppContext";

jest.mock("@/lib/api", () => ({
  apiClient: {
    startStepRun: jest.fn(),
    getStepRunStatus: jest.fn(),
    cancelStepRun: jest.fn(),
  },
  buildLlmRequestOptions: ({
    selectedModel,
    availableModels,
  }: {
    selectedModel: string;
    availableModels: Array<{ id: string; provider: string }>;
  }) => {
    const selectedModelData = availableModels.find(
      (model) => model.id === selectedModel
    );
    return {
      model: selectedModel || undefined,
      provider: selectedModelData?.provider?.toLowerCase(),
      keys: {
        openaiApiKey: localStorage.getItem("openai_api_key") || undefined,
        deepinfraApiKey: localStorage.getItem("deepinfra_api_key") || undefined,
        geminiApiKey: localStorage.getItem("gemini_api_key") || undefined,
      },
    };
  },
}));

jest.mock("@/contexts/AppContext", () => ({
  useApp: jest.fn(),
}));

const mockUseApp = useApp as jest.Mock;
const mockStartStepRun = apiClient.startStepRun as jest.Mock;
const mockGetStepRunStatus = apiClient.getStepRunStatus as jest.Mock;

const baseState = {
  currentTab: 5,
  appSessionId: "ABC123",
  selectedNormAddressee: "business",
  selectedModel: "gpt-5",
  availableModels: [
    { id: "gpt-5", name: "GPT-5", provider: "OpenAI" },
  ],
  selectedCurrentLaw: "",
  selectedRegulation: "",
  availableRegulations: [],
  summaryReady: true,
  regulationsReady: true,
  processesReady: true,
  caseGroupsReady: true,
  processStepsReady: true,
  effortReady: false,
  totalCostReady: false,
};

describe("EffortPanel", () => {
  beforeEach(() => {
    mockStartStepRun.mockReset();
    mockGetStepRunStatus.mockReset();
    localStorage.clear();
  });

  it("disables the button when process steps are not ready", () => {
    mockUseApp.mockReturnValue({
      state: { ...baseState, processStepsReady: false },
      setCurrentTab: jest.fn(),
      setEffortReady: jest.fn(),
    });

    render(<EffortPanel />);

    const button = screen.getByRole("button", { name: /Aufwand berechnen/i });
    expect(button).toBeDisabled();
  });

  it("calls the API and advances the tab on success", async () => {
    const setCurrentTab = jest.fn();
    const setEffortReady = jest.fn();
    mockUseApp.mockReturnValue({
      state: baseState,
      setCurrentTab,
      setEffortReady,
    });
    localStorage.setItem("openai_api_key", "sk-test");
    mockStartStepRun.mockResolvedValue({
      app_session_id: "ABC123",
      run_id: "run-1",
      started: true,
      status: "running",
    });
    mockGetStepRunStatus.mockResolvedValue({
      run_id: "run-1",
      app_session_id: "ABC123",
      status: "completed",
      ok: true,
      steps: [{ key: "effort", label: "Aufwand berechnen", status: "completed" }],
      final_status: { ...baseState, effort_ready: true },
    });

    render(<EffortPanel />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /Aufwand berechnen/i }));

    await waitFor(() => {
      expect(mockStartStepRun).toHaveBeenCalledTimes(1);
    });
    expect(mockStartStepRun).toHaveBeenCalledWith({
      appSessionId: "ABC123",
      stepKey: "effort",
      model: "gpt-5",
      provider: "openai",
      keys: {
        openaiApiKey: "sk-test",
        deepinfraApiKey: undefined,
        geminiApiKey: undefined,
      },
    });
    await waitFor(() => {
      expect(mockGetStepRunStatus).toHaveBeenCalledWith("run-1");
      expect(setCurrentTab).toHaveBeenCalledWith(6);
      expect(setEffortReady).toHaveBeenCalledWith(true);
    });
  });

  it("shows an error when the API fails", async () => {
    const setCurrentTab = jest.fn();
    const setEffortReady = jest.fn();
    mockUseApp.mockReturnValue({
      state: baseState,
      setCurrentTab,
      setEffortReady,
    });
    mockStartStepRun.mockRejectedValue(new Error("boom"));

    render(<EffortPanel />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /Aufwand berechnen/i }));

    expect(
      await screen.findByText("Aufwand konnte nicht gestartet werden.")
    ).toBeInTheDocument();
    expect(setCurrentTab).not.toHaveBeenCalled();
  });

  it("handles already computed effort without re-running", async () => {
    const setCurrentTab = jest.fn();
    const setEffortReady = jest.fn();
    mockUseApp.mockReturnValue({
      state: baseState,
      setCurrentTab,
      setEffortReady,
    });
    mockStartStepRun.mockResolvedValue({
      app_session_id: "ABC123",
      run_id: "run-existing",
      started: true,
      status: "running",
    });
    mockGetStepRunStatus.mockResolvedValue({
      run_id: "run-existing",
      app_session_id: "ABC123",
      status: "completed",
      ok: true,
      steps: [
        {
          key: "effort",
          label: "Aufwand berechnen",
          status: "skipped",
          message: "Step already complete",
        },
      ],
      final_status: { ...baseState, effort_ready: true },
    });

    render(<EffortPanel />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /Aufwand berechnen/i }));

    expect(
      await screen.findByText(
        "Aufwand fuer Verwaltung, Wirtschaft und Buerger berechnet.",
        {},
        { timeout: 2000 }
      )
    ).toBeInTheDocument();
    expect(mockStartStepRun).toHaveBeenCalledTimes(1);
    expect(setEffortReady).toHaveBeenCalledWith(true);
    expect(setCurrentTab).toHaveBeenCalledWith(6);
  });
});
