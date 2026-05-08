"""
Regression-Guard fuer Review-Befund "Admin-Laufbahn-Mapping fragil".

Vorher: unbekannte Laufbahn-Bezeichnungen (z.B. 'm. d.' mit Punkt-Leerzeichen-
Variante, Abkuerzungen wie 'md', 'hd' etc.) wurden stumm zu None aufgeloest,
die jeweilige Rolle wurde verworfen, der Aufwand fehlte in der
Kostenberechnung.

Jetzt:
- Erweitertes Alias-Mapping deckt die haeufigsten Varianten ab.
- Nicht-leerer aber unbekannter Input wirft HTTPException(422).
- Leerer Input bleibt None (natuerliches Fehlen).
"""
import pytest
from fastapi import HTTPException

from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS
from backend.routers.effort import _resolve_effort_group


@pytest.mark.parametrize(
    "raw_value,expected_slot",
    [
        ("mittlerer Dienst", "a"),
        ("m. d.", "a"),
        ("m.d.", "a"),
        ("MD", "a"),
        ("einfacher Dienst", "a"),
        ("gehobener Dienst", "b"),
        ("g. d.", "b"),
        ("GD", "b"),
        ("hoeherer Dienst", "c"),
        ("höherer Dienst", "c"),
        ("h. d.", "c"),
        ("HD", "c"),
        ("Durchschnitt", "d"),
    ],
)
def test_admin_laufbahn_aliases_resolve(raw_value, expected_slot):
    assert _resolve_effort_group({"rolle": raw_value}, ADMINISTRATION) == expected_slot


def test_admin_unknown_laufbahn_raises_422():
    with pytest.raises(HTTPException) as excinfo:
        _resolve_effort_group({"rolle": "beliebiger Quark"}, ADMINISTRATION)
    assert excinfo.value.status_code == 422
    assert "Unbekannte Laufbahn" in excinfo.value.detail


def test_unknown_lohngruppe_letter_raises_422():
    with pytest.raises(HTTPException) as excinfo:
        _resolve_effort_group({"lohngruppe": "e"}, ADMINISTRATION)
    assert excinfo.value.status_code == 422
    assert "Unbekannte Lohngruppe" in excinfo.value.detail


def test_empty_input_returns_none():
    assert _resolve_effort_group({}, ADMINISTRATION) is None
    assert _resolve_effort_group({"rolle": ""}, ADMINISTRATION) is None
    assert _resolve_effort_group({"rolle": "   "}, ADMINISTRATION) is None


def test_valid_lohngruppe_letter_resolves_directly():
    assert _resolve_effort_group({"lohngruppe": "a"}, ADMINISTRATION) == "a"
    assert _resolve_effort_group({"lohngruppe": "D"}, ADMINISTRATION) == "d"


@pytest.mark.parametrize(
    "raw_value,expected_slot",
    [("niedrig", "a"), ("low", "a"), ("mittel", "b"), ("medium", "b"), ("hoch", "c"), ("high", "c")],
)
def test_business_level_aliases_resolve(raw_value, expected_slot):
    assert _resolve_effort_group({"niveau": raw_value}, BUSINESS) == expected_slot


def test_business_unknown_level_raises_422():
    with pytest.raises(HTTPException) as excinfo:
        _resolve_effort_group({"niveau": "extrem"}, BUSINESS)
    assert excinfo.value.status_code == 422
