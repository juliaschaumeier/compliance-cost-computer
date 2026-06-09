import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import SessionMenu from "@/components/SessionMenu";
import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";
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
  const setIsComplianceExportRunning = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
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
      setIsComplianceExportRunning,
    });
    mockRebuildTiles.mockResolvedValue({ ok: true });
    mockListSessions.mockResolvedValue({
      sessions: [
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
      screen.getByRole("button", { name: /vorblatt\/begründung exportieren/i })
    );

    await waitFor(() =>
      expect(mockDownloadComplianceTextExport).toHaveBeenCalledWith(
        expect.objectContaining({
          appSessionId: "ABC123",
          userEditPolicy: "reject_if_user_edits",
        })
      )
    );
    expect(await screen.findByText("Vorblatt/Begründung exportiert.")).toBeInTheDocument();
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
      screen.getByRole("button", { name: /vorblatt\/begründung exportieren/i })
    );
    expect(await screen.findByText("Vorblatt/Begründung exportiert.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /schließen/i }));
    await user.click(screen.getByTitle("Session Aktionen"));

    expect(screen.queryByText("Vorblatt/Begründung exportiert.")).not.toBeInTheDocument();
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
      screen.getByRole("button", { name: /vorblatt\/begründung exportieren/i })
    );

    await waitFor(() =>
      expect(downloadNames).toContain("ccc_vorblatt_begruendung_ABC123.pdf")
    );
  });

  it("offers explicit edited EA export or cancellation when compliance export detects edits", async () => {
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
    const user = await openMenu();

    await user.click(
      screen.getByRole("button", { name: /vorblatt\/begründung exportieren/i })
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
    await user.click(
      screen.getByRole("button", {
        name: /bearbeitete ea-werte verwenden/i,
      })
    );

    await waitFor(() =>
      expect(mockDownloadComplianceTextExport).toHaveBeenLastCalledWith(
        expect.objectContaining({
          userEditPolicy: "use_user_edits",
        })
      )
    );
    expect(
      await screen.findByText("Vorblatt/Begründung mit bearbeiteten EA-Werten exportiert.")
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
      screen.getByRole("button", { name: /vorblatt\/begründung exportieren/i })
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
      screen.getByRole("button", { name: /vorblatt\/begründung wird geladen/i })
    ).toBeDisabled();

    resolveExport?.(new Blob(["pdf"], { type: "application/pdf" }));
    expect(
      await screen.findByText("Vorblatt/Begründung mit bearbeiteten EA-Werten exportiert.")
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
      screen.getByRole("button", { name: /vorblatt\/begründung exportieren/i })
    );
    await user.click(await screen.findByRole("button", { name: /abbrechen/i }));

    expect(mockDownloadComplianceTextExport).toHaveBeenCalledTimes(1);
    expect(
      await screen.findByText("Vorblatt/Begründung-Export abgebrochen.")
    ).toBeInTheDocument();
  });
});
