import { ModelsResponse, OrganizedModelsResponse, Tile, TilesResponse } from "@/types";

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

  async seedTiles(): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/tiles/seed`, {
      method: "POST",
    });
    if (!response.ok) {
      throw new Error("Failed to seed tiles");
    }
  },
};
