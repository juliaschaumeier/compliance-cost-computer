"""
INV-SYM-005 / Regression-Guard fuer Review-Befund Block 1.1.

Behauptung: clear_effort_metrics(session_id, norm_addressee) darf
ausschliesslich Daten des angegebenen Adressaten loeschen.
"""
import pytest

from backend.core import db
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS


def _seed_case_group_with_metrics(session_id: int, norm_addressee: str) -> int:
    process_id = db.insert_process(
        session_id=session_id,
        process="P",
        description="d",
        norm_addressee=norm_addressee,
    )
    case_group_id = db.insert_case_group(
        session_id=session_id,
        process_id=process_id,
        case_group="CG",
        description="d",
        norm_addressee=norm_addressee,
    )
    db.upsert_case_group_metrics_by_addressee(
        session_id=session_id,
        case_group_id=case_group_id,
        norm_addressee=norm_addressee,
        addressees_current=100.0,
        annual_frequency_current=2.0,
        cases_current=200.0,
        addressees_proposed=100.0,
        annual_frequency_proposed=2.0,
        cases_proposed=200.0,
    )
    return case_group_id


@pytest.mark.parametrize("target_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_clear_effort_metrics_only_touches_target_addressee(session_id, target_addressee):
    seeded = {
        addressee: _seed_case_group_with_metrics(session_id, addressee)
        for addressee in (ADMINISTRATION, BUSINESS, CITIZENS)
    }

    db.clear_effort_metrics(session_id, target_addressee)

    for addressee, case_group_id in seeded.items():
        groups = db.list_case_groups_for_session_and_addressee(session_id, addressee)
        row = next(g for g in groups if int(g["case_group_id"]) == case_group_id)
        if addressee == target_addressee:
            assert row["addressees_current"] is None
            assert row["annual_frequency_current"] is None
            assert row["cases_current"] is None
        else:
            assert row["addressees_current"] == 100.0
            assert row["annual_frequency_current"] == 2.0
            assert row["cases_current"] == 200.0
