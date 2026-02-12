from backend.core import db


def test_build_process_step_tile_text_execution_scope_handles_zero_int():
    """Renders per-case vs per-group correctly for SQLite int flags."""
    text = db.build_process_step_tile_text(
        description="Beschreibung",
        hourly_rates={"a": None, "b": None, "c": None, "d": None, "e": None},
        time_required={"a": None, "b": None, "c": None, "d": None, "e": None},
        expenses=None,
        cost=100,
        execution_per_case=0,
    )
    assert "Kosten:" in text
    assert "pro Fallgruppe" in text


def test_build_process_step_tile_text_execution_scope_handles_one_str():
    """Accepts string flags and treats '1' as per-case."""
    text = db.build_process_step_tile_text(
        description="Beschreibung",
        hourly_rates={"a": None, "b": None, "c": None, "d": None, "e": None},
        time_required={"a": None, "b": None, "c": None, "d": None, "e": None},
        expenses=None,
        cost=100,
        execution_per_case="1",
    )
    assert "Kosten:" in text
    assert "pro Einzelfall" in text
