"use client";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import userEvent from "@testing-library/user-event";

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
    importLegisLlmExport: jest.fn(),
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
const mockImportLegisLlmExport = apiClient.importLegisLlmExport as jest.Mock;
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
    mockImportLegisLlmExport.mockResolvedValue({
      ok: true,
      created: true,
      current_filename: "gueltig_import_20260811_abcd1234.legisllm",
      proposed_filename: "vorschlag_import_20260811_abcd1234.legisllm",
      current_document_id: 1,
      proposed_document_id: 2,
      message: "LegisLLM-Export importiert. Gültige Fassung und Vorschlag sind ausgewählt.",
    });
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

  it("imports a LegisLLM export and selects both generated laws", async () => {
    const app = createAppValue();
    mockUseApp.mockReturnValue(app);
    mockFetchRegulations
      .mockResolvedValueOnce({ files: [] })
      .mockResolvedValueOnce({
        files: [
          "gueltig_import_20260811_abcd1234.legisllm",
          "vorschlag_import_20260811_abcd1234.legisllm",
        ],
      });

    render(<UploadPanel />);

    await waitFor(() => expect(mockFetchRegulations).toHaveBeenCalled());
    const dropZone = screen.getByTestId("legisllm-drop-zone");
    const file = new File(['{"schritte":{}}'], "export.json", {
      type: "application/json",
    });

    fireEvent.drop(dropZone, {
      dataTransfer: {
        files: [file],
      },
    });
    await waitFor(() => expect(mockImportLegisLlmExport).toHaveBeenCalledWith(file));
    await waitFor(() =>
      expect(app.setAvailableRegulations).toHaveBeenCalledWith([
        "gueltig_import_20260811_abcd1234.legisllm",
        "vorschlag_import_20260811_abcd1234.legisllm",
      ])
    );
    expect(app.setSelectedCurrentLaw).toHaveBeenCalledWith(
      "gueltig_import_20260811_abcd1234.legisllm"
    );
    expect(app.setSelectedRegulation).toHaveBeenCalledWith(
      "vorschlag_import_20260811_abcd1234.legisllm"
    );
    await waitFor(() =>
      expect(screen.getByText(/legisllm-export importiert/i)).toBeInTheDocument()
    );
  });

  it.each(["drop", "picker"])("shows LegisLLM import errors from %s", async (source) => {
    const app = createAppValue({
      selectedCurrentLaw: "current.txt",
      selectedRegulation: "proposed.txt",
    });
    mockUseApp.mockReturnValue(app);
    mockFetchRegulations.mockResolvedValueOnce({
      files: ["current.txt", "proposed.txt"],
    });
    mockImportLegisLlmExport.mockRejectedValueOnce(new Error("Import kaputt"));

    render(<UploadPanel />);

    await waitFor(() => expect(mockFetchRegulations).toHaveBeenCalled());
    const dropZone = screen.getByTestId("legisllm-drop-zone");
    const file = new File(["not-json"], "export.json", { type: "application/json" });
    if (source === "drop") {
      fireEvent.drop(dropZone, { dataTransfer: { files: [file] } });
    } else {
      fireEvent.change(screen.getByLabelText("LegisLLM: JSON-Datei"), { target: { files: [file] } });
    }

    await waitFor(() =>
      expect(screen.getByText("Fehler")).toBeInTheDocument()
    );
    expect(app.setSelectedCurrentLaw).not.toHaveBeenCalled();
    expect(app.setSelectedRegulation).not.toHaveBeenCalled();
    expect(app.setSummaryReady).not.toHaveBeenCalled();
  });

  it.each([
    ["current", "Gültiges Gesetz", "setPendingCurrentUpload", "setPendingCurrentUploadName", "setSelectedCurrentLaw"],
    ["proposed", "Gesetzesvorschlag", "setPendingProposedUpload", "setPendingProposedUploadName", "setSelectedRegulation"],
  ] as const)("stages %s files from picker and drop without starting execution", async (target, label, fileSetter, nameSetter, selectedSetter) => {
    const app = createAppValue();
    mockUseApp.mockReturnValue(app);
    render(<UploadPanel />);
    await waitFor(() => expect(mockFetchRegulations).toHaveBeenCalled());
    const input = screen.getByLabelText(`${label}: lokale Datei`) as HTMLInputElement;
    const click = jest.spyOn(input, "click");
    fireEvent.click(screen.getByRole("button", { name: `${label} vom Computer auswählen` }));
    expect(click).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: `${label}: bereits hochgeladene Datei auswählen` })).toHaveAttribute("aria-expanded", "false");
    const file = new File(["law"], "law.txt", { type: "text/plain" });
    await userEvent.setup().upload(input, file);
    expect(app[fileSetter]).toHaveBeenLastCalledWith(file);
    expect(app[nameSetter]).toHaveBeenLastCalledWith("law.txt");
    expect(app[selectedSetter]).toHaveBeenLastCalledWith("");
    expect(input.value).toBe("");
    await userEvent.setup().upload(input, file);
    expect(app[fileSetter]).toHaveBeenCalledTimes(2);
    fireEvent.drop(screen.getByTestId(`${target}-law-drop-zone`), { dataTransfer: { files: [file] } });
    expect(app[fileSetter]).toHaveBeenCalledTimes(3);
    fireEvent.change(input, { target: { files: [] } });
    expect(app[fileSetter]).toHaveBeenCalledTimes(3);
    expect(mockPrepareSessionDocuments).not.toHaveBeenCalled();
    expect(apiClient.startStepRun).not.toHaveBeenCalled();
    expect(mockImportLegisLlmExport).not.toHaveBeenCalled();
  });

  it("keeps a selected file while changing it and lets stored content replace it", async () => {
    const app = createAppValue({
      pendingProposedUpload: new File(["law"], "local.txt"),
      pendingProposedUploadName: "local.txt",
      availableRegulations: ["stored.txt"],
    });
    mockUseApp.mockReturnValue(app);
    mockFetchRegulations.mockResolvedValue({ files: ["stored.txt"] });
    render(<UploadPanel />);
    await waitFor(() => expect(mockFetchRegulations).toHaveBeenCalled());
    expect(screen.getByText("Wird beim Start hochgeladen")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Gesetzesvorschlag: Auswahl ändern" }));
    fireEvent.change(screen.getByLabelText("Gesetzesvorschlag: lokale Datei"), { target: { files: [] } });
    expect(app.setPendingProposedUpload).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("proposed-law-drop-zone"));
    const storedButton = screen.getByRole("button", { name: "Gesetzesvorschlag: bereits hochgeladene Datei auswählen" });
    expect(storedButton).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(storedButton);
    expect(storedButton).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(screen.getByRole("button", { name: "stored.txt" }));
    expect(app.setSelectedRegulation).toHaveBeenCalledWith("stored.txt");
    expect(app.setPendingProposedUpload).toHaveBeenCalledWith(null);
    expect(app.setPendingProposedUploadName).toHaveBeenCalledWith("");
  });

  it("shows stored selection status and clears only its target", async () => {
    const app = createAppValue({ selectedRegulation: "stored.txt" });
    mockUseApp.mockReturnValue(app);
    mockFetchRegulations.mockResolvedValue({ files: ["stored.txt"] });
    render(<UploadPanel />);
    await waitFor(() => expect(mockFetchRegulations).toHaveBeenCalled());
    expect(screen.getByText("Bereits hochgeladen")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Gesetzesvorschlag: Auswahl entfernen" }));
    expect(app.setSelectedRegulation).toHaveBeenCalledWith("");
    expect(app.setPendingProposedUpload).toHaveBeenCalledWith(null);
    expect(app.setSelectedCurrentLaw).not.toHaveBeenCalled();
  });

  it("opens the JSON picker and imports immediately through the existing API", async () => {
    const app = createAppValue();
    mockUseApp.mockReturnValue(app);
    render(<UploadPanel />);
    await waitFor(() => expect(mockFetchRegulations).toHaveBeenCalled());
    const input = screen.getByLabelText("LegisLLM: JSON-Datei") as HTMLInputElement;
    const click = jest.spyOn(input, "click");
    fireEvent.click(screen.getByRole("button", { name: "LegisLLM-JSON vom Computer auswählen" }));
    expect(click).toHaveBeenCalledTimes(1);
    expect(input).toHaveAttribute("accept", ".json,application/json");
    fireEvent.change(input, { target: { files: [] } });
    expect(mockImportLegisLlmExport).not.toHaveBeenCalled();
    expect(app.setSummaryReady).not.toHaveBeenCalled();
    const file = new File(["{}"], "export.json", { type: "application/json" });
    await userEvent.setup().upload(input, file);
    await waitFor(() => expect(app.setSelectedCurrentLaw).toHaveBeenCalledWith("gueltig_import_20260811_abcd1234.legisllm"));
    expect(app.setSelectedRegulation).toHaveBeenCalledWith("vorschlag_import_20260811_abcd1234.legisllm");
    expect(app.setPendingCurrentUpload).toHaveBeenCalledWith(null);
    expect(app.setPendingProposedUpload).toHaveBeenCalledWith(null);
    expect(input.value).toBe("");
    await userEvent.setup().upload(input, file);
    await waitFor(() => expect(mockImportLegisLlmExport).toHaveBeenCalledTimes(2));
    expect(apiClient.startStepRun).not.toHaveBeenCalled();
  });

  it("blocks overlapping JSON imports and law selection while importing", async () => {
    let finish!: (value: unknown) => void;
    mockImportLegisLlmExport.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
    const app = createAppValue();
    mockUseApp.mockReturnValue(app);
    render(<UploadPanel />);
    await waitFor(() => expect(mockFetchRegulations).toHaveBeenCalled());
    const file = new File(["{}"], "export.json", { type: "application/json" });
    fireEvent.drop(screen.getByTestId("legisllm-drop-zone"), { dataTransfer: { files: [file] } });
    fireEvent.drop(screen.getByTestId("legisllm-drop-zone"), { dataTransfer: { files: [file] } });
    expect(mockImportLegisLlmExport).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "LegisLLM-JSON vom Computer auswählen" })).toBeDisabled();
    fireEvent.drop(screen.getByTestId("proposed-law-drop-zone"), { dataTransfer: { files: [file] } });
    expect(app.setPendingProposedUpload).not.toHaveBeenCalled();
    finish({ current_filename: "current.txt", proposed_filename: "proposed.txt", message: "Imported" });
    await waitFor(() => expect(screen.getByText("Imported")).toBeInTheDocument());
  });

  it("keeps conflict reuse and rename available after selection", async () => {
    const app = createAppValue({
      availableRegulations: ["existing.txt"],
      pendingProposedUpload: new File(["law"], "existing.txt"),
      pendingProposedUploadName: "existing.txt",
    });
    mockUseApp.mockReturnValue(app);
    render(<UploadPanel />);
    await waitFor(() => expect(mockFetchRegulations).toHaveBeenCalled());
    fireEvent.change(screen.getByLabelText("Gesetzesvorschlag: neuer Dateiname"), { target: { value: "renamed.txt" } });
    expect(app.setPendingProposedUploadName).toHaveBeenCalledWith("renamed.txt");
    fireEvent.click(screen.getByRole("button", { name: "Vorhandene Datei verwenden" }));
    expect(app.setSelectedRegulation).toHaveBeenCalledWith("existing.txt");
    expect(app.setPendingProposedUpload).toHaveBeenCalledWith(null);
  });

  it("passes staged picker documents into shared preparation before manual start", async () => {
    const file = new File(["law"], "local.txt");
    mockUseApp.mockReturnValue(createAppValue({ pendingProposedUpload: file, pendingProposedUploadName: "local.txt" }));
    (apiClient.startStepRun as jest.Mock).mockResolvedValueOnce({ run_id: "manual-1" });
    (apiClient.getStepRunStatus as jest.Mock).mockResolvedValueOnce({ status: "completed", steps: [], ok: true });
    render(<UploadPanel />);
    await waitFor(() => expect(mockFetchRegulations).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: "CCC starten" }));
    await waitFor(() => expect(apiClient.startStepRun).toHaveBeenCalled());
    expect(mockPrepareSessionDocuments).toHaveBeenCalledWith(expect.objectContaining({ pendingProposed: { file, desiredName: "local.txt" } }));
    expect(apiClient.startStepRun).toHaveBeenCalledWith(expect.objectContaining({ stepKey: "summary", proposedFilename: "proposed.txt" }));
  });

});
