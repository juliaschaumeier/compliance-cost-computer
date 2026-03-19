```mermaid
classDiagram
  class laws {
    INTEGER document_id [PK]
    TEXT file_name
    TEXT law_text
    INTEGER text_length
    TEXT uploaded_at
  }

  class sessions {
    INTEGER session_id [PK]
    TEXT app_session_id [UIDX]
    TEXT created_at
    TEXT llm_model
    INTEGER current_law_id [FK, IDX]
    INTEGER proposed_law_id [FK, IDX]
    TEXT law_diff_title
    TEXT law_diff_summary
    REAL cc_cost
  }

  class tiles {
    INTEGER session_id [PK, FK, IDX]
    TEXT id [PK]
    TEXT title
    TEXT text
    JSON meta
    INTEGER col
    INTEGER row
    INTEGER deletable
  }

  class links {
    INTEGER session_id [PK, IDX]
    TEXT source [PK, FK, IDX]
    TEXT target [PK, FK, IDX]
  }

  class llm_answers {
    INTEGER answer_id [PK]
    INTEGER session_id [FK, IDX]
    TEXT prompt_id [IDX]
    TEXT model
    TEXT answer_text
    JSON metadata
    INTEGER input_tokens
    INTEGER output_tokens
    INTEGER hidden_thinking_tokens
    REAL estimated_cost_usd
    JSON provider_response_json
    TEXT answer_state [IDX]
    TEXT state_reason
    TEXT created_at
  }

  class web_sources_sessions {
    INTEGER source_id [PK]
    INTEGER session_id [FK, IDX]
    TEXT exact_url
    TEXT direct_quote
    TEXT accessed_at
    TEXT url_validation
    TEXT quote_validation
    TEXT validated_at
  }

  class regulations {
    INTEGER regulation_id [PK]
    INTEGER process_id [FK, IDX]
    INTEGER session_id [FK, IDX]
    TEXT legal_citation
    TEXT description
    TEXT change_status
    TEXT created_at
  }

  class web_sources_regulations {
    INTEGER source_id [PK]
    INTEGER regulation_id [FK, IDX]
    TEXT exact_url
    TEXT direct_quote
    TEXT accessed_at
    TEXT url_validation
    TEXT quote_validation
    TEXT validated_at
  }

  class processes {
    INTEGER process_id [PK]
    INTEGER session_id [FK, IDX]
    TEXT process
    TEXT description
    TEXT change_status
    TEXT created_at
    REAL cost
  }

  class web_sources_processes {
    INTEGER source_id [PK]
    INTEGER process_id [FK, IDX]
    TEXT exact_url
    TEXT direct_quote
    TEXT accessed_at
    TEXT url_validation
    TEXT quote_validation
    TEXT validated_at
  }

  class case_groups {
    INTEGER case_group_id [PK]
    INTEGER process_id [FK, IDX]
    INTEGER session_id [FK, IDX]
    TEXT case_group
    TEXT description
    TEXT change_status
    TEXT created_at
    REAL addressees_current
    REAL annual_frequency_current
    REAL cases_current
    REAL addressees_proposed
    REAL annual_frequency_proposed
    REAL cases_proposed
    REAL cost
  }

  class web_sources_case_groups {
    INTEGER source_id [PK]
    INTEGER case_group_id [FK, IDX]
    TEXT exact_url
    TEXT direct_quote
    TEXT accessed_at
    TEXT url_validation
    TEXT quote_validation
    TEXT validated_at
  }

  class process_steps {
    INTEGER step_id [PK]
    INTEGER case_group_id [FK, IDX]
    INTEGER session_id [FK, IDX]
    TEXT step
    TEXT description
    TEXT change_status
    TEXT created_at
    INTEGER previous_id
    INTEGER next_id
    REAL hourly_rate_a_current
    REAL hourly_rate_b_current
    REAL hourly_rate_c_current
    REAL hourly_rate_d_current
    REAL time_required_in_min_a_current
    REAL time_required_in_min_b_current
    REAL time_required_in_min_c_current
    REAL time_required_in_min_d_current
    REAL expenses_current
    REAL hourly_rate_a_proposed
    REAL hourly_rate_b_proposed
    REAL hourly_rate_c_proposed
    REAL hourly_rate_d_proposed
    REAL time_required_in_min_a_proposed
    REAL time_required_in_min_b_proposed
    REAL time_required_in_min_c_proposed
    REAL time_required_in_min_d_proposed
    REAL expenses_proposed
    REAL cost_current
    REAL cost_proposed
  }

  class web_sources_process_steps {
    INTEGER source_id [PK]
    INTEGER step_id [FK, IDX]
    TEXT exact_url
    TEXT direct_quote
    TEXT accessed_at
    TEXT url_validation
    TEXT quote_validation
    TEXT validated_at
  }

  sessions "0..*" --> "0..1" laws : current_law_id
  sessions "0..*" --> "0..1" laws : proposed_law_id

  tiles "0..*" --> "1" sessions : session_id
  links "0..*" --> "1" tiles : source_fk(session_id,id)
  links "0..*" --> "1" tiles : target_fk(session_id,id)

  llm_answers "0..*" --> "1" sessions : session_id
  web_sources_sessions "0..*" --> "1" sessions : session_id

  regulations "0..*" --> "1" sessions : session_id
  regulations "0..*" --> "0..1" processes : process_id
  web_sources_regulations "0..*" --> "1" regulations : regulation_id

  processes "0..*" --> "1" sessions : session_id
  web_sources_processes "0..*" --> "1" processes : process_id

  case_groups "0..*" --> "1" sessions : session_id
  case_groups "0..*" --> "1" processes : process_id
  web_sources_case_groups "0..*" --> "1" case_groups : case_group_id

  process_steps "0..*" --> "1" sessions : session_id
  process_steps "0..*" --> "1" case_groups : case_group_id
  web_sources_process_steps "0..*" --> "1" process_steps : step_id

  class index_legend {
    [PK] primary_key
    [FK] foreign_key
    [IDX] index
    [UIDX] unique_index
  }

  style tiles fill:#f3e8ff,stroke:#7c3aed,color:#111827
  style links fill:#f3e8ff,stroke:#7c3aed,color:#111827

  style sessions fill:#fef3c7,stroke:#d97706,color:#111827
  style regulations fill:#fef3c7,stroke:#d97706,color:#111827
  style processes fill:#fef3c7,stroke:#d97706,color:#111827
  style case_groups fill:#fef3c7,stroke:#d97706,color:#111827
  style process_steps fill:#fef3c7,stroke:#d97706,color:#111827

  style laws fill:#e0f2fe,stroke:#0284c7,color:#111827
  style llm_answers fill:#e0f2fe,stroke:#0284c7,color:#111827
  style web_sources_sessions fill:#e0f2fe,stroke:#0284c7,color:#111827
  style web_sources_regulations fill:#e0f2fe,stroke:#0284c7,color:#111827
  style web_sources_processes fill:#e0f2fe,stroke:#0284c7,color:#111827
  style web_sources_case_groups fill:#e0f2fe,stroke:#0284c7,color:#111827
  style web_sources_process_steps fill:#e0f2fe,stroke:#0284c7,color:#111827
  style index_legend fill:#f8fafc,stroke:#94a3b8,color:#111827
```

Relationship notes:
- `links` has no direct FK to `sessions`, but both `source` and `target` must resolve to `tiles(session_id, id)`, so links are effectively constrained to a single session.
- `regulations.process_id` is nullable (`0..1`) and uses `ON DELETE SET NULL`.
