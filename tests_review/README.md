# tests_review/

Tests, die aus der Code-Review vom 2026-04-14 hervorgegangen sind. Liegen bewusst
außerhalb von `tests/`, damit sie als eigene, unabhängige Suite erkennbar bleiben
und einzeln ausgeführt werden können.

## Ausführen

```bash
source venv/bin/activate
python -m pytest tests_review/ -v
```

Nur eine Unter-Suite:

```bash
python -m pytest tests_review/invariants/ -v
python -m pytest tests_review/regressions/ -v
python -m pytest tests_review/contracts/ -v
```

## Struktur

- `invariants/` — Tests, die domänenweite Invarianten zementieren. Müssen
  immer grün sein. Jedes Failure ist eine echte Regression.
- `regressions/` — Ein Test pro Befund aus `tmp/CODE_REVIEW_2026-04-14.md`.
  Test-Name referenziert Block und Befundnummer.
- `contracts/` — JSON-Schema- und Parser-Verträge zwischen LLM und Backend.

## Begleitdokumente

- `tmp/CODE_REVIEW_2026-04-14.md` — Befundkatalog
- `tmp/TEST_STRATEGY_2026-04-14.md` — Vollständige Test-Strategie (10 Schichten)

## Hinweis zu behobenen Befunden

Vier ursprünglich als KRITISCH markierte Befunde waren beim Schreiben der Tests
bereits durch den `normaddressees-on-develop`-Branch adressiert (Befund 1.1,
1.2, 1.3, 4.1). Die zugehörigen Tests sind als **Regression-Guards** angelegt —
sie müssen grün sein und bleiben.

Zwei Befunde sind mit `pytest.mark.xfail(strict=True)` markiert und
dokumentieren den noch offenen Zustand. Sobald der Fix kommt, wechselt der
Test von xfail nach xpass-strict → failt → xfail-Marker entfernen → echter
Regression-Guard.
