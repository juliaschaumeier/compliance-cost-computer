export type Provider = "OpenAI" | "DeepInfra" | "Gemini";
export type NormAddressee = "administration" | "business" | "citizens";
export const AUTOMATED_NORM_ADDRESSEES: NormAddressee[] = [
  "administration",
  "business",
  "citizens",
];

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
  used_llm_models?: string | null;
}

export interface SessionsResponse {
  sessions: SessionSummary[];
}

export interface SessionStatus {
  summary_ready: boolean;
  regulations_ready: boolean;
  processes_ready: boolean;
  processes_ready_by_addressee?: Record<NormAddressee, boolean>;
  case_groups_ready: boolean;
  case_groups_ready_by_addressee?: Record<NormAddressee, boolean>;
  process_steps_ready: boolean;
  process_steps_ready_by_addressee?: Record<NormAddressee, boolean>;
  effort_ready: boolean;
  effort_ready_by_addressee?: Record<NormAddressee, boolean>;
  total_cost_ready: boolean;
  total_cost_ready_by_addressee?: Record<NormAddressee, boolean>;
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

export interface LlmMonitorEvent {
  event_type: string;
  attempt_id?: string | null;
  answer_id?: number | null;
  app_session_id?: string | null;
  session_id?: number | null;
  prompt_id?: string | null;
  model?: string | null;
  provider?: string | null;
  request_id?: string | null;
  route_method?: string | null;
  route_path?: string | null;
  elapsed_ms?: number | null;
  error?: string | null;
  error_kind?: string | null;
  error_status_code?: number | null;
  answer_state?: string | null;
  state_reason?: string | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  hidden_thinking_tokens?: number | null;
  estimated_cost_usd?: number | null;
  timestamp_ms?: number | null;
  sequence?: number | null;
}

export interface LlmMonitorPendingCall {
  attempt_id?: string | null;
  app_session_id?: string | null;
  session_id?: number | null;
  prompt_id?: string | null;
  model?: string | null;
  provider?: string | null;
  request_id?: string | null;
  route_method?: string | null;
  route_path?: string | null;
  started_at_ms?: number | null;
  status?: string | null;
  answer_id?: number | null;
  elapsed_ms?: number | null;
}

export interface LlmMonitorStreamChunk {
  sequence?: number | null;
  timestamp_ms?: number | null;
  delta_text?: string | null;
  delta_chars?: number | null;
  cumulative_chars?: number | null;
}

export interface LlmMonitorStreamAttempt {
  attempt_id?: string | null;
  app_session_id?: string | null;
  session_id?: number | null;
  prompt_id?: string | null;
  model?: string | null;
  provider?: string | null;
  request_id?: string | null;
  route_method?: string | null;
  route_path?: string | null;
  started_at_ms?: number | null;
  updated_at_ms?: number | null;
  completed_at_ms?: number | null;
  status?: string | null;
  answer_id?: number | null;
  elapsed_ms?: number | null;
  streaming?: boolean | null;
  stream_mode?: string | null;
  stream_fallback_reason?: string | null;
  chunk_count?: number | null;
  text?: string | null;
  text_chars?: number | null;
  error?: string | null;
  error_kind?: string | null;
  error_status_code?: number | null;
  answer_state?: string | null;
  state_reason?: string | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  hidden_thinking_tokens?: number | null;
  estimated_cost_usd?: number | null;
  chunks?: LlmMonitorStreamChunk[] | null;
}

export interface LlmMonitorRecentCall {
  answer_id?: number | null;
  prompt_id: string;
  model: string;
  provider?: string | null;
  attempt_id?: string | null;
  request_id?: string | null;
  route_method?: string | null;
  route_path?: string | null;
  elapsed_ms?: number | null;
  answer_state: string;
  state_reason?: string | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  hidden_thinking_tokens?: number | null;
  estimated_cost_usd?: number | null;
  error_kind?: string | null;
  error_status_code?: number | null;
  error?: string | null;
  created_at?: string | null;
}

export interface LlmMonitorSnapshotResponse {
  app_session_id: string;
  pending: LlmMonitorPendingCall[];
  recent: LlmMonitorRecentCall[];
  events?: LlmMonitorEvent[] | null;
  stream_attempts?: LlmMonitorStreamAttempt[] | null;
}

export interface LlmMonitorStreamAttemptResponse {
  app_session_id: string;
  attempt: LlmMonitorStreamAttempt;
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

export interface SessionPayRatesResponse {
  app_session_id: string;
  administration_level: string;
  defaults: Record<string, number>;
  edited: Record<string, number | null>;
  active: Record<string, number>;
}

export interface SessionEditAuditRow {
  audit_id: number;
  session_id: number;
  entity_type: string;
  entity_id: number | null;
  field_name: string;
  old_value: string | null;
  new_value: string | null;
  edited_at: string;
}

export interface SessionEditAuditResponse {
  app_session_id: string;
  rows: SessionEditAuditRow[];
}

export interface EditableCaseGroupRow {
  case_group_id: number;
  process_id: number;
  case_group: string;
  description: string;
  change_status: string;
  addressees_current: number | null;
  annual_frequency_current: number | null;
  cases_current: number | null;
  addressees_current_edited: number | null;
  annual_frequency_current_edited: number | null;
  cases_current_edited: number | null;
  addressees_proposed: number | null;
  annual_frequency_proposed: number | null;
  cases_proposed: number | null;
  addressees_proposed_edited: number | null;
  annual_frequency_proposed_edited: number | null;
  cases_proposed_edited: number | null;
  addressees_current_effective: number | null;
  annual_frequency_current_effective: number | null;
  cases_current_effective: number | null;
  addressees_proposed_effective: number | null;
  annual_frequency_proposed_effective: number | null;
  cases_proposed_effective: number | null;
}

export interface EditableCaseGroupsResponse {
  rows: EditableCaseGroupRow[];
}

export interface EditableProcessStepRow {
  step_id: number;
  case_group_id: number;
  step: string;
  description: string;
  change_status: string;
  time_required_in_min_a_current: number | null;
  time_required_in_min_b_current: number | null;
  time_required_in_min_c_current: number | null;
  time_required_in_min_d_current: number | null;
  expenses_current: number | null;
  time_required_in_min_a_current_edited: number | null;
  time_required_in_min_b_current_edited: number | null;
  time_required_in_min_c_current_edited: number | null;
  time_required_in_min_d_current_edited: number | null;
  expenses_current_edited: number | null;
  time_required_in_min_a_proposed: number | null;
  time_required_in_min_b_proposed: number | null;
  time_required_in_min_c_proposed: number | null;
  time_required_in_min_d_proposed: number | null;
  expenses_proposed: number | null;
  time_required_in_min_a_proposed_edited: number | null;
  time_required_in_min_b_proposed_edited: number | null;
  time_required_in_min_c_proposed_edited: number | null;
  time_required_in_min_d_proposed_edited: number | null;
  expenses_proposed_edited: number | null;
  time_required_in_min_a_current_effective: number | null;
  time_required_in_min_b_current_effective: number | null;
  time_required_in_min_c_current_effective: number | null;
  time_required_in_min_d_current_effective: number | null;
  expenses_current_effective: number | null;
  time_required_in_min_a_proposed_effective: number | null;
  time_required_in_min_b_proposed_effective: number | null;
  time_required_in_min_c_proposed_effective: number | null;
  time_required_in_min_d_proposed_effective: number | null;
  expenses_proposed_effective: number | null;
}

export interface EditableProcessStepsResponse {
  rows: EditableProcessStepRow[];
}
