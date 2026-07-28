import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import EffortPanel from "@/components/EffortPanel";
import { apiClient } from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import {
  emitRunAllStepCleared,
  emitRunAllStepStarted,
} from "@/lib/runAllStepEvents";

jest.mock("@/lib/api", () => ({
  apiClient: {
    startStepRun: jest.fn(),
    getStepRunStatus: jest.fn(),
    cancelStepRun: jest.fn(),
    cancelRunAll: jest.fn(),
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
const mockCancelStepRun = apiClient.cancelStepRun as jest.Mock;
const mockCancelRunAll = apiClient.cancelRunAll as jest.Mock;

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
  const baseActions = {
    setCurrentTab: jest.fn(),
    setEffortReady: jest.fn(),
    setLastFailedStep: jest.fn(),
    setLastFailedLabel: jest.fn(),
    setLastFailedMessage: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockStartStepRun.mockReset();
    mockGetStepRunStatus.mockReset();
    mockCancelStepRun.mockReset();
    mockCancelRunAll.mockReset();
    emitRunAllStepCleared();
    localStorage.clear();
  });

  it("disables the button when process steps are not ready", () => {
    mockUseApp.mockReturnValue({
      state: { ...baseState, processStepsReady: false },
      ...baseActions,
    });

    render(<EffortPanel />);

    const button = screen.getByRole("button", { name: /Ausführen/i });
    expect(button).toBeDisabled();
  });

  it("calls the API and advances the tab on success", async () => {
    const setCurrentTab = jest.fn();
    const setEffortReady = jest.fn();
    mockUseApp.mockReturnValue({
      state: baseState,
      ...baseActions,
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
      steps: [{ key: "effort", label: "Aufwand quantifizieren", status: "completed" }],
      final_status: { ...baseState, effort_ready: true },
    });

    render(<EffortPanel />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /Ausführen/i }));

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
      ...baseActions,
      setCurrentTab,
      setEffortReady,
    });
    mockStartStepRun.mockRejectedValue(new Error("boom"));

    render(<EffortPanel />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /Ausführen/i }));

    expect(
      await screen.findByText("Aufwand konnte nicht gestartet werden.")
    ).toBeInTheDocument();
    expect(setCurrentTab).not.toHaveBeenCalled();
  });

  it("shows a login-expired message when step start returns 401", async () => {
    const setCurrentTab = jest.fn();
    const setEffortReady = jest.fn();
    mockUseApp.mockReturnValue({
      state: baseState,
      ...baseActions,
      setCurrentTab,
      setEffortReady,
    });
    mockStartStepRun.mockRejectedValue(
      Object.assign(new Error("Not authenticated"), { status: 401 })
    );

    render(<EffortPanel />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /Ausführen/i }));

    expect(
      await screen.findByText(
        "Ihre Anmeldung ist abgelaufen. Bitte melden Sie sich erneut an."
      )
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Aufwand konnte nicht gestartet werden.")
    ).not.toBeInTheDocument();
    expect(setCurrentTab).not.toHaveBeenCalled();
  });

  it("shows a login-expired message when step status polling returns 401", async () => {
    const setCurrentTab = jest.fn();
    const setEffortReady = jest.fn();
    mockUseApp.mockReturnValue({
      state: baseState,
      ...baseActions,
      setCurrentTab,
      setEffortReady,
    });
    mockStartStepRun.mockResolvedValue({
      app_session_id: "ABC123",
      run_id: "run-401",
      started: true,
      status: "running",
    });
    mockGetStepRunStatus.mockRejectedValue(
      Object.assign(new Error("Not authenticated"), { status: 401 })
    );

    render(<EffortPanel />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /Ausführen/i }));

    expect(
      await screen.findByText(
        "Ihre Anmeldung ist abgelaufen. Bitte melden Sie sich erneut an."
      )
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Status konnte nicht aktualisiert werden.")
    ).not.toBeInTheDocument();
    expect(setCurrentTab).not.toHaveBeenCalled();
  });

  it("handles already computed effort without re-running", async () => {
    const setCurrentTab = jest.fn();
    const setEffortReady = jest.fn();
    mockUseApp.mockReturnValue({
      state: baseState,
      ...baseActions,
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
          label: "Aufwand quantifizieren",
          status: "skipped",
          message: "Step already complete",
        },
      ],
      final_status: { ...baseState, effort_ready: true },
    });

    const { rerender } = render(<EffortPanel />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /Ausführen/i }));

    expect(
      await screen.findByText(
        "Aufwand für Verwaltung, Wirtschaft und Bürger berechnet.",
        {},
        { timeout: 2000 }
      )
    ).toBeInTheDocument();
    expect(mockStartStepRun).toHaveBeenCalledTimes(1);
    expect(setEffortReady).toHaveBeenCalledWith(true);
    expect(setCurrentTab).toHaveBeenCalledWith(6);

    mockUseApp.mockReturnValue({
      state: { ...baseState, effortReady: true },
      ...baseActions,
      setCurrentTab,
      setEffortReady,
    });
    rerender(<EffortPanel />);

    mockUseApp.mockReturnValue({
      state: { ...baseState, effortReady: false },
      ...baseActions,
      setCurrentTab,
      setEffortReady,
    });
    rerender(<EffortPanel />);

    await waitFor(() =>
      expect(
        screen.queryByText("Aufwand für Verwaltung, Wirtschaft und Bürger berechnet.")
      ).not.toBeInTheDocument()
    );
  });

  it("cancels the active run-all when run-all is executing effort", async () => {
    mockUseApp.mockReturnValue({
      state: baseState,
      ...baseActions,
    });
    mockCancelRunAll.mockResolvedValue({
      run_id: "run-all-1",
      app_session_id: "ABC123",
      status: "cancelling",
      accepted: true,
      message: "Cancellation requested",
    });

    render(<EffortPanel />);
    act(() => {
      emitRunAllStepStarted("effort", "run-all-1");
    });
    const user = userEvent.setup();

    const button = screen.getByRole("button", { name: /abbrechen/i });
    expect(button).not.toBeDisabled();
    await user.click(button);

    expect(mockCancelRunAll).toHaveBeenCalledWith("run-all-1");
    expect(apiClient.cancelStepRun).not.toHaveBeenCalled();
    expect(await screen.findByText("Abbruch angefordert...")).toBeInTheDocument();

    act(() => {
      emitRunAllStepCleared();
    });

    await waitFor(() =>
      expect(screen.queryByText("Abbruch angefordert...")).not.toBeInTheDocument()
    );
  });

  it("does not send duplicate run-all cancel requests after cancellation starts", async () => {
    mockUseApp.mockReturnValue({
      state: baseState,
      ...baseActions,
    });
    mockCancelRunAll.mockResolvedValue({
      run_id: "run-all-1",
      app_session_id: "ABC123",
      status: "cancelling",
      accepted: true,
      message: "Cancellation requested",
    });

    render(<EffortPanel />);
    act(() => {
      emitRunAllStepStarted("effort", "run-all-1");
    });

    const button = screen.getByRole("button", { name: /abbrechen/i });
    fireEvent.click(button);
    fireEvent.click(button);
    await screen.findByText("Abbruch angefordert...");

    expect(mockCancelRunAll).toHaveBeenCalledTimes(1);
    expect(mockCancelStepRun).not.toHaveBeenCalled();
  });

  it("cancels a manual effort run via the step-run endpoint, not run-all", async () => {
    mockUseApp.mockReturnValue({
      state: baseState,
      ...baseActions,
    });
    mockStartStepRun.mockResolvedValue({
      app_session_id: "ABC123",
      run_id: "manual-run-1",
      started: true,
      status: "running",
    });
    mockGetStepRunStatus.mockResolvedValue({
      run_id: "manual-run-1",
      app_session_id: "ABC123",
      status: "running",
      ok: null,
      current_label: "Aufwand quantifizieren",
      steps: [{ key: "effort", label: "Aufwand quantifizieren", status: "running" }],
    });
    mockCancelStepRun.mockResolvedValue({
      run_id: "manual-run-1",
      app_session_id: "ABC123",
      status: "cancelling",
      accepted: true,
      message: "Cancellation requested",
    });

    render(<EffortPanel />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /Ausführen/i }));
    const cancelButton = await screen.findByRole("button", { name: /abbrechen/i });
    await user.click(cancelButton);

    expect(mockCancelStepRun).toHaveBeenCalledWith("manual-run-1");
    expect(mockCancelRunAll).not.toHaveBeenCalled();
  });
});
