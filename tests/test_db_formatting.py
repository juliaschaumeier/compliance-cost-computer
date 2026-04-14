from backend.core.db_formatting import format_currency
from backend.routers.costs import _build_total_tile_text
from backend.core.norm_addressees import ADMINISTRATION, CITIZENS


def test_format_currency_keeps_compact_format_for_non_annual_values():
    assert format_currency(123_456_789) == "123,5 Mio. €"


def test_format_currency_uses_whole_millions_for_large_annual_values():
    assert (
        format_currency(123_456_789, annualized=True)
        == "123 Millionen Euro pro Jahr"
    )


def test_build_total_tile_text_uses_annualized_wording_for_large_admin_totals():
    assert (
        _build_total_tile_text(
            norm_addressee=ADMINISTRATION,
            total_cost=123_456_789,
            total_time_minutes=None,
            total_expenses=None,
        )
        == "123 Millionen Euro pro Jahr"
    )


def test_build_total_tile_text_keeps_citizens_time_and_expenses_format():
    assert (
        _build_total_tile_text(
            norm_addressee=CITIZENS,
            total_cost=None,
            total_time_minutes=120,
            total_expenses=50,
        )
        == "Zeit: 2 Std.\nSachaufwand: 50 €"
    )
