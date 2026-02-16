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

export interface SessionSummary {
  app_session_id: string;
  created_at: string;
  llm_model: string;
}

export interface SessionsResponse {
  sessions: SessionSummary[];
}

export interface SessionStatus {
  summary_ready: boolean;
  regulations_ready: boolean;
  processes_ready: boolean;
  case_groups_ready: boolean;
  process_steps_ready: boolean;
  effort_ready: boolean;
  total_cost_ready: boolean;
  last_completed_step?: string | null;
  last_completed_label?: string | null;
}

export interface UndoStepResponse {
  status: string;
  undone_step?: string;
  undone_label?: string;
  message?: string;
}

export interface RunAllStepResult {
  key: string;
  label: string;
  status: "completed" | "skipped" | "failed";
  message?: string | null;
}

export interface RunAllResponse {
  app_session_id: string;
  ok: boolean;
  steps: RunAllStepResult[];
  final_status: SessionStatus;
}

export interface RunAllStartResponse {
  app_session_id: string;
  run_id: string;
  started: boolean;
  status: "running" | "completed" | "failed" | "cancelled";
}

export interface RunAllStatusResponse {
  run_id: string;
  app_session_id: string;
  status: "running" | "completed" | "failed" | "cancelled";
  ok?: boolean | null;
  steps: RunAllStepResult[];
  final_status?: SessionStatus | null;
}

export interface RunAllCancelResponse {
  run_id: string;
  app_session_id: string;
  status: "cancelling" | "completed" | "failed" | "cancelled";
  accepted: boolean;
  message?: string | null;
}

export interface RegulationsResponse {
  files: string[];
}

export interface Vorgabe {
  regulation_id?: number;
  normzitat: string;
  beschreibung: string;
}

export interface VorgabenResponse {
  vorgaben: Vorgabe[];
  status?: string;
}

export interface Prozess {
  process_id?: number;
  prozess_bezeichnung: string;
  prozess_beschreibung: string;
}

export interface ProzesseResponse {
  prozesse: Prozess[];
  status?: string;
}

export interface Fallgruppe {
  case_group_id?: number;
  beschreibung_fallgruppe: string;
}

export interface FallgruppenProzess {
  process_id?: number;
  prozess_bezeichnung: string;
  prozess_beschreibung: string;
  fallgruppen: Fallgruppe[];
}

export interface FallgruppenResponse {
  prozesse: FallgruppenProzess[];
  status?: string;
}

export interface Prozessschritt {
  step_id?: number;
  case_group_id?: number;
  taetigkeit: string;
  beschreibung: string;
}

export interface ProzessschritteResponse {
  steps: Prozessschritt[];
  status?: string;
}

export interface EffortCalculationResponse {
  case_groups_updated: number;
  steps_updated: number;
  status?: string;
}

export interface TotalCostResponse {
  total_cost: number;
}
