import { ApiClientError, apiClient, buildLlmRequestOptions } from "@/lib/api";
import { formatActionErrorMessage, logClientError } from "@/lib/errorFeedback";
import type { Model } from "@/types";

type UploadTarget = "current" | "proposed";

type PendingUpload = {
  file: File | null;
  desiredName: string;
};

type PrepareSessionDocumentsOptions = {
  appSessionId: string;
  selectedModel: string;
  availableModels: Model[];
  availableRegulations: string[];
  selectedCurrentLaw: string;
  selectedRegulation: string;
  pendingCurrent: PendingUpload;
  pendingProposed: PendingUpload;
  setSelectedCurrentLaw: (law: string) => void;
  setSelectedRegulation: (regulation: string) => void;
  setPendingCurrentUpload: (file: File | null) => void;
  setPendingProposedUpload: (file: File | null) => void;
  setPendingCurrentUploadName: (name: string) => void;
  setPendingProposedUploadName: (name: string) => void;
  setAvailableRegulations: (regulations: string[]) => void;
};

export type PrepareSessionDocumentsResult = {
  currentFilename?: string;
  proposedFilename: string;
  llm: ReturnType<typeof buildLlmRequestOptions>;
};

function _normalizedDesiredName(upload: PendingUpload): string {
  return (upload.desiredName || upload.file?.name || "").trim();
}

function _isUnresolvedConflict(
  upload: PendingUpload,
  availableRegulations: string[]
): boolean {
  if (!upload.file) {
    return false;
  }
  const desiredName = _normalizedDesiredName(upload);
  return Boolean(desiredName) && availableRegulations.includes(desiredName);
}

async function _uploadIfNeeded(
  target: UploadTarget,
  upload: PendingUpload,
  availableRegulations: string[],
  onSelected: (filename: string) => void,
  clearPendingFile: () => void,
  clearPendingName: () => void
): Promise<string | null> {
  if (!upload.file) {
    return null;
  }
  const desiredName = _normalizedDesiredName(upload);
  if (!desiredName) {
    throw new Error("Bitte einen Dateinamen angeben.");
  }
  if (_isUnresolvedConflict(upload, availableRegulations)) {
    throw new Error(
      target === "current"
        ? "Bitte Namenskonflikt fuer das geltende Gesetz zuerst im Upload-Bereich aufloesen."
        : "Bitte Namenskonflikt fuer den Gesetzesvorschlag zuerst im Upload-Bereich aufloesen."
    );
  }
  try {
    const response = await apiClient.uploadRegulation(
      upload.file,
      desiredName !== upload.file.name ? desiredName : undefined
    );
    onSelected(response.filename);
    clearPendingFile();
    clearPendingName();
    return response.filename;
  } catch (error) {
    const err = error as ApiClientError;
    const details =
      err.details && typeof err.details === "object"
        ? (err.details as { error?: unknown; filename?: unknown })
        : null;
    if (
      err.status === 409 &&
      details?.error === "exists" &&
      typeof details.filename === "string"
    ) {
      throw new Error(
        `Bitte Namenskonflikt im Upload-Bereich aufloesen: ${details.filename}`
      );
    }
    throw error;
  }
}

export async function prepareSessionDocuments(
  options: PrepareSessionDocumentsOptions
): Promise<PrepareSessionDocumentsResult> {
  if (!options.selectedModel) {
    throw new Error("Bitte zuerst ein Modell auswählen.");
  }

  const llm = buildLlmRequestOptions({
    selectedModel: options.selectedModel,
    availableModels: options.availableModels,
  });

  const uploadedCurrentFilename = await _uploadIfNeeded(
      "current",
      options.pendingCurrent,
      options.availableRegulations,
      options.setSelectedCurrentLaw,
      () => options.setPendingCurrentUpload(null),
      () => options.setPendingCurrentUploadName("")
    );
  const currentFilename =
    uploadedCurrentFilename || options.selectedCurrentLaw || undefined;

  const uploadedProposedFilename = await _uploadIfNeeded(
      "proposed",
      options.pendingProposed,
      options.availableRegulations,
      options.setSelectedRegulation,
      () => options.setPendingProposedUpload(null),
      () => options.setPendingProposedUploadName("")
    );
  const proposedFilename = uploadedProposedFilename || options.selectedRegulation;

  if (!proposedFilename) {
    throw new Error("Bitte zuerst einen Gesetzesvorschlag auswählen.");
  }

  if (uploadedCurrentFilename || uploadedProposedFilename) {
    const refreshed = await apiClient.fetchRegulations();
    options.setAvailableRegulations(refreshed.files);
  }

  return {
    currentFilename,
    proposedFilename,
    llm,
  };
}

type StartSummaryOptions = PrepareSessionDocumentsOptions & {
  setSummaryReady: (ready: boolean) => void;
  setRegulationsReady: (ready: boolean) => void;
  setProcessesReady: (ready: boolean) => void;
  setCurrentTab: (tab: number) => void;
};

export async function prepareSessionDocumentsAndStartSummary(
  options: StartSummaryOptions
): Promise<void> {
  const { currentFilename, proposedFilename, llm } = await prepareSessionDocuments(options);
  options.setSummaryReady(false);
  await apiClient.summarizeRegulation(proposedFilename, {
    currentFilename,
    appSessionId: options.appSessionId,
    model: llm.model,
    provider: llm.provider,
    keys: llm.keys,
  });
  window.dispatchEvent(new Event("tiles-updated"));
  options.setSummaryReady(true);
  options.setRegulationsReady(false);
  options.setProcessesReady(false);
  options.setCurrentTab(1);
}

export function formatSessionStartError(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return formatActionErrorMessage("Schritte konnten nicht vorbereitet werden", error);
}

export function logSessionStartError(
  scope: string,
  error: unknown,
  context: Record<string, unknown>
): void {
  logClientError(scope, error, context);
}
