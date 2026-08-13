from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any


class LegisLlmImportError(ValueError):
    """Raised when a LegisLLM export cannot be transformed into law texts."""


@dataclass(frozen=True)
class LegisLlmLawTexts:
    current_text: str
    proposed_text: str
    current_filename: str
    proposed_filename: str


_STOP_WORDS = {
    "an",
    "aus",
    "das",
    "dem",
    "den",
    "der",
    "des",
    "die",
    "eine",
    "einem",
    "einen",
    "einer",
    "eines",
    "fuer",
    "in",
    "im",
    "oder",
    "sowie",
    "und",
    "von",
    "zur",
    "zum",
}

_TRANSLATION_TABLE = str.maketrans(
    {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "ae",
        "Ö": "oe",
        "Ü": "ue",
        "ß": "ss",
    }
)


def build_legisllm_law_texts(payload: bytes | str) -> LegisLlmLawTexts:
    data = _load_json(payload)
    steps = data.get("schritte")
    if not isinstance(steps, dict):
        raise LegisLlmImportError("schritte fehlt oder ist kein Objekt")

    implementation = steps.get("5_umsetzung")
    if not isinstance(implementation, list) or not implementation:
        raise LegisLlmImportError("schritte.5_umsetzung fehlt oder ist leer")

    title = _optional_string(steps.get("1_aufgabenstellung"))
    export_date = _format_export_date(data.get("exportiertAm"))
    pair_hash = _short_hash(implementation)
    slug = _slugify(title) or "legisllm-import"

    current_sections = _initial_sections(title)
    proposed_sections = _initial_sections(title)

    for index, item in enumerate(implementation, start=1):
        if not isinstance(item, dict):
            raise LegisLlmImportError(
                f"schritte.5_umsetzung[{index}] ist kein Objekt"
            )
        original = item.get("originalNorm")
        amended = item.get("amendedNorm")
        if not isinstance(original, dict):
            raise LegisLlmImportError(
                f"schritte.5_umsetzung[{index}].originalNorm fehlt oder ist kein Objekt"
            )
        if not isinstance(amended, dict):
            raise LegisLlmImportError(
                f"schritte.5_umsetzung[{index}].amendedNorm fehlt oder ist kein Objekt"
            )
        current_sections.append(_format_norm_section(original, "Ursprüngliche Fassung"))
        proposed_sections.append(_format_norm_section(amended, "Geänderte Fassung"))

    base = f"{slug}_{export_date}_{pair_hash}"
    return LegisLlmLawTexts(
        current_text="\n\n".join(current_sections).strip(),
        proposed_text="\n\n".join(proposed_sections).strip(),
        current_filename=f"{base}_gueltig.legisllm",
        proposed_filename=f"{base}_vorschlag.legisllm",
    )


def _load_json(payload: bytes | str) -> dict[str, Any]:
    if isinstance(payload, bytes):
        if not payload:
            raise LegisLlmImportError("Datei ist leer")
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise LegisLlmImportError("Datei ist nicht UTF-8-kodiert") from exc
    else:
        text = payload
    if not text.strip():
        raise LegisLlmImportError("Datei ist leer")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LegisLlmImportError(f"JSON konnte nicht gelesen werden: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise LegisLlmImportError("LegisLLM-Export muss ein JSON-Objekt sein")
    return data


def _optional_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _initial_sections(title: str) -> list[str]:
    return [title] if title else []


def _format_export_date(value: Any) -> str:
    raw = _optional_string(value)
    if raw:
        normalized = raw.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized).strftime("%Y%m%d")
        except ValueError:
            pass
    return "ohne-datum"


def _short_hash(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:8]


def _slugify(value: str) -> str:
    normalized = value.translate(_TRANSLATION_TABLE).lower()
    words = [
        word
        for word in re.split(r"[^a-z0-9]+", normalized)
        if word and word not in _STOP_WORDS
    ]
    slug = "-".join(words)
    return slug[:72].strip("-")


def _format_norm_section(norm: dict[str, Any], label: str) -> str:
    header = _format_norm_header(norm)
    wording = _optional_string(norm.get("wording")) or "entfällt"
    return f"{header}\n{label}\n{wording}"


def _format_norm_header(norm: dict[str, Any]) -> str:
    enbez = _optional_string(norm.get("enbez"))
    jurabk = _optional_string(norm.get("jurabk"))
    paragraph = _optional_string(norm.get("P"))
    if not enbez and not jurabk:
        raise LegisLlmImportError("Norm ohne enbez/jurabk kann nicht importiert werden")
    parts = [enbez] if enbez else []
    if paragraph:
        parts.extend(["Abs.", paragraph])
    if jurabk:
        parts.append(jurabk)
    return " ".join(parts)
