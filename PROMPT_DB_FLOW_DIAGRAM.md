# Prompt-DB-Flow Diagramm

```mermaid
flowchart TD
    A[law_summary] --> S[(sessions)]
    A --> LT[law_tile]

    S --> B[regulations_identification]
    B --> R[(regulations)]
    B --> RT[regulation_tiles]

    R --> C[process_compilation<br/>pro Normadressat]
    C --> P[(processes)]
    C --> PT[process_tiles]

    P --> D[case_group_development<br/>pro Normadressat]
    R --> D
    D --> CG[(case_groups)]
    D --> CGT[case_group_tiles]

    P --> E[process_step_analysis<br/>pro Normadressat]
    CG --> E
    R --> E
    E --> PS[(process_steps)]
    E --> PST[step_tiles]

    CG --> F[cases_calculation<br/>pro Normadressat]
    R --> F
    F --> CG

    PS --> G[effort_calculation<br/>pro Normadressat]
    CG --> G
    G --> PS

    CG --> H[total_cost]
    PS --> H
    H --> COST[(cost fields / aggregates)]

    subgraph Prompt Rendering
        S2[sessions summary]
        NA[norm addressee rules]
    end

    S2 --> C
    S2 --> D
    S2 --> E
    S2 --> F
    S2 --> G

    NA --> C
    NA --> D
    NA --> E
    NA --> F
    NA --> G
```

## Lesart

- `law_summary` schreibt die Zusammenfassung in `sessions`
- `regulations_identification` erzeugt `regulations`
- ab `process_compilation` laufen die Schritte getrennt pro Normadressat
- `cases_calculation` berechnet Fallzahlen pro Normadressat
- `effort_calculation` liest `process_steps` + `case_groups`
- `total_cost` ist rein deterministisch und nutzt die bereits gespeicherten Werte
