# Dokumentation des Tool-Ablaufs anhand des Traces vom 2026-04-14

Bezug:
- [Trace `20260414-200049_sessions-su98uc-run-all_03deacf2.md`](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/tmp/traces/20260414-200049_sessions-su98uc-run-all_03deacf2.md)
- [Review `REVIEW_2026-04-14.md`](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/REVIEW_2026-04-14.md)
- [Plan `REVIEW_2026-04-14_PLAN.md`](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/REVIEW_2026-04-14_PLAN.md)

## Zweck dieses Dokuments

Dieses Dokument erklaert, wie der Ablauf des Tools technisch zustande kommt und wie sich das konkret im vorhandenen Trace zeigt:

- wann das LLM aufgerufen wird,
- welche Daten jeweils an das LLM geschickt werden,
- wie die Normadressaten in die Pipeline eingehen,
- wie Antworten verarbeitet und gespeichert werden,
- warum im konkreten Trace nur `administration` und `business` auftauchen,
- und wie daraus die Spaeteren Review-Befunde ableitbar sind.

---

## Kurzfassung

Das Tool arbeitet in einer festen Pipeline:

1. Gesetz zusammenfassen
2. Vorgaben identifizieren
3. Prozesse bilden
4. Fallgruppen bilden
5. Prozessschritte bilden
6. Fallzahlen berechnen
7. Aufwand berechnen
8. Kosten deterministisch berechnen

Ab `processes` wird diese Pipeline getrennt pro Normadressat gefahren:

- `administration`
- `business`
- `citizens`

Wenn fuer einen Normadressaten inhaltlich nichts zu tun ist, wird der jeweilige Lauf geskippt. Dann gibt es fuer diesen Normadressaten keinen LLM-Prompt im Trace.

---

## Technischer Gesamtfluss

Der zentrale Einstieg ist `run-all` in [backend/routers/sessions.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/routers/sessions.py).

Die Reihenfolge der Schritte ist:

1. `summary`
2. `regulations`
3. `processes`
4. `case_groups`
5. `process_steps`
6. `effort`
7. `total_cost`

Davon sind nur die ersten beiden global fuer die Session. Ab `processes` wird intern ueber alle unterstuetzten Normadressaten iteriert:

- `administration`
- `business`
- `citizens`

Die Konstanten dafuer stehen in [backend/core/norm_addressees.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/core/norm_addressees.py).

Vereinfacht sieht der Ablauf so aus:

```text
Gesetz alt + neu
-> LAW_SUMMARY
-> REGULATIONS_IDENTIFICATION
-> pro Normadressat:
   -> PROCESS_COMPILATION
   -> CASE_GROUP_DEVELOPMENT
   -> PROCESS_STEP_ANALYSIS
   -> CASES_CALCULATION
   -> EFFORT_CALCULATION
-> TOTAL_COST ohne LLM
```

---

## Wann das LLM aufgerufen wird

Ein LLM-Call passiert immer dann, wenn ein Router einen Prompt rendert und ueber die LLM-Hilfsfunktionen abschickt.

Das Muster ist ueberall gleich:

1. Daten aus der DB lesen
2. Prompt-Payload bauen
3. Prompt rendern
4. LLM aufrufen
5. Antwort als `pending` speichern
6. Antwort parsen und validieren
7. Daten in die Session anwenden
8. Antwort auf `active` setzen

Die zentrale Query-/Staging-Logik liegt in:

- [backend/core/llm_attempts.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/core/llm_attempts.py)
- [backend/routers/_llm_router_utils.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/routers/_llm_router_utils.py)

Die Statuslogik der Antworten liegt in [backend/core/db.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/core/db.py):

- `pending`
- `active`
- `invalid`

Wichtig:

- `pending` bedeutet: das Modell hat geantwortet, aber die Antwort ist noch nicht erfolgreich auf die Session angewendet
- `active` bedeutet: die Antwort wurde erfolgreich verarbeitet
- `invalid` bedeutet: Query, Parsing oder Apply sind fehlgeschlagen oder wurden spaeter verdraengt

---

## Welche Daten an das LLM gehen

Das Tool schickt dem Modell nicht die ganze Session unstrukturiert, sondern je Stufe einen gezielt gebauten JSON-Payload.

Die Payloads werden in [backend/core/payload_builders.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/core/payload_builders.py) gebaut.

### 1. `law_summary`

Input:
- geltender Gesetzestext
- vorgeschlagener Gesetzestext

Output:
- `title`
- `blurb`
- `summary`

### 2. `regulations_identification`

Input:
- Gesetzestexte
- Zusammenfassung aus `law_summary`

Output:
- einzelne Vorgaben
- deren Aenderungsstatus
- betroffene Normadressaten
- Spiegelhinweise
- `mirror_anchor_key`

### 3. `process_compilation`

Input:
- Vorgaben fuer den betroffenen Normadressaten

Output:
- Prozesse
- Prozessbeschreibung
- Zuordnung der Vorgaben zu Prozessen

### 4. `case_group_development`

Input:
- Prozesse plus zugeordnete Vorgaben

Output:
- Fallgruppen pro Prozess

### 5. `process_step_analysis`

Input:
- Prozesse
- Fallgruppen
- Vorgaben

Output:
- Taetigkeiten/Schritte pro Fallgruppe

### 6. `cases_calculation`

Input:
- Prozesse
- Fallgruppen

Output:
- Anzahl Betroffene
- Haeufigkeit pro Jahr
- getrennt fuer `gueltig` und `vorschlag`

### 7. `effort_calculation`

Input:
- Prozesse
- Fallgruppen
- Taetigkeiten

Output:
- Zeitaufwaende
- Rollen/Lohngruppen bei Verwaltung und Wirtschaft
- Sachaufwaende
- Ausfuehrung pro Einzelfall

### 8. `total_cost`

Hier gibt es im Normalfall keinen LLM-Call mehr.

Die Kosten werden aus den vorher persistierten Fallzahlen und Aufwandsdaten deterministisch berechnet in [backend/routers/costs.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/routers/costs.py).

---

## Wie die Normadressaten in die Pipeline eingehen

Ab `processes` wird jeder Schritt fuer jeden Normadressaten getrennt ausgefuehrt.

Das ist wichtig, weil:

- jeder Adressat andere Prozesse haben kann,
- andere Fallgruppen plausibel sind,
- andere Zeit-/Kostenlogiken gelten,
- andere Prompt-Regeln gelten.

Die Prompts in [backend/core/prompts.py](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/backend/core/prompts.py) enthalten dafuer explizite Abschnitte wie:

- `Dieser Lauf betrifft den Normadressaten Verwaltung.`
- `Dieser Lauf betrifft den Normadressaten Wirtschaft.`
- `Dieser Lauf betrifft den Normadressaten Buergerinnen und Buerger.`

Der jeweilige Normadressat steuert damit:

- den Prompt-Text,
- die Auslegung des Falls,
- das erwartete JSON-Schema,
- die spaetere Persistenz in NA-spezifischen Tabellen-/Spaltenpfaden.

---

## Rolle der Normadressaten im konkreten Trace

Der Trace [tmp/traces/20260414-200049_sessions-su98uc-run-all_03deacf2.md](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/tmp/traces/20260414-200049_sessions-su98uc-run-all_03deacf2.md) zeigt insgesamt 16 Eintraege:

- 12 echte LLM-Erfolge
- 4 Fallback-Ereignisse

Die eigentlichen LLM-Schritte sind:

1. `law_summary`
2. `regulations_identification`
3. `process_compilation` fuer `administration`
4. `process_compilation` fuer `business`
5. `case_group_development` fuer `administration`
6. `case_group_development` fuer `business`
7. `process_step_analysis` fuer `administration`
8. `process_step_analysis` fuer `business`
9. `cases_calculation` fuer `administration`
10. `effort_calculation` fuer `administration`
11. `cases_calculation` fuer `business`
12. `effort_calculation` fuer `business`

Die Fallbacks sind:

13. Parser-Fallback zu `cases_calculation` fuer `administration`
14. Parser-Fallback zu `effort_calculation` fuer `administration`
15. Parser-Fallback zu `cases_calculation` fuer `business`
16. Parser-Fallback zu `effort_calculation` fuer `business`

### Zentrale Beobachtung

Im gesamten Trace taucht kein Prompt mit

`Dieser Lauf betrifft den Normadressaten Buergerinnen und Buerger.`

auf.

Das bedeutet mit hoher Wahrscheinlichkeit:

- `citizens` wurde im `run-all` zwar als Normadressat mitgedacht,
- aber fuer diesen konkreten Fall spaetestens ab `processes` fachlich geskippt,
- daher gab es keinen Buerger-spezifischen LLM-Call,
- und folglich auch keinen Trace-Eintrag.

Das passt zum Inhalt des Falls: Die identifizierten Vorgaben betreffen in der Antwort von `regulations_identification` nur:

- `business`
- `administration`

Nicht aber `citizens`.

---

## Wie man die Normadressaten im Trace erkennt

Die Normadressaten stehen nicht als eigenes Header-Feld ueber jedem Trace-Schritt, sondern im Prompttext selbst.

Beispiele aus dem Trace:

- `Dieser Lauf betrifft den Normadressaten Verwaltung.`
- `Dieser Lauf betrifft den Normadressaten Wirtschaft.`

Zusaetzlich sieht man in den Prompt-Payloads frueh:

- `normadressaten: ["administration", "business"]`

schon in den identifizierten Vorgaben. Dadurch wird spaeter nachvollziehbar, warum genau diese beiden Adressaten eigene Prozess- und Aufwandslinien bekommen.

---

## Wie Antworten verarbeitet werden

Der Ablauf nach einem LLM-Call ist entscheidend:

1. Antwort kommt vom Modell zurueck
2. Antwort wird in `llm_answers` als `pending` gespeichert
3. Antwort wird geparst
4. semantisch validiert
5. in DB-Strukturen uebernommen
6. bei Erfolg auf `active` gesetzt

Wenn es Probleme gibt:

- Query-Fehler -> `invalid`
- Parsing-/Apply-Fehler -> `invalid`
- aeltere Antworten desselben `(session, prompt, norm_addressee)` werden verdrängt

Das verhindert, dass eine blosse Modellantwort schon automatisch als gueltiger Session-Zustand gilt.

---

## Was die Fallbacks im Trace bedeuten

Die Schritte 11, 12, 15 und 16 sind keine neuen LLM-Aufrufe.

Sie bedeuten nur:

- beim Parsen der Modellantwort wurde ein Legacy-Key-Alias verwendet
- die Parserlogik war also tolerant gegenueber einer aelteren oder leicht abweichenden JSON-Struktur

Im Trace sieht man das an:

- gleichem `attempt_id` wie der echte LLM-Call davor
- keinem neuen Prompt
- keiner neuen Raw Response
- nur `fallback_kind`

Im konkreten Trace:

- `cases_legacy_key_alias`
- `effort_legacy_key_alias`

Das ist eher ein Hinweis auf Parser-Robustheit als auf einen inhaltlichen neuen Schritt.

---

## Warum die Review genau an diesen Stellen Probleme findet

Die Review [REVIEW_2026-04-14.md](/Users/hochstrasser/Documents/vscode/compliance-cost-computer/REVIEW_2026-04-14.md) analysiert im Grunde dieselbe Pipeline, aber nicht aus Sicht eines erfolgreichen LLM-Laufs, sondern aus Sicht von:

- Persistenz
- Korrektheit
- Undo
- Aggregation
- Prompt-Konsistenz
- Frontend-Verhalten

Der Trace zeigt bereits, dass das System normadressaten-spezifisch arbeitet. Die Review zeigt dann, wo diese Trennung noch nicht konsequent zu Ende gedacht ist.

Beispiele:

- Prompts sind bereits NA-spezifisch
- Persistenz und Session-Aggregation sind aber nicht ueberall sauber pro NA umgesetzt
- `run-all` arbeitet pro NA, Undo aber laut Review nicht fein genug
- `citizens` hat eigene Regeln, aber an mehreren Stellen fehlen noch Guards oder Post-Validierungen

Die Review ist deshalb im Kern keine freie Spekulation, sondern eine Bewertung der realen Ablaufarchitektur.

---

## Konkrete Interpretation dieses Traces

Fuer die Session `SU98UC` bedeutet der Trace:

1. Das Gesetz wurde zusammengefasst.
2. Es wurden zwei Vorgaben identifiziert.
3. Diese Vorgaben betreffen `administration` und `business`.
4. Fuer `administration` wurde eine eigene Vollzugslinie erzeugt:
   - Prozess
   - Fallgruppen
   - Schritte
   - Fallzahlen
   - Aufwand
5. Fuer `business` wurde eine eigene Aufwandslinie erzeugt:
   - Prozess
   - Fallgruppen
   - Schritte
   - Fallzahlen
   - Aufwand
6. Fuer `citizens` ist kein eigener LLM-Lauf sichtbar, also wurde dieser Zweig sehr wahrscheinlich fachlich geskippt.
7. Danach konnte das Backend auf Basis der gespeicherten Werte Kosten berechnen, ohne weiteren LLM-Aufruf.

---

## Schritt-fuer-Schritt-Tabelle

| Stufe | Typ | Input | LLM? | Output |
|---|---|---|---|---|
| `law_summary` | global | alte + neue Gesetzesfassung | ja | Titel, Blurb, Summary |
| `regulations_identification` | global | Gesetz + Summary | ja | Vorgaben, Aenderungsstatus, Normadressaten, Spiegelhinweise |
| `process_compilation` | pro Normadressat | Vorgaben des Adressaten | ja | Prozesse |
| `case_group_development` | pro Normadressat | Prozesse + Vorgaben | ja | Fallgruppen |
| `process_step_analysis` | pro Normadressat | Prozesse + Fallgruppen + Vorgaben | ja | Taetigkeiten/Schritte |
| `cases_calculation` | pro Normadressat | Prozesse + Fallgruppen | ja | Fallzahlen |
| `effort_calculation` | pro Normadressat | Prozesse + Fallgruppen + Schritte | ja | Zeit-/Sachaufwand |
| `total_cost` | pro Normadressat | persistierte Fallzahlen + Aufwand | nein | Kostenaggregation |

---

## Fazit

Der Trace bestaetigt den zentralen Architekturpunkt des Tools:

- globale Vorstufen fuer Gesetz und Vorgaben
- danach adressatenspezifische LLM-Pipelines
- anschliessend deterministische Kostenrechnung

Im vorliegenden Trace laufen nur `administration` und `business` sichtbar durch die LLM-Schritte. `citizens` taucht nicht als Prompt auf und wurde fuer diesen Fall sehr wahrscheinlich fachlich geskippt.

Genau diese Architektur erklaert auch, warum die Review so stark auf Multi-Normadressaten-Risiken fokussiert ist: Die eigentliche Pipeline ist bereits nach Normadressaten getrennt, aber nicht jede Persistenz-, Undo-, Aggregations- und UI-Stelle ist laut Review schon gleich sauber mitgezogen.
