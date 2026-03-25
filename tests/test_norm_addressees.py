import pytest

from backend.core.norm_addressees import (
    ADMINISTRATION,
    BUSINESS,
    CITIZENS,
    normalize_norm_addressee,
)
from backend.routers.regulations import _parse_addressee_list


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (None, ADMINISTRATION),
        ("administration", ADMINISTRATION),
        ("business", BUSINESS),
        ("citizens", CITIZENS),
    ],
)
def test_normalize_norm_addressee_accepts_supported_aliases(raw_value, expected):
    assert normalize_norm_addressee(raw_value) == expected


@pytest.mark.parametrize(
    "raw_value",
    ["verwaltung", "wirtschaft", "unternehmen", "buerger", "bürger", "citizen", "invalid"],
)
def test_normalize_norm_addressee_rejects_non_canonical_values(raw_value):
    with pytest.raises(ValueError):
        normalize_norm_addressee(raw_value)


def test_parse_addressee_list_accepts_only_canonical_values_and_deduplicates():
    parsed = _parse_addressee_list(["administration", "business", "citizens", "business"])

    assert parsed == [ADMINISTRATION, BUSINESS, CITIZENS]


def test_parse_addressee_list_rejects_non_canonical_values():
    assert _parse_addressee_list(["", None, "verwaltung", "business;citizens", "unbekannt"]) == [
        BUSINESS,
        CITIZENS,
    ]
