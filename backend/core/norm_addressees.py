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

# Compact wage-source tags for the row-based provenance shown in tiles, mirroring
# the EA editor (frontend SOURCE_TAGS). Business WZ sections (A..S) have no entry
# and fall back to the bare section letter.
WAGE_SOURCE_TAGS: dict[str, str] = {
    "bund": "Bund",
    "laender": "Laender",
    "kommunen": "Kommunen",
    "sozialversicherung": "SV",
    "durchschnitt": "Durchschnitt",
    "gesamtwirtschaft": "Gesamtwirtschaft",
}

# Human labels for the row-model qualification dimension, by norm addressee.
PERSONNEL_QUALIFICATION_LABELS: dict[str, dict[str, str]] = {
    ADMINISTRATION: {
        "einfacher_und_mittlerer_dienst": "Einfacher und mittlerer Dienst",
        "gehobener_dienst": "Gehobener Dienst",
        "hoeherer_dienst": "Hoeherer Dienst",
        "durchschnitt": "Durchschnitt",
    },
    BUSINESS: {
        "niedrig": "Niedrig",
        "mittel": "Mittel",
        "hoch": "Hoch",
        "durchschnitt": "Durchschnitt",
    },
}


def personnel_provenance_label(
    norm_addressee: str, wage_source_value: str, qualification: str
) -> str:
    """Compact wage provenance for a personnel-effort row, e.g. ``Bund -
    Gehobener Dienst`` or ``R - Mittel`` (Comment 2)."""
    source = WAGE_SOURCE_TAGS.get(wage_source_value, wage_source_value)
    qualification_label = PERSONNEL_QUALIFICATION_LABELS.get(norm_addressee, {}).get(
        qualification, qualification
    )
    return f"{source} - {qualification_label}"


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
