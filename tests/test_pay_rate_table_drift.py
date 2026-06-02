"""Guard: die Lohnsatz-Konstanten in db.py duerfen nicht von der Lohnkostentabelle
im Handbuch (handbook_tables.Appendix) abweichen.

db.py haelt die Lohnsaetze als strukturierte Rechen-Konstanten
(PAY_RATE_LEVEL_DEFAULTS / PAY_RATE_BUSINESS_SECTION_DEFAULTS); das Handbuch haelt
dieselben Werte als Markdown-Prosa fuer den LLM-Prompt. Beide muessen uebereinstimmen,
sonst rechnet/zeigt der Tab andere Saetze als der Prompt dem Modell nennt. Dieser Test
parst die jeweilige "Lohnkosten pro Stunde"-Tabelle und vergleicht sie 1:1.
"""

from backend.core import db
from backend.core.handbook_tables import Appendix

# Zeilen-Label im Handbuch -> Konstanten-Key in db.py.
_ADMIN_LABEL_TO_KEY = {
    "Bund": "bund",
    "Länder": "laender",
    "Kommunen": "kommunen",
    "Sozialversicherung": "sozialversicherung",
    "Durchschnitt Öffentliche Verwaltung, Verteidigung, Sozialversicherung": "durchschnitt",
}


def _parse_german_decimal(token: str) -> float:
    # Handbuch nutzt Komma als Dezimaltrenner (z. B. "30,50"); MAK-Tabelle nutzt
    # Leerzeichen-Tausender, die hier nicht vorkommen (wir parsen nur "pro Stunde").
    return float(token.strip().replace(",", "."))


def _parse_hourly_table(markdown: str) -> dict[str, tuple[float, float, float, float]]:
    """Liest die EINE Tabelle unter '*Lohnkosten pro Stunde in Euro*'.

    Ankert bewusst auf diese Ueberschrift und stoppt an der naechsten
    '*Lohnkosten ...*'-Sektion (die Verwaltungs-Tabelle enthaelt zusaetzlich eine
    MAK-/Jahres-Tabelle mit denselben Zeilen-Labels, die NICHT gemeint ist).
    """
    start = markdown.index("*Lohnkosten pro Stunde in Euro*")
    rest = markdown[start + len("*Lohnkosten pro Stunde in Euro*"):]
    next_section = rest.find("*Lohnkosten")
    if next_section != -1:
        rest = rest[:next_section]

    parsed: dict[str, tuple[float, float, float, float]] = {}
    for line in rest.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 5:
            continue
        label = cells[0]
        # Kopf- und Trennzeile ueberspringen.
        if label in ("Verwaltungsebene", "Wirtschaftsabschnitt") or set(label) <= {"-"}:
            continue
        parsed[label] = tuple(_parse_german_decimal(c) for c in cells[1:])
    return parsed


def test_administration_constants_match_handbook_hourly_table():
    table = _parse_hourly_table(Appendix.Lohnkostentabelle_Verwaltung)
    assert _ADMIN_LABEL_TO_KEY.keys() <= table.keys()
    for label, key in _ADMIN_LABEL_TO_KEY.items():
        a, b, c, d = table[label]
        const = db.PAY_RATE_LEVEL_DEFAULTS[key]
        assert (const["a"], const["b"], const["c"], const["d"]) == (a, b, c, d), (
            f"Verwaltungsebene {key!r} weicht von der Handbuch-Tabelle ab"
        )


def test_business_constants_match_handbook_hourly_table():
    table = _parse_hourly_table(Appendix.Lohnkostentabelle_Wirtschaft)
    for label, rates in table.items():
        if label.startswith("Gesamtwirtschaft"):
            key = "gesamtwirtschaft"
        else:
            # WZ-Code = erster Buchstabe des Zeilen-Labels (z. B. "K Erbringung ...").
            key = label.split(" ", 1)[0]
        const = db.PAY_RATE_BUSINESS_SECTION_DEFAULTS[key]
        a, b, c, d = rates
        assert (const["a"], const["b"], const["c"], const["d"]) == (a, b, c, d), (
            f"Wirtschaftsabschnitt {key!r} weicht von der Handbuch-Tabelle ab"
        )


def test_no_extra_business_sections_beyond_handbook():
    # Jede Konstanten-Sektion muss durch eine Handbuch-Zeile gedeckt sein
    # (Gesamtwirtschaft wird separat als eigene Handbuch-Zeile gefuehrt).
    table = _parse_hourly_table(Appendix.Lohnkostentabelle_Wirtschaft)
    handbook_keys = {
        "gesamtwirtschaft" if label.startswith("Gesamtwirtschaft") else label.split(" ", 1)[0]
        for label in table
    }
    assert set(db.PAY_RATE_BUSINESS_SECTION_DEFAULTS.keys()) == handbook_keys
