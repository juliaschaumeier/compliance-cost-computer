"""
Regression-Guard fuer Review-Befund "Admin-Laufbahn-Mapping fragil".

Vorher: unbekannte Laufbahn-Bezeichnungen (z.B. 'm. d.' mit Punkt-Leerzeichen-
Variante, Abkuerzungen wie 'md', 'hd' etc.) wurden stumm zu None aufgeloest,
die jeweilige Rolle wurde verworfen, der Aufwand fehlte in der
Kostenberechnung.

Jetzt (row-based Modell): das `qualifikation`-Feld wird ueber dieselben Aliase
auf den Slot a/b/c/d abgebildet.
- Erweitertes Alias-Mapping deckt die haeufigsten Varianten ab.
- Nicht-leerer aber unbekannter Input wirft HTTPException(422).
- Leerer Input bleibt None (natuerliches Fehlen).
"""
import pytest
from fastapi import HTTPException

from backend.core.norm_addressees import ADMINISTRATION, BUSINESS
from backend.routers.effort import _resolve_qualification_slot


@pytest.mark.parametrize(
    "raw_value,expected_slot",
    [
        ("mittlerer Dienst", "a"),
        ("m. d.", "a"),
        ("m.d.", "a"),
        ("MD", "a"),
        ("einfacher Dienst", "a"),
        ("einfacher_und_mittlerer_dienst", "a"),
        ("gehobener Dienst", "b"),
        ("gehobener_dienst", "b"),
        ("g. d.", "b"),
        ("GD", "b"),
        ("hoeherer Dienst", "c"),
        ("höherer Dienst", "c"),
        ("hoeherer_dienst", "c"),
        ("h. d.", "c"),
        ("HD", "c"),
        ("Durchschnitt", "d"),
    ],
)
def test_admin_qualifikation_aliases_resolve(raw_value, expected_slot):
    assert _resolve_qualification_slot({"qualifikation": raw_value}, ADMINISTRATION) == expected_slot


def test_admin_unknown_qualifikation_raises_422():
    with pytest.raises(HTTPException) as excinfo:
        _resolve_qualification_slot({"qualifikation": "beliebiger Quark"}, ADMINISTRATION)
    assert excinfo.value.status_code == 422
    assert "qualifikation" in excinfo.value.detail.lower()


def test_empty_input_returns_none():
    assert _resolve_qualification_slot({}, ADMINISTRATION) is None
    assert _resolve_qualification_slot({"qualifikation": ""}, ADMINISTRATION) is None
    assert _resolve_qualification_slot({"qualifikation": "   "}, ADMINISTRATION) is None


def test_canonical_slot_letter_resolves_directly():
    assert _resolve_qualification_slot({"qualifikation": "a"}, ADMINISTRATION) == "a"
    assert _resolve_qualification_slot({"qualifikation": "D"}, ADMINISTRATION) == "d"


@pytest.mark.parametrize(
    "raw_value,expected_slot",
    [("niedrig", "a"), ("low", "a"), ("mittel", "b"), ("medium", "b"), ("hoch", "c"), ("high", "c")],
)
def test_business_level_aliases_resolve(raw_value, expected_slot):
    assert _resolve_qualification_slot({"qualifikation": raw_value}, BUSINESS) == expected_slot


def test_business_unknown_level_raises_422():
    with pytest.raises(HTTPException) as excinfo:
        _resolve_qualification_slot({"qualifikation": "extrem"}, BUSINESS)
    assert excinfo.value.status_code == 422
