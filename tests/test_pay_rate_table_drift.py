"""Guard: the wage-rate constants in db.py must match the handbook wage table.

db.py holds the rates as compute constants (PAY_RATE_LEVEL_DEFAULTS /
PAY_RATE_BUSINESS_SECTION_DEFAULTS); handbook_tables.Appendix holds the same values
as markdown prose for the LLM prompt. The two must agree, otherwise the tab computes
or shows rates that differ from what the prompt tells the model. This test parses the
"Lohnkosten pro Stunde" table and compares it 1:1.
"""

from backend.core import db
from backend.core.handbook_tables import Appendix

# Handbook row label -> constants key in db.py.
_ADMIN_LABEL_TO_KEY = {
    "Bund": "bund",
    "Länder": "laender",
    "Kommunen": "kommunen",
    "Sozialversicherung": "sozialversicherung",
    "Durchschnitt Öffentliche Verwaltung, Verteidigung, Sozialversicherung": "durchschnitt",
}


def _parse_german_decimal(token: str) -> float:
    # Handbook uses comma as decimal separator (e.g. "30,50").
    return float(token.strip().replace(",", "."))


def _parse_hourly_table(markdown: str) -> dict[str, tuple[float, float, float, float]]:
    """Parse the single table under '*Lohnkosten pro Stunde in Euro*'.

    Anchors on that heading and stops at the next '*Lohnkosten ...*' section: the
    admin table also has a per-MAK (yearly) table with identical row labels.
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
        # Skip header and separator rows.
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
            # WZ code = first token of the row label (e.g. "K Erbringung ...").
            key = label.split(" ", 1)[0]
        const = db.PAY_RATE_BUSINESS_SECTION_DEFAULTS[key]
        a, b, c, d = rates
        assert (const["a"], const["b"], const["c"], const["d"]) == (a, b, c, d), (
            f"Wirtschaftsabschnitt {key!r} weicht von der Handbuch-Tabelle ab"
        )


def test_no_extra_business_sections_beyond_handbook():
    # Every constants section must be covered by a handbook row
    # (gesamtwirtschaft is its own handbook row).
    table = _parse_hourly_table(Appendix.Lohnkostentabelle_Wirtschaft)
    handbook_keys = {
        "gesamtwirtschaft" if label.startswith("Gesamtwirtschaft") else label.split(" ", 1)[0]
        for label in table
    }
    assert set(db.PAY_RATE_BUSINESS_SECTION_DEFAULTS.keys()) == handbook_keys
