# Konsistenz und Stabilitaet von Aufwandsschaetzungen

## Ziel

Dieses Dokument haelt einen Arbeitsvorschlag fest, wie die Aufwandsschaetzungen des Tools und des LLM systematisch konsistenter, nachvollziehbarer und methodisch stabiler werden koennen.

Im Fokus stehen:

- Konsistenzpruefung
- quantitative Schaetzung
- Ursachen stark schwankender Betraege
- systematische Nutzung weiterer Handbuch-Inhalte

## Beobachtung

Stark schwankende Schaetzungen entstehen meist nicht durch einen einzelnen Modellfehler, sondern durch eine Kombination aus:

1. zu vielen freien Annahmen im LLM,
2. zu wenig methodischer Fuehrung im Prompt,
3. fehlender harter Validierung nach der LLM-Antwort.

## Hauptursachen fuer schwankende Betraege

### 1. Unterschiedliche Granularitaet

Ein Lauf modelliert wenige Fallgruppen oder Sammelschritte, ein anderer Lauf differenziert deutlich feiner. Dadurch veraendern sich Fallzahlen, Einzelfallaufwaende und Gesamtkosten bereits strukturell.

### 2. Freie Wahl von Zeitwerten und Schätzpfaden

Das Modell kann oft zwischen Tabellenwert, Erfahrungswert und freier Plausibilitaetsschaetzung wechseln. Ohne feste Leitplanken fuehrt das zu Drift.

### 3. Vermischung von laufendem und einmaligem Aufwand

Das Handbuch trennt diese Kategorien sauber. Wenn das Modell diese Trennung nicht stabil einhaelt, schwanken Ergebnisse erheblich.

### 4. Fehlende Wiederverwendung von Referenzankern

Aehnliche Taetigkeiten werden bei wiederholten Runs neu und unterschiedlich geschaetzt, statt auf bekannte Ankerwerte oder methodische Defaults zurueckzugreifen.

### 5. Spiegelprobleme zwischen Normadressaten

Bei logisch gekoppelten Sachverhalten sollten Fallzahlen oft gleich oder systematisch verbunden sein. Ohne harte Konsistenzpruefung driften die Schaetzungen fuer Buerger, Wirtschaft und Verwaltung auseinander.

### 6. Fehlende nachgelagerte Normierung

Auch vertretbare Rohantworten des LLM werden derzeit nicht konsequent auf methodische Konsistenz getrimmt.

## Strategischer Vorschlag

Der groesste Hebel ist nicht nur "mehr Handbuch im Prompt", sondern eine Kombination aus:

1. staerkerer methodischer Fuehrung vor dem LLM,
2. strukturierterem Output des LLM,
3. harter Konsistenz- und Plausibilitaetspruefung nach dem LLM,
4. gezielter Nutzung des Handbuchs als Regelwerk und Referenzanker.

## Verbesserungen vor dem LLM

### Klassifizieren vor Schaetzen

Prompts sollten staerker in einen methodischen Ablauf gezwungen werden.

Beispiele:

- Bei Fallzahlen zuerst entscheiden:
  - periodisch oder anlassbezogen
  - laufend oder einmalig
  - mit oder ohne Sowieso-Anteil
- Bei Aufwand pro Fall zuerst entscheiden:
  - welche Taetigkeitstypen vorliegen
  - welche Komplexitaetsstufe vorliegt
  - ob Tabellenwerte als Default anzuwenden sind

Ziel:

- weniger freie Freiheitsgrade
- weniger implizite Ad-hoc-Entscheidungen
- stabilere Schätzpfade

## Verbesserungen im LLM-Output

Das LLM sollte nicht nur Endwerte liefern, sondern zusaetzliche methodische Felder.

### Vorschlag fuer zusaetzliche Felder bei Fallzahlen

- `calculation_mode`: `periodic | event_based`
- `is_one_time`: `true | false`
- `addressee_count`
- `annual_frequency`
- `case_count`
- `sowieso_share`
- `mirror_anchor_key`
- `estimation_reason`
- `method_source`: `handbook_rule | handbook_example | table_default | own_estimate | external_source`

### Vorschlag fuer zusaetzliche Felder bei Aufwand pro Fall

- `activity_type`
- `complexity_level`: `simple | medium | high`
- `time_source`: `table | estimate | external`
- `time_reference`
- `wage_source`
- `expense_source`
- `is_per_case`: `true | false`
- `estimation_reason`

Ziel:

- bessere Auditierbarkeit
- bessere Konsistenzpruefung
- bessere Erklaerbarkeit, warum Werte so ausfallen

## Verbesserungen nach dem LLM

### Harte Konsistenzpruefung

Nach dem LLM sollte ein systematischer Validator laufen.

### Beispielregeln fuer Fallzahlen

- Wenn `calculation_mode = periodic`, dann muss gelten:
  - `case_count ~= addressee_count * annual_frequency`
- Wenn `calculation_mode = event_based`, dann sollen `addressee_count` und `annual_frequency` nicht frei konstruiert werden, wenn stattdessen direkt Jahresfaelle geschaetzt werden.
- Wenn `is_one_time = true`, dann darf der Wert nicht wie laufender Jahresaufwand behandelt werden.
- Wenn ein erheblicher `sowieso_share` angesetzt wird, muss dies begruendet sein.

### Beispielregeln fuer Spiegelbeziehungen

- Bei 1:1-Spiegelsachverhalten sollten Fallzahlen synchronisiert oder aktiv als Abweichung markiert werden.
- Wenn derselbe `mirror_anchor_key` auf mehreren Seiten auftaucht, muessen die abgeleiteten Fallzahlen logisch zusammenpassen.

### Beispielregeln fuer Aufwand pro Fall

- Bei Buergerinnen und Buergern darf Zeit nicht monetarisiert werden.
- Bei Wirtschaft und Verwaltung muss nachvollziehbar sein, woher Lohnsaetze stammen.
- Stark abweichende Werte fuer sehr aehnliche Taetigkeiten sollten geflaggt werden.
- Einmaliger Einfuehrungsaufwand darf nicht ohne weiteres als Aufwand pro Einzelfall vervielfacht werden.

## Nutzung des Handbuchs

Das Handbuch sollte kuenftig nicht nur als Prompt-Kontext, sondern als strukturierte methodische Referenz genutzt werden.

### 1. Entscheidungsregeln aus dem Handbuch ableiten

Beispiele:

- periodische Vorgabe -> Fallzahl ueber Haeufigkeit mal Betroffene
- anlassbezogene Vorgabe -> erwartete Jahresfaelle
- einmaliger Aufwand separat ausweisen
- Ersatzinvestitionen nur anteilig als Erfuellungsaufwand ansetzen
- Sowieso-Kosten beruecksichtigen
- automatisch ablaufende IT-Prozesse zunaechst ohne Zeitaufwand ansetzen

Diese Regeln sollten nicht nur im Prompt stehen, sondern auch im Validator technisch abgebildet werden.

### 2. Referenzanker aus dem Handbuch ableiten

Statt nur langer Beispielpassagen:

- kompakte Standardanker fuer typische Taetigkeiten
- typische Muster fuer Fallzahlen
- typische Muster fuer Spiegelbeziehungen
- typische Einordnung von einmaligem vs. laufendem Aufwand

Diese Anker koennen dem Modell helfen, bei aehnlichen Faellen konsistent zu bleiben.

### 3. Tabellen als echte Defaults behandeln

Die Tabellen des Handbuchs sollten methodisch staerker als Default verankert werden.

Das Modell sollte moeglichst angeben:

- ob ein Tabellenwert verwendet wurde,
- welche Komplexitaetsstufe gewaehlt wurde,
- warum davon abgewichen wurde.

## Empfohlene Architektur

### Ebene A: Prompting

- weniger offene Formulierungen
- staerkerer methodischer Ablauf
- klare Few-Shot-Beispiele
- klare Entscheidungsregeln

### Ebene B: Strukturierter Output

- zusaetzliche methodische Felder
- explizite Kennzeichnung von Schaetzpfad und Quellenart

### Ebene C: Validierung

- mathematische Konsistenzpruefungen
- Plausibilitaetspruefungen
- Spiegelpruefungen
- Warnungen bei methodischen Bruechen

### Ebene D: Kalibrierung

- kleines Benchmark-Set aus realen oder kuratierten Faellen
- Wiederholungslaufe messen
- Streuung dokumentieren
- Prompt- und Validator-Versionen gegeneinander vergleichen

## Vorschlag fuer eine Umsetzungsreihenfolge

### Phase 1

- Output-Schema um methodische Felder erweitern
- erste Konsistenzvalidatoren einfuehren

### Phase 2

- Prompts auf "klassifizieren vor schaetzen" umbauen
- mehr Handbuch-Regeln strukturiert einbauen

### Phase 3

- Referenzanker und Benchmark-Set aufbauen
- Streuung ueber mehrere Runs systematisch messen

### Phase 4

- optional einen zweiten LLM-Schritt als Reviewer oder Konsistenzpruefer einfuehren

Hinweis:
Ein zweiter Review-Schritt ist nur sinnvoll, wenn die harten Regeln und Validatoren zuerst stehen. Sonst wird nur eine weiche zweite Meinungsrunde auf unscharfer Grundlage erzeugt.

## Konkrete naechste Arbeitspakete

1. Bestehende JSON-Schemas fuer Fallzahl- und Aufwandsschaetzung analysieren und um methodische Felder erweitern.
2. Validator-Regeln fuer periodisch, anlassbezogen, einmalig, Spiegelbeziehung und Sowieso-Anteile definieren.
3. Relevante Handbuch-Regeln als strukturierte Referenzsammlung im Code hinterlegen.
4. Prompt-Schritte fuer Fallzahl und Aufwand so umbauen, dass zuerst methodische Klassifikation und dann numerische Schaetzung erfolgt.
5. Ein kleines Benchmark-Set mit wiederholbaren Testfaellen anlegen.

## Kurzfazit

Wenn konsistentere Schätzungen gewuenscht sind, reicht mehr Prompt-Text allein nicht aus.

Der nachhaltige Weg ist:

- weniger Freiheit im Schätzprozess,
- mehr methodische Struktur im Output,
- harte Validierung nach dem LLM,
- und die Nutzung des Handbuchs als Regelwerk, nicht nur als Lesestoff.
