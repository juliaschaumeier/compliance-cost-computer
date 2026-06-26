"""Global EA reset clears the NEU stores (wage overrides + effort-time edits).

During the Dual-Write phase the global reset must symmetrically clear both NEU
stores so it yields pure model costs. These tests assert DB state, the returned
counts, and the cent-exact cost effect via the real cost path.
"""

import pytest

from backend.core import db
from backend.core.norm_addressees import ADMINISTRATION


def _seed_session_with_rows(app_id="EA-RESET"):
    """One personnel-effort row: model time 60 min, model rate 40.4.

    Mirrors tests/test_session_wage_rates.py: child rows are authoritative; the
    slot columns mirror them (cost-input validation still reads the slots).
    """
    session_id, _ = db.upsert_session(app_id, "test-model")
    process_id = db.insert_process(session_id, "Prozess", "Beschreibung")
    case_group_id = db.insert_case_group(session_id, process_id, "Fallgruppe", "Beschreibung")
    step_id = db.insert_process_step(session_id, case_group_id, "Schritt", "Beschreibung")
    db.replace_process_step_personnel_effort(
        session_id, ADMINISTRATION, step_id,
        [
            {"period": "proposed", "qualification": "gehobener_dienst",
             "wage_source_kind": "verwaltungsebene", "wage_source_value": "bund",
             "time_required_in_min": 60, "model_hourly_rate": 40.4},
        ],
    )
    db.update_process_step_effort_split(
        session_id=session_id, step_id=step_id,
        hourly_rates_current={}, time_required_current={}, expenses_current=None,
        hourly_rates_proposed={"a": None, "b": 40.4, "c": None, "d": None},
        time_required_proposed={"a": None, "b": 60, "c": None, "d": None},
        expenses_proposed=None,
    )
    return app_id, session_id, case_group_id, step_id


def _proposed_rows(session_id, step_id):
    return [
        r for r in db.list_process_step_personnel_effort(session_id, ADMINISTRATION, step_id)
        if r["period"] == "proposed"
    ]


def _step_cost(session_id, step_id):
    from backend.core.cost_aggregation import _compute_step_personnel_cost_from_rows

    return _compute_step_personnel_cost_from_rows(
        _proposed_rows(session_id, step_id),
        db.get_session_wage_rate_overrides(session_id, ADMINISTRATION),
    )


def test_reset_clears_wage_override_and_effort_time_edit():
    app_id, session_id, _cg, step_id = _seed_session_with_rows("EA-RESET-BOTH")

    # (a) wage-rate override and (b) effort-time edit on the same row.
    db.upsert_session_wage_rate_override(
        session_id, ADMINISTRATION, "verwaltungsebene", "bund", "gehobener_dienst", 100.0,
    )
    db.upsert_personnel_effort_time_edit(
        session_id, ADMINISTRATION, step_id, "proposed", "gehobener_dienst",
        "verwaltungsebene", "bund", time_required_in_min_edited=30.0,
    )

    # Precondition: cost deviates from the model (override 100 * edited 30/60 = 50.0).
    assert _step_cost(session_id, step_id) == pytest.approx(50.0)

    counts = db.reset_all_ea_edit_overrides(session_id)

    # (1) wage overrides empty for the session.
    assert db.get_session_wage_rate_overrides(session_id, ADMINISTRATION) == {}
    # (2) every effort-time edit overlay is NULL.
    rows = _proposed_rows(session_id, step_id)
    assert rows, "personnel-effort rows must still exist"
    assert all(r["time_required_in_min_edited"] is None for r in rows)
    # (3) the personnel-effort row still exists and keeps its model time + rate.
    assert len(rows) == 1
    assert rows[0]["time_required_in_min"] == 60
    assert rows[0]["model_hourly_rate"] == pytest.approx(40.4)
    # (4) return dict carries the new counters.
    assert counts["wage_overrides"] == 1
    assert counts["effort_time_edits"] == 1

    # Cent-exact: cost after reset equals pure model cost (40.4 * 60/60 = 40.4).
    assert _step_cost(session_id, step_id) == pytest.approx(40.4)


def _all_rows_normalized(session_id, step_id):
    """Comparable view of all proposed rows: stable order, edit/audit cols dropped."""
    rows = _proposed_rows(session_id, step_id)
    keep = [
        "norm_addressee", "period", "qualification", "wage_source_kind",
        "wage_source_value", "time_required_in_min", "time_required_in_min_edited",
        "model_hourly_rate",
    ]
    norm = [tuple((k, r[k]) for k in keep) for r in rows]
    return sorted(norm)


def test_global_reset_matches_per_row_reset_for_user_created_row():
    """Global reset removes a user-created (model-time NULL) row instead of leaving a
    NULL/NULL zombie, exactly like clearing it per row. The surviving LLM row keeps its
    model time with a NULL edit overlay. Both reset paths must yield identical state.
    """
    # Build two parallel sessions with identical content.
    _app_g, sid_global, _cg_g, step_global = _seed_session_with_rows("EA-RESET-USERROW-G")
    _app_p, sid_perrow, _cg_p, step_perrow = _seed_session_with_rows("EA-RESET-USERROW-P")

    for sid, step in ((sid_global, step_global), (sid_perrow, step_perrow)):
        # (a) LLM row (model time 60): set a time edit.
        db.upsert_personnel_effort_time_edit(
            sid, ADMINISTRATION, step, "proposed", "gehobener_dienst",
            "verwaltungsebene", "bund", time_required_in_min_edited=30.0,
        )
        # (b) user-created row: a qualification the LLM did not assign (model time NULL).
        db.upsert_personnel_effort_time_edit(
            sid, ADMINISTRATION, step, "proposed", "hoeherer_dienst",
            "verwaltungsebene", "bund", time_required_in_min_edited=15.0,
        )
        # Precondition: both rows exist (one model, one user-created).
        rows = _proposed_rows(sid, step)
        assert len(rows) == 2
        user_rows = [r for r in rows if r["time_required_in_min"] is None]
        assert len(user_rows) == 1
        assert user_rows[0]["qualification"] == "hoeherer_dienst"

    # Global reset on session #1.
    counts = db.reset_all_ea_edit_overrides(sid_global)

    # Per-row reset on session #2: clear the edit of every proposed row individually.
    for r in _proposed_rows(sid_perrow, step_perrow):
        db.upsert_personnel_effort_time_edit(
            sid_perrow, r["norm_addressee"], step_perrow, r["period"],
            r["qualification"], r["wage_source_kind"], r["wage_source_value"],
            time_required_in_min_edited=None,
        )

    rows_global = _proposed_rows(sid_global, step_global)
    # The user-created row is gone entirely (no NULL/NULL zombie).
    assert len(rows_global) == 1
    survivor = rows_global[0]
    assert survivor["qualification"] == "gehobener_dienst"
    assert survivor["time_required_in_min"] == 60
    assert survivor["time_required_in_min_edited"] is None
    assert survivor["model_hourly_rate"] == pytest.approx(40.4)
    # No leftover NULL-model rows survived the global reset.
    assert all(r["time_required_in_min"] is not None for r in rows_global)

    # Identical resulting row state for global vs N per-row resets.
    assert _all_rows_normalized(sid_global, step_global) == _all_rows_normalized(
        sid_perrow, step_perrow
    )

    # Counter plausibility: 1 user-created DELETE + 1 model-row edit UPDATE = 2.
    assert counts["effort_time_edits"] == 2


def test_reset_counts_zero_when_no_neu_overrides():
    app_id, session_id, _cg, step_id = _seed_session_with_rows("EA-RESET-NONE")

    counts = db.reset_all_ea_edit_overrides(session_id)

    assert counts["wage_overrides"] == 0
    assert counts["effort_time_edits"] == 0
    # Model cost unaffected.
    assert _step_cost(session_id, step_id) == pytest.approx(40.4)
