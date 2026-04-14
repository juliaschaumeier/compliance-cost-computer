# Abarbeitungsplan zum Review vom 2026-04-14

Bezug: [REVIEW_2026-04-14.md](REVIEW_2026-04-14.md)

## Arbeitsprinzipien (verbindlich)

1. **Verifikation vor Aktion.** Jeder Befund wird unmittelbar vor dem Fix erneut im aktuellen Code geprüft. Der Review ist eine Momentaufnahme von Agent-Output — einzelne Befunde können falsch, schon gefixt oder in der beschriebenen Form nicht mehr zutreffend sein. Wenn die Prüfung ergibt, dass der Befund nicht mehr stimmt, wird er im Review als `~~verworfen~~` markiert, mit einem einzeiligen Grund.
2. **Ein Befund pro Commit.** Jede Änderung referenziert genau einen Befund (oder eine eng zusammengehörige Gruppe, z.B. Schema-Migration + zugehöriges UPDATE-Statement).
3. **Grüner Testlauf vor jedem Commit.** Nach jeder Änderung:
   - Betroffener Backend-Bereich: `pytest` auf mindestens dem relevanten Unterordner + ein Smoke-Lauf `pytest -x backend/tests` und `pytest -x tests_review`.
   - Betroffener Frontend-Bereich: `npm --prefix frontend test -- --run` (oder das projekt-übliche Kommando, falls abweichend — einmalig verifizieren).
   - Pro Fix wird zusätzlich ein **neuer Regressionstest** geschrieben, der den Befund festhält (red → green).
4. **Commit + Push nach jeder Änderung.** Commit-Message: `review(<block>): <kurzbeschreibung> (Befund #n)`. Push auf den aktuellen Branch `normaddressees-on-develop`. Keine force-pushes.
5. **Abbruchkriterium.** Wenn ein Fix eine strukturelle Änderung erfordert, die den nächsten Schritt blockiert oder bestehende Tests nicht mehr aussagekräftig sind, Stop und Rücksprache — nicht stumm weiterlaufen.
6. **Keine Feature-Drift.** Jeder Fix bleibt minimal. Keine Nebenrefactors, keine vorauseilenden Abstraktionen. Andere Befunde werden nicht „nebenbei mitgenommen".

## Reihenfolge-Logik

Die Priorisierung folgt nicht stur der Nummerierung des Reviews, sondern Abhängigkeit + Risiko:

- Zuerst **Datenintegrität** (falsche Zahlen in DB). Ein falsch gespeicherter Wert vergiftet alle späteren Berechnungen.
- Dann **Berechnungs-Korrektheit** (falsche Aggregation auf korrekt gespeicherten Daten).
- Dann **Pipeline-Robustheit** (atomare Sessions, Undo).
- Dann **Prompt-Korrektheit** (falsche LLM-Outputs).
- Dann **Frontend-Sicherheit** (stille Teilerfolge).
- Dann **Test-Absicherung** der bisher ungetesteten Pfade.
- Zuletzt **Hygiene-/MITTEL-Befunde**.

---

## Phase A — Datenintegrität (KRITISCH)

### A1. Step-Bürokratiekosten persistieren (Befund #7)
- **Vorab-Verifikation:** `upsert_process_step_cost_by_addressee` in [backend/core/db.py](backend/core/db.py) lesen. Prüfen, dass die Parameter `bureaucracy_cost_*`/`other_cost_*` tatsächlich deklariert, aber im UPDATE ignoriert werden und die Spalten im Schema fehlen. Falls sie mittlerweile existieren → Befund verwerfen.
- **Fix:** Schema-Migration (`ALTER TABLE process_steps ADD COLUMN …`) + UPDATE-Statement vervollständigen + Read-back über `resolve_effective_process_step_metrics` prüfen.
- **Test:** Integrationstest, der `compute_costs()` ausführt und über direkten DB-Read die `bureaucracy_cost_current > 0` verifiziert.

### A2. Citizens-Lohnsatz-Guard vor Insert (Befund #4)
- **Vorab-Verifikation:** Existierende Trigger in db.py + Input-Validierung in effort.py lesen.
- **Fix:** Pre-insert-Check `_assert_no_rates_for_citizens()` in der upsert-Funktion, harte `CITIZENS`-Konstante statt String.
- **Test:** Direkter Aufruf der Upsert-Funktion mit citizens+rate>0 → erwartet `ValueError`.

### A3. `mirror_matches` referenzielle Integrität (Befund #8)
- **Vorab-Verifikation:** Schema-Definition + alle Delete-Pfade für case_groups/processes auflisten.
- **Entscheidung:** FK + `ON DELETE CASCADE` (SQLite erfordert `PRAGMA foreign_keys=ON`, bestehende Tabelle muss neu angelegt werden) ODER Kompensations-DELETE in Delete-Pfaden. Der zweite Weg ist risikoärmer, wenn die Tabelle groß ist oder Fremd-Writer existieren — in diesem Projekt ist Variante 1 vermutlich sauberer. Entscheidung beim Implementieren anhand der tatsächlichen Schema-Definition.
- **Test:** case_group löschen → mirror_matches-Zeilen sind weg; Waisen-Szenario wird nicht mehr erzeugt.

### A4. Cascade-Delete räumt mirror_matches zu aggressiv (Befund #15)
- **Vorab-Verifikation:** Tatsächliches Verhalten in `delete_case_groups_for_session` und `delete_processes_for_session` prüfen.
- **Fix:** Auf `source_norm_addressee`/`target_norm_addressee` filtern.
- **Test:** Setup mit drei NAs + zwei Mirror-Paaren, NA-spezifisches Löschen erhält das andere Paar.
- **Hinweis:** Wenn A3 via CASCADE umgesetzt wird, überschneidet sich dieser Fix teilweise. Reihenfolge: A3 zuerst, dann A4 mit verbleibender Logik.

### A5. `apply_deterministic_mirror_case_group_sync` Pre-Check (Befund #16)
- **Vorab-Verifikation:** Tatsächlich existierende NULL-Pfade nachvollziehen.
- **Fix:** Skip bei NULL-Source-Metriken + Logging/Status.
- **Test:** Sync mit Source=NULL → Target bleibt unverändert.

---

## Phase B — Berechnungs-Korrektheit (KRITISCH)

### B1. `has_effort_metrics` vs. `_has_step_cost_inputs` (Befund #3)
- **Vorab-Verifikation:** Genaues Verhalten beider Funktionen an einem Citizens-Szenario reproduzieren (Test, der aktuell das Problem zeigt).
- **Fix:** `has_effort_metrics()` adressatspezifisch.
- **Test:** parametrisiert über alle NAs.

### B2. `sessions.cc_cost` Multi-NA-Aggregat (Befund #1)
- **Vorab-Verifikation:** Alle Leser von `sessions.cc_cost` identifizieren (Backend + Frontend + Tests). Liste bildet die Migrations-Oberfläche.
- **Fix:** Neue Spalten oder `session_totals_by_addressee`. Entscheidung: neue Tabelle ist sauberer, erzeugt aber mehr Migrations-Arbeit — bei aktueller Nutzungsbreite vermutlich sinnvoll.
- **Legacy:** `cc_cost` nicht sofort entfernen, sondern als Legacy-Alias beibehalten, bis alle Leser umgestellt sind (separate Commits).
- **Test:** Multi-NA-Session → alle drei Summen korrekt persistiert und gelesen.

---

## Phase C — Pipeline-Robustheit (KRITISCH)

### C1. `run-all` atomar pro NA + NA-spezifisches Undo (Befund #2)
- **Vorab-Verifikation:** Aktuelles Undo-Verhalten in `undo_step` und `llm_answers`-Invalidierung dokumentieren.
- **Fix:** SAVEPOINT pro NA-Schritt in `run-all`; `undo_step(norm_addressee=...)` nimmt Filter entgegen.
- **Test:** Fehlerhafte business-Stufe lässt admin+citizens unberührt; `undo_step(business)` berührt nur business-`llm_answers`.

---

## Phase D — Prompt-Korrektheit (KRITISCH/HOCH)

### D1. Citizens-Effort Post-Validation (Befund #6)
- **Fix:** Zentrale `_validate_effort_by_norm_addressee`. Aufruf nach Parsing, vor DB-Insert.
- **Test:** Mock-LLM liefert citizens+rate>0 → 422.

### D2. Rechtsquelle-Feld + PROCESS_COMPILATION-Guard (Befund #5)
- **Vorab-Verifikation:** VorgabePayload und REGULATIONS_IDENTIFICATION-Prompt lesen.
- **Fix:** Schema-Spalte, Prompt-Erweiterung, Payload-Erweiterung, deterministischer Pre-Check.
- **Test:** EU+national gemischt → 422 vor LLM-Call.
- **Hinweis:** Dieser Fix ist größer als die übrigen — prüfen, ob er vor der Frontend-Phase hingehört oder ob er als eigene Teil-Pipeline läuft.

### D3. IP-Flag Semantik + Reparatur zu Validation (Befund #11)
- **Fix:** Prompt-Wording schärfen; Router wirft 422 statt still zu reparieren (oder Audit-Event).
- **Test:** LLM setzt Flag ohne BUSINESS → klares Fehlerbild.

### D4. Admin-Regeln PROCESS_STEP_ANALYSIS NA-gated (Befund #13)
### D5. Citizens-Wegezeiten präzisieren (Befund #14)
### D6. VorgabePayload.normadressaten filtern (Befund #12)
- **Hinweis:** Dieser Fix kann Prompt-Regressionen erzeugen. Danach Snapshot-Tests der gerenderten Prompts.

---

## Phase E — Frontend-Sicherheit (KRITISCH/HOCH)

### E1. `TotalCostPanel` Promise.allSettled (Befund #9)
### E2. `AppContext` Default + Fallback (Befund #10)
### E3. EffortPanel/ProcessStepsPanel/CaseGroupsPanel Promise.allSettled (Befund #26)
### E4. `EaPayRatesTab` für citizens (Befund #18)
- **Vorab-Verifikation:** Aktuelles Tab-Verhalten im Browser-Smoke-Test prüfen, nicht nur im Code.

---

## Phase F — Sowieso-Kosten (HOCH)

### F1. `sowieso_kosten`-Flag (Befund #17)
- **Vorab-Verifikation:** Prüfen, ob es eine angrenzende Modellierung (z.B. `effort_relevant`) bereits gibt, die den Zweck erfüllt. Falls ja, Befund verwerfen oder zu Rename reduzieren.
- **Fix:** Schema + Prompt + Filter in `processes.py` und `costs.py`.

---

## Phase G — Test-Absicherung (HOCH)

### G1. Backend-Flow-Tests NA-parametrisieren (Befund #20)
### G2. Frontend-Tests NA-parametrisieren (Befund #19)
### G3. citizens↔business-Spiegel Integrationstest (Befund #21)
### G4. `format_currency` gegen Leitfaden-Beispiele (Befund #34)
### G5. Malformed-JSON-Pfad (Block 2.7)

---

## Phase H — Restliche HOCH-Befunde

H1–H10: Pay-rates-defaults-Guard (#28), Admin-Laufbahn-Alias (#24), IP-Flag-CHECK (#22), Schritt↔Regulation-Assertion (#23), Migration-Idempotenz (#25), Timeout/Backoff (#29), Citizens-Input-Post-Parse (#30), NA-Prompt-Register (#27), Prompt „Bürokratiekosten später" vs Pipeline (Block 2 Schluss).

Reihenfolge innerhalb H ergibt sich aus Abhängigkeit beim Abarbeiten — bei Bedarf dynamisch.

---

## Phase I — MITTEL

I1–I4: `_mirror_matches_are_current` (#31), `NORM_ADDRESSEE_CHECK_SQL` (#32), LLM-Exception-Mapping (#33), `format_currency`-Hygiene.

---

## Definition of Done pro Schritt

1. Befund im aktuellen Code verifiziert (oder als verworfen dokumentiert).
2. Fix implementiert, minimal-invasiv.
3. Mindestens ein neuer Test, der den Befund red→green bringt.
4. Betroffene Test-Suite grün.
5. Commit mit klarer Message + Push auf den aktuellen Branch.
6. Eintrag in `REVIEW_2026-04-14.md`: Befund mit `✅ <commit-sha>` markiert oder `~~verworfen~~`.

## Was nicht Teil dieses Plans ist

- Niedrig-Befunde und rein kosmetische Änderungen (TODO-Entfernung etc.) laufen bei Bedarf gesammelt am Ende.
- Tiefergehende Refactorings der Prompt-Architektur oder des Session-Modells. Wenn sich bei der Abarbeitung herausstellt, dass ein Fix einen strukturellen Umbau braucht, Stop und Rücksprache.
