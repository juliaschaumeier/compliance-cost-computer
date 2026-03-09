from __future__ import annotations

from collections.abc import Mapping


CHANGE_STATUS_KEYS = ("aenderungsstatus", "change_status", "status_change", "status")


def normalize_change_status(value: object) -> str:
    raw = str(value or "").strip().lower()
    if raw in {
        "unveraendert",
        "unverändert",
        "gleich",
        "gleichbleibend",
        "unveraendert geblieben",
        "unchanged",
        "same",
        "no_change",
        "no change",
    }:
        return "unveraendert"
    if raw in {"eingefuehrt", "eingeführt", "introduced", "new"}:
        return "eingefuehrt"
    if raw in {"abgeschafft", "entfallen", "entfaellt", "obsolete", "deleted", "removed"}:
        return "abgeschafft"
    if raw in {"geaendert", "geändert", "changed", "updated"}:
        return "geaendert"
    return "geaendert"


def extract_change_status(payload: Mapping[str, object]) -> str:
    for key in CHANGE_STATUS_KEYS:
        value = payload.get(key)
        if value is None:
            continue
        return normalize_change_status(value)
    return "geaendert"
