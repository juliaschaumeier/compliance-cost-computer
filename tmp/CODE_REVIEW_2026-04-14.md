# Code-Review: Erfüllungsaufwand-Rechner

**Datum:** 2026-04-14
**Basis:** Leitfaden StBA "Ermittlung und Darstellung des Erfüllungsaufwands in Regelungsvorhaben der Bundesregierung" (Februar 2026)
**Scope:** Backend (FastAPI + SQLite), Frontend (React/Next), LLM-Pipeline, alle drei Normadressaten (administration, business, citizens)

> **Korrektur-Vermerk:** Beim Schreiben der Begleit-Tests stellte sich heraus, dass **vier der ursprünglich als KRITISCH markierten Befunde** auf dem Branch `normaddressees-on-develop` bereits gefixt sind (1.1, 1.2, 1.3, 4.1). Die ersten Recherche-Durchläufe beruhten auf älteren Codestellen. Betroffene Befunde sind als **[BEHOBEN]** markiert und mit dem zementierenden Regression-Test verlinkt.

---

## Einordnung

Das System wurde zuerst für `administration` gebaut, `business` und `citizens` nachträglich ergänzt. Asymmetrien sind Folge dieser Entstehungsgeschichte. Der `normaddressees-on-develop`-Branch hat einen substanziellen Teil der Symmetrie-Arbeit bereits erledigt.

**Urteil vorab (revidiert):** Näher an Produktionsreife als erste Pass annahm. Offen: JSON-Robustheit, Bürokratiekosten-Bug, Spiegel-Edge-Cases, Leitfaden-Konformität (Sowieso, Union/National, Rundung).

---

## BLOCK 1 — Strukturelle Symmetrie

### [BEHOBEN ✓] 1.1 — Undo löscht adressatenübergreifend
**Tatsächlich:** [db.py:3656-3717](../backend/core/db.py#L3656-L3717) `clear_effort_metrics` scoped korrekt auf `WHERE session_id = ? AND norm_addressee = ?`.
**Regression-Guard:** [tests_review/invariants/test_clear_effort_metrics_is_addressee_scoped.py](../tests_review/invariants/test_clear_effort_metrics_is_addressee_scoped.py)

### [BEHOBEN ✓] 1.2 — `cc_cost` nur für Administration
**Tatsächlich:** Tabelle `session_total_costs_by_addressee` mit PK `(session_id, norm_addressee)` existiert. [db.py:3618](../backend/core/db.py#L3618).
**Regression-Guard:** [tests_review/invariants/test_session_total_costs_per_addressee.py](../tests_review/invariants/test_session_total_costs_per_addressee.py)

### [BEHOBEN ✓] 1.3 — Citizens können Lohnsätze persistieren
**Tatsächlich:** Upsert-Validation + DB-Trigger. [db.py:3440-3465](../backend/core/db.py#L3440-L3465).
**Regression-Guards:** [tests/test_db_norm_addressee_constraints.py](../tests/test_db_norm_addressee_constraints.py) (Trigger-Ebene) + [tests_review/invariants/test_citizens_effort_upsert_strips_hourly_rates.py](../tests_review/invariants/test_citizens_effort_upsert_strips_hourly_rates.py) (Application-Level, parametrisiert über alle 8 Slot/Phase-Kombinationen)

### [HOCH] 1.4 — `pay_rate_defaults` ist Admin/Bund-only
**Ort:** [db.py:199-258](../backend/core/db.py#L199-L258)
**Problem:** Tabelle ohne `norm_addressee`, PK `administration_level`, seed nur mit `bund`. Keine Wirtschaftsabschnitte A–S, keine Länder/Kommunen/Sozialversicherung.
**Empfehlung:** Refactor zu `(norm_addressee, bucket_key, qualification_level)` + vollständiges Seeding.

### [HOCH] 1.5 — Citizens-Slot-Modell
**Ort:** [norm_addressees.py:30-46](../backend/core/norm_addressees.py#L30-L46)
**Problem:** `EFFORT_GROUP_LABELS[CITIZENS]` hat Slots `b/c/d` als "Reserve". Semantisch nutzt Citizens nur `a`.
**Empfehlung:** Single-Slot-Modell oder `addressee_slots()`-Parametrisierung.

---

## BLOCK 2 — LLM-Prompts & Payload-Builder

### [KRITISCH] 2.1 — Silent Failure im JSON-Parsing
**Ort:** [llm_json.py:35-51](../backend/core/llm_json.py#L35-L51)
**Problem:** `parse_json_object_with_mode` gibt bei malformiertem Output stumm `None` zurück. Aufrufer: `if not isinstance(data, dict): return []`.
**Empfehlung:** Überall `require_json_object` verwenden; `parse_json_object` als Silent-Variante deprecaten.
**Guard:** xfail-strict in [tests_review/contracts/test_llm_json_robustness.py](../tests_review/contracts/test_llm_json_robustness.py) — wird grün, sobald `parse_json_object` hart wirft.

### [KRITISCH] 2.2 — Union/National-Bündelungsregel fehlt im Prompt
**Ort:** [prompts.py PROCESS_COMPILATION](../backend/core/prompts.py)
**Problem:** Keine Regel, dass Unionsrecht nicht mit nationalem Recht gebündelt werden darf.
**Empfehlung:** Harte Prompt-Regel.

### [HOCH] 2.3 — Sowieso-Kosten nur narrativ, nur für Citizens
**Problem:** Kein strukturiertes `ist_sowieso`-Feld in Payload/Output/DB. Regel nur für Citizens im Prompt.
**Empfehlung:** Sowieso-Flag an Vorgabe und Tätigkeit; für alle drei Adressaten.

### [HOCH] 2.4 — Effort-Prompt Business ohne Anhang-Referenzen
**Ort:** [prompts.py](../backend/core/prompts.py) ~Z.187-203
**Problem:** "Zeitwerttabelle Wirtschaft" ohne Anhang 4, SKM-Standardaktivitäten nur beiläufig.

### [MITTEL] 2.5 — Stiller Admin-Fallback im Prompt-Render
**Ort:** [prompts.py:1067](../backend/core/prompts.py#L1067)

---

## BLOCK 3 — Bürokratiekosten / Informationspflichten

### [KRITISCH] 3.1 — All-Regulations-Bug
**Ort:** [costs.py:132-148](../backend/routers/costs.py#L132-L148) `_list_business_information_step_ids`
**Problem:** Schritt wird nur als Bürokratiekosten gezählt, wenn **alle** verknüpften Vorgaben Informationspflichten sind. Gemischt verknüpfte Schritte fallen raus. Durch [tests/test_costs_flow.py](../tests/test_costs_flow.py) zementiert.
**Leitfaden:** Bürokratiekosten pro Informationspflicht separat ausweisen, auch innerhalb eines größeren Prozesses.
**Guard:** xfail-strict in [tests_review/regressions/test_review_block3_bureaucracy_mixed_regulations.py](../tests_review/regressions/test_review_block3_bureaucracy_mixed_regulations.py)

### [HOCH] 3.2 — `process_step_regulation_links` ohne FK auf `process_steps`
**Empfehlung:** Composite-FK mit CASCADE.

### [MITTEL] 3.3 — BKI-Persistenz fehlt

---

## BLOCK 4 — Spiegel-Logik

### [BEHOBEN ✓] 4.1 — Administration nie Sync-Ziel
**Tatsächlich:** [mirror_context.py:280-325](../backend/core/mirror_context.py#L280-L325) generisch.
**Regression-Guard:** [tests_review/regressions/test_review_block4_mirror_non_admin_target.py](../tests_review/regressions/test_review_block4_mirror_non_admin_target.py) — 6 Paarungen.
**Zusätzliche Guards:** [tests_review/mirror/test_mirror_value_identity.py](../tests_review/mirror/test_mirror_value_identity.py) — Identität, Edit-Propagation, `sync_cases=false`.

### [KRITISCH] 4.2 — Inkongruenz Prompt-Renderer vs. Sync-Logik
### [KRITISCH] 4.3 — Race Condition durch Adressaten-Reihenfolge
### [KRITISCH] 4.4 — Keine Post-Processing-Validierung für `sync_cases=1`
### [HOCH] 4.5 — Keine FK auf `mirror_matches` zu `case_groups`
### [HOCH] 4.6 — `delete_mirror_matches_for_session` ohne Aufrufer
### [HOCH] 4.7 — Bidirektionale Konsistenz nicht erzwungen
### [HOCH] 4.8 — Fehlende Tests für `citizens ↔ business`
### [MITTEL] 4.9 — Payload-Builder ohne Mirror-Metadaten
### [MITTEL] 4.10 — Fallback "implizite Heuristik"

---

## BLOCK 5 — Persistenz / Session

### [HOCH] 5.1 — "Run all" ohne Saga-Pattern
**Ort:** [sessions.py:399-484](../backend/routers/sessions.py#L399-L484)
**Belegt durch:** [tests/test_sessions_run_all.py::test_run_all_successful_restart_clears_transient_status_fields](../tests/test_sessions_run_all.py) — failt aktuell. Nach gezieltem Fehler im Business-Schritt bleibt die Session nach Neustart im `failed`-Status hängen, obwohl der Restart erfolgreich durchlaufen sollte.

### [HOCH] 5.2 — Legacy-Migration zweckentfremdet Admin-Spalten

---

## BLOCK 6 — Fehlerbehandlung

### [HOCH] 6.1 — LLM-Service ohne Timeout/Backoff
### [MITTEL] 6.2 — Rundungslogik nicht leitfadenkonform
### [MITTEL] 6.3 — Test-Lücken

---

## BLOCK 7 — Frontend

### [MITTEL] 7.1 — Hartcodierter Default `administration`
### [MITTEL] 7.2 — `norm_addressee` im API-Client optional

---

## Neue Befunde aus dem Test-Schreiben

- **Leerstring `""` in `normalize_norm_addressee`** — defaultete still auf Administration; **inzwischen gefixt**, Regression-Guard aktiv in [tests_review/invariants/test_norm_addressee_validation.py](../tests_review/invariants/test_norm_addressee_validation.py).
- **Fehlender `CITIZENS`-Import in [db.py:19-26](../backend/core/db.py#L19-L26)** — führte zu `NameError` in `update_session_pay_rate_edits_for_addressee`. In dieser Session als Quick-Fix behoben.

---

## Priorisierte Gesamtliste

**BEHOBEN (durch Regression-Tests zementiert):** 1.1, 1.2, 1.3, 4.1

**KRITISCH (offen):**
1. Silent-Failure-JSON-Parsing (Block 2.1)
2. Bürokratiekosten-All-Regulations-Bug (Block 3.1)
3. Union/National-Bündelungsregel (Block 2.2)
4. Run-all-Restart nach Teilfehler (Block 5.1) — durch bestehenden Test aktiv signalisiert
5. Mirror-Inkongruenz Renderer/Sync (Block 4.2)
6. Mirror-Race durch Adressaten-Reihenfolge (Block 4.3)
7. Mirror-Enforcement `sync_cases=1` (Block 4.4)
8. Mirror-FK auf `case_groups` (Block 4.5)
9. Mirror-Delete-Cleanup (Block 4.6)

**HOCH:** 1.4, 1.5, 2.3, 2.4, 3.2, 4.7, 4.8, 5.2, 6.1

**MITTEL/NIEDRIG:** 2.5, 3.3, 4.9, 4.10, 6.2, 6.3, 7.1, 7.2

---

## Urteil: Produktionsreife

**Administration:** Bedingt einsatzfähig. Strukturell sauber nach Symmetrie-Refactoring. Offen: Rundung, Sowieso, Union/National, JSON-Robustheit.

**Business:** Näher dran als zunächst angenommen. Offen: Bürokratiekosten-Bug, Pro-Tätigkeit-Info-Pflicht-Markierung, `pay_rate_defaults` für Wirtschaftsabschnitte.

**Citizens:** Näher dran. Lohnsatz-Schutz auf DB-Ebene aktiv. Offen: Silent-Failure beim JSON-Parsing, Sowieso-Persistenz.

**Gesamt:** Nicht produktionsreif für Gesetzgebung, aber 2–3 Sprints entfernt. Symmetrie-Arbeit auf `normaddressees-on-develop` ist substanziell.
