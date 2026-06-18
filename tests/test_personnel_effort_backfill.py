"""Phase D2a: one-time backfill of legacy slot effort into the row model.

The backfill recovers the wage source from role_sources_*_json or, when missing,
by reverse-lookup of the stored slot rate, and preserves per-step personnel cost
exactly (model_hourly_rate == stored slot rate for legacy data).
"""

import pytest

from backend.core import db
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS

_EMPTY = {"a": None, "b": None, "c": None, "d": None}


def _slots(**vals):
    out = dict(_EMPTY)
    out.update(vals)
    return out


def _seed(app_id, addressee, *, hourly_rates, time_required, role_sources=None):
    session_id, _ = db.upsert_session(app_id, "test-model")
    process_id = db.insert_process(session_id, "Prozess", "Beschreibung", norm_addressee=addressee)
    case_group_id = db.insert_case_group(
        session_id, process_id, "Fallgruppe", "Beschreibung", norm_addressee=addressee
    )
    step_id = db.insert_process_step(
        session_id, case_group_id, "Schritt", "Beschreibung", norm_addressee=addressee
    )
    db.upsert_process_step_effort_split_by_addressee(
        session_id=session_id,
        step_id=step_id,
        norm_addressee=addressee,
        hourly_rates_current=hourly_rates,
        time_required_current=time_required,
        expenses_current=None,
        hourly_rates_proposed=hourly_rates,
        time_required_proposed=time_required,
        expenses_proposed=None,
        role_sources_current=role_sources,
        role_sources_proposed=role_sources,
    )
    return session_id, step_id


def _run_backfill():
    conn = db.get_conn()
    cur = conn.cursor()
    inserted = db._backfill_process_step_personnel_effort(cur)
    db._maybe_commit(conn)
    db._maybe_close(conn)
    return inserted


def test_backfill_recovers_recorded_source(test_client):
    session_id, step_id = _seed(
        "BACKFILL-RECORDED",
        ADMINISTRATION,
        hourly_rates=_slots(a=33.8),
        time_required=_slots(a=30),
        role_sources=[
            {"slot": "a", "role": "", "source_kind": "verwaltungsebene", "source_value": "bund"}
        ],
    )
    # Seeding writes slot data only, no child rows yet.
    assert db.list_process_step_personnel_effort(session_id, ADMINISTRATION, step_id) == []

    _run_backfill()

    rows = db.list_process_step_personnel_effort(session_id, ADMINISTRATION, step_id)
    current = [r for r in rows if r["period"] == "current"]
    assert len(current) == 1
    row = current[0]
    assert row["qualification"] == "einfacher_und_mittlerer_dienst"
    assert row["wage_source_kind"] == "verwaltungsebene"
    assert row["wage_source_value"] == "bund"
    assert row["model_hourly_rate"] == 33.8
    assert row["time_required_in_min"] == 30


def test_backfill_reverse_lookup_unique_source(test_client):
    # laender/gehobener_dienst = 43.2 is unique among administration slot b rates.
    session_id, step_id = _seed(
        "BACKFILL-UNIQUE",
        ADMINISTRATION,
        hourly_rates=_slots(b=43.2),
        time_required=_slots(b=10),
        role_sources=None,
    )
    _run_backfill()

    row = next(
        r
        for r in db.list_process_step_personnel_effort(session_id, ADMINISTRATION, step_id)
        if r["period"] == "current"
    )
    assert row["qualification"] == "gehobener_dienst"
    assert row["wage_source_value"] == "laender"
    assert row["model_hourly_rate"] == 43.2


def test_backfill_ambiguous_without_aggregate_picks_first(test_client):
    # business slot b = 32.2 matches sections H and R (not gesamtwirtschaft);
    # the deterministic tie-break takes the first alphabetically (H).
    session_id, step_id = _seed(
        "BACKFILL-AMBIG",
        BUSINESS,
        hourly_rates=_slots(b=32.2),
        time_required=_slots(b=15),
        role_sources=None,
    )
    _run_backfill()

    row = next(
        r
        for r in db.list_process_step_personnel_effort(session_id, BUSINESS, step_id)
        if r["period"] == "current"
    )
    assert row["qualification"] == "mittel"
    assert row["wage_source_value"] == "H"
    assert row["model_hourly_rate"] == 32.2


def test_backfill_ambiguous_prefers_aggregate_label(test_client):
    # business slot c = 62.4 matches section G and gesamtwirtschaft; when the
    # aggregate label is among the equal-rate candidates it is preferred.
    session_id, step_id = _seed(
        "BACKFILL-AGGREGATE",
        BUSINESS,
        hourly_rates=_slots(c=62.4),
        time_required=_slots(c=20),
        role_sources=None,
    )
    _run_backfill()

    row = next(
        r
        for r in db.list_process_step_personnel_effort(session_id, BUSINESS, step_id)
        if r["period"] == "current"
    )
    assert row["qualification"] == "hoch"
    assert row["wage_source_value"] == "gesamtwirtschaft"
    assert row["model_hourly_rate"] == 62.4


def test_backfill_is_idempotent(test_client):
    session_id, step_id = _seed(
        "BACKFILL-IDEMPOTENT",
        ADMINISTRATION,
        hourly_rates=_slots(a=33.8),
        time_required=_slots(a=30),
        role_sources=None,
    )
    first = _run_backfill()
    assert first >= 2  # current + proposed
    rows_after_first = db.list_process_step_personnel_effort(session_id, ADMINISTRATION, step_id)

    second = _run_backfill()
    assert second == 0
    assert db.list_process_step_personnel_effort(session_id, ADMINISTRATION, step_id) == rows_after_first


def test_backfill_skips_citizens(test_client):
    session_id, step_id = _seed(
        "BACKFILL-CITIZENS",
        CITIZENS,
        hourly_rates=_EMPTY,
        time_required=_slots(a=30),
        role_sources=None,
    )
    _run_backfill()
    assert db.list_process_step_personnel_effort(session_id, CITIZENS, step_id) == []


def test_backfill_skips_steps_with_existing_rows(test_client):
    session_id, step_id = _seed(
        "BACKFILL-EXISTING",
        ADMINISTRATION,
        hourly_rates=_slots(a=33.8),
        time_required=_slots(a=30),
        role_sources=None,
    )
    # An authoritative row already exists (e.g. a fresh effort calc): backfill
    # must not touch this step.
    db.replace_process_step_personnel_effort(
        session_id, ADMINISTRATION, step_id,
        [
            {"period": "current", "qualification": "hoeherer_dienst",
             "wage_source_kind": "verwaltungsebene", "wage_source_value": "bund",
             "time_required_in_min": 99, "model_hourly_rate": 67.6},
        ],
    )
    _run_backfill()
    rows = db.list_process_step_personnel_effort(session_id, ADMINISTRATION, step_id)
    assert len(rows) == 1
    assert rows[0]["wage_source_value"] == "bund"
    assert rows[0]["qualification"] == "hoeherer_dienst"


def test_backfill_preserves_personnel_cost(test_client):
    # Two qualifications in one step; row cost must equal the slot cost exactly.
    session_id, step_id = _seed(
        "BACKFILL-COST",
        ADMINISTRATION,
        hourly_rates=_slots(a=33.8, b=43.2),
        time_required=_slots(a=30, b=10),
        role_sources=[
            {"slot": "a", "role": "", "source_kind": "verwaltungsebene", "source_value": "bund"},
            {"slot": "b", "role": "", "source_kind": "verwaltungsebene", "source_value": "laender"},
        ],
    )
    _run_backfill()

    rows = [
        r
        for r in db.list_process_step_personnel_effort(session_id, ADMINISTRATION, step_id)
        if r["period"] == "current"
    ]
    row_cost = sum(r["model_hourly_rate"] * r["time_required_in_min"] / 60 for r in rows)
    slot_cost = 33.8 * 30 / 60 + 43.2 * 10 / 60
    assert row_cost == pytest.approx(slot_cost)
