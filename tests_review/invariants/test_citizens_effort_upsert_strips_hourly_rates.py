"""
INV-SYM-002 / Regression-Guard fuer Review-Befund Block 1.3.

Behauptung: upsert_process_step_effort_split_by_addressee lehnt jeden Versuch
ab, fuer Citizens einen Lohnsatz zu speichern - parametrisiert ueber alle
acht moeglichen Slots (current/proposed x a/b/c/d).
"""
import itertools

import pytest

from backend.core import db
from backend.core.norm_addressees import CITIZENS


def _seed_citizens_step(session_id: int) -> int:
    process_id = db.insert_process(
        session_id=session_id,
        process="Buergerprozess",
        description="d",
        norm_addressee=CITIZENS,
    )
    case_group_id = db.insert_case_group(
        session_id=session_id,
        process_id=process_id,
        case_group="CG",
        description="d",
        norm_addressee=CITIZENS,
    )
    return db.insert_process_step(
        session_id=session_id,
        case_group_id=case_group_id,
        step="Schritt",
        description="d",
        norm_addressee=CITIZENS,
    )


def _empty_rates() -> dict[str, float | None]:
    return {"a": None, "b": None, "c": None, "d": None}


def _empty_times() -> dict[str, float | None]:
    return {"a": 30.0, "b": None, "c": None, "d": None}


def test_citizens_upsert_with_only_time_succeeds(session_id):
    step_id = _seed_citizens_step(session_id)
    db.upsert_process_step_effort_split_by_addressee(
        session_id=session_id,
        step_id=step_id,
        norm_addressee=CITIZENS,
        hourly_rates_current=_empty_rates(),
        time_required_current=_empty_times(),
        expenses_current=12.0,
        hourly_rates_proposed=_empty_rates(),
        time_required_proposed=_empty_times(),
        expenses_proposed=12.0,
    )


@pytest.mark.parametrize(
    "phase,slot",
    list(itertools.product(["current", "proposed"], ["a", "b", "c", "d"])),
)
def test_citizens_upsert_rejects_any_hourly_rate_slot(session_id, phase, slot):
    step_id = _seed_citizens_step(session_id)
    rates_current = _empty_rates()
    rates_proposed = _empty_rates()
    target = rates_current if phase == "current" else rates_proposed
    target[slot] = 42.0

    with pytest.raises(ValueError, match="Citizens effort must not persist hourly rates"):
        db.upsert_process_step_effort_split_by_addressee(
            session_id=session_id,
            step_id=step_id,
            norm_addressee=CITIZENS,
            hourly_rates_current=rates_current,
            time_required_current=_empty_times(),
            expenses_current=None,
            hourly_rates_proposed=rates_proposed,
            time_required_proposed=_empty_times(),
            expenses_proposed=None,
        )
