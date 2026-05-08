"""
Regression-Guard fuer Review-Befund Block 1 (pay_rate_defaults + Citizens).

Behauptung: get_default_pay_rates_for_addressee() wirft ValueError, wenn
der Aufruf fuer Citizens erfolgt. Vorher lieferte die Funktion still
Null-Werte zurueck - ein Silent-Failure-Pfad, der manuelle DB-Eintraege
und semantische Aufruffehler unbemerkt machte.

Citizens haben per Methodik keine Lohnsaetze (nur Zeit + Sachaufwand),
daher ist jeder Aufruf mit CITIZENS ein Programmierfehler und soll
hart scheitern.
"""
import pytest

from backend.core import db
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS


def test_get_default_pay_rates_for_citizens_raises():
    with pytest.raises(ValueError, match="pay-rate defaults"):
        db.get_default_pay_rates_for_addressee(CITIZENS)


def test_get_default_pay_rates_for_unknown_addressee_raises():
    # normalize_norm_addressee kickt frueher und wirft seinen eigenen
    # ValueError - beide Fehlerpfade sind akzeptabel, wichtig ist: kein
    # stummes Null-Result.
    with pytest.raises(ValueError):
        db.get_default_pay_rates_for_addressee("unknown_addressee")


def test_get_default_pay_rates_for_business_still_works():
    defaults = db.get_default_pay_rates_for_addressee(BUSINESS)
    assert set(defaults.keys()) == {"a", "b", "c", "d"}
    assert all(isinstance(v, float) for v in defaults.values())


def test_get_default_pay_rates_for_administration_still_works():
    defaults = db.get_default_pay_rates_for_addressee(ADMINISTRATION)
    assert set(defaults.keys()) == {"a", "b", "c", "d"}
    assert all(isinstance(v, float) for v in defaults.values())
