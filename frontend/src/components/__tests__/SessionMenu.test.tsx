import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import SessionMenu from "@/components/SessionMenu";
import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";
import {
  emitRunAllStepCleared,
  emitRunAllStepStarted,
} from "@/lib/runAllStepEvents";
import { prepareSessionDocuments } from "@/lib/sessionStart";

jest.mock("@/contexts/AppContext", () => ({
  useApp: jest.fn(),
}));

jest.mock("@/lib/api", () => ({
  apiClient: {
    rebuildTiles: jest.fn(),
    listSessions: jest.fn(),
    getSessionStatus: jest.fn(),
    undoLastStep: jest.fn(),
    exportSession: jest.fn(),
    getCaseGroupResearchSettings: jest.fn(),
    updateCaseGroupResearchSettings: jest.fn(),
    downloadDeepResearchReport: jest.fn(),
    startRunAllSteps: jest.fn(),
    cancelRunAll: jest.fn(),
    getRunAllStatus: jest.fn(),
    getRunAllEventsUrl: jest.fn(() => "/events"),
  },
  buildLlmRequestOptions: jest.fn(() => ({
    model: undefined,
    provider: undefined,
    keys: {},
  })),
}));

jest.mock("@/lib/sessionStart", () => ({
  prepareSessionDocuments: jest.fn(),
  formatSessionStartError: jest.fn(() => "Fehler"),
  logSessionStartError: jest.fn(),
}));

const mockUseApp = useApp as jest.Mock;
const mockRebuildTiles = apiClient.rebuildTiles as jest.Mock;
const mockListSessions = apiClient.listSessions as jest.Mock;
const mockGetSessionStatus = apiClient.getSessionStatus as jest.Mock;
const mockUndoLastStep = apiClient.undoLastStep as jest.Mock;
const mockGetCaseGroupResearchSettings =
  apiClient.getCaseGroupResearchSettings as jest.Mock;
const mockStartRunAllSteps = apiClient.startRunAllSteps as jest.Mock;
const mockPrepareSessionDocuments = prepareSessionDocuments as jest.Mock;

describe("SessionMenu", () => {
  const setCurrentTab = jest.fn();
  const setAppSessionId = jest.fn();
  const setAvailableRegulations = jest.fn();
  const setSelectedCurrentLaw = jest.fn();
  const setSelectedRegulation = jest.fn();
  const setPendingCurrentUpload = jest.fn();
  const setPendingProposedUpload = jest.fn();
  const setPendingCurrentUploadName = jest.fn();
  const setPendingProposedUploadName = jest.fn();
  const setSummaryReady = jest.fn();
  const setRegulationsReady = jest.fn();
  const setLastCompletedStep = jest.fn();
  const setLastCompletedLabel = jest.fn();
  const setLastFailedStep = jest.fn();
  const setLastFailedLabel = jest.fn();
  const setLastFailedMessage = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    emitRunAllStepCleared();
    mockUseApp.mockReturnValue({
      state: {
        appSessionId: "ABC123",
        selectedNormAddressee: "business",
        selectedModel: "gpt-5.4",
        availableModels: [],
        selectedCurrentLaw: "",
        selectedRegulation: "",
        availableRegulations: [],
        pendingCurrentUpload: null,
        pendingProposedUpload: null,
        pendingCurrentUploadName: "",
        pendingProposedUploadName: "",
        summaryReady: true,
        regulationsReady: true,
        processesReady: true,
        caseGroupsReady: true,
        processStepsReady: true,
        effortReady: false,
        totalCostReady: false,
        lastCompletedStep: "effort",
        lastCompletedLabel: "Aufwand berechnen",
      },
      setAvailableRegulations,
      setCurrentTab,
      setAppSessionId,
      setSelectedCurrentLaw,
      setSelectedRegulation,
      setPendingCurrentUpload,
      setPendingProposedUpload,
      setPendingCurrentUploadName,
      setPendingProposedUploadName,
      setSummaryReady,
      setRegulationsReady,
      setLastCompletedStep,
      setLastCompletedLabel,
      setLastFailedStep,
      setLastFailedLabel,
      setLastFailedMessage,
    });
    mockRebuildTiles.mockResolvedValue({ ok: true });
    mockListSessions.mockResolvedValue({
      sessions: [
        {
          app_session_id: "ABC123",
          created_at: "2026-04-14T08:00:00Z",
          llm_model: "gpt-5.4",
          used_llm_models: "gpt-5.4",
        },
        {
          app_session_id: "XYZ789",
          created_at: "2026-04-14T09:00:00Z",
          llm_model: "gpt-5.4",
          used_llm_models: "gpt-5.4",
        },
      ],
    });
    mockGetSessionStatus.mockResolvedValue({
      summary_ready: true,
      regulations_ready: true,
      processes_ready: true,
      case_groups_ready: true,
      process_steps_ready: true,
      effort_ready: true,
      total_cost_ready: false,
      last_completed_step: "effort",
      last_completed_label: "Aufwand berechnen",
    });
    mockUndoLastStep.mockResolvedValue({
      status: "ok",
      undone_step: "effort",
      undone_label: "Aufwand berechnen",
    });
    mockGetCaseGroupResearchSettings.mockResolvedValue({
      app_session_id: "ABC123",
      enabled: true,
      status: "idle",
      locked: false,
      elapsed_seconds: null,
    });
    mockStartRunAllSteps.mockResolvedValue({
      run_id: "run-123",
      started: true,
      status: "running",
    });
    mockPrepareSessionDocuments.mockResolvedValue({
      currentFilename: undefined,
      proposedFilename: "prepared-proposed.txt",
      llm: {
        model: "gpt-5.4",
        provider: "openai",
        keys: { openaiApiKey: "key" },
      },
    });
    (global as typeof globalThis & { EventSource: jest.Mock }).EventSource = jest
      .fn()
      .mockImplementation(() => ({
        addEventListener: jest.fn(),
        close: jest.fn(),
      }));
  });

  async function openMenu() {
    const user = userEvent.setup();
    render(<SessionMenu />);
    await user.click(screen.getByTitle("Session Aktionen"));
    await screen.findByText("Session Aktionen");
    return user;
  }

  it("rebuilds the selected norm addressee after loading another session", async () => {
    const user = await openMenu();

    await waitFor(() => expect(mockListSessions).toHaveBeenCalled());
    await user.selectOptions(screen.getByRole("combobox"), "XYZ789");
    await user.click(screen.getByRole("button", { name: /wechseln/i }));

    await waitFor(() =>
      expect(mockRebuildTiles).toHaveBeenCalledWith("XYZ789", "business")
    );
    expect(setAppSessionId).toHaveBeenCalledWith("XYZ789");
  });

  it("rebuilds the selected norm addressee after undo", async () => {
    const user = await openMenu();

    await user.click(
      screen.getByRole("button", {
        name: /aufwand berechnen/i,
      })
    );

    await waitFor(() =>
      expect(mockRebuildTiles).toHaveBeenCalledWith("ABC123", "business")
    );
    expect(mockUndoLastStep).toHaveBeenCalledWith("ABC123");
  });

  it("prepares pending uploads before starting run-all", async () => {
    mockUseApp.mockReturnValue({
      state: {
        appSessionId: "ABC123",
        selectedNormAddressee: "business",
        selectedModel: "gpt-5.4",
        availableModels: [],
        selectedCurrentLaw: "",
        selectedRegulation: "",
        availableRegulations: [],
        pendingCurrentUpload: null,
        pendingProposedUpload: new File(["p"], "proposal.txt", {
          type: "text/plain",
        }),
        pendingCurrentUploadName: "",
        pendingProposedUploadName: "proposal.txt",
        summaryReady: false,
        regulationsReady: false,
        processesReady: false,
        caseGroupsReady: false,
        processStepsReady: false,
        effortReady: false,
        totalCostReady: false,
        lastCompletedStep: null,
        lastCompletedLabel: null,
      },
      setAvailableRegulations,
      setCurrentTab,
      setAppSessionId,
      setSelectedCurrentLaw,
      setSelectedRegulation,
      setPendingCurrentUpload,
      setPendingProposedUpload,
      setPendingCurrentUploadName,
      setPendingProposedUploadName,
      setSummaryReady,
      setRegulationsReady,
      setLastCompletedStep,
      setLastCompletedLabel,
      setLastFailedStep,
      setLastFailedLabel,
      setLastFailedMessage,
    });

    const user = await openMenu();

    await user.click(
      screen.getByRole("button", { name: /alle schritte ausführen/i })
    );

    await waitFor(() =>
      expect(mockPrepareSessionDocuments).toHaveBeenCalledWith(
        expect.objectContaining({
          appSessionId: "ABC123",
          pendingProposed: expect.objectContaining({
            desiredName: "proposal.txt",
          }),
        })
      )
    );
    await waitFor(() =>
      expect(mockStartRunAllSteps).toHaveBeenCalledWith({
        appSessionId: "ABC123",
        currentFilename: undefined,
        proposedFilename: "prepared-proposed.txt",
        model: "gpt-5.4",
        provider: "openai",
        keys: { openaiApiKey: "key" },
      })
    );
  });

  it("shows elapsed Deep Research runtime while running", async () => {
    mockGetCaseGroupResearchSettings.mockResolvedValue({
      app_session_id: "ABC123",
      enabled: true,
      status: "running",
      locked: true,
      elapsed_seconds: 125,
    });

    await openMenu();

    expect(
      await screen.findByText(/Status: running · läuft seit 2:05 min/i)
    ).toBeInTheDocument();
  });

  it("disables reset while a workflow run is active", async () => {
    const user = await openMenu();

    act(() => {
      emitRunAllStepStarted("regulations", "run-1", "run_all");
    });

    const resetButton = screen.getByRole("button", {
      name: /aufwand berechnen.*zurücksetzen/i,
    });
    expect(resetButton).toBeDisabled();

    await user.click(resetButton);

    expect(mockUndoLastStep).not.toHaveBeenCalled();
  });

  it("re-enables the Deep Research toggle after a pre-effort run is cleared", async () => {
    const user = await openMenu();
    const toggle = await screen.findByRole("switch");

    act(() => {
      emitRunAllStepStarted("regulations", "run-1", "run_all");
    });
    expect(toggle).toBeDisabled();

    act(() => {
      emitRunAllStepCleared();
    });
    expect(toggle).not.toBeDisabled();

    await user.click(toggle);

    expect(apiClient.updateCaseGroupResearchSettings).toHaveBeenCalledWith(
      "ABC123",
      false
    );
  });

  it("does not toggle Deep Research while run-all is being prepared", async () => {
    const user = await openMenu();

    await user.click(
      screen.getByRole("button", { name: /alle schritte ausführen/i })
    );
    const toggle = await screen.findByRole("switch");
    expect(toggle).toBeDisabled();

    await user.click(toggle);

    expect(apiClient.updateCaseGroupResearchSettings).not.toHaveBeenCalled();
  });

  it("does not load a selected session when the modal is closed before Wechseln", async () => {
    const user = await openMenu();

    await waitFor(() => expect(mockListSessions).toHaveBeenCalled());
    const select = screen.getByRole("combobox");
    expect(select).toHaveValue("ABC123");

    await user.selectOptions(select, "XYZ789");
    expect(select).toHaveValue("XYZ789");
    await user.click(screen.getByRole("button", { name: /schließen/i }));

    expect(mockGetSessionStatus).not.toHaveBeenCalledWith("XYZ789");
    expect(mockRebuildTiles).not.toHaveBeenCalledWith("XYZ789", "business");
    expect(setAppSessionId).not.toHaveBeenCalledWith("XYZ789");

    await user.click(screen.getByTitle("Session Aktionen"));
    await screen.findByText("Session Aktionen");
    expect(screen.getByRole("combobox")).toHaveValue("ABC123");
  });

  it("sends only one cancellation request when run-all cancel is clicked repeatedly", async () => {
    const user = await openMenu();

    await user.click(
      screen.getByRole("button", { name: /alle schritte ausführen/i })
    );
    const cancelButton = await screen.findByRole("button", {
      name: /ausführung abbrechen/i,
    });
    fireEvent.click(cancelButton);
    fireEvent.click(cancelButton);
    await screen.findByRole("button", {
      name: /abbruch wird ausgeführt/i,
    });

    expect(apiClient.cancelRunAll).toHaveBeenCalledTimes(1);
    expect(apiClient.cancelRunAll).toHaveBeenCalledWith("run-123");
  });
});
