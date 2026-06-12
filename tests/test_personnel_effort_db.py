"""Phase A DB layer for the row-based personnel-effort model.

Covers the wage-rate lookup seam, the child-table round-trip, the UNIQUE
constraint that lets mixed wage sources coexist, and the undo behaviour.
"""

import sqlite3

import pytest

from backend.core import db


def _seed_step(app_session_id: str = "PERSONNEL-EFFORT") -> tuple[int, int]:
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    process_id = db.insert_process(session_id, "Prozess", "Beschreibung")
    case_group_id = db.insert_case_group(
        session_id, process_id, "Fallgruppe", "Beschreibung"
    )
    step_id = db.insert_process_step(
        session_id, case_group_id, "Schritt 1", "Beschreibung Schritt 1"
    )
    return session_id, step_id


def test_get_model_hourly_rate_resolves_from_constants():
    # admin bund / gehobener Dienst -> slot b -> 40.4
    assert db.get_model_hourly_rate("administration", "bund", "gehobener_dienst") == 40.4
    # business WZ K / hoch -> slot c -> 93.1
    assert db.get_model_hourly_rate("business", "K", "hoch") == 93.1
    # citizens are not monetised
    assert db.get_model_hourly_rate("citizens", "x", "y") == 0.0
    # unknown source / qualification -> None (caller decides)
    assert db.get_model_hourly_rate("administration", "unknown", "gehobener_dienst") is None
    assert db.get_model_hourly_rate("administration", "bund", "unknown") is None


def test_replace_and_list_round_trip_keeps_mixed_sources_separate():
    session_id, step_id = _seed_step()
    rows = [
        {
            "period": "current",
            "qualification": "gehobener_dienst",
            "wage_source_kind": "verwaltungsebene",
            "wage_source_value": "bund",
            "time_required_in_min": 30,
            "model_hourly_rate": 40.4,
        },
        {
            "period": "current",
            "qualification": "gehobener_dienst",
            "wage_source_kind": "verwaltungsebene",
            "wage_source_value": "laender",
            "time_required_in_min": 20,
            "model_hourly_rate": 43.2,
        },
    ]
    db.replace_process_step_personnel_effort(session_id, "administration", step_id, rows)

    stored = db.list_process_step_personnel_effort(session_id, "administration", step_id)
    # Bund and Laender for the same qualification coexist (no overwrite).
    assert len(stored) == 2
    by_source = {row["wage_source_value"]: row for row in stored}
    assert by_source["bund"]["time_required_in_min"] == 30
    assert by_source["bund"]["model_hourly_rate"] == 40.4
    assert by_source["laender"]["time_required_in_min"] == 20


def test_replace_is_idempotent_per_step():
    session_id, step_id = _seed_step()
    row = {
        "period": "proposed",
        "qualification": "mittel",
        "wage_source_kind": "wirtschaftsabschnitt",
        "wage_source_value": "K",
        "time_required_in_min": 15,
        "model_hourly_rate": 54.4,
    }
    db.replace_process_step_personnel_effort(session_id, "business", step_id, [row])
    db.replace_process_step_personnel_effort(session_id, "business", step_id, [row])

    stored = db.list_process_step_personnel_effort(session_id, "business", step_id)
    assert len(stored) == 1


def test_unique_constraint_rejects_duplicate_dimensions():
    session_id, step_id = _seed_step()
    dup = {
        "period": "current",
        "qualification": "gehobener_dienst",
        "wage_source_kind": "verwaltungsebene",
        "wage_source_value": "bund",
        "time_required_in_min": 30,
        "model_hourly_rate": 40.4,
    }
    with pytest.raises(sqlite3.IntegrityError):
        db.replace_process_step_personnel_effort(
            session_id, "administration", step_id, [dup, dict(dup)]
        )


def test_undo_clears_personnel_rows_but_keeps_wage_overrides():
    session_id, step_id = _seed_step()
    db.replace_process_step_personnel_effort(
        session_id,
        "administration",
        step_id,
        [
            {
                "period": "current",
                "qualification": "gehobener_dienst",
                "wage_source_kind": "verwaltungsebene",
                "wage_source_value": "bund",
                "time_required_in_min": 30,
                "model_hourly_rate": 40.4,
            }
        ],
    )
    # A standalone session wage override must survive an effort undo.
    conn = db.get_conn()
    conn.execute(
        """
        INSERT INTO session_wage_rate_overrides (
            session_id, norm_addressee, wage_source_kind, wage_source_value,
            qualification, hourly_rate_edited, last_edited_at
        ) VALUES (?, 'administration', 'verwaltungsebene', 'bund',
                  'gehobener_dienst', 55.0, current_timestamp)
        """,
        (session_id,),
    )
    conn.commit()

    db.clear_effort_metrics(session_id, "administration")

    assert db.list_process_step_personnel_effort(session_id, "administration") == []
    surviving = db.get_conn().execute(
        "SELECT COUNT(*) FROM session_wage_rate_overrides WHERE session_id = ?",
        (session_id,),
    ).fetchone()[0]
    assert surviving == 1
