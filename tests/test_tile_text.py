from backend.core import db


def test_build_process_tile_text_omits_cost_line():
    text = db.build_process_tile_text("Prozessbeschreibung", 1234.5)
    assert text == "Prozessbeschreibung"
