"""
INV-SYM (Validierung): Normadressat-Strings werden streng validiert.

Stellt sicher, dass nur die drei kanonischen Werte akzeptiert werden und jeder
unbekannte String hart abgelehnt wird.
"""
import pytest

from backend.core.norm_addressees import (
    ADMINISTRATION,
    ALL_NORM_ADDRESSEES,
    BUSINESS,
    CITIZENS,
    normalize_norm_addressee,
)


def test_canonical_values_pass_through():
    assert normalize_norm_addressee("administration") == ADMINISTRATION
    assert normalize_norm_addressee("business") == BUSINESS
    assert normalize_norm_addressee("citizens") == CITIZENS


def test_case_and_whitespace_normalised():
    assert normalize_norm_addressee("  Administration  ") == ADMINISTRATION
    assert normalize_norm_addressee("BUSINESS") == BUSINESS
    assert normalize_norm_addressee("Citizens") == CITIZENS


@pytest.mark.parametrize(
    "bad",
    [
        "verwaltung",
        "wirtschaft",
        "buerger",
        "admin",
        "biz",
        "all",
        "unknown",
        "administrtion",
    ],
)
def test_unknown_or_misspelled_values_are_rejected(bad):
    if bad.strip().lower() in ALL_NORM_ADDRESSEES:
        return
    with pytest.raises(ValueError):
        normalize_norm_addressee(bad)


def test_none_falls_back_to_administration_and_is_documented():
    """
    Aktuelles Verhalten: None -> administration. Dokumentiert den Status quo,
    damit eine zukuenftige Haertung sichtbar wird.
    """
    assert normalize_norm_addressee(None) == ADMINISTRATION


def test_empty_string_is_rejected_not_silently_defaulted():
    """
    Regression-Guard: Ein beim ersten Schreiben dieser Suite entdeckter
    Befund - Leerstring '' wurde durch `value or ADMINISTRATION` still zu
    'administration' - ist inzwischen gefixt. Test sichert den Zustand ab,
    damit das Verhalten nicht zurueckfaellt.
    """
    with pytest.raises(ValueError):
        normalize_norm_addressee("")


def test_all_three_addressees_are_distinct():
    assert len({ADMINISTRATION, BUSINESS, CITIZENS}) == 3
    assert set(ALL_NORM_ADDRESSEES) == {ADMINISTRATION, BUSINESS, CITIZENS}
