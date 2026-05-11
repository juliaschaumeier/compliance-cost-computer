# Pipeline-Übersicht: 7-Schritte-Workflow

Der CCC berechnet den Erfüllungsaufwand einer Gesetzesänderung in sieben Schritten. Die Schritte 3–6b laufen je dreimal — einmal pro Normadressat (Verwaltung, Wirtschaft, Bürger). Jeder Prompt wird aus wiederverwendbaren Bausteinen zusammengesetzt, die `render_prompt()` anhand von `prompt_id` und `norm_addressee` auswählt und einbettet.

---

## Schritte und ihre Prompt-Bausteine

| # | Schritt | NA? | Prompt-Bausteine |
|---|---------|:---:|-----------------|
| 1 | **Zusammenfassung** | — | Legist-Intro (inline) · `{gesetz_gueltig}` · `{gesetz_vorschlag}` · JSON-Format (inline) |
| 2 | **Vorgaben-Identifikation** | — | Legist-Intro (inline) · `{gesetz_gueltig}` · `{gesetz_vorschlag}` · NA-Definitionen (inline) · JSON-Format (inline) |
| 3 | **Prozess-Kompilierung** | ✓ | `LEGIST_PROMPT_OPENING` + `{law_summary}` · `{norm_addressee_prompt_opening}` · `{norm_addressee_rule}` · `{handbook_process_example}`¹ · JSON-Format (inline) |
| 4 | **Fallgruppenentwicklung** | ✓ | `LEGIST_PROMPT_OPENING` + `{law_summary}` · `{norm_addressee_prompt_opening}` · `{norm_addressee_rule}` · `{handbook_case_group_example}`¹ · JSON-Format (inline) |
| 5 | **Prozessschrittanalyse** | ✓ | `LEGIST_PROMPT_OPENING` + `{law_summary}` · `{step_analysis_addressee_context}` · `{step_analysis_addressee_rule}` · `{step_analysis_checklist}` · JSON-Format (inline) |
| 6a | **Fallzahlberechnung** | ✓ | `LEGIST_PROMPT_OPENING` + `{law_summary}` · `{norm_addressee_prompt_opening}` · `{norm_addressee_rule}` · `{handbook_cases_frequency_example}` · `{handbook_cases_case_example}`² · JSON-Format (inline) |
| 6b | **Aufwandsberechnung** | ✓ | `LEGIST_PROMPT_OPENING` + `{law_summary}` · `{norm_addressee_prompt_opening}` · `{effort_method_guidance}` · `{effort_appendix}` · `{effort_json_schema}`³ |
| 7 | **Gesamtkosten** | ✓ | Kein LLM-Aufruf — Rechenoperation: Fallzahl (6a) × Aufwand pro Fall (6b) |

¹ nur Wirtschaft · ² nur Bürger · ³ dynamisch je Normadressat (Bürger ohne Stundenlohn-Felder) · Schritte 6a und 6b laufen parallel

---

## Bausteine

| Baustein | Beschreibung | Variiert nach Adressat | Variiert nach Schritt |
|----------|-------------|:---:|:---:|
| **Legist-Intro** | Eigenständige Rolleneinleitung in Schritten 1–2, hardcoded im Template, ohne `law_summary` | ✗ | ✗ |
| **`LEGIST_PROMPT_OPENING`** | Gemeinsamer Rollenframe in Schritten 3–6b; bettet `{law_summary}` (Ergebnis aus Schritt 1) ein | ✗ | ✗ |
| **`{norm_addressee_prompt_opening}`** | Grundrahmen: was für diesen Normadressat gilt und was nicht — gleicher Text pro Adressat in jedem Schritt | ✓ | ✗ |
| **`{norm_addressee_rule}`** | Operative Anweisung für die jeweilige Schrittaufgabe (z. B. Bündelungslogik in Schritt 3, Differenzierungsachsen in Schritt 4, Fallzahllogik in Schritt 6a) | ✓ | ✓ |
| **`{step_analysis_addressee_context}`** | Schritt 5: enger Rahmen, was als Tätigkeit für diesen Normadressat zählt | ✓ | — |
| **`{step_analysis_addressee_rule}`** | Schritt 5: was ausgewiesen werden darf / nicht darf (z. B. keine Verwaltungshandlungen als Bürgertätigkeiten) | ✓ | — |
| **`{step_analysis_checklist}`** | Schritt 5: Standardtätigkeiten aus Leitfaden Erfüllungsaufwand (Kap. 5/6/7), normadressatenspezifisch | ✓ | — |
| **`{handbook_process_example}`** | Schritt 3, nur Wirtschaft: Methodenbeispiel Prozessbildung aus Leitfaden | — | — |
| **`{handbook_case_group_example}`** | Schritt 4, nur Wirtschaft: Methodenbeispiel Fallgruppenbildung aus Leitfaden | — | — |
| **`{handbook_cases_frequency_example}`** | Schritt 6a, alle Normadressaten: Methodenbeispiel Häufigkeitsermittlung | — | — |
| **`{handbook_cases_case_example}`** | Schritt 6a, nur Bürger: Methodenbeispiel Fallzahlermittlung | — | — |
| **`{effort_method_guidance}`** | Schritt 6b: Berechnungsverfahren je Normadressat (Lohngruppen, Zeitwerte, Sachaufwand) | ✓ | — |
| **`{effort_appendix}`** | Schritt 6b: Verwaltung + Wirtschaft erhalten Zeitwerttabelle + Lohnkostentabelle + Wegezeiten; Bürger nur Zeitwerttabelle + Wegezeiten | ✓ | — |
| **`{effort_json_schema}`** | Schritt 6b: Ausgabeschema je Normadressat — Bürger ohne Rollen/Lohngruppen/Stundenlohn-Felder | ✓ | — |

**`{norm_addressee_prompt_opening}` vs. `{norm_addressee_rule}`:** `norm_addressee_prompt_opening` erklärt *wer* der Normadressat ist — identischer Text in Schritten 3, 4, 6a und 6b. `norm_addressee_rule` sagt *wie* die jeweilige Schrittaufgabe für diesen Normadressat zu lösen ist — 3 Normadressaten × 3 Schritte = 9 verschiedene Texte.
