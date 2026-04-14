# Spiegelsituationen: Technische Umsetzung

## Ziel

Spiegelsituationen werden nicht mehr nur als lose Prompt-Anweisung behandelt, sondern als persistierte, wiederverwendbare Datenstruktur im Workflow.

Ziel ist:

- Spiegelbeziehungen frueh zu erkennen
- konsistent ueber mehrere LLM-Schritte zu transportieren
- spaetere Fallzahl-Synchronisierung nicht frei schaetzen zu lassen, wenn ein fachlich klarer 1:1-Zusammenhang vorliegt

## 1. Erfassung bei der Vorgaben-Identifikation

Datei: [backend/routers/regulations.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/routers/regulations.py)

Beim Parsen der `vorgaben` wird `spiegelsituation` aus dem LLM-Output gelesen und normalisiert:

- `mirror_anchor_key`
- Spiegel-Normadressaten
- Spiegel-Beschreibung

Wichtig:

- der `mirror_anchor_key` wird normalisiert
- eigene Normadressaten werden aus der Spiegelseite herausgefiltert
- die Spiegelinfos werden in DB und Tile-Metadaten gespeichert

## 2. Persistenz in der Datenbank

Datei: [backend/core/db.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/core/db.py)

### Regulations

In `regulations` wurden zusaetzliche Felder aufgenommen:

- `mirror_applies_to_administration`
- `mirror_applies_to_business`
- `mirror_applies_to_citizens`
- `mirror_description`
- `mirror_anchor_key`

### Mirror-Matches

Zusaetzlich gibt es jetzt die Tabelle `mirror_matches`.

Sie speichert persistierte Zuordnungen zwischen Fallgruppen verschiedener Normadressaten:

- gemeinsamer `mirror_anchor_key`
- `shared_situation`
- Source/Target-Normadressat
- Source/Target-Prozess
- Source/Target-Fallgruppe
- `relation_type`
- `sync_addressees`
- `sync_frequency`
- `sync_cases`
- `reason`

Zugriff ueber:

- `list_mirror_matches(...)`
- `replace_mirror_matches(...)`
- `delete_mirror_matches_for_session(...)`

## 3. Zentrale Mirror-Logik

Datei: [backend/core/mirror_context.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/core/mirror_context.py)

Dieses Modul ist die zentrale technische Schicht fuer Spiegelsituationen.

Es macht drei Dinge:

1. Aufbau strukturierter Mirror-Cluster fuer Prompts
2. Ausfuehrung des expliziten `MIRROR_MATCHING`
3. deterministische Fallzahl-Synchronisierung auf Basis gespeicherter Matches

Wichtige Funktionen:

- `render_mirror_prompt_context(...)`
- `build_mirror_clusters_for_prompt(...)`
- `build_mirror_clusters_for_matching(...)`
- `ensure_mirror_matching(...)`
- `parse_mirror_matching_payload(...)`
- `apply_deterministic_mirror_case_group_sync(...)`

## 4. Prompt-Anbindung

Datei: [backend/core/prompts.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/core/prompts.py)

Die bestehenden Prompt-Platzhalter

- `mirror_process_context`
- `mirror_case_group_context`
- `mirror_step_context`
- `mirror_case_context`

werden jetzt beim Rendern automatisch aus `mirror_context.py` befuellt.

Das bedeutet:

- Prompts bekommen nicht nur allgemeinen Hinweistext zu Spiegelsituationen
- sondern konkreten strukturierten Spiegelkontext aus bereits bekannten Daten
- inklusive vorhandener `mirror_matches`

Zusaetzlich wurden die Prompt-Texte selbst verschaerft:

- strukturierter Spiegelkontext ist als verbindlicher Konsistenzrahmen beschrieben
- vorhandene Matches und Sync-Flags sind als autoritative Hinweise formuliert

## 5. Explizites Mirror-Matching im Workflow

Datei: [backend/routers/effort.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/routers/effort.py)

Vor der Fallzahl- und Aufwandsermittlung wird jetzt `ensure_mirror_matching(...)` aufgerufen.

Das heisst:

1. Falls bereits Matches existieren, werden sie nur dann wiederverwendet,
   wenn Anchor, Normadressaten sowie referenzierte Prozesse/Fallgruppen noch
   zur aktuellen Session-Struktur passen
2. Falls nicht, wird der `MIRROR_MATCHING`-Prompt ausgefuehrt
3. Das Ergebnis wird in `mirror_matches` persistiert

Damit wird Spiegel-Matching zu einem echten technischen Zwischenschritt und nicht nur zu einer losen Prompt-Idee.

## 6. Deterministische Synchronisierung

Ebenfalls in [backend/routers/effort.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/routers/effort.py):

Nach dem Parsen der Fallzahlen wird

- `apply_deterministic_mirror_case_group_sync(...)`

aufgerufen.

Logik:

- Wenn fuer eine Ziel-Fallgruppe ein persistiertes Match mit `sync_cases = 1` vorliegt,
  werden die Fallzahl-Werte von der Quellseite uebernommen
- das gilt jetzt symmetrisch auch dann, wenn `administration` die Zielseite ist
- nur wenn kein persistiertes Match vorliegt, greift die konservative Fallback-Logik ueber eindeutige 1:1-Anker

Damit werden klare Spiegel-Faelle nicht mehr auf beiden Seiten separat frei geschaetzt.

## 7. Tests

Relevante Tests:

- [tests/test_regulations_flow.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/tests/test_regulations_flow.py)
- [tests/test_payload_builders.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/tests/test_payload_builders.py)
- [tests/test_prompts.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/tests/test_prompts.py)
- [tests/test_effort_flow.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/tests/test_effort_flow.py)
- [tests/test_sessions_run_all.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/tests/test_sessions_run_all.py)

Abgedeckt werden insbesondere:

- Persistenz der Spiegelinfos
- Prompt-Kontext mit Mirror-Daten
- explizites Mirror-Matching
- deterministische Fallzahl-Synchronisierung
- Run-All-Kompatibilitaet

## Kurzfassung zum Weitergeben

Technisch haben wir Spiegelsituationen von einem reinen Prompt-Konzept zu einer persistierten Workflow-Struktur ausgebaut:

- Spiegelinfos werden schon bei den Vorgaben gespeichert
- spaeter in strukturierte Prompt-Kontexte eingespeist
- ueber einen eigenen Matching-Schritt explizit verbunden
- und bei klaren 1:1-Faellen fuer Fallzahlen deterministisch synchronisiert

Dadurch ist die Pipeline deutlich robuster und weniger von zufaelliger LLM-Konsistenz abhaengig.
