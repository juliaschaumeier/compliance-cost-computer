"use client";

import { render, screen, waitFor } from "@testing-library/react";

import UploadPanel from "@/components/UploadPanel";
import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";
import { useActiveWorkflowRun } from "@/lib/runAllStepEvents";
import { prepareSessionDocuments } from "@/lib/sessionStart";

jest.mock("@/contexts/AppContext", () => ({
  useApp: jest.fn(),
}));

jest.mock("@/lib/api", () => ({
  apiClient: {
    fetchRegulations: jest.fn(),
    startStepRun: jest.fn(),
    getStepRunStatus: jest.fn(),
    cancelStepRun: jest.fn(),
    cancelRunAll: jest.fn(),
  },
  buildLlmRequestOptions: () => ({
    model: "gpt-5.4",
    provider: "openai",
    keys: {},
  }),
}));

jest.mock("@/lib/sessionStart", () => ({
  prepareSessionDocuments: jest.fn(),
  formatSessionStartError: jest.fn(() => "Fehler"),
  logSessionStartError: jest.fn(),
}));

jest.mock("@/lib/runAllStepEvents", () => ({
  useActiveWorkflowRun: jest.fn(() => ({
    isActive: false,
    stepKey: null,
    runId: null,
    runKind: null,
    label: null,
  })),
}));

const mockUseApp = useApp as jest.Mock;
const mockFetchRegulations = apiClient.fetchRegulations as jest.Mock;
const mockPrepareSessionDocuments = prepareSessionDocuments as jest.Mock;
const mockUseActiveWorkflowRun = useActiveWorkflowRun as jest.Mock;

function createAppValue(overrides: Record<string, unknown> = {}) {
  return {
    state: {
      appSessionId: "ABC123",
      selectedModel: "gpt-5.4",
      availableModels: [],
      availableRegulations: [],
      selectedCurrentLaw: "",
      selectedRegulation: "",
      pendingCurrentUpload: null,
      pendingProposedUpload: null,
      pendingCurrentUploadName: "",
      pendingProposedUploadName: "",
      ...overrides,
    },
    setAvailableRegulations: jest.fn(),
    setCurrentTab: jest.fn(),
    setSelectedCurrentLaw: jest.fn(),
    setSelectedRegulation: jest.fn(),
    setPendingCurrentUpload: jest.fn(),
    setPendingProposedUpload: jest.fn(),
    setPendingCurrentUploadName: jest.fn(),
    setPendingProposedUploadName: jest.fn(),
    setProcessesReady: jest.fn(),
    setRegulationsReady: jest.fn(),
    setSummaryReady: jest.fn(),
    setLastFailedStep: jest.fn(),
    setLastFailedLabel: jest.fn(),
    setLastFailedMessage: jest.fn(),
  };
}

describe("UploadPanel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetchRegulations.mockResolvedValue({ files: [] });
    mockPrepareSessionDocuments.mockResolvedValue({
      proposedFilename: "proposed.txt",
      llm: { model: "gpt-5.4", provider: "openai", keys: {} },
    });
    mockUseActiveWorkflowRun.mockReturnValue({
      isActive: false,
      stepKey: null,
      runId: null,
      runKind: null,
      label: null,
    });
    mockUseApp.mockReturnValue(createAppValue());
  });

  it("disables CCC starten when no file is selected", async () => {
    render(<UploadPanel />);

    await waitFor(() => expect(mockFetchRegulations).toHaveBeenCalled());
    expect(screen.getByRole("button", { name: /ccc starten/i })).toBeDisabled();
  });

  it("disables CCC starten when only a current law is selected", async () => {
    mockUseApp.mockReturnValue(
      createAppValue({
        selectedCurrentLaw: "current.txt",
      })
    );

    render(<UploadPanel />);

    await waitFor(() => expect(mockFetchRegulations).toHaveBeenCalled());
    expect(screen.getByRole("button", { name: /ccc starten/i })).toBeDisabled();
  });

  it("enables CCC starten when only a proposed law is selected", async () => {
    mockUseApp.mockReturnValue(
      createAppValue({
        selectedRegulation: "proposed.txt",
      })
    );

    render(<UploadPanel />);

    await waitFor(() => expect(mockFetchRegulations).toHaveBeenCalled());
    expect(screen.getByRole("button", { name: /ccc starten/i })).toBeEnabled();
  });

  it("enables CCC starten when current and proposed law are selected", async () => {
    mockUseApp.mockReturnValue(
      createAppValue({
        selectedCurrentLaw: "current.txt",
        selectedRegulation: "proposed.txt",
      })
    );

    render(<UploadPanel />);

    await waitFor(() => expect(mockFetchRegulations).toHaveBeenCalled());
    expect(screen.getByRole("button", { name: /ccc starten/i })).toBeEnabled();
  });

  it("hides upload controls while run-all is starting CCC", async () => {
    mockUseApp.mockReturnValue(
      createAppValue({
        selectedCurrentLaw: "current.txt",
        selectedRegulation: "proposed.txt",
      })
    );
    mockUseActiveWorkflowRun.mockReturnValue({
      isActive: true,
      stepKey: "summary",
      runId: "run-all-1",
      runKind: "run_all",
      label: "CCC starten",
    });

    render(<UploadPanel />);

    await waitFor(() => expect(mockFetchRegulations).toHaveBeenCalled());
    expect(screen.getByRole("button", { name: /abbrechen/i })).toBeEnabled();
    const uploadGrid = screen.getByTestId("law-selection-grid");
    expect(uploadGrid).toHaveClass("hidden");
  });

  it("clears selected laws that are no longer visible to the current user", async () => {
    const app = createAppValue({
      selectedCurrentLaw: "legacy-current.txt",
      selectedRegulation: "legacy-proposed.txt",
    });
    mockUseApp.mockReturnValue(app);
    mockFetchRegulations.mockResolvedValue({ files: ["shared-proposed.txt"] });

    render(<UploadPanel />);

    await waitFor(() => expect(mockFetchRegulations).toHaveBeenCalled());
    expect(app.setAvailableRegulations).toHaveBeenCalledWith([
      "shared-proposed.txt",
    ]);
    expect(app.setSelectedCurrentLaw).toHaveBeenCalledWith("");
    expect(app.setSelectedRegulation).toHaveBeenCalledWith("");
  });

  it("disables CCC starten while a proposed upload conflict is unresolved", async () => {
    mockUseApp.mockReturnValue(
      createAppValue({
        availableRegulations: ["conflict.txt"],
        pendingProposedUpload: new File(["x"], "proposed.txt", { type: "text/plain" }),
        pendingProposedUploadName: "conflict.txt",
      })
    );

    render(<UploadPanel />);

    await waitFor(() => expect(mockFetchRegulations).toHaveBeenCalled());
    expect(screen.getByRole("button", { name: /ccc starten/i })).toBeDisabled();
    expect(screen.getByText(/datei existiert bereits/i)).toBeInTheDocument();
  });
});
