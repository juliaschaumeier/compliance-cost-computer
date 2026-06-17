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
    downloadComplianceTextExport: jest.fn(),
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
const mockDownloadComplianceTextExport =
  apiClient.downloadComplianceTextExport as jest.Mock;
const mockStartRunAllSteps = apiClient.startRunAllSteps as jest.Mock;
const mockPrepareSessionDocuments = prepareSessionDocuments as jest.Mock;

describe("SessionMenu", () => {
  const setCurrentTab = jest.fn();
  const setAppSessionId = jest.fn();
  const setSelectedModel = jest.fn();
  const setAvailableRegulations = jest.fn();
  const setSelectedCurrentLaw = jest.fn();
  const setSelectedRegulation = jest.fn();
  const setPendingCurrentUpload = jest.fn();
  const setPendingProposedUpload = jest.fn();
  const setPendingCurrentUploadName = jest.fn();
  const setPendingProposedUploadName = jest.fn();
  const setSummaryReady = jest.fn();
  const setRegulationsReady = jest.fn();
  const setProcessesReady = jest.fn();
  const setCaseGroupsReady = jest.fn();
  const setProcessStepsReady = jest.fn();
  const setEffortReady = jest.fn();
  const setTotalCostReady = jest.fn();
  const setLastCompletedStep = jest.fn();
  const setLastCompletedLabel = jest.fn();
  const setLastFailedStep = jest.fn();
  const setLastFailedLabel = jest.fn();
  const setLastFailedMessage = jest.fn();
  const setIsComplianceExportRunning = jest.fn();
  const applySessionStatus = jest.fn();

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
        lastCompletedLabel: "Aufwand quantifizieren",
      },
      setAvailableRegulations,
      setCurrentTab,
      setAppSessionId,
      setSelectedModel,
      setSelectedCurrentLaw,
      setSelectedRegulation,
      setPendingCurrentUpload,
      setPendingProposedUpload,
      setPendingCurrentUploadName,
      setPendingProposedUploadName,
      setSummaryReady,
      setRegulationsReady,
      setProcessesReady,
      setCaseGroupsReady,
      setProcessStepsReady,
      setEffortReady,
      setTotalCostReady,
      setLastCompletedStep,
      setLastCompletedLabel,
      setLastFailedStep,
      setLastFailedLabel,
      setLastFailedMessage,
      setIsComplianceExportRunning,
      applySessionStatus,
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
          llm_model: "gemini-3.5-flash",
          used_llm_models: "gemini-3.5-flash",
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
      last_completed_label: "Aufwand quantifizieren",
    });
    mockUndoLastStep.mockResolvedValue({
      status: "ok",
      undone_step: "effort",
      undone_label: "Aufwand quantifizieren",
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
    mockDownloadComplianceTextExport.mockReset();
    mockDownloadComplianceTextExport.mockResolvedValue(
      new Blob(["pdf"], { type: "application/pdf" })
    );
    URL.createObjectURL = jest.fn(() => "blob:export");
    URL.revokeObjectURL = jest.fn();
    HTMLAnchorElement.prototype.click = jest.fn();
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
    mockGetSessionStatus.mockImplementation((appSessionId: string) =>
      Promise.resolve(
        appSessionId === "XYZ789"
          ? {
              summary_ready: true,
              regulations_ready: true,
              processes_ready: true,
              case_groups_ready: true,
              process_steps_ready: true,
              effort_ready: true,
              total_cost_ready: true,
              last_completed_step: "total_cost",
              last_completed_label: "Gesamtkosten berechnen",
            }
          : {
              summary_ready: true,
              regulations_ready: true,
              processes_ready: true,
              case_groups_ready: true,
              process_steps_ready: true,
              effort_ready: true,
              total_cost_ready: false,
              last_completed_step: "effort",
              last_completed_label: "Aufwand quantifizieren",
            }
      )
    );
    const user = await openMenu();

    await waitFor(() => expect(mockListSessions).toHaveBeenCalled());
    await user.selectOptions(screen.getByRole("combobox"), "XYZ789");

    await waitFor(() =>
      expect(mockRebuildTiles).toHaveBeenCalledWith("XYZ789", "business")
    );
    expect(setAppSessionId).toHaveBeenCalledWith("XYZ789");
    expect(setSelectedModel).toHaveBeenCalledWith("gemini-3.5-flash");
    expect(applySessionStatus).toHaveBeenCalledWith(
      expect.objectContaining({
        total_cost_ready: true,
        last_completed_step: "total_cost",
      })
    );
  });

  it("rebuilds the selected norm addressee after undo", async () => {
    const user = await openMenu();

    await user.click(
      screen.getByRole("button", {
        name: /aufwand quantifizieren/i,
      })
    );

    await waitFor(() =>
      expect(mockRebuildTiles).toHaveBeenCalledWith("ABC123", "business")
    );
    expect(mockUndoLastStep).toHaveBeenCalledWith("ABC123");
  });

  it("shows the activity conflict reason when undo is blocked by EA editing", async () => {
    const error = new Error("Conflict") as Error & {
      status?: number;
      details?: unknown;
    };
    error.status = 409;
    error.details = {
      error: "session_activity_conflict",
      active_type: "ea_edit",
      message:
        "Diese Aktion ist während einer laufenden EA-Bearbeitung in derselben Session nicht möglich. Bitte die Bearbeitung zuerst abschließen.",
    };
    mockUndoLastStep.mockRejectedValueOnce(error);
    const user = await openMenu();

    await user.click(
      screen.getByRole("button", {
        name: /aufwand quantifizieren/i,
      })
    );

    expect(
      await screen.findByText(
        /laufenden ea-bearbeitung in derselben session nicht möglich/i
      )
    ).toBeInTheDocument();
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
      setIsComplianceExportRunning,
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

  it("disables run-all when all steps are complete", async () => {
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
        effortReady: true,
        totalCostReady: true,
        lastCompletedStep: "total_cost",
        lastCompletedLabel: "Gesamtkosten berechnen",
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
      setProcessesReady,
      setCaseGroupsReady,
      setProcessStepsReady,
      setEffortReady,
      setTotalCostReady,
      setLastCompletedStep,
      setLastCompletedLabel,
      setLastFailedStep,
      setLastFailedLabel,
      setLastFailedMessage,
      setIsComplianceExportRunning,
    });
    await openMenu();

    const runAllButton = screen.getByRole("button", {
      name: /alle schritte abgeschlossen/i,
    });
    expect(runAllButton).toBeDisabled();
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
      name: /aufwand quantifizieren.*zurücksetzen/i,
    });
    expect(resetButton).toBeDisabled();

    await user.click(resetButton);

    expect(mockUndoLastStep).not.toHaveBeenCalled();
  });

  it("disables run-all while a single step run is active", async () => {
    const user = await openMenu();

    act(() => {
      emitRunAllStepStarted("effort", "step-run-1", "step", "Aufwand berechnen");
    });

    const runAllButton = screen.getByRole("button", {
      name: /verbleibende schritte ausführen/i,
    });
    expect(runAllButton).toBeDisabled();

    act(() => {
      emitRunAllStepCleared();
    });
    expect(runAllButton).not.toBeDisabled();

    await user.click(runAllButton);
    expect(apiClient.startRunAllSteps).toHaveBeenCalledTimes(1);
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
      screen.getByRole("button", { name: /verbleibende schritte ausführen/i })
    );
    const toggle = await screen.findByRole("switch");
    expect(toggle).toBeDisabled();

    await user.click(toggle);

    expect(apiClient.updateCaseGroupResearchSettings).not.toHaveBeenCalled();
  });

  it("loads a selected session immediately and closes the menu", async () => {
    const user = await openMenu();

    await waitFor(() => expect(mockListSessions).toHaveBeenCalled());
    const select = screen.getByRole("combobox");
    expect(select).toHaveValue("ABC123");

    await user.selectOptions(select, "XYZ789");

    await waitFor(() =>
      expect(mockGetSessionStatus).toHaveBeenCalledWith("XYZ789")
    );
    await waitFor(() =>
      expect(mockRebuildTiles).toHaveBeenCalledWith("XYZ789", "business")
    );
    expect(setAppSessionId).toHaveBeenCalledWith("XYZ789");
    expect(
      screen.queryByRole("button", { name: "Session Aktionsmenü schließen" })
    ).not.toBeInTheDocument();

    await user.click(screen.getByTitle("Session Aktionen"));
    await screen.findByText("Session Aktionen");
    expect(screen.getByRole("combobox")).toHaveValue("ABC123");
  });

  it("does not commit a session switch when rebuilding tiles fails", async () => {
    mockGetSessionStatus.mockImplementation((appSessionId: string) =>
      Promise.resolve(
        appSessionId === "XYZ789"
          ? {
              summary_ready: true,
              regulations_ready: true,
              processes_ready: true,
              case_groups_ready: true,
              process_steps_ready: true,
              effort_ready: true,
              total_cost_ready: true,
              last_completed_step: "total_cost",
              last_completed_label: "Gesamtkosten berechnen",
            }
          : {
              summary_ready: true,
              regulations_ready: true,
              processes_ready: true,
              case_groups_ready: true,
              process_steps_ready: true,
              effort_ready: true,
              total_cost_ready: false,
              last_completed_step: "effort",
              last_completed_label: "Aufwand quantifizieren",
            }
      )
    );
    mockRebuildTiles.mockRejectedValueOnce(new Error("tile rebuild failed"));
    const user = await openMenu();

    await waitFor(() => expect(mockListSessions).toHaveBeenCalled());
    await user.selectOptions(screen.getByRole("combobox"), "XYZ789");

    await waitFor(() =>
      expect(mockRebuildTiles).toHaveBeenCalledWith("XYZ789", "business")
    );
    expect(setAppSessionId).not.toHaveBeenCalledWith("XYZ789");
    expect(applySessionStatus).not.toHaveBeenCalledWith(
      expect.objectContaining({ total_cost_ready: true })
    );
    expect(screen.getByRole("combobox")).toHaveValue("ABC123");
    expect(
      await screen.findByText("Session konnte nicht geladen werden.")
    ).toBeInTheDocument();
  });

  it("sends only one cancellation request when run-all cancel is clicked repeatedly", async () => {
    const user = await openMenu();

    await user.click(
      screen.getByRole("button", { name: /verbleibende schritte ausführen/i })
    );
    const cancelButton = await screen.findByRole("button", {
      name: /"schritte" abbrechen/i,
    });
    fireEvent.click(cancelButton);
    fireEvent.click(cancelButton);
    await screen.findByRole("button", {
      name: /abbruch wird ausgeführt/i,
    });

    expect(apiClient.cancelRunAll).toHaveBeenCalledTimes(1);
    expect(apiClient.cancelRunAll).toHaveBeenCalledWith("run-123");
  });

  it("shows the current run-all step name in the cancel button", async () => {
    const listeners: Record<string, EventListener> = {};
    (global as typeof globalThis & { EventSource: jest.Mock }).EventSource = jest
      .fn()
      .mockImplementation(() => ({
        addEventListener: jest.fn((eventName: string, listener: EventListener) => {
          listeners[eventName] = listener;
        }),
        close: jest.fn(),
      }));
    const user = await openMenu();

    await user.click(
      screen.getByRole("button", { name: /verbleibende schritte ausführen/i })
    );

    await waitFor(() => expect(listeners.step_started).toBeDefined());
    act(() => {
      listeners.step_started(
        new MessageEvent("step_started", {
          data: JSON.stringify({
            key: "process_steps",
            label: "Prozessschritte bestimmen",
          }),
        })
      );
    });

    expect(
      screen.getByRole("button", {
        name: /"prozessschritte bestimmen" abbrechen/i,
      })
    ).toBeInTheDocument();
  });

  it("downloads the compliance text export from the export section", async () => {
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
        effortReady: true,
        totalCostReady: true,
        lastCompletedStep: "total_cost",
        lastCompletedLabel: "Gesamtkosten berechnen",
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
      setIsComplianceExportRunning,
    });
    const user = await openMenu();

    await user.click(
      screen.getByRole("button", { name: /vorblatt und begründung exportieren/i })
    );

    await waitFor(() =>
      expect(mockDownloadComplianceTextExport).toHaveBeenCalledWith(
        expect.objectContaining({
          appSessionId: "ABC123",
          userEditPolicy: "reject_if_user_edits",
        })
      )
    );
    expect(await screen.findByText("Vorblatt und Begründung exportiert.")).toBeInTheDocument();
    expect(setIsComplianceExportRunning).toHaveBeenCalledWith(true);
    expect(setIsComplianceExportRunning).toHaveBeenCalledWith(false);
  });

  it("clears transient export status when the session menu is reopened", async () => {
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
        effortReady: true,
        totalCostReady: true,
        lastCompletedStep: "total_cost",
        lastCompletedLabel: "Gesamtkosten berechnen",
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
      setIsComplianceExportRunning,
    });
    const user = await openMenu();

    await user.click(
      screen.getByRole("button", { name: /vorblatt und begründung exportieren/i })
    );
    expect(await screen.findByText("Vorblatt und Begründung exportiert.")).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Session Aktionsmenü schließen" })
    );
    await user.click(screen.getByTitle("Session Aktionen"));

    expect(screen.queryByText("Vorblatt und Begründung exportiert.")).not.toBeInTheDocument();
  });

  it("uses the session id captured at export start for the compliance filename", async () => {
    const downloadNames: string[] = [];
    const originalCreateElement = document.createElement.bind(document);
    jest.spyOn(document, "createElement").mockImplementation((tagName) => {
      const element = originalCreateElement(tagName);
      if (tagName.toLowerCase() === "a") {
        Object.defineProperty(element, "download", {
          configurable: true,
          get: () => downloadNames[downloadNames.length - 1] || "",
          set: (value: string) => {
            downloadNames.push(value);
          },
        });
      }
      return element;
    });
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
        effortReady: true,
        totalCostReady: true,
        lastCompletedStep: "total_cost",
        lastCompletedLabel: "Gesamtkosten berechnen",
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
      setIsComplianceExportRunning,
    });
    const user = await openMenu();

    await user.click(
      screen.getByRole("button", { name: /vorblatt und begründung exportieren/i })
    );

    await waitFor(() =>
      expect(downloadNames).toContain("ccc_vorblatt_begruendung_ABC123.pdf")
    );
  });

  it("clears the edited EA export choice on session change and exports the new session", async () => {
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
        effortReady: true,
        totalCostReady: true,
        lastCompletedStep: "total_cost",
        lastCompletedLabel: "Gesamtkosten berechnen",
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
      setIsComplianceExportRunning,
    });
    mockDownloadComplianceTextExport
      .mockRejectedValueOnce({
        status: 409,
        details: { error: "user_edits_present" },
      })
      .mockResolvedValueOnce(new Blob(["pdf"], { type: "application/pdf" }));
    const user = userEvent.setup();
    const { rerender } = render(<SessionMenu />);
    await user.click(screen.getByTitle("Session Aktionen"));
    await screen.findByText("Session Aktionen");

    await user.click(
      screen.getByRole("button", { name: /vorblatt und begründung exportieren/i })
    );
    expect(
      await screen.findByText("Bearbeitete EA-Werte vorhanden.")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/der export verwendet immer den aktuell sichtbaren ea-stand/i)
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: /ursprüngliche generierte werte verwenden/i,
      })
    ).not.toBeInTheDocument();
    mockUseApp.mockReturnValue({
      state: {
        appSessionId: "XYZ789",
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
        effortReady: true,
        totalCostReady: true,
        lastCompletedStep: "total_cost",
        lastCompletedLabel: "Gesamtkosten berechnen",
      },
      setAvailableRegulations,
      setCurrentTab,
      setAppSessionId,
      setSelectedModel,
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
      setIsComplianceExportRunning,
      applySessionStatus,
    });
    rerender(<SessionMenu />);
    expect(screen.queryByText("Bearbeitete EA-Werte vorhanden.")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: /bearbeitete ea-werte verwenden/i,
      })
    ).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /vorblatt und begründung exportieren/i })
    );

    await waitFor(() =>
      expect(mockDownloadComplianceTextExport).toHaveBeenLastCalledWith(
        expect.objectContaining({
          appSessionId: "XYZ789",
          userEditPolicy: "reject_if_user_edits",
        })
      )
    );
    expect(
      await screen.findByText("Vorblatt und Begründung exportiert.")
    ).toBeInTheDocument();
  });

  it("clears the compliance export choice warning while generating the selected variant", async () => {
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
        effortReady: true,
        totalCostReady: true,
        lastCompletedStep: "total_cost",
        lastCompletedLabel: "Gesamtkosten berechnen",
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
      setIsComplianceExportRunning,
    });
    let resolveExport: ((value: Blob) => void) | null = null;
    mockDownloadComplianceTextExport
      .mockRejectedValueOnce({
        status: 409,
        details: { error: "user_edits_present" },
      })
      .mockImplementationOnce(
        () =>
          new Promise<Blob>((resolve) => {
            resolveExport = resolve;
          })
      );
    const user = await openMenu();

    await user.click(
      screen.getByRole("button", { name: /vorblatt und begründung exportieren/i })
    );
    expect(
      await screen.findByText("Es gibt bearbeitete EA-Werte. Bitte Exportvariante auswählen.")
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", {
        name: /bearbeitete ea-werte verwenden/i,
      })
    );

    expect(
      screen.queryByText("Es gibt bearbeitete EA-Werte. Bitte Exportvariante auswählen.")
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /vorblatt und begründung werden geladen/i })
    ).toBeDisabled();

    resolveExport?.(new Blob(["pdf"], { type: "application/pdf" }));
    expect(
      await screen.findByText("Vorblatt und Begründung mit bearbeiteten EA-Werten exportiert.")
    ).toBeInTheDocument();
  });

  it("cancels the compliance text export choice without downloading a second file", async () => {
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
        effortReady: true,
        totalCostReady: true,
        lastCompletedStep: "total_cost",
        lastCompletedLabel: "Gesamtkosten berechnen",
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
      setIsComplianceExportRunning,
    });
    mockDownloadComplianceTextExport.mockRejectedValueOnce({
      status: 409,
      details: { error: "user_edits_present" },
    });
    const user = await openMenu();

    await user.click(
      screen.getByRole("button", { name: /vorblatt und begründung exportieren/i })
    );
    await user.click(await screen.findByRole("button", { name: /abbrechen/i }));

    expect(mockDownloadComplianceTextExport).toHaveBeenCalledTimes(1);
    expect(
      await screen.findByText("Export von Vorblatt und Begründung abgebrochen.")
    ).toBeInTheDocument();
  });
});
