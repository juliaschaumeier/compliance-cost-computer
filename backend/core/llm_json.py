from __future__ import annotations

import json
import re
from typing import Any

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


def parse_json_object(payload: str) -> dict[str, Any] | None:
    cleaned = clean_llm_payload(payload)
    try:
        data = json.loads(cleaned)
    except Exception:
        data = extract_last_json_object(cleaned)
    if not isinstance(data, dict):
        return None
    return data


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
