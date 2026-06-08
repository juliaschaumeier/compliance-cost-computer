from backend.core import db
from backend.routers.costs import _build_total_tile_text


def test_build_process_tile_text_omits_cost_line():
    text = db.build_process_tile_text("Prozessbeschreibung", 1234.5)
    assert text == "Prozessbeschreibung"


def test_total_tile_text_citizens_time_and_expenses():
    text = _build_total_tile_text(
        norm_addressee="citizens",
        total_cost=None,
        bureaucracy_cost=None,
        total_time_minutes=120000.0,
        total_expenses=4200.0,
    )
    assert "Veränderung des jährlichen Zeitaufwandes: 2000 Std." in text
    assert "Veränderung des jährlichen Sachaufwandes: 4,20 Tsd. €" in text


def test_total_tile_text_business_shows_bureaucracy_line():
    text = _build_total_tile_text(
        norm_addressee="business",
        total_cost=59864.73,
        bureaucracy_cost=59864.73,
        total_time_minutes=None,
        total_expenses=None,
    )
    lines = text.splitlines()
    assert lines[0].startswith("Veränderung des jährlichen Erfüllungsaufwandes:")
    assert lines[1].startswith("davon Bürokratiekosten aus Informationspflichten:")


def test_total_tile_text_administration_splits_by_session_level():
    bund = _build_total_tile_text(
        norm_addressee="administration",
        total_cost=-6322.83,
        bureaucracy_cost=None,
        total_time_minutes=None,
        total_expenses=None,
        administration_level="bund",
    )
    assert "davon auf Bundesebene: -6,32 Tsd. €" in bund
    assert "davon auf Landesebene: 0 €" in bund

    laender = _build_total_tile_text(
        norm_addressee="administration",
        total_cost=100000.0,
        bureaucracy_cost=None,
        total_time_minutes=None,
        total_expenses=None,
        administration_level="laender",
    )
    assert "davon auf Bundesebene: 0 €" in laender
    assert "davon auf Landesebene: 100 Tsd. €" in laender
