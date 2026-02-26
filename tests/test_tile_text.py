from backend.core import db


def test_build_process_step_tile_text_execution_scope_handles_zero_int():
    """Renders per-case vs per-group correctly for SQLite int flags."""
    text = db.build_process_step_tile_text(
        description="Beschreibung",
        hourly_rates_current={"a": None, "b": None, "c": None, "d": None},
        time_required_current={"a": None, "b": None, "c": None, "d": None},
        expenses_current=None,
        cost_current=None,
        hourly_rates_proposed={"a": None, "b": None, "c": None, "d": None},
        time_required_proposed={"a": None, "b": None, "c": None, "d": None},
        expenses_proposed=None,
        cost_proposed=100,
        execution_per_case=0,
    )
    assert "Kosten:" in text
    assert "pro Fallgruppe" in text


def test_build_process_step_tile_text_execution_scope_handles_one_str():
    """Accepts string flags and omits default per-case scope label."""
    text = db.build_process_step_tile_text(
        description="Beschreibung",
        hourly_rates_current={"a": None, "b": None, "c": None, "d": None},
        time_required_current={"a": None, "b": None, "c": None, "d": None},
        expenses_current=None,
        cost_current=None,
        hourly_rates_proposed={"a": None, "b": None, "c": None, "d": None},
        time_required_proposed={"a": None, "b": None, "c": None, "d": None},
        expenses_proposed=None,
        cost_proposed=100,
        execution_per_case="1",
    )
    assert "Kosten:" in text
    assert "pro Einzelfall" not in text
    assert "pro Fallgruppe" not in text
