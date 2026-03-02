import {
  OrganizedModelsResponse,
  RegulationsResponse,
  Tile,
  TilesResponse,
  ProzesseResponse,
  VorgabenResponse,
  FallgruppenResponse,
  ProzessschritteResponse,
  EffortCalculationResponse,
  TotalCostResponse,
  SessionsResponse,
  SessionStatus,
  UndoStepResponse,
  RunAllStartResponse,
  RunAllStatusResponse,
  RunAllCancelResponse,
  Model,
} from "@/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:5000";

export type ApiKeys = {
  openaiApiKey?: string;
  deepinfraApiKey?: string;
  geminiApiKey?: string;
};

export type ApiClientError = Error & {
  status?: number;
  details?: unknown;
  raw?: string;
};

export type LlmRequestOptions = {
  model?: string;
  provider?: string;
  keys: ApiKeys;
};

type LlmRequestOptionsInput = {
  selectedModel: string;
  availableModels: Model[];
  storage?: Pick<Storage, "getItem"> | null;
};

export function buildLlmRequestOptions({
  selectedModel,
  availableModels,
  storage,
}: LlmRequestOptionsInput): LlmRequestOptions {
  const selectedModelData = availableModels.find((model) => model.id === selectedModel);
  const activeStorage =
    storage !== undefined ? storage : typeof window !== "undefined" ? window.localStorage : null;

  return {
    model: selectedModel || undefined,
    provider: selectedModelData?.provider?.toLowerCase(),
    keys: {
      openaiApiKey: activeStorage?.getItem("openai_api_key") || undefined,
      deepinfraApiKey: activeStorage?.getItem("deepinfra_api_key") || undefined,
      geminiApiKey: activeStorage?.getItem("gemini_api_key") || undefined,
    },
  };
}

function buildKeyHeaders(keys: ApiKeys) {
  const headers: Record<string, string> = {};
  if (keys.openaiApiKey) {
    headers["x-openai-key"] = keys.openaiApiKey;
  }
  if (keys.deepinfraApiKey) {
    headers["x-deepinfra-key"] = keys.deepinfraApiKey;
  }
  if (keys.geminiApiKey) {
    headers["x-gemini-key"] = keys.geminiApiKey;
  }
  return headers;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function createApiClientError(
  message: string,
  extras?: Pick<ApiClientError, "status" | "details" | "raw">
): ApiClientError {
  const error = new Error(message) as ApiClientError;
  if (extras) {
    error.status = extras.status;
    error.details = extras.details;
    error.raw = extras.raw;
  }
  return error;
}

async function parseErrorPayload(response: Response): Promise<{
  detail: unknown;
  errorBody: unknown;
  rawText: string;
}> {
  let errorBody: unknown = null;
  let rawText = "";
  try {
    rawText = await response.text();
    errorBody = rawText ? JSON.parse(rawText) : null;
  } catch {
    errorBody = null;
  }
  return {
    detail: isRecord(errorBody) ? errorBody.detail : undefined,
    errorBody,
    rawText,
  };
}

function resolveDetailMessage(detail: unknown, rawText: string): string | null {
  return (typeof detail === "string" ? detail : null) || rawText || null;
}

function extractDetailError(detail: unknown): string | null {
  if (!isRecord(detail)) {
    return null;
  }
  return typeof detail.error === "string" ? detail.error : null;
}

type ApiErrorOptions = {
  includeStatusLabel?: boolean;
  prefixWithFallback?: boolean;
  preferDetailErrorField?: boolean;
};

async function throwApiClientErrorFromResponse(
  response: Response,
  fallbackMessage: string,
  options: ApiErrorOptions = {}
): Promise<never> {
  const { detail, errorBody, rawText } = await parseErrorPayload(response);
  const detailMessage =
    (options.preferDetailErrorField ? extractDetailError(detail) : null) ||
    resolveDetailMessage(detail, rawText);

  const statusLabel = `${response.status} ${response.statusText}`.trim();
  const baseMessage = options.includeStatusLabel
    ? `${fallbackMessage} (${statusLabel})`
    : fallbackMessage;
  const message = options.prefixWithFallback
    ? detailMessage
      ? `${baseMessage}: ${detailMessage}`
      : baseMessage
    : detailMessage || baseMessage;

  throw createApiClientError(message, {
    status: response.status,
    details: detail ?? errorBody ?? rawText,
    raw: rawText,
  });
}

export const apiClient = {
  async upsertSession(
    appSessionId: string,
    llmModel: string
  ): Promise<{ app_session_id: string; created: boolean }> {
    const response = await fetch(`${API_BASE_URL}/sessions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: appSessionId,
        llm_model: llmModel,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to upsert session");
    }
    return response.json();
  },
  async fetchOrganizedModels(keys: ApiKeys): Promise<OrganizedModelsResponse> {
    const response = await fetch(`${API_BASE_URL}/models/organized`, {
      headers: buildKeyHeaders(keys),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(
        response,
        "Failed to load organized models"
      );
    }
    return response.json();
  },

  async fetchTiles(appSessionId: string): Promise<TilesResponse> {
    const query = `?app_session_id=${encodeURIComponent(appSessionId)}`;
    const response = await fetch(`${API_BASE_URL}/tiles${query}`);
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load tiles");
    }
    return response.json();
  },

  async upsertTile(tile: Tile, appSessionId: string): Promise<Tile> {
    const query = `?app_session_id=${encodeURIComponent(appSessionId)}`;
    const response = await fetch(`${API_BASE_URL}/tiles${query}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(tile),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to save tile");
    }
    return response.json();
  },

  async deleteTile(tileId: string, appSessionId: string): Promise<void> {
    const query = `?app_session_id=${encodeURIComponent(appSessionId)}`;
    const response = await fetch(`${API_BASE_URL}/tiles/${tileId}${query}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to delete tile");
    }
  },

  async rebuildTiles(appSessionId: string): Promise<{ ok: boolean }> {
    const response = await fetch(`${API_BASE_URL}/tiles/rebuild`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: appSessionId,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to rebuild tiles");
    }
    return response.json();
  },

  async fetchRegulations(): Promise<RegulationsResponse> {
    const response = await fetch(`${API_BASE_URL}/regulations`);
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load regulations");
    }
    return response.json();
  },

  async listSessions(limit = 50): Promise<SessionsResponse> {
    const response = await fetch(`${API_BASE_URL}/sessions?limit=${limit}`);
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load sessions");
    }
    return response.json();
  },

  async getSessionStatus(appSessionId: string): Promise<SessionStatus> {
    const response = await fetch(
      `${API_BASE_URL}/sessions/status?app_session_id=${encodeURIComponent(
        appSessionId
      )}`
    );
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load session status");
    }
    return response.json();
  },

  async undoLastStep(appSessionId: string): Promise<UndoStepResponse> {
    const response = await fetch(`${API_BASE_URL}/sessions/undo`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ app_session_id: appSessionId }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to undo last step");
    }
    return response.json();
  },
  async exportSession(
    appSessionId: string
  ): Promise<{ filename: string; markdown: string }> {
    const response = await fetch(
      `${API_BASE_URL}/sessions/export?app_session_id=${encodeURIComponent(
        appSessionId
      )}`
    );
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to export session");
    }
    return response.json();
  },
  async startRunAllSteps(
    options: {
      appSessionId: string;
      currentFilename?: string;
      proposedFilename?: string;
      model?: string;
      provider?: string;
      keys?: ApiKeys;
    }
  ): Promise<RunAllStartResponse> {
    const response = await fetch(`${API_BASE_URL}/sessions/run-all/start`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildKeyHeaders(options.keys || {}),
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
        current_filename: options.currentFilename,
        proposed_filename: options.proposedFilename,
        model: options.model,
        provider: options.provider,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to start run-all steps");
    }
    return response.json();
  },
  async getRunAllStatus(runId: string): Promise<RunAllStatusResponse> {
    const response = await fetch(
      `${API_BASE_URL}/sessions/run-all/${encodeURIComponent(runId)}`
    );
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load run-all status");
    }
    return response.json();
  },
  getRunAllEventsUrl(runId: string): string {
    return `${API_BASE_URL}/sessions/run-all/${encodeURIComponent(runId)}/events`;
  },
  async cancelRunAll(runId: string): Promise<RunAllCancelResponse> {
    const response = await fetch(
      `${API_BASE_URL}/sessions/run-all/${encodeURIComponent(runId)}/cancel`,
      {
        method: "POST",
      }
    );
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to cancel run-all");
    }
    return response.json();
  },
  async uploadRegulation(
    file: File,
    filenameOverride?: string
  ): Promise<{ ok: boolean; filename: string }> {
    const formData = new FormData();
    formData.append("file", file);
    if (filenameOverride) {
      formData.append("filename", filenameOverride);
    }
    const response = await fetch(`${API_BASE_URL}/regulations/upload`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to upload regulation", {
        preferDetailErrorField: true,
      });
    }
    return response.json();
  },

  async summarizeRegulation(
    filename: string,
    options: {
      currentFilename?: string;
      appSessionId?: string;
      model?: string;
      provider?: string;
      keys?: ApiKeys;
    } = {}
  ): Promise<{ title: string; blurb: string; filename: string }> {
    const response = await fetch(`${API_BASE_URL}/regulations/summary`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildKeyHeaders(options.keys || {}),
      },
      body: JSON.stringify({
        filename,
        current_filename: options.currentFilename,
        app_session_id: options.appSessionId,
        model: options.model,
        provider: options.provider,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to summarize regulation", {
        includeStatusLabel: true,
        prefixWithFallback: true,
        preferDetailErrorField: true,
      });
    }
    return response.json();
  },
  async identifyRegulations(
    options: {
      currentFilename: string;
      proposedFilename: string;
      appSessionId: string;
      model?: string;
      provider?: string;
      keys?: ApiKeys;
    }
  ): Promise<VorgabenResponse> {
    const response = await fetch(`${API_BASE_URL}/regulations/identify`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildKeyHeaders(options.keys || {}),
      },
      body: JSON.stringify({
        current_filename: options.currentFilename,
        proposed_filename: options.proposedFilename,
        app_session_id: options.appSessionId,
        model: options.model,
        provider: options.provider,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to identify regulations");
    }
    return response.json();
  },
  async compileProcesses(
    options: {
      appSessionId: string;
      model?: string;
      provider?: string;
      keys?: ApiKeys;
    }
  ): Promise<ProzesseResponse> {
    const response = await fetch(`${API_BASE_URL}/processes/compile`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildKeyHeaders(options.keys || {}),
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
        model: options.model,
        provider: options.provider,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to compile processes");
    }
    return response.json();
  },

  async developCaseGroups(
    options: {
      appSessionId: string;
      model?: string;
      provider?: string;
      keys?: ApiKeys;
    }
  ): Promise<FallgruppenResponse> {
    const response = await fetch(`${API_BASE_URL}/case-groups/develop`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildKeyHeaders(options.keys || {}),
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
        model: options.model,
        provider: options.provider,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to develop case groups");
    }
    return response.json();
  },

  async analyzeProcessSteps(
    options: {
      appSessionId: string;
      model?: string;
      provider?: string;
      keys?: ApiKeys;
    }
  ): Promise<ProzessschritteResponse> {
    const response = await fetch(`${API_BASE_URL}/process-steps/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildKeyHeaders(options.keys || {}),
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
        model: options.model,
        provider: options.provider,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to analyze process steps");
    }
    return response.json();
  },

  async calculateEffort(
    options: {
      appSessionId: string;
      model?: string;
      provider?: string;
      keys?: ApiKeys;
    }
  ): Promise<EffortCalculationResponse> {
    const response = await fetch(`${API_BASE_URL}/effort/calculate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildKeyHeaders(options.keys || {}),
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
        model: options.model,
        provider: options.provider,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to calculate effort");
    }
    return response.json();
  },

  async computeTotalCost(
    options: { appSessionId: string }
  ): Promise<TotalCostResponse> {
    const response = await fetch(`${API_BASE_URL}/costs/compute`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to compute total cost");
    }
    return response.json();
  },
};
