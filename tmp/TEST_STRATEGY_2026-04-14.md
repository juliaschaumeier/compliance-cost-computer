# Test-Strategie für vollständige Leitfaden-Robustheit

**Datum:** 2026-04-14
**Zweck:** Testkatalog, der Leitfaden-Konformität und interne Robustheit absichert. Begleitdokument zu `CODE_REVIEW_2026-04-14.md`.

**Prinzipien:**
- Jeder Test hat eine klare Leitfaden- oder Invariantenreferenz.
- Tests testen Verhalten, nicht Implementierung.
- LLM-Aufrufe werden gemockt; echte LLM-Calls nur in manuell getriggerter Smoke-Suite.
- Golden-Master-Files für Session-Snapshots.
- Property-based Tests (Hypothesis) für Invarianten.

---

## Schicht 1 — Invarianten der Domäne (property-based)

### 1.1 Normadressaten-Symmetrie
- **INV-SYM-001** Jeder Codepfad existiert für alle drei Adressaten — Parametrisierung pro Endpoint.
- **INV-SYM-002** Citizens haben nie Lohnsätze (DB-Constraint). ✓ Abgedeckt: `tests_review/invariants/test_citizens_effort_upsert_strips_hourly_rates.py`
- **INV-SYM-003** Citizens-Kosten-Response enthält keine `total_cost_eur`.
- **INV-SYM-004** `session_total_costs_by_addressee` existiert für alle drei. ✓ Abgedeckt.
- **INV-SYM-005** Undo scoped pro Adressat. ✓ Abgedeckt.

### 1.2 Fallzahl- und Zeitinvarianten
- **INV-CASE-001** Fallzahl ≥ 0.
- **INV-CASE-002** Gespiegelte Cluster haben identische Fallzahlen. ✓ Teilabgedeckt: `tests_review/mirror/test_mirror_value_identity.py`
- **INV-CASE-003** `cases = addressees × annual_frequency` ± ε.
- **INV-TIME-001** Zeit ≥ 0.
- **INV-TIME-002** Einmal/jährlich nicht doppelt.

### 1.3 Kosten-Invarianten
- **INV-COST-001** Kostensummen konsistent über Schritt/Fallgruppe/Prozess.
- **INV-COST-002** Business: `total = bureaucracy + other`.
- **INV-COST-003** Citizens: `total_cost_eur` undefiniert.
- **INV-COST-004** Sowieso reduziert ausgewiesenen Aufwand.
- **INV-COST-005** Rundung leitfadenkonform.

### 1.4 Referenzielle Invarianten
- **INV-REF-001** Keine Waisen.
- **INV-REF-002** Cascade-Delete vollständig.
- **INV-REF-003** Cross-Adressat-Kopplung verboten.

---

## Schicht 2 — LLM-Contract-Tests

### 2.1 JSON-Schema pro Stufe × Adressat (15 Verträge)
Für jede Kombination `(prompt_stage × norm_addressee)`:
- **LLM-VALID-happy** Wohlgeformter Output → korrekte Persistenz.
- **LLM-VALID-unknown-field** Unbekannte Felder → Warnung, aber kein Fail.
- **LLM-VALID-missing-required** Pflichtfeld fehlt → harte Exception.
- **LLM-VALID-wrong-type** Typ-Mismatch → Coercion oder Fail.
- **LLM-VALID-truncated** Abgeschnittenes JSON → erkannt.
- **LLM-VALID-extra-wrapper** `{"result": {...}}` oder Codefence → entpackt.
- **LLM-VALID-double-object** Zwei Objekte → definierter Gewinner.
- **LLM-VALID-null-pflichtfeld** → "unbekannt" vs. "0".

### 2.2 Adressaten-spezifische Vertragsbrüche
- **LLM-CTR-CIT-001** Citizens mit `rollen_gueltig` → Ablehnung.
- **LLM-CTR-CIT-002** Citizens mit `stundenlohn > 0` → Ablehnung.
- **LLM-CTR-BUS-001** Business ohne `ist_informationspflicht` trotz Info-Vorgabe → Warnung.
- **LLM-CTR-ADM-001** Admin mit unbekannter Laufbahn → Ablehnung.

### 2.3 Prompt-Regel-Tests
- **LLM-PRM-001** PROCESS_COMPILATION enthält Union/National-Regel.
- **LLM-PRM-002** EFFORT_CALCULATION Citizens: "keine Rollen, keine Lohngruppen".
- **LLM-PRM-003** EFFORT_CALCULATION Business: Anhang 4 + SKM.
- **LLM-PRM-004** EFFORT_CALCULATION Admin: Anhang 7/8, einmalig/jährlich.
- **LLM-PRM-005** REGULATIONS_IDENTIFICATION: Vorgaben-Definition + Info-Pflicht.
- **LLM-PRM-006** CASES_CALCULATION: Sowieso für alle drei Adressaten.
- **LLM-PRM-007** Kein stiller Default für `norm_addressee`.

### 2.4 Payload-Builder
- **LLM-PBL-001** `norm_addressee` in allen Pipeline-Stufen.
- **LLM-PBL-002** `mirror_anchor_key` in Tätigkeiten.
- **LLM-PBL-003** `is_mirror_target`, `canonical_side`, `is_sowieso` in Fallgruppen.
- **LLM-PBL-004** Citizens-Schema entfernt `rollen_gueltig`.

---

## Schicht 3 — Persistenz / Migration

### 3.1 Schema-Constraints
- **DB-CON-001** Citizens-Lohnsatz CHECK. ✓ Teilabgedeckt.
- **DB-CON-002** FK `process_step_regulation_links → process_steps`.
- **DB-CON-003** FK `mirror_matches → case_groups` bidirektional.
- **DB-CON-004** Unique-Constraint mirror.
- **DB-CON-005** Non-null auf Session-Totals.

### 3.2 Migrationstests
- **MIG-FWD-001** bis **MIG-FWD-004** Vorwärts, idempotent.
- **MIG-BCK-001** Backup vor destruktiven Schritten.
- **MIG-DATA-001/002** Zeilenzahlen und Spot-Checks vor/nach.

### 3.3 Transaktionen
- **TXN-001** Rollback bei Teilfehler.
- **TXN-002** Run-all Teilfehler → sauberer Status.
- **TXN-003** Parallele Adressaten-Calls isoliert.
- **TXN-004** Timeout-Rollback.

### 3.4 Undo und Re-Run
- **UNDO-001** bis **UNDO-005** Deterministik.

---

## Schicht 4 — Spiegel-Suite

### 4.1 Grundverhalten pro Paarung
- **MIR-BASE-a→b** / **MIR-BASE-b→a** für alle 3 Paarungen. ✓ Abgedeckt.
- **MIR-BASE-bidir-edit** Edit auf einer Seite propagiert. ✓ Teilabgedeckt.
- **MIR-BASE-identity** Cluster-Hash. ✓ Teilabgedeckt.

### 4.2 Reihenfolge
- **MIR-ORD-001/002** Run-all Standard + umgekehrt → gleiches Ergebnis.
- **MIR-ORD-003** Idempotent.
- **MIR-ORD-004** Zwei Läufe byte-identisch.

### 4.3 Kanonische Seite
- **MIR-CAN-001/002/003** Konfliktlösung, Pflichtwahl, Wechsel.

### 4.4 Delete-Verhalten
- **MIR-DEL-001** bis **MIR-DEL-004** Cascade und Waisen.

### 4.5 Re-Matching
- **MIR-RE-001** Stale-Cleanup vor Re-Run.
- **MIR-RE-002** Deterministik.
- **MIR-RE-003** Fantasie-IDs abgelehnt.

### 4.6 Enforcement
- **MIR-ENF-001/002/003** LLM-Output vs. persistierte Matches.

### 4.7 UI
- **MIR-UI-001/002/003** Lock-Icon, Warnung, Cluster-Übersicht.

---

## Schicht 5 — E2E-Workflow

### 5.1 Kanonische Szenarien (Golden-Master)
- **E2E-SCN-001** bis **E2E-SCN-009** Reine/gemischte Szenarien.

### 5.2 Vorwärts-Rückwärts
- **E2E-FWD-BCK-001** bis **E2E-FWD-BCK-004**

### 5.3 Bedienfehler
- **E2E-ERR-001** bis **E2E-ERR-008**

### 5.4 Eingabe-Edge-Cases
- **EDG-IN-001** bis **EDG-IN-010** (0, 10^9, Unicode, Zyklen, ...)

### 5.5 Ausgabe-Edge-Cases
- **EDG-OUT-001** bis **EDG-OUT-004** Rundungsgrenzen.

---

## Schicht 6 — LLM-Chaos

- **CHAOS-001** bis **CHAOS-010** Timeout, leer, Plaintext, Content-Filter, Provider-Fallback, etc.

---

## Schicht 7 — Frontend

### 7.1 Unit (React Testing Library)
- **UI-UNIT-001** bis **UI-UNIT-005**

### 7.2 API-Client
- **UI-API-001** `norm_addressee` als Pflichtparameter.
- **UI-API-002** Lint gegen hartcodiertes "administration".
- **UI-API-003** Fehlerresponses konsistent.

### 7.3 Playwright E2E
- **UI-E2E-001** bis **UI-E2E-007**

---

## Schicht 8 — Leitfaden-Regeln explizit

- **LF-K4-001** Vorgaben-Definition.
- **LF-K5-001** Info-Pflichten separat.
- **LF-K6-001/002** Fallgruppen und Spiegel.
- **LF-K7-001/002** Zeitwerttabellen, Wegezeiten.
- **LF-K8-001** Lohnkosten-Schemata.
- **LF-K9-001** Sowieso.
- **LF-K10-001** Union/National.
- **LF-K11-001/002** Rundung, einmalig/jährlich.
- **LF-K12-001** BKI.

---

## Schicht 9 — Regressions-Guardrails

- **REG-001** Ein Test pro Review-Befund. ✓ Teilabgedeckt in `tests_review/regressions/`.
- **REG-002** Golden-Master nur mit expliziter Aktualisierung.
- **REG-003** Prompt-Snapshot-Tests.
- **REG-004** DB-Schema-Snapshot.

---

## Schicht 10 — NFR

- **NFR-PERF-001/002** Performance.
- **NFR-LOAD-001** Parallele Sessions.
- **NFR-MEM-001** Leak-frei.
- **NFR-SEC-001/002/003** SQL-Injection, XSS, Secrets in Logs.

---

## Umsetzungsreihenfolge

1. **Sofort:** Schicht 1, Schicht 2.1, Schicht 3.1 — parallel zu Fix-Stufe 1.
2. **Kurz:** Schicht 4, Schicht 5.1, Schicht 5.2 — mit Spiegel-Refactor.
3. **Mittel:** Schicht 2.2–2.4, Schicht 3.2–3.4, Schicht 5.3–5.5, Schicht 7.
4. **Dauerhaft:** Schicht 6, Schicht 8, Schicht 9, Schicht 10.

---

## Infrastruktur

- Deterministischer Mock-LLM per Fixture-File.
- `tests/fixtures/scenarios/` für Golden-Master.
- Hypothesis für Property-Tests.
- Playwright für UI-E2E.
- DB-Consistency-Check als pytest-Fixture.
- CI-Jobs: `unit`, `integration`, `e2e`, `chaos` (nightly), `smoke-real-llm` (manuell).

---

## Aktueller Abdeckungsstand

| Schicht | Status | Dateien |
|---|---|---|
| 1.1 Normadressaten-Symmetrie | Teilabgedeckt | `tests_review/invariants/` |
| 1.2 Fallzahl-Invarianten | Teilabgedeckt (Mirror) | `tests_review/mirror/` |
| 2.1 JSON-Contract | Teilabgedeckt | `tests_review/contracts/` |
| 3.1 DB-Constraints | Teilabgedeckt | `tests/test_db_norm_addressee_constraints.py`, `tests_review/invariants/` |
| 4 Spiegel | Grundgerüst | `tests_review/mirror/`, `tests_review/regressions/` |
| 9 Regressions | Grundgerüst | `tests_review/regressions/` |

Nicht begonnen: Schichten 5 (E2E), 6 (Chaos), 7 (Frontend), 8 (Leitfaden-Regel-Tests), 10 (NFR).
