# Prompt Rendering Overview

Stand: lokaler Branch `issue-26-step-analysis-prompts`.

Diese Datei beschreibt das Big Picture der Prompt-Pipeline und die Render-Logik
in `backend/core/prompts.py`. Sie ist als Arbeitsuebersicht gedacht: Welche
Prompts gibt es, welche Eingangsfelder werden eingesetzt, welche Felder fuellt
`render_prompt()` automatisch, und welche JSON-Struktur erwarten wir vom LLM?

## Big Picture

Der CCC-Workflow ist eine mehrstufige Pipeline. Jeder Schritt nimmt die
persistierten Ergebnisse des vorherigen Schritts, baut daraus ein JSON-Payload,
rendert daraus einen Prompt und schreibt die geparste LLM-Antwort wieder in die
DB.

```text
1. LAW_SUMMARY
   Gesetzestexte -> Kurzbeschreibung der Gesetzesaenderung

2. REGULATIONS_IDENTIFICATION
   Gesetzestexte -> Vorgaben

3. PROCESS_COMPILATION
   Vorgaben je Normadressat -> Prozesse

4. CASE_GROUP_DEVELOPMENT
   Prozesse je Normadressat -> Fallgruppen

5. PROCESS_STEP_ANALYSIS
   Prozesse + Fallgruppen je Normadressat -> fachliche Taetigkeiten

6a. CASES_CALCULATION
    Fallgruppen je Normadressat -> Fallzahlen

6b. EFFORT_CALCULATION
    Taetigkeiten je Normadressat -> Zeit-/Personal-/Sachaufwand

7. TOTAL_COST
   Fallzahlen + Aufwand -> Kosten
```

Wichtig: Schritt 6 besteht aus zwei LLM-Prompts, die im Code als Paerchen
ausgefuehrt werden:

```text
CASES_CALCULATION + EFFORT_CALCULATION
```

Die eigentliche Kostenberechnung (`total_cost`) ist kein eigener Prompt in
`backend/core/prompts.py`, sondern eine nachgelagerte Berechnung aus den
persistierten Fallzahlen und Aufwandwerten.

## Wo Gerendert Wird

Die zentrale Funktion ist:

```python
render_prompt(prompt_id: str, **kwargs: Any) -> str
```

Sie arbeitet in dieser Reihenfolge:

1. Template aus `PROMPT_TEMPLATES[prompt_id]` holen.
2. `kwargs` in `render_values` kopieren.
3. Bei mehrstufigen NA-Prompts `norm_addressee` verlangen und validieren.
4. Gemeinsame und prompt-spezifische Platzhalter automatisch setzen.
5. Falls noetig Gesetzestexte (`gesetz_gueltig`, `gesetz_vorschlag`) aus der DB nachladen.
6. Python-String-Formatierung ausfuehren:

```python
prompt = template.format(**appendix_values, **render_values)
```

## Normadressaten-Logik

Die meisten Pipeline-Prompts laufen je Normadressat:

```text
administration
business
citizens
```

Fuer diese Prompts muss `norm_addressee` explizit uebergeben werden:

```text
PROCESS_COMPILATION
CASE_GROUP_DEVELOPMENT
PROCESS_STEP_ANALYSIS
CASES_CALCULATION
EFFORT_CALCULATION
```

`render_prompt()` setzt dafuer zentral:

```text
{norm_addressee_context}
{norm_addressee_rule}
```

`norm_addressee_context` kommt aus `NORM_ADDRESSEE_PROMPT_OPENINGS` und erklaert
den Normadressaten allgemein.

`norm_addressee_rule` kommt je nach Normadressat aus:

```text
ADMINISTRATION_PROMPT_RULES
BUSINESS_PROMPT_RULES
CITIZENS_PROMPT_RULES
```

Bei `PROCESS_STEP_ANALYSIS` gibt es zusaetzliche, eigene Bausteine:

```text
{step_analysis_addressee_context}
{step_analysis_addressee_rule}
{step_analysis_checklist}
```

Diese sind bewusst enger als die allgemeinen Normadressaten-Regeln: Sie
beschreiben nur, welche Taetigkeiten in der Schrittanalyse zum jeweiligen
Normadressaten gehoeren.

## Gemeinsames Opening

Mehrere Prompts verwenden `LEGIST_PROMPT_OPENING`. Es soll nur den gemeinsamen
Kontext setzen, aber keinen konkreten Arbeitsschritt vorwegnehmen:

```text
Rolle: Legist im Bundestag
Gegenstand: Erfuellungsaufwandsaenderung
Grundbegriff: Aufwand durch Befolgung gesetzlicher Vorgaben
gesetz_gueltig: konsolidierter geltender Gesetzestext
gesetz_vorschlag: konsolidierter vorgeschlagener Gesetzestext
```

Der konkrete Auftrag steht danach im jeweiligen Prompt-Template, z. B.
Vorgaben identifizieren, Prozesse buendeln, Taetigkeiten identifizieren oder
Aufwand schaetzen.

## Hauptprompt-Bausteine

Diese Tabelle zeigt, welche groesseren Textbausteine in welchem Hauptprompt
wirklich eingesetzt werden. Wichtig: `render_prompt()` kann intern Werte
vorbereiten, aber sichtbar werden sie nur, wenn das Template den passenden
Platzhalter enthaelt.

| PromptId | Eingesetzte Hauptbausteine | Kurzinhalt |
|---|---|---|
| `LAW_SUMMARY` | kein `LEGIST_PROMPT_OPENING`; direkter Template-Text | Rolle als Legist; Gesetzestexte vergleichen; `title`, `blurb`, `summary` erzeugen. |
| `REGULATIONS_IDENTIFICATION` | `LEGIST_PROMPT_OPENING` | Gemeinsamer Erfuellungsaufwand-Kontext; dann Vorgaben identifizieren, Normadressaten bestimmen, Informationspflicht Wirtschaft markieren. |
| `PROCESS_COMPILATION` | `LEGIST_PROMPT_OPENING`, `{norm_addressee_context}`, `{norm_addressee_rule}`, ggf. `{handbook_process_example}` | Allgemeiner NA-Kontext; Vorgaben eines Normadressaten zu Prozessen buendeln; NA-spezifische Prozessregeln; fuer Business ein Leitfadenbeispiel. |
| `CASE_GROUP_DEVELOPMENT` | `LEGIST_PROMPT_OPENING`, `{norm_addressee_context}`, `{norm_addressee_rule}`, ggf. `{handbook_case_group_example}` | Allgemeiner NA-Kontext; Prozesse in Fallgruppen differenzieren; NA-spezifische Fallgruppenregeln; fuer Business ein Leitfadenbeispiel. |
| `PROCESS_STEP_ANALYSIS` | `LEGIST_PROMPT_OPENING`, `{step_analysis_addressee_context}`, `{step_analysis_addressee_rule}`, `{step_analysis_checklist}` | Kein allgemeines `{norm_addressee_context}`; stattdessen enger Step-Analysis-Kontext. Identifiziert Taetigkeiten, grenzt den Normadressaten fachlich ab, nutzt passende Checkliste, schaetzt noch keinen Aufwand. |
| `CASES_CALCULATION` | `LEGIST_PROMPT_OPENING`, `{norm_addressee_context}`, `{norm_addressee_rule}`, `{handbook_cases_frequency_example}`, ggf. `{handbook_cases_case_example}` | Allgemeiner NA-Kontext; Fallzahlen je Fallgruppe bestimmen; NA-spezifische Fallzahlregeln; Frequency-Beispiel fuer alle, Citizens-Fallzahlbeispiel nur fuer Citizens. |
| `EFFORT_CALCULATION` | `LEGIST_PROMPT_OPENING`, `{norm_addressee_context}`, `{effort_method_guidance}`, `{effort_appendix}`, `{effort_json_schema}` | Allgemeiner NA-Kontext; Aufwand je Taetigkeit schaetzen; NA-spezifische Methodik, Tabellen/Anhaenge und JSON-Schema. |

### Welche Bausteine Gibt Es?

| Baustein | Wo definiert | Wird eingesetzt in | Inhalt |
|---|---|---|---|
| `LEGIST_PROMPT_OPENING` | `backend/core/prompts.py` | alle PromptIds ausser `LAW_SUMMARY` | Rolle, Erfuellungsaufwand-Grundbegriff, vollstaendige Gesetzestexte (`gesetz_gueltig`, `gesetz_vorschlag`). |
| `NORM_ADDRESSEE_PROMPT_OPENINGS` -> `{norm_addressee_context}` | `backend/core/prompts.py` | `PROCESS_COMPILATION`, `CASE_GROUP_DEVELOPMENT`, `CASES_CALCULATION`, `EFFORT_CALCULATION` | Allgemeiner Kontext fuer Verwaltung, Wirtschaft oder Citizens; was dieser Normadressat umfasst und was auszuschliessen ist. |
| `ADMINISTRATION_PROMPT_RULES` / `BUSINESS_PROMPT_RULES` / `CITIZENS_PROMPT_RULES` -> `{norm_addressee_rule}` | `backend/core/prompts.py` | `PROCESS_COMPILATION`, `CASE_GROUP_DEVELOPMENT`, `CASES_CALCULATION`; teilweise weitere PromptIds je Mapping | Prompt-spezifische Regeln pro Normadressat, z. B. Prozessbuendelung, Fallgruppenachsen, Fallzahlermittlung. |
| `PROCESS_STEP_ANALYSIS_ADDRESSEE_CONTEXTS` -> `{step_analysis_addressee_context}` | `backend/core/prompts.py` | nur `PROCESS_STEP_ANALYSIS` | Kurzer, enger Kontext: Dieser Lauf betrifft nur diesen Normadressaten und welche Art Taetigkeiten dazu gehoeren. |
| `PROCESS_STEP_ANALYSIS_ADDRESSEE_RULES` -> `{step_analysis_addressee_rule}` | `backend/core/prompts.py` | nur `PROCESS_STEP_ANALYSIS` | Adressatenspezifische Abgrenzung der Taetigkeiten: Verwaltungshandlungen, Unternehmenshandlungen, Buergerhandlungen. |
| `_PROCESS_STEP_ANALYSIS_CHECKLIST_*` -> `{step_analysis_checklist}` | `backend/core/prompts.py` | nur `PROCESS_STEP_ANALYSIS` | Leitfaden-Checkliste je Normadressat zur Identifikation plausibler Haupttaetigkeiten. |
| `EFFORT_METHOD_GUIDANCE` -> `{effort_method_guidance}` | `backend/core/prompts.py` | nur `EFFORT_CALCULATION` | Methodische Regeln zur Aufwandsschaetzung je Normadressat. |
| `EFFORT_APPENDICES` -> `{effort_appendix}` | `backend/core/prompts.py` | nur `EFFORT_CALCULATION` | Passende Leitfaden-Anhaenge, Zeitwert-/Lohnkostentabellen und Sachaufwand-Hinweise. |
| `EFFORT_JSON_SCHEMA_BY_ADDRESSEE` / `EFFORT_JSON_SCHEMA_DEFAULT` -> `{effort_json_schema}` | `backend/core/prompts.py` | nur `EFFORT_CALCULATION` | Konkretes JSON-Schema je Normadressat. Citizens ohne Rollen/Lohngruppen/Stundenlohn. |
| Handbook-Beispiele -> `{handbook_*}` | `backend/core/handbook_examples.py` | ausgewaehlte Prompts | Leitfadenbeispiele als Orientierung, ausdruecklich nicht als Sachverhalt des Regelungsvorhabens. |

### Wichtige Nicht-Dopplung

`PROCESS_STEP_ANALYSIS` nutzt **nicht** `{norm_addressee_context}` aus
`NORM_ADDRESSEE_PROMPT_OPENINGS`. Stattdessen nutzt es nur:

```text
{step_analysis_addressee_context}
{step_analysis_addressee_rule}
{step_analysis_checklist}
```

Dadurch erscheint im gerenderten Schrittanalyse-Prompt nicht gleichzeitig:

```text
Dieser Lauf betrifft den Normadressaten Wirtschaft.
Dieser Lauf betrifft nur den Normadressaten `business` ...
```

Es erscheint nur der Step-Analysis-spezifische Satz. Die allgemeine
Normadressaten-Opening-Logik wird fuer die anderen NA-Prompts genutzt.

## Prompt-Uebersicht

| PromptId | Pipeline-Schritt | Manuell uebergebene Hauptfelder | Automatisch gerenderte Felder | LLM-Output |
|---|---|---|---|---|
| `LAW_SUMMARY` | Start / Zusammenfassung | `gesetz_gueltig`, `gesetz_vorschlag` | Appendix-Werte | `title`, `blurb`, `summary` |
| `REGULATIONS_IDENTIFICATION` | Vorgaben bestimmen | `gesetz_gueltig`, `gesetz_vorschlag`; alternativ `session_id` fuer auto-load | `gesetz_gueltig`/`gesetz_vorschlag` aus Session, falls nicht direkt uebergeben | `vorgaben[]` |
| `PROCESS_COMPILATION` | Prozesse buendeln | `vorgaben_json`, `norm_addressee`, `session_id` | `gesetz_gueltig`/`gesetz_vorschlag` via LEGIST_PROMPT_OPENING (Session-auto-load), `norm_addressee_context`, `norm_addressee_rule`, ggf. `handbook_process_example` | `normadressat`, `prozesse[]` |
| `CASE_GROUP_DEVELOPMENT` | Fallgruppen entwickeln | `prozesse_json`, `norm_addressee`, `session_id` | `gesetz_gueltig`/`gesetz_vorschlag` via LEGIST_PROMPT_OPENING (Session-auto-load), `norm_addressee_context`, `norm_addressee_rule`, ggf. `handbook_case_group_example` | `normadressat`, `prozesse[].fallgruppen[]` |
| `PROCESS_STEP_ANALYSIS` | Taetigkeiten identifizieren | `case_groups_json`, `norm_addressee`, `session_id` | `gesetz_gueltig`/`gesetz_vorschlag` via LEGIST_PROMPT_OPENING (Session-auto-load), `step_analysis_addressee_context`, `step_analysis_addressee_rule`, `step_analysis_checklist` | `normadressat`, `prozesse[].fallgruppen[].taetigkeiten[]` |
| `CASES_CALCULATION` | Fallzahlen bestimmen | `case_groups_json`, `norm_addressee`, `session_id` | `gesetz_gueltig`/`gesetz_vorschlag` via LEGIST_PROMPT_OPENING (Session-auto-load), `norm_addressee_context`, `norm_addressee_rule`, `handbook_cases_frequency_example`, ggf. `handbook_cases_case_example` | Fallgruppen mit `anzahl_betroffene_*` und `haeufigkeit_pro_jahr_*` |
| `EFFORT_CALCULATION` | Aufwand schaetzen | `step_analysis_json`, `norm_addressee`, `session_id` | `gesetz_gueltig`/`gesetz_vorschlag` via LEGIST_PROMPT_OPENING (Session-auto-load), `norm_addressee_context`, `effort_method_guidance`, `effort_appendix`, `effort_json_schema` | Taetigkeiten mit Aufwandfeldern |

## Prompt-Details Nach Schritt

### 1. `LAW_SUMMARY`

Zweck:

```text
Geltendes Gesetz und Gesetzesvorschlag vergleichen.
Ziel und wesentliche Unterschiede der Gesetzesaenderung zusammenfassen.
```

Input-Platzhalter:

```text
{gesetz_gueltig}
{gesetz_vorschlag}
```

Erwartetes JSON:

```json
{
  "title": "",
  "blurb": "",
  "summary": ""
}
```

### 2. `REGULATIONS_IDENTIFICATION`

Zweck:

```text
Alle relevanten Vorgaben aus geltendem und vorgeschlagenem Gesetz erkennen.
Normadressaten bestimmen.
Informationspflichten der Wirtschaft markieren.
```

Input-Platzhalter:

```text
{gesetz_gueltig}    (in LEGIST_PROMPT_OPENING; auto-load via session_id moeglich)
{gesetz_vorschlag}  (in LEGIST_PROMPT_OPENING; auto-load via session_id moeglich)
```

Erwartetes JSON:

```json
{
  "vorgaben": [
    {
      "normzitat": "",
      "beschreibung": "",
      "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft",
      "normadressaten": ["administration | business | citizens"],
      "ist_informationspflicht_wirtschaft": "0 | 1"
    }
  ]
}
```

### 3. `PROCESS_COMPILATION`

Zweck:

```text
Vorgaben eines Normadressaten zu fachlich zusammenhaengenden Prozessen buendeln.
```

Input-Platzhalter:

```text
{vorgaben_json}
{norm_addressee}
{gesetz_gueltig}    (in LEGIST_PROMPT_OPENING; auto-load via session_id)
{gesetz_vorschlag}  (in LEGIST_PROMPT_OPENING; auto-load via session_id)
{norm_addressee_context}
{norm_addressee_rule}
{handbook_process_example}
```

Payload-Quelle:

```text
build_vorgaben_payload(...)
dump_prompt_json(...)
```

Erwartete Kernfelder:

```json
{
  "normadressat": "administration | business | citizens",
  "prozesse": [
    {
      "prozess_bezeichnung": "",
      "prozess_beschreibung": "",
      "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft",
      "vorgaben": [
        {
          "vorgaben_id": "",
          "normzitat": "",
          "beschreibung": "",
          "aenderungsstatus": ""
        }
      ]
    }
  ]
}
```

Hinweis:

```text
Das Feld `normadressat` wird mit dem konkreten Wert gerendert, z. B.
"business". Das LLM soll den Wert nicht aus einer Liste auswaehlen.
```

### 4. `CASE_GROUP_DEVELOPMENT`

Zweck:

```text
Prozesse nach wesentlich unterschiedlichen Erfuellungswegen in Fallgruppen
unterteilen.
```

Input-Platzhalter:

```text
{prozesse_json}
{norm_addressee}
{gesetz_gueltig}    (in LEGIST_PROMPT_OPENING; auto-load via session_id)
{gesetz_vorschlag}  (in LEGIST_PROMPT_OPENING; auto-load via session_id)
{norm_addressee_context}
{norm_addressee_rule}
{handbook_case_group_example}
```

Payload-Quelle:

```text
build_processes_payload_with_regulations(...)
dump_prompt_json(...)
```

Erwartete Kernfelder:

```json
{
  "normadressat": "administration | business | citizens",
  "prozesse": [
    {
      "prozess_id": "",
      "prozess_bezeichnung": "",
      "prozess_beschreibung": "",
      "aenderungsstatus": "",
      "vorgaben": [],
      "fallgruppen": [
        {
          "fallgruppe_bezeichnung": "",
          "fallgruppe_beschreibung": "",
          "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft"
        }
      ]
    }
  ]
}
```

### 5. `PROCESS_STEP_ANALYSIS`

Zweck:

```text
Nur fachlich relevante Haupttaetigkeiten je Prozess/Fallgruppe identifizieren.
Noch keine Minuten, Lohngruppen, Stundenloehne, Sachaufwaende oder Kosten
schaetzen.
```

Input-Platzhalter:

```text
{case_groups_json}
{norm_addressee}
{gesetz_gueltig}    (in LEGIST_PROMPT_OPENING; auto-load via session_id)
{gesetz_vorschlag}  (in LEGIST_PROMPT_OPENING; auto-load via session_id)
{step_analysis_addressee_context}
{step_analysis_addressee_rule}
{step_analysis_checklist}
```

Payload-Quelle:

```text
build_case_groups_payload(...)
dump_prompt_json(...)
```

Automatische Step-Analysis-Bausteine:

```text
step_analysis_addressee_context:
  Kurzkontext, welcher Normadressat analysiert wird.

step_analysis_addressee_rule:
  Adressatenspezifische Abgrenzung: welche Taetigkeiten gehoeren zu
  Verwaltung, Wirtschaft oder Buergerinnen/Buergern?

step_analysis_checklist:
  Leitfaden-Checkliste je Normadressat.
```

Zentrale Abgrenzung:

```text
Schaetzen Sie in diesem Schritt keine Minuten, Lohngruppen,
Stundenloehne, Sachaufwaende oder Kosten.
```

Diese Regel steht einmal zentral im Prompt-Body, nicht in jeder
adressatenspezifischen Rule.

Erwartete Kernfelder:

```json
{
  "normadressat": "administration | business | citizens",
  "prozesse": [
    {
      "prozess_id": "",
      "prozess_bezeichnung": "",
      "prozess_beschreibung": "",
      "aenderungsstatus": "",
      "vorgaben": [],
      "fallgruppen": [
        {
          "fallgruppen_id": "",
          "fallgruppe_bezeichnung": "",
          "fallgruppe_beschreibung": "",
          "aenderungsstatus": "",
          "taetigkeiten": [
            {
              "taetigkeit": "",
              "beschreibung": "",
              "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert"
            }
          ]
        }
      ]
    }
  ]
}
```

### 6a. `CASES_CALCULATION`

Zweck:

```text
Fallzahlen je Fallgruppe bestimmen: Anzahl Betroffene und Haeufigkeit pro Jahr
fuer geltende und vorgeschlagene Rechtslage.
```

Input-Platzhalter:

```text
{case_groups_json}
{norm_addressee}
{gesetz_gueltig}    (in LEGIST_PROMPT_OPENING; auto-load via session_id)
{gesetz_vorschlag}  (in LEGIST_PROMPT_OPENING; auto-load via session_id)
{norm_addressee_context}
{norm_addressee_rule}
{handbook_cases_frequency_example}
{handbook_cases_case_example}
```

Payload-Quelle:

```text
build_case_groups_payload(...)
dump_prompt_json(...)
```

Erwartete Kernfelder:

```json
{
  "normadressat": "administration | business | citizens",
  "prozesse": [
    {
      "fallgruppen": [
        {
          "anzahl_betroffene_gueltig": "",
          "haeufigkeit_pro_jahr_gueltig": "",
          "anzahl_betroffene_vorschlag": "",
          "haeufigkeit_pro_jahr_vorschlag": ""
        }
      ]
    }
  ]
}
```

### 6b. `EFFORT_CALCULATION`

Zweck:

```text
Aufwand je Taetigkeit und Fall schaetzen.
Je Normadressat gelten unterschiedliche Schemata und Methodenhinweise.
```

Input-Platzhalter:

```text
{step_analysis_json}
{norm_addressee}
{gesetz_gueltig}    (in LEGIST_PROMPT_OPENING; auto-load via session_id)
{gesetz_vorschlag}  (in LEGIST_PROMPT_OPENING; auto-load via session_id)
{norm_addressee_context}
{effort_method_guidance}
{effort_appendix}
{effort_json_schema}
```

Payload-Quelle:

```text
build_step_analysis_payload(...)
dump_prompt_json(...)
```

Automatische Effort-Bausteine:

```text
effort_method_guidance:
  Methodischer Hinweis je Normadressat.

effort_appendix:
  Passende Leitfaden-Anhaenge und Tabellen je Normadressat.

effort_json_schema:
  JSON-Schema je Normadressat.
```

Wichtige Unterschiede:

```text
administration:
  Rollen/Lohngruppen A-D, Stundenlohn, Zeitaufwand, Sachaufwand.

business:
  Rollen/Schwierigkeitsgrade A-D, Stundenlohn, Zeitaufwand, Sachaufwand,
  Buerokratiekosten-Hinweise.

citizens:
  Zeitaufwand und privater Sachaufwand, aber keine Rollen, Lohngruppen,
  Stundenloehne und keine generelle Monetarisierung der Zeit.
```

Gemeinsames Feld:

```text
ausfuehrung_pro_einzelfall
```

Dieses Feld markiert, ob eine Taetigkeit pro Einzelfall (`1`) oder einmal pro
gesamte Fallgruppe (`0`) ausgefuehrt wird. Die weitergehende fachliche
Klaerung zu einmaligem vs. laufendem Aufwand bleibt bewusst ausserhalb von
PR 32 und gehoert in Issue 25.

## Auto-Fill-Details in `render_prompt()`

### Immer verfuegbar: Appendix-Werte

Alle String-Felder aus `Appendix` werden als Formatwerte angeboten:

```python
appendix_values = {
    name: value
    for name, value in Appendix.__dict__.items()
    if not name.startswith("_") and isinstance(value, str)
}
```

### Gesetzestexte

`LEGIST_PROMPT_OPENING` enthaelt `{gesetz_gueltig}` und `{gesetz_vorschlag}`.
Alle Prompts, die `LEGIST_PROMPT_OPENING` einbinden, erhalten damit die
vollstaendigen Gesetzestexte. Falls `gesetz_gueltig` oder `gesetz_vorschlag`
nicht direkt uebergeben werden, laedt `render_prompt()` sie automatisch aus
der Session, wenn `session_id` oder `app_session_id` uebergeben wurde.

### Normadressat

Bei NA-Prompts:

```text
norm_addressee ist Pflicht.
norm_addressee muss in SUPPORTED_NORM_ADDRESSEES liegen.
```

Danach setzt `render_prompt()`:

```text
norm_addressee_context
norm_addressee_rule
```

### Handbook-Beispiele

Diese Platzhalter werden mit `setdefault()` befuellt und koennen theoretisch
ueberschrieben werden:

```text
handbook_process_example
handbook_case_group_example
handbook_cases_frequency_example
handbook_cases_case_example
```

Aktuelle Logik:

```text
PROCESS_COMPILATION:
  Business bekommt das Prozess-Beispiel aus dem Leitfaden.

CASE_GROUP_DEVELOPMENT:
  Business bekommt das Fallgruppen-Beispiel aus dem Leitfaden.

CASES_CALCULATION:
  Alle bekommen das Frequency-Beispiel.
  Citizens bekommen zusaetzlich das Citizens-Fallzahlbeispiel.
```

### Step Analysis

Nur fuer `PROCESS_STEP_ANALYSIS`:

```text
step_analysis_checklist
step_analysis_addressee_context
step_analysis_addressee_rule
```

Diese Werte werden direkt gesetzt, nicht per `setdefault()`. Externe Overrides
in `kwargs` werden dadurch nicht uebernommen.

### Effort Calculation

Nur fuer `EFFORT_CALCULATION`:

```text
effort_method_guidance
effort_appendix
effort_json_schema
```

Auch diese Werte werden direkt gesetzt, nicht per `setdefault()`.

## Router-Flow

Die Router bauen die fachlichen JSON-Payloads und uebergeben sie an
`render_prompt()`:

```text
regulations.py
  LAW_SUMMARY
  REGULATIONS_IDENTIFICATION

processes.py
  PROCESS_COMPILATION

case_groups.py
  CASE_GROUP_DEVELOPMENT

process_steps.py
  PROCESS_STEP_ANALYSIS

effort.py
  CASES_CALCULATION
  EFFORT_CALCULATION
```

Danach laeuft jeweils:

```text
render_prompt(...)
query_and_stage_or_http(...) / query_and_stage_llm_answers_parallel(...)
LLM-Antwort parsen
DB schreiben
LLM-Antwort als applied markieren
```

Bei `effort.py` werden `CASES_CALCULATION` und `EFFORT_CALCULATION` als
gemeinsame Specs gebaut und parallel/staged verarbeitet.

## Persistenz und Pruefbarkeit

Die gerenderte Prompt-Version wird in `llm_answers.prompt_text` gespeichert.
Dadurch kann man spaeter in der DB sehen:

```text
Welcher Prompt wurde tatsaechlich an das LLM geschickt?
Welche Antwort kam darauf zurueck?
Welcher prompt_id/model/provider/attempt gehoerte dazu?
```

Zusaetzlich kann `prompt_audit` Markdown-Dateien schreiben, wenn
`PROMPT_AUDIT_ENABLED` aktiv ist.

## Review-Hinweise Fuer PR 32

Die aktuelle lokale Richtung ist:

```text
Ein gemeinsames neutrales LEGIST_PROMPT_OPENING.
Keine zusaetzliche LEGIST_CONTEXT_OPENING-Schicht.
PROCESS_STEP_ANALYSIS beschreibt zentral: keine Schaetzung in diesem Schritt.
Adressatenspezifische Step-Analysis-Rules beschreiben nur noch, welche
Taetigkeiten zum Normadressaten gehoeren.
```

Damit soll die Struktur leichter lesbar bleiben:

```text
Gemeinsamer Kontext
-> konkreter Prompt-Auftrag
-> fachliche Normadressaten-Abgrenzung
-> Output-Schema
```
