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


# Echo-Feld im Antwort-JSON der addressee-spezifischen Prompts. Das LLM soll
# den erwarteten Normadressaten im Output wiederholen; der Parser vergleicht
# das Echo mit dem Run-NA als Lane-Telemetrie.
NORM_ADDRESSEE_ECHO_KEY: Final[str] = "normadressat"
NORM_ADDRESSEE_ECHO_MISSING: Final[str] = "norm_addressee_missing"
NORM_ADDRESSEE_ECHO_MISMATCH: Final[str] = "norm_addressee_mismatch"


def check_norm_addressee_echo(
    data: dict,
    expected: str | None,
) -> set[str]:
    """Soft-Validation: vergleicht top-level normadressat-Echo mit Run-NA.

    Liefert ein Set mit Fallback-Kinds fuer mark_llm_parse_fallback. Blockiert
    den Flow NICHT - reine Telemetrie, um zu erkennen wenn das LLM die
    Adressaten-Spur verlaesst.
    """
    if expected is None:
        return set()
    if not isinstance(data, dict):
        return {NORM_ADDRESSEE_ECHO_MISSING}
    raw = data.get(NORM_ADDRESSEE_ECHO_KEY)
    if raw is None:
        return {NORM_ADDRESSEE_ECHO_MISSING}
    echoed = str(raw).strip().lower()
    if not echoed:
        return {NORM_ADDRESSEE_ECHO_MISSING}
    if echoed != expected:
        return {NORM_ADDRESSEE_ECHO_MISMATCH}
    return set()
