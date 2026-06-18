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
  LlmMonitorSnapshotResponse,
  LlmMonitorStreamAttemptResponse,
  SessionWageRatesResponse,
  SessionEditAuditResponse,
  EditableCaseGroupsResponse,
  EditableProcessStepsResponse,
  NormAddressee,
  CaseGroupResearchSettingsResponse,
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
    const response = await fetch(`${API_BASE_URL}/tiles${query}`);
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

  async undoLastStep(
    appSessionId: string
  ): Promise<UndoStepResponse> {
    const response = await fetch(`${API_BASE_URL}/sessions/undo`, {
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
  async getCaseGroupResearchSettings(
    appSessionId: string
  ): Promise<CaseGroupResearchSettingsResponse> {
    const response = await fetch(
      `${API_BASE_URL}/sessions/case-group-research?app_session_id=${encodeURIComponent(
        appSessionId
      )}`
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
      method: "POST",
      headers: {
        "Content-Type": "application/json",
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
      )}&format=pdf`
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
        "Failed to download Vorblatt/Begründung export"
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
      `${API_BASE_URL}/sessions/step-runs/${encodeURIComponent(runId)}`
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
      }
    );
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to cancel step");
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
  async getLlmMonitorSnapshot(options: {
    appSessionId: string;
    limit?: number;
  }): Promise<LlmMonitorSnapshotResponse> {
    const limit = Math.min(Math.max(options.limit ?? 80, 1), 500);
    const response = await fetch(
      `${API_BASE_URL}/sessions/llm-monitor?app_session_id=${encodeURIComponent(
        options.appSessionId
      )}&limit=${limit}`
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
      )}?app_session_id=${encodeURIComponent(options.appSessionId)}`
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
  ): Promise<{ title: string; summary: string; blurb?: string; filename: string }> {
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
      normAddressee?: NormAddressee;
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
        norm_addressee: options.normAddressee,
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
      normAddressee?: NormAddressee;
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
        norm_addressee: options.normAddressee,
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
      normAddressee?: NormAddressee;
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
        norm_addressee: options.normAddressee,
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
      normAddressee?: NormAddressee;
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
        norm_addressee: options.normAddressee,
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
    options: { appSessionId: string; normAddressee?: NormAddressee }
  ): Promise<TotalCostResponse> {
    const response = await fetch(`${API_BASE_URL}/costs/compute`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
        norm_addressee: options.normAddressee,
      }),
    });
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to compute total cost");
    }
    return response.json();
  },

  async resetSessionEaEdits(options: {
    appSessionId: string;
  }): Promise<{
    app_session_id: string;
    reset_counts: Record<string, number>;
    recomputed_norm_addressees: string[];
  }> {
    const response = await fetch(`${API_BASE_URL}/sessions/ea-edits/reset`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
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
    const response = await fetch(`${API_BASE_URL}/sessions/wage-rates?${params.toString()}`);
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load session wage rates");
    }
    return response.json();
  },

  async updateSessionWageRate(options: {
    appSessionId: string;
    normAddressee?: NormAddressee;
    wageSourceKind: string;
    wageSourceValue: string;
    qualification: string;
    hourlyRateEdited: number | null;
  }): Promise<SessionWageRatesResponse> {
    const response = await fetch(`${API_BASE_URL}/sessions/wage-rates`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
        norm_addressee: options.normAddressee,
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
    const response = await fetch(`${API_BASE_URL}/sessions/edit-audit?${params.toString()}`);
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
      )}`
    );
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load editable case groups");
    }
    return response.json();
  },

  async bulkUpdateCaseGroups(options: {
    appSessionId: string;
    rows: Array<{
      case_group_id: number;
      addressees_current: number | null;
      annual_frequency_current: number | null;
      addressees_proposed: number | null;
      annual_frequency_proposed: number | null;
    }>;
  }): Promise<{ updated: number }> {
    const response = await fetch(`${API_BASE_URL}/case-groups/bulk-update`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
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
    const response = await fetch(`${API_BASE_URL}/process-steps/editable?${params.toString()}`);
    if (!response.ok) {
      await throwApiClientErrorFromResponse(response, "Failed to load editable process steps");
    }
    return response.json();
  },

  async bulkUpdateProcessSteps(options: {
    appSessionId: string;
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
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
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
    normAddressee: NormAddressee;
    stepId: number;
    period: "current" | "proposed";
    qualification: string;
    wageSourceKind: string;
    wageSourceValue: string;
    timeRequiredInMinEdited: number | null;
  }): Promise<{ updated: number }> {
    const response = await fetch(`${API_BASE_URL}/process-steps/personnel-effort-edit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        app_session_id: options.appSessionId,
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
