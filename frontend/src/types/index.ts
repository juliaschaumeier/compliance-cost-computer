export type Provider = "OpenAI" | "DeepInfra" | "Gemini";

export interface Model {
  id: string;
  name: string;
  provider: Provider;
}

export interface ProviderModels {
  recommended: Model[];
  additional: Model[];
}

export interface OrganizedModels {
  openai: ProviderModels;
  deepinfra: ProviderModels;
  gemini: ProviderModels;
}

export interface ModelsResponse {
  models: Model[];
  default: string;
}

export interface OrganizedModelsResponse {
  organized: OrganizedModels;
  default: string;
}

export interface Tile {
  id: string;
  title: string;
  text: string;
  meta_information: Record<string, unknown>;
  column: number;
  row: number;
  deletable: boolean;
  link_from_tile: string[];
}

export interface TilesResponse {
  tiles: Tile[];
}
