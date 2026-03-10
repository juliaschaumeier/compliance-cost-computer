from backend.core import db


def test_build_process_step_tile_text_omits_cost_lines():
    """Step tile body keeps effort details but omits aggregated cost output."""
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
    assert "Beschreibung" in text
    assert "Kosten:" not in text


def test_build_process_tile_text_omits_cost_line():
    text = db.build_process_tile_text("Prozessbeschreibung", 1234.5)
    assert text == "Prozessbeschreibung"
