import {
  ModelsResponse,
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
} from "@/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:5000";

type ApiKeys = {
  openaiApiKey?: string;
  deepinfraApiKey?: string;
  geminiApiKey?: string;
};

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

export const apiClient = {
  async upsertSession(
    appSessionId: string,
    llmModel: string
  ): Promise<{ session_id: number; created: boolean }> {
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
      throw new Error("Failed to upsert session");
    }
    return response.json();
  },
  async fetchModels(keys: ApiKeys): Promise<ModelsResponse> {
    const response = await fetch(`${API_BASE_URL}/models`, {
      headers: buildKeyHeaders(keys),
    });
    if (!response.ok) {
      throw new Error("Failed to load models");
    }
    return response.json();
  },

  async fetchOrganizedModels(keys: ApiKeys): Promise<OrganizedModelsResponse> {
    const response = await fetch(`${API_BASE_URL}/models/organized`, {
      headers: buildKeyHeaders(keys),
    });
    if (!response.ok) {
      throw new Error("Failed to load organized models");
    }
    return response.json();
  },

  async fetchTiles(): Promise<TilesResponse> {
    const response = await fetch(`${API_BASE_URL}/tiles`);
    if (!response.ok) {
      throw new Error("Failed to load tiles");
    }
    return response.json();
  },

  async upsertTile(tile: Tile): Promise<Tile> {
    const response = await fetch(`${API_BASE_URL}/tiles`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(tile),
    });
    if (!response.ok) {
      throw new Error("Failed to save tile");
    }
    return response.json();
  },

  async deleteTile(tileId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/tiles/${tileId}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error("Failed to delete tile");
    }
  },

  async rebuildTiles(appSessionId?: string): Promise<{ ok: boolean }> {
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
      throw new Error("Failed to rebuild tiles");
    }
    return response.json();
  },

  async seedTiles(): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/tiles/seed`, {
      method: "POST",
    });
    if (!response.ok) {
      throw new Error("Failed to seed tiles");
    }
  },

  async fetchRegulations(): Promise<RegulationsResponse> {
    const response = await fetch(`${API_BASE_URL}/regulations`);
    if (!response.ok) {
      throw new Error("Failed to load regulations");
    }
    return response.json();
  },

  async listSessions(limit = 50): Promise<SessionsResponse> {
    const response = await fetch(`${API_BASE_URL}/sessions?limit=${limit}`);
    if (!response.ok) {
      throw new Error("Failed to load sessions");
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
      throw new Error("Failed to load session status");
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
      throw new Error("Failed to undo last step");
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
      let errorBody: any = null;
      try {
        errorBody = await response.json();
      } catch {
        errorBody = null;
      }
      const error = new Error(
        errorBody?.detail?.error || "Failed to upload regulation"
      );
      (error as any).status = response.status;
      (error as any).details = errorBody?.detail ?? errorBody;
      throw error;
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
      let errorBody: any = null;
      let rawText = "";
      try {
        rawText = await response.text();
        errorBody = rawText ? JSON.parse(rawText) : null;
      } catch {
        errorBody = null;
      }
      const statusLabel = `${response.status} ${response.statusText}`.trim();
      const detailMessage =
        errorBody?.detail?.error || errorBody?.detail || rawText;
      const error = new Error(
        detailMessage
          ? `Failed to summarize regulation (${statusLabel}): ${detailMessage}`
          : `Failed to summarize regulation (${statusLabel})`
      );
      (error as any).status = response.status;
      (error as any).details = errorBody?.detail ?? errorBody ?? rawText;
      (error as any).raw = rawText;
      throw error;
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
      throw new Error("Failed to identify regulations");
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
      throw new Error("Failed to compile processes");
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
      throw new Error("Failed to develop case groups");
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
      throw new Error("Failed to analyze process steps");
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
      throw new Error("Failed to calculate effort");
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
      throw new Error("Failed to compute total cost");
    }
    return response.json();
  },
};
