from __future__ import annotations

import json
import logging
import re
from typing import Any

from fastapi import HTTPException

logger = logging.getLogger(__name__)

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_THINK_FENCE_RE = re.compile(r"```(?:think|thinking)[\s\S]*?```", re.IGNORECASE)


def clean_llm_payload(payload: str) -> str:
    cleaned = _THINK_BLOCK_RE.sub("", payload)
    cleaned = _THINK_FENCE_RE.sub("", cleaned)
    return cleaned.strip()


def extract_last_json_object(payload: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    index = 0
    last: dict[str, Any] | None = None
    while True:
        start = payload.find("{", index)
        if start == -1:
            break
        try:
            data, end = decoder.raw_decode(payload, start)
            if isinstance(data, dict):
                last = data
            index = end
        except json.JSONDecodeError:
            index = start + 1
    return last


def parse_json_object(payload: str) -> dict[str, Any]:
    data, _parse_mode = parse_json_object_with_mode(payload)
    if not isinstance(data, dict):
        raise ValueError("no JSON object found in payload")
    return data


def parse_json_object_with_mode(payload: str) -> tuple[dict[str, Any] | None, str]:
    cleaned = clean_llm_payload(payload)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data, "direct_json_loads"
    except Exception:
        pass
    data = extract_last_json_object(cleaned)
    if not isinstance(data, dict):
        return None, "no_json_object"
    # Fallback-Pfad: LLM-Output konnte nicht direkt als JSON geladen
    # werden. Das kommt bei LLMs mit Vor-/Nachtext oder bei abgeschnittenen
    # Ausgaben vor. Wir loggen das systemweit als WARN, damit Ops
    # systematische Qualitaetsprobleme eines Modells / Providers erkennen
    # koennen - auch in Routern, die die fallback_kinds nicht ueber
    # mark_llm_parse_fallback tracken.
    logger.warning(
        "llm_json: fallback extract_last_json_object verwendet "
        "(payload_len=%d, direct_json_loads fehlgeschlagen)",
        len(cleaned),
    )
    return data, "extract_last_json_object"


def looks_truncated(payload: str) -> bool:
    text = clean_llm_payload(payload)
    if not text.startswith("{"):
        return False
    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        return exc.pos >= len(text)
    return False


def require_json_object(
    payload: str,
    *,
    error_context: str,
    required_top_level_key: str | None = None,
) -> tuple[dict[str, Any], str]:
    if looks_truncated(payload):
        expected = (
            f", expected top-level key '{required_top_level_key}'"
            if required_top_level_key is not None
            else ""
        )
        logger.warning(
            "llm_json: abgeschnittene LLM-Antwort erkannt "
            "(payload_len=%d, context=%s)",
            len(clean_llm_payload(payload)),
            error_context,
        )
        raise HTTPException(
            status_code=422,
            detail=(
                f"{error_context}: truncated LLM response, "
                f"stream ended mid-JSON{expected}"
            ),
        )
    data, parse_mode = parse_json_object_with_mode(payload)
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=422,
            detail=f"{error_context}: no JSON object found in LLM response",
        )
    if required_top_level_key is not None and required_top_level_key not in data:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{error_context}: expected top-level key "
                f"'{required_top_level_key}' in LLM response"
            ),
        )
    return data, parse_mode


def extract_fallgruppen(data: dict[str, Any]) -> list[dict[str, Any]]:
    if "fallgruppen" in data and isinstance(data["fallgruppen"], list):
        return [item for item in data["fallgruppen"] if isinstance(item, dict)]
    processes = data.get("prozesse")
    if not isinstance(processes, list):
        return []
    fallgruppen: list[dict[str, Any]] = []
    for process in processes:
        if not isinstance(process, dict):
            continue
        process_groups = process.get("fallgruppen")
        if isinstance(process_groups, list):
            fallgruppen.extend([item for item in process_groups if isinstance(item, dict)])
    return fallgruppen
