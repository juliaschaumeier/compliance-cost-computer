import {
  OrganizedModelsResponse,
  RegulationsResponse,
  Tile,
  TilesResponse,
  VorgabenResponse,
  TotalCostResponse,
  TotalCostSummaryResponse,
  SessionsResponse,
  SessionStatus,
  UndoStepResponse,
  RunAllStartResponse,
  RunAllStatusResponse,
  RunAllCancelResponse,
  Model,
  LlmMonitorSnapshotResponse,
  LlmMonitorStreamAttemptResponse,
  SessionWageRatesResponse,
  SessionEditAuditResponse,
  EditableCaseGroupsResponse,
  EditableProcessStepsResponse,
  NormAddressee,
  CaseGroupResearchSettingsResponse,
  AuthUser,
  AdminUser,
  LegisLlmImportResponse,
} from "@/types";
import { hasPlausibleApiKey } from "@/lib/apiKeys";
import { notifyAuthExpired } from "@/lib/authExpired";

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

export type ComplianceTextUserEditPolicy =
  | "reject_if_user_edits"
  | "use_user_edits";

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
      openaiApiKey: normalizeStoredApiKey(activeStorage?.getItem("openai_api_key")),
      deepinfraApiKey: normalizeStoredApiKey(activeStorage?.getItem("deepinfra_api_key")),
      geminiApiKey: normalizeStoredApiKey(activeStorage?.getItem("gemini_api_key")),
    },
  };
}

function normalizeStoredApiKey(value: string | null | undefined): string | undefined {
  if (!hasPlausibleApiKey(value)) {
    return undefined;
  }
  return value?.trim();
}

function readStoredApiKeys(): ApiKeys {
  const activeStorage = typeof window !== "undefined" ? window.localStorage : null;
  return {
    openaiApiKey: normalizeStoredApiKey(activeStorage?.getItem("openai_api_key")),
    deepinfraApiKey: normalizeStoredApiKey(activeStorage?.getItem("deepinfra_api_key")),
    geminiApiKey: normalizeStoredApiKey(activeStorage?.getItem("gemini_api_key")),
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
  if (typeof detail === "string") {
    return detail;
  }
  if (isRecord(detail) && typeof detail.message === "string") {
    return detail.message;
  }
  return rawText || null;
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
  suppressAuthExpiredEvent?: boolean;
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

  if (response.status === 401 && !options.suppressAuthExpiredEvent) {
    notifyAuthExpired();
  }

  throw createApiClientError(message, {
    status: response.status,
    details: detail ?? errorBody ?? rawText,
    raw: rawText,
  });
}

export const apiClient = {
  async login(email: string, password: string): Promise<AuthUser> {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      credentials: "include",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Anmeldung fehlgeschlagen", {
        suppressAuthExpiredEvent: true,
      });
    }
    return response.json();
  },
  async logout(): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/auth/logout`, {
      credentials: "include",
      method: "POST",
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Abmeldung fehlgeschlagen");
    }
  },
  async getMe(): Promise<AuthUser> {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      credentials: "include",
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load current user", {
        suppressAuthExpiredEvent: true,
      });
    }
    return response.json();
  },
  async listUsers(): Promise<AdminUser[]> {
    const response = await fetch(`${API_BASE_URL}/auth/users`, {
      credentials: "include",
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load users");
    }
    return response.json();
  },
  async createUser(
    email: string,
    password: string,
    isAdmin?: boolean
  ): Promise<AdminUser> {
    const response = await fetch(`${API_BASE_URL}/auth/users`, {
      credentials: "include",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email,
        password,
        is_admin: isAdmin ?? false,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to create user");
    }
    return response.json();
  },
  async updateUser(
    userId: number,
    patch: { is_active?: boolean; is_admin?: boolean; password?: string }
  ): Promise<AdminUser> {
    const response = await fetch(
      `${API_BASE_URL}/auth/users/${encodeURIComponent(String(userId))}`,
      {
        credentials: "include",
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(patch),
      }
    );
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to update user");
    }
    return response.json();
  },
  async createSession(
    llmModel: string
  ): Promise<{
    app_session_id: string;
    created: boolean;
    case_group_research_enabled: boolean;
  }> {
    const response = await fetch(`${API_BASE_URL}/sessions`, {
      credentials: "include",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildKeyHeaders(readStoredApiKeys()),
      },
      body: JSON.stringify({
        llm_model: llmModel,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to create session");
    }
    return response.json();
  },
  async fetchOrganizedModels(keys: ApiKeys): Promise<OrganizedModelsResponse> {
    const response = await fetch(`${API_BASE_URL}/models/organized`, {
      credentials: "include",
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

  async fetchTiles(
    appSessionId: string,
    normAddressee?: NormAddressee
  ): Promise<TilesResponse> {
    const params = new URLSearchParams({
      app_session_id: appSessionId,
    });
    if (normAddressee && normAddressee !== "administration") {
      params.set("norm_addressee", normAddressee);
    }
    const query = `?${params.toString()}`;
    const response = await fetch(`${API_BASE_URL}/tiles${query}`, {
      credentials: "include",
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load tiles");
    }
    return response.json();
  },

  async upsertTile(
    tile: Tile,
    appSessionId: string,
    normAddressee?: NormAddressee
  ): Promise<Tile> {
    const params = new URLSearchParams({
      app_session_id: appSessionId,
    });
    if (normAddressee && normAddressee !== "administration") {
      params.set("norm_addressee", normAddressee);
    }
    const query = `?${params.toString()}`;
    const response = await fetch(`${API_BASE_URL}/tiles${query}`, {
      credentials: "include",
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

  async rebuildTiles(
    appSessionId: string,
    normAddressee?: NormAddressee
  ): Promise<{ ok: boolean }> {
    const response = await fetch(`${API_BASE_URL}/tiles/rebuild`, {
      credentials: "include",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: appSessionId,
        norm_addressee:
          normAddressee && normAddressee !== "administration"
            ? normAddressee
            : undefined,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to rebuild tiles");
    }
    return response.json();
  },

  async fetchRegulations(): Promise<RegulationsResponse> {
    const response = await fetch(`${API_BASE_URL}/regulations`, {
      credentials: "include",
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load regulations");
    }
    return response.json();
  },

  async listSessions(limit = 50, offset = 0): Promise<SessionsResponse> {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    const response = await fetch(`${API_BASE_URL}/sessions?${params.toString()}`, {
      credentials: "include",
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load sessions");
    }
    return response.json();
  },

  async getSessionStatus(appSessionId: string): Promise<SessionStatus> {
    const response = await fetch(
      `${API_BASE_URL}/sessions/status?app_session_id=${encodeURIComponent(
        appSessionId
      )}`,
      {
        credentials: "include",
      }
    );
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load session status");
    }
    return response.json();
  },

  async undoLastStep(
    appSessionId: string
  ): Promise<UndoStepResponse> {
    const response = await fetch(`${API_BASE_URL}/sessions/undo`, {
      credentials: "include",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: appSessionId,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to undo last step");
    }
    return response.json();
  },
  async getCaseGroupResearchSettings(
    appSessionId: string
  ): Promise<CaseGroupResearchSettingsResponse> {
    const response = await fetch(
      `${API_BASE_URL}/sessions/case-group-research?app_session_id=${encodeURIComponent(
        appSessionId
      )}`,
      {
        credentials: "include",
        headers: buildKeyHeaders(readStoredApiKeys()),
      }
    );
    if (!response.ok) {
      await throwApiClientErrorFromResponse(
        response,
        "Failed to load Deep Research settings"
      );
    }
    return response.json();
  },
  async updateCaseGroupResearchSettings(
    appSessionId: string,
    enabled: boolean
  ): Promise<CaseGroupResearchSettingsResponse> {
    const response = await fetch(`${API_BASE_URL}/sessions/case-group-research`, {
      credentials: "include",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildKeyHeaders(readStoredApiKeys()),
      },
      body: JSON.stringify({
        app_session_id: appSessionId,
        enabled,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(
        response,
        "Failed to update Deep Research settings"
      );
    }
    return response.json();
  },
  async downloadDeepResearchReport(appSessionId: string): Promise<Blob> {
    const response = await fetch(
      `${API_BASE_URL}/sessions/deep-research-report?app_session_id=${encodeURIComponent(
        appSessionId
      )}&format=pdf`,
      {
        credentials: "include",
      }
    );
    if (!response.ok) {
      await throwApiClientErrorFromResponse(
        response,
        "Failed to download Deep Research report"
      );
    }
    return response.blob();
  },
  async downloadComplianceTextExport(options: {
    appSessionId: string;
    model?: string;
    provider?: string;
    keys?: ApiKeys;
    userEditPolicy?: ComplianceTextUserEditPolicy;
  }): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/sessions/compliance-text-export`, {
      credentials: "include",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildKeyHeaders(options.keys || {}),
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
        model: options.model,
        provider: options.provider,
        user_edit_policy: options.userEditPolicy || "reject_if_user_edits",
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(
        response,
        "Failed to download Vorblatt und Begründung export"
      );
    }
    return response.blob();
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
      credentials: "include",
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
  async startStepRun(
    options: {
      appSessionId: string;
      stepKey: string;
      currentFilename?: string;
      proposedFilename?: string;
      model?: string;
      provider?: string;
      keys?: ApiKeys;
    }
  ): Promise<RunAllStartResponse> {
    const response = await fetch(`${API_BASE_URL}/sessions/step-runs/start`, {
      credentials: "include",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildKeyHeaders(options.keys || {}),
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
        step_key: options.stepKey,
        current_filename: options.currentFilename,
        proposed_filename: options.proposedFilename,
        model: options.model,
        provider: options.provider,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to start step");
    }
    return response.json();
  },
  async getStepRunStatus(runId: string): Promise<RunAllStatusResponse> {
    const response = await fetch(
      `${API_BASE_URL}/sessions/step-runs/${encodeURIComponent(runId)}`,
      {
        credentials: "include",
      }
    );
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load step status");
    }
    return response.json();
  },
  getStepRunEventsUrl(runId: string): string {
    return `${API_BASE_URL}/sessions/step-runs/${encodeURIComponent(runId)}/events`;
  },
  async cancelStepRun(runId: string): Promise<RunAllCancelResponse> {
    const response = await fetch(
      `${API_BASE_URL}/sessions/step-runs/${encodeURIComponent(runId)}/cancel`,
      {
        method: "POST",
        credentials: "include",
      }
    );
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to cancel step");
    }
    return response.json();
  },
  async getRunAllStatus(runId: string): Promise<RunAllStatusResponse> {
    const response = await fetch(
      `${API_BASE_URL}/sessions/run-all/${encodeURIComponent(runId)}`,
      {
        credentials: "include",
      }
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
        credentials: "include",
      }
    );
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to cancel run-all");
    }
    return response.json();
  },
  async getLlmMonitorSnapshot(options: {
    appSessionId: string;
    limit?: number;
  }): Promise<LlmMonitorSnapshotResponse> {
    const limit = Math.min(Math.max(options.limit ?? 80, 1), 500);
    const response = await fetch(
      `${API_BASE_URL}/sessions/llm-monitor?app_session_id=${encodeURIComponent(
        options.appSessionId
      )}&limit=${limit}`,
      {
        credentials: "include",
      }
    );
    if (!response.ok) {
      await throwApiClientErrorFromResponse(
        response,
        "Failed to load LLM monitor snapshot"
      );
    }
    return response.json();
  },
  getLlmMonitorEventsUrl(options: {
    appSessionId: string;
    limit?: number;
  }): string {
    const limit = Math.min(Math.max(options.limit ?? 80, 1), 500);
    return `${API_BASE_URL}/sessions/llm-monitor/events?app_session_id=${encodeURIComponent(
      options.appSessionId
    )}&limit=${limit}`;
  },
  async getLlmMonitorStreamAttempt(options: {
    appSessionId: string;
    attemptId: string;
  }): Promise<LlmMonitorStreamAttemptResponse> {
    const response = await fetch(
      `${API_BASE_URL}/sessions/llm-monitor/stream/${encodeURIComponent(
        options.attemptId
      )}?app_session_id=${encodeURIComponent(options.appSessionId)}`,
      {
        credentials: "include",
      }
    );
    if (!response.ok) {
      await throwApiClientErrorFromResponse(
        response,
        "Failed to load LLM stream attempt"
      );
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
      credentials: "include",
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

  async importLegisLlmExport(file: File): Promise<LegisLlmImportResponse> {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${API_BASE_URL}/regulations/import/legisllm`, {
      credentials: "include",
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(
        response,
        "Failed to import LegisLLM export",
        {
          preferDetailErrorField: true,
        }
      );
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
  ): Promise<{ title: string; summary: string; blurb?: string; filename: string }> {
    const response = await fetch(`${API_BASE_URL}/regulations/summary`, {
      credentials: "include",
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
      appSessionId: string;
      model?: string;
      provider?: string;
      keys?: ApiKeys;
    }
  ): Promise<VorgabenResponse> {
    const response = await fetch(`${API_BASE_URL}/regulations/identify`, {
      credentials: "include",
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
      await throwApiClientErrorFromResponse(response, "Failed to identify regulations");
    }
    return response.json();
  },
  async acquireEaEditActivity(options: {
    appSessionId: string;
  }): Promise<{ app_session_id: string; activity_id: string; lease_seconds: number; expires_at?: number | null }> {
    const response = await fetch(`${API_BASE_URL}/sessions/ea-edit-activity/acquire`, {
      credentials: "include",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to acquire EA edit activity");
    }
    return response.json();
  },
  async heartbeatEaEditActivity(options: {
    appSessionId: string;
    activityId: string;
  }): Promise<{ app_session_id: string; activity_id: string; lease_seconds: number; expires_at?: number | null }> {
    const response = await fetch(`${API_BASE_URL}/sessions/ea-edit-activity/heartbeat`, {
      credentials: "include",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
        activity_id: options.activityId,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to refresh EA edit activity");
    }
    return response.json();
  },
  async releaseEaEditActivity(options: {
    appSessionId: string;
    activityId: string;
  }): Promise<{ ok: boolean }> {
    const response = await fetch(`${API_BASE_URL}/sessions/ea-edit-activity/release`, {
      credentials: "include",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
        activity_id: options.activityId,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to release EA edit activity");
    }
    return response.json();
  },
  async computeTotalCost(options: {
    appSessionId: string;
    normAddressee?: NormAddressee;
    eaActivityId?: string;
  }): Promise<TotalCostResponse> {
    const response = await fetch(`${API_BASE_URL}/costs/compute`, {
      credentials: "include",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
        norm_addressee: options.normAddressee,
        ea_activity_id: options.eaActivityId,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to compute total cost");
    }
    return response.json();
  },

  async getTotalCostSummary(
    appSessionId: string
  ): Promise<TotalCostSummaryResponse> {
    const params = new URLSearchParams();
    params.set("app_session_id", appSessionId);
    const response = await fetch(`${API_BASE_URL}/costs/totals?${params.toString()}`, {
      credentials: "include",
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load total costs");
    }
    return response.json();
  },

  async resetSessionEaEdits(options: {
    appSessionId: string;
    eaActivityId?: string;
  }): Promise<{
    app_session_id: string;
    reset_counts: Record<string, number>;
    recomputed_norm_addressees: string[];
  }> {
    const response = await fetch(`${API_BASE_URL}/sessions/ea-edits/reset`, {
      credentials: "include",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
        ea_activity_id: options.eaActivityId,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to reset EA edits");
    }
    return response.json();
  },

  async getSessionWageRates(options: {
    appSessionId: string;
    normAddressee?: NormAddressee;
  }): Promise<SessionWageRatesResponse> {
    const params = new URLSearchParams();
    params.set("app_session_id", options.appSessionId);
    if (options.normAddressee) {
      params.set("norm_addressee", options.normAddressee);
    }
    const response = await fetch(`${API_BASE_URL}/sessions/wage-rates?${params.toString()}`, {
      credentials: "include",
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load session wage rates");
    }
    return response.json();
  },

  async updateSessionWageRate(options: {
    appSessionId: string;
    normAddressee?: NormAddressee;
    eaActivityId?: string;
    wageSourceKind: string;
    wageSourceValue: string;
    qualification: string;
    hourlyRateEdited: number | null;
  }): Promise<SessionWageRatesResponse> {
    const response = await fetch(`${API_BASE_URL}/sessions/wage-rates`, {
      credentials: "include",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
        norm_addressee: options.normAddressee,
        ea_activity_id: options.eaActivityId,
        wage_source_kind: options.wageSourceKind,
        wage_source_value: options.wageSourceValue,
        qualification: options.qualification,
        hourly_rate_edited: options.hourlyRateEdited,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to update session wage rate");
    }
    return response.json();
  },

  async getSessionEditAudit(options: {
    appSessionId: string;
    limit?: number;
  }): Promise<SessionEditAuditResponse> {
    const params = new URLSearchParams();
    params.set("app_session_id", options.appSessionId);
    if (typeof options.limit === "number") {
      params.set("limit", String(options.limit));
    }
    const response = await fetch(`${API_BASE_URL}/sessions/edit-audit?${params.toString()}`, {
      credentials: "include",
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load session edit audit");
    }
    return response.json();
  },

  async getEditableCaseGroups(options: {
    appSessionId: string;
  }): Promise<EditableCaseGroupsResponse> {
    const response = await fetch(
      `${API_BASE_URL}/case-groups/editable?app_session_id=${encodeURIComponent(
        options.appSessionId
      )}`,
      {
        credentials: "include",
      }
    );
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load editable case groups");
    }
    return response.json();
  },

  async bulkUpdateCaseGroups(options: {
    appSessionId: string;
    eaActivityId?: string;
    rows: Array<{
      case_group_id: number;
      addressees_current: number | null;
      annual_frequency_current: number | null;
      addressees_proposed: number | null;
      annual_frequency_proposed: number | null;
    }>;
  }): Promise<{ updated: number }> {
    const response = await fetch(`${API_BASE_URL}/case-groups/bulk-update`, {
      credentials: "include",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
        ea_activity_id: options.eaActivityId,
        rows: options.rows,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to update case groups");
    }
    return response.json();
  },

  async getEditableProcessSteps(options: {
    appSessionId: string;
    caseGroupId?: number;
  }): Promise<EditableProcessStepsResponse> {
    const params = new URLSearchParams();
    params.set("app_session_id", options.appSessionId);
    if (typeof options.caseGroupId === "number") {
      params.set("case_group_id", String(options.caseGroupId));
    }
    const response = await fetch(`${API_BASE_URL}/process-steps/editable?${params.toString()}`, {
      credentials: "include",
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load editable process steps");
    }
    return response.json();
  },

  async bulkUpdateProcessSteps(options: {
    appSessionId: string;
    eaActivityId?: string;
    rows: Array<{
      step_id: number;
      time_required_in_min_a_current: number | null;
      time_required_in_min_b_current: number | null;
      time_required_in_min_c_current: number | null;
      time_required_in_min_d_current: number | null;
      expenses_current: number | null;
      time_required_in_min_a_proposed: number | null;
      time_required_in_min_b_proposed: number | null;
      time_required_in_min_c_proposed: number | null;
      time_required_in_min_d_proposed: number | null;
      expenses_proposed: number | null;
    }>;
  }): Promise<{ updated: number }> {
    const response = await fetch(`${API_BASE_URL}/process-steps/bulk-update`, {
      credentials: "include",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
        ea_activity_id: options.eaActivityId,
        rows: options.rows,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to update process steps");
    }
    return response.json();
  },

  async updatePersonnelEffortTime(options: {
    appSessionId: string;
    eaActivityId?: string;
    normAddressee: NormAddressee;
    stepId: number;
    period: "current" | "proposed";
    qualification: string;
    wageSourceKind: string;
    wageSourceValue: string;
    timeRequiredInMinEdited: number | null;
  }): Promise<{ updated: number }> {
    const response = await fetch(`${API_BASE_URL}/process-steps/personnel-effort-edit`, {
      credentials: "include",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
        ea_activity_id: options.eaActivityId,
        norm_addressee: options.normAddressee,
        step_id: options.stepId,
        period: options.period,
        qualification: options.qualification,
        wage_source_kind: options.wageSourceKind,
        wage_source_value: options.wageSourceValue,
        time_required_in_min_edited: options.timeRequiredInMinEdited,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to update personnel effort time");
    }
    return response.json();
  },
};
