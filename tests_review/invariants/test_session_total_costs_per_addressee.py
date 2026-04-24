"""
INV-SYM-004 / Regression-Guard fuer Review-Befund Block 1.2.

Behauptung: Gesamtkosten werden pro Normadressat persistiert.
"""
from backend.core import db
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS


def test_each_addressee_has_independent_totals(session_id):
    db.upsert_session_total_costs_by_addressee(
        session_id=session_id,
        norm_addressee=ADMINISTRATION,
        total_cost=1234.0,
        bureaucracy_cost=None,
        total_time_minutes=None,
        total_expenses=None,
    )
    db.upsert_session_total_costs_by_addressee(
        session_id=session_id,
        norm_addressee=BUSINESS,
        total_cost=5678.0,
        bureaucracy_cost=900.0,
        total_time_minutes=None,
        total_expenses=None,
    )
    db.upsert_session_total_costs_by_addressee(
        session_id=session_id,
        norm_addressee=CITIZENS,
        total_cost=None,
        bureaucracy_cost=None,
        total_time_minutes=4200.0,
        total_expenses=150.0,
    )

    admin = db.get_session_total_costs_by_addressee(session_id, ADMINISTRATION)
    business = db.get_session_total_costs_by_addressee(session_id, BUSINESS)
    citizens = db.get_session_total_costs_by_addressee(session_id, CITIZENS)

    assert admin is not None and admin["total_cost"] == 1234.0
    assert admin["bureaucracy_cost"] is None

    assert business is not None and business["total_cost"] == 5678.0
    assert business["bureaucracy_cost"] == 900.0

    assert citizens is not None
    assert citizens["total_cost"] is None, "Buerger duerfen keine Eurokosten haben"
    assert citizens["total_time_minutes"] == 4200.0
    assert citizens["total_expenses"] == 150.0


def test_upsert_overwrites_only_target_addressee(session_id):
    db.upsert_session_total_costs_by_addressee(session_id, ADMINISTRATION, 1000.0, None, None, None)
    db.upsert_session_total_costs_by_addressee(session_id, BUSINESS, 2000.0, 500.0, None, None)

    db.upsert_session_total_costs_by_addressee(session_id, ADMINISTRATION, 9999.0, None, None, None)

    admin = db.get_session_total_costs_by_addressee(session_id, ADMINISTRATION)
    business = db.get_session_total_costs_by_addressee(session_id, BUSINESS)
    assert admin["total_cost"] == 9999.0
    assert business["total_cost"] == 2000.0, "Business-Eintrag darf nicht beruehrt werden"
