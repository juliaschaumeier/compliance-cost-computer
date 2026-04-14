from __future__ import annotations

from typing import Final


ADMINISTRATION: Final[str] = "administration"
BUSINESS: Final[str] = "business"
CITIZENS: Final[str] = "citizens"

ALL_NORM_ADDRESSEES: tuple[str, ...] = (
    ADMINISTRATION,
    BUSINESS,
    CITIZENS,
)

SUPPORTED_NORM_ADDRESSEES: tuple[str, ...] = (
    ADMINISTRATION,
    BUSINESS,
    CITIZENS,
)

DISPLAY_LABELS: dict[str, str] = {
    ADMINISTRATION: "Verwaltung",
    BUSINESS: "Wirtschaft",
    CITIZENS: "Buerger",
}

EFFORT_GROUP_LABELS: dict[str, dict[str, str]] = {
    ADMINISTRATION: {
        "a": "Einfacher und mittlerer Dienst",
        "b": "Gehobener Dienst",
        "c": "Hoeherer Dienst",
        "d": "Durchschnitt",
    },
    BUSINESS: {
        "a": "Niedrig",
        "b": "Mittel",
        "c": "Hoch",
        "d": "Durchschnitt",
    },
    CITIZENS: {
        "a": "Zeit",
        "b": "Reserve B",
        "c": "Reserve C",
        "d": "Reserve D",
    },
}


def normalize_norm_addressee(value: str | None) -> str:
    if value is None:
        return ADMINISTRATION
    normalized = str(value).strip().lower()
    if not normalized:
        raise ValueError("Unsupported norm_addressee: empty value")
    if normalized == ADMINISTRATION:
        return ADMINISTRATION
    if normalized == BUSINESS:
        return BUSINESS
    if normalized == CITIZENS:
        return CITIZENS
    raise ValueError(f"Unsupported norm_addressee: {value}")
