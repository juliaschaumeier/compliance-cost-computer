# Prompt- und DB-Flow

## Zweck

Diese Datei beschreibt knapp, welcher Prompt welche Daten erzeugt, wo sie gespeichert werden und welche Folgeschritte darauf zugreifen.

## Grobe Reihenfolge

1. `law_summary`
2. `regulations_identification`
3. `process_compilation`
4. `case_group_development`
5. `process_step_analysis`
6. `mirror_matching`
7. `cases_calculation`
8. `effort_calculation`
9. `total_cost` (kein LLM-Prompt)

Ab `process_compilation` laufen die Schritte getrennt pro Normadressat:

- `administration`
- `business`
- `citizens`

## 1. `law_summary`

Prompt-Quelle:
[backend/core/prompts.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/core/prompts.py)

Route:
[backend/routers/regulations.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/routers/regulations.py)

Speichert:

- `sessions.law_diff_title`
- `sessions.law_diff_blurb`
- `sessions.law_diff_summary`
- `sessions.current_law_id`
- `sessions.proposed_law_id`
- `law_tile`

Wird spaeter gelesen von:

- allen Folgeprompts ueber `{law_summary}`

## 2. `regulations_identification`

Route:
[backend/routers/regulations.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/routers/regulations.py)

Speichert:

- `regulations`
  - `legal_citation`
  - `description`
  - `change_status`
  - Normadressaten-Flags
  - Informationspflicht-Flag
  - Spiegelinfos:
    - `mirror_anchor_key`
    - `mirror_description`
    - Mirror-Adressaten-Flags
- Regulation-Tiles

Wird spaeter gelesen von:

- `process_compilation`
- Mirror-Kontext-Aufbau

## 3. `process_compilation`

Route:
[backend/routers/processes.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/routers/processes.py)

Input:

- Regulations der jeweiligen Normadressaten
- strukturierter Mirror-Kontext aus
  [backend/core/mirror_context.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/core/mirror_context.py)

Speichert:

- `processes`
- Verknuepfung Regulation -> Prozess
  - fuer Verwaltung direkt in `regulations.process_id`
  - fuer andere Normadressaten ueber addressee-spezifische Links
- Process-Tiles

Wird spaeter gelesen von:

- `case_group_development`
- Mirror-Kontext

## 4. `case_group_development`

Route:
[backend/routers/case_groups.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/routers/case_groups.py)

Input:

- Prozesse des jeweiligen Normadressaten
- zugeordnete Regulations
- strukturierter Mirror-Kontext

Speichert:

- `case_groups`
- Case-Group-Tiles

Wird spaeter gelesen von:

- `process_step_analysis`
- `mirror_matching`
- `cases_calculation`

## 5. `process_step_analysis`

Route:
[backend/routers/process_steps.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/routers/process_steps.py)

Input:

- Prozesse
- Fallgruppen
- Regulations
- strukturierter Mirror-Kontext

Speichert:

- `process_steps`
- Step-Tiles

Wird spaeter gelesen von:

- `effort_calculation`
- Mirror-Kontext

## 6. `mirror_matching`

Prompt:
[backend/core/prompts.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/core/prompts.py)

Logik:
[backend/core/mirror_context.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/core/mirror_context.py)

Ausfuehrung:
derzeit vor `cases_calculation` / `effort_calculation`

Input:

- bereits vorhandene Regulations
- Prozesse
- Fallgruppen
- Spiegelanker (`mirror_anchor_key`)

Speichert:

- `mirror_matches`
  - gemeinsame Situation
  - Source/Target-Normadressat
  - Source/Target-Prozess
  - Source/Target-Fallgruppe
  - `sync_addressees`
  - `sync_frequency`
  - `sync_cases`

Wird spaeter gelesen von:

- Mirror-Prompt-Kontext
- deterministische Fallzahl-Synchronisierung

## 7. `cases_calculation`

Route:
[backend/routers/effort.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/routers/effort.py)

Input:

- Prozesse
- Fallgruppen
- Regulations
- strukturierter Mirror-Kontext
- vorhandene `mirror_matches`

Speichert in `case_groups`:

- `addressees_current`
- `annual_frequency_current`
- `cases_current`
- `addressees_proposed`
- `annual_frequency_proposed`
- `cases_proposed`

Besonderheit:

- wenn `mirror_matches` ein klares `sync_cases = 1` vorgeben,
  werden Fallzahlen deterministisch von der Quellseite uebernommen

## 8. `effort_calculation`

Route:
[backend/routers/effort.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/routers/effort.py)

Input:

- Prozesse
- Fallgruppen
- Prozessschritte
- strukturierter Mirror-Kontext

Speichert in `process_steps`:

- Lohn-/Zeit-/Sachaufwand aktuell
- Lohn-/Zeit-/Sachaufwand vorgeschlagen
- `execution_per_case`

Wird spaeter gelesen von:

- `total_cost`
- Tile-Refresh

## 9. `total_cost`

Route:
[backend/routers/costs.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/routers/costs.py)

Input:

- Fallzahlen aus `case_groups`
- Aufwand pro Fall aus `process_steps`

Speichert:

- Kosten auf Step-/Prozess-/Session-Ebene
- aktualisierte Tiles

## Wo die Prompt-Kontexte zusammengesetzt werden

Datei:
[backend/core/prompts.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/core/prompts.py)

Wichtige Mechanik:

- `render_prompt(...)`
- zieht `law_summary` aus `sessions`
- haengt Normadressaten-spezifische Zusatztexte an
- befuellt `mirror_*_context` automatisch aus
  [backend/core/mirror_context.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/core/mirror_context.py)

## Kurzform zum Erklaeren

Jeder Prompt schreibt einen klaren Zwischenschritt in die DB, und der naechste Prompt liest genau diese strukturierte Vorstufe wieder ein. Die Pipeline ist also nicht nur eine Folge loser LLM-Antworten, sondern ein stufenweiser Datenaufbau: Zusammenfassung -> Vorgaben -> Prozesse -> Fallgruppen -> Schritte -> Spiegel-Matching -> Fallzahlen -> Aufwand -> Kosten.
