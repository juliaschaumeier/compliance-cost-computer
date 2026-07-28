import {
  formatSessionStartError,
  prepareSessionDocuments,
  prepareSessionDocumentsAndStartSummary,
} from "@/lib/sessionStart";
import { apiClient } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  apiClient: {
    uploadRegulation: jest.fn(),
    fetchRegulations: jest.fn(),
    summarizeRegulation: jest.fn(),
  },
  buildLlmRequestOptions: jest.fn(() => ({
    model: "gpt-5.4",
    provider: "openai",
    keys: { openaiApiKey: "key" },
  })),
}));

jest.mock("@/lib/errorFeedback", () => ({
  AUTH_EXPIRED_MESSAGE:
    "Ihre Anmeldung ist abgelaufen. Bitte melden Sie sich erneut an.",
  formatActionErrorMessage: jest.fn(() => "formatted"),
  isUnauthorizedApiError: jest.fn((error: unknown) => {
    return (error as { status?: unknown })?.status === 401;
  }),
  logClientError: jest.fn(),
}));

const mockUploadRegulation = apiClient.uploadRegulation as jest.Mock;
const mockFetchRegulations = apiClient.fetchRegulations as jest.Mock;
const mockSummarizeRegulation = apiClient.summarizeRegulation as jest.Mock;

function createOptions(overrides: Partial<Parameters<typeof prepareSessionDocuments>[0]> = {}) {
  return {
    appSessionId: "ABC123",
    selectedModel: "gpt-5.4",
    availableModels: [],
    availableRegulations: [],
    selectedCurrentLaw: "",
    selectedRegulation: "",
    pendingCurrent: { file: null, desiredName: "" },
    pendingProposed: { file: null, desiredName: "" },
    setSelectedCurrentLaw: jest.fn(),
    setSelectedRegulation: jest.fn(),
    setPendingCurrentUpload: jest.fn(),
    setPendingProposedUpload: jest.fn(),
    setPendingCurrentUploadName: jest.fn(),
    setPendingProposedUploadName: jest.fn(),
    setAvailableRegulations: jest.fn(),
    ...overrides,
  };
}

describe("sessionStart", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetchRegulations.mockResolvedValue({ files: ["uploaded-current.txt", "uploaded-proposed.txt"] });
    mockSummarizeRegulation.mockResolvedValue({ ok: true });
  });

  it("uploads pending current and proposed files before returning filenames", async () => {
    mockUploadRegulation
      .mockResolvedValueOnce({ filename: "uploaded-current.txt" })
      .mockResolvedValueOnce({ filename: "uploaded-proposed.txt" });

    const options = createOptions({
      availableRegulations: ["existing.txt"],
      pendingCurrent: {
        file: new File(["current"], "current.txt", { type: "text/plain" }),
        desiredName: "uploaded-current.txt",
      },
      pendingProposed: {
        file: new File(["proposed"], "proposed.txt", { type: "text/plain" }),
        desiredName: "uploaded-proposed.txt",
      },
    });

    const result = await prepareSessionDocuments(options);

    expect(mockUploadRegulation).toHaveBeenNthCalledWith(
      1,
      expect.any(File),
      "uploaded-current.txt"
    );
    expect(mockUploadRegulation).toHaveBeenNthCalledWith(
      2,
      expect.any(File),
      "uploaded-proposed.txt"
    );
    expect(mockFetchRegulations).toHaveBeenCalledTimes(1);
    expect(result).toEqual({
      currentFilename: "uploaded-current.txt",
      proposedFilename: "uploaded-proposed.txt",
      llm: {
        model: "gpt-5.4",
        provider: "openai",
        keys: { openaiApiKey: "key" },
      },
    });
    expect(options.setSelectedCurrentLaw).toHaveBeenCalledWith("uploaded-current.txt");
    expect(options.setSelectedRegulation).toHaveBeenCalledWith("uploaded-proposed.txt");
  });

  it("returns proposed-only selections without uploading or refetching", async () => {
    const options = createOptions({
      selectedRegulation: "existing-proposed.txt",
    });

    const result = await prepareSessionDocuments(options);

    expect(result.currentFilename).toBeUndefined();
    expect(result.proposedFilename).toBe("existing-proposed.txt");
    expect(mockUploadRegulation).not.toHaveBeenCalled();
    expect(mockFetchRegulations).not.toHaveBeenCalled();
  });

  it("rejects when only a current law is selected", async () => {
    const options = createOptions({
      selectedCurrentLaw: "current-only.txt",
    });

    await expect(prepareSessionDocuments(options)).rejects.toThrow(
      "Bitte zuerst einen Gesetzesvorschlag auswählen."
    );
    expect(mockUploadRegulation).not.toHaveBeenCalled();
  });

  it("rejects when no law file is selected", async () => {
    await expect(prepareSessionDocuments(createOptions())).rejects.toThrow(
      "Bitte zuerst einen Gesetzesvorschlag auswählen."
    );
  });

  it("rejects unresolved upload conflicts before calling the API", async () => {
    const options = createOptions({
      availableRegulations: ["conflict.txt"],
      pendingProposed: {
        file: new File(["proposed"], "proposed.txt", { type: "text/plain" }),
        desiredName: "conflict.txt",
      },
    });

    await expect(prepareSessionDocuments(options)).rejects.toThrow(
      "Bitte Namenskonflikt fuer den Gesetzesvorschlag zuerst im Upload-Bereich aufloesen."
    );
    expect(mockUploadRegulation).not.toHaveBeenCalled();
  });

  it("formats expired login errors clearly", () => {
    const message = formatSessionStartError(
      Object.assign(new Error("Not authenticated"), { status: 401 })
    );

    expect(message).toBe(
      "Ihre Anmeldung ist abgelaufen. Bitte melden Sie sich erneut an."
    );
  });

  it("starts summary after preparing session documents", async () => {
    mockUploadRegulation.mockResolvedValueOnce({ filename: "uploaded-proposed.txt" });

    const options = {
      ...createOptions({
        pendingProposed: {
          file: new File(["proposed"], "proposed.txt", { type: "text/plain" }),
          desiredName: "uploaded-proposed.txt",
        },
      }),
      setSummaryReady: jest.fn(),
      setRegulationsReady: jest.fn(),
      setProcessesReady: jest.fn(),
      setCurrentTab: jest.fn(),
    };

    await prepareSessionDocumentsAndStartSummary(options);

    expect(mockSummarizeRegulation).toHaveBeenCalledWith("uploaded-proposed.txt", {
      currentFilename: undefined,
      appSessionId: "ABC123",
      model: "gpt-5.4",
      provider: "openai",
      keys: { openaiApiKey: "key" },
    });
    expect(options.setSummaryReady).toHaveBeenCalledWith(true);
    expect(options.setCurrentTab).toHaveBeenCalledWith(1);
  });
});
