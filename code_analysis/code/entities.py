from __future__ import annotations

import difflib
import json
import math
import re
from typing import Any, Iterable

from common import ADDRESSEES, REQUIRED_TOP_LEVEL, parse_json_maybe, truthy

def norm_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.lower()
    repl = {
        "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
        "Ä": "ae", "Ö": "oe", "Ü": "ue",
    }
    for src, dst in repl.items():
        text = text.replace(src, dst)
    text = re.sub(r"\b(fallgruppe|prozess|schritt|taetigkeit|tätigkeit)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def similarity(a: Any, b: Any) -> float:
    aa = norm_text(a)
    bb = norm_text(b)
    if not aa and not bb:
        return 1.0
    if not aa or not bb:
        return 0.0
    return difflib.SequenceMatcher(None, aa, bb).ratio()

def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, str):
            value = value.replace(",", ".")
        num = float(value)
        if math.isnan(num):
            return None
        return num
    except (TypeError, ValueError):
        return None

def effective(row: dict[str, Any], base: str, edited: str | None = None) -> float | None:
    if edited and row.get(edited) is not None:
        return safe_float(row.get(edited))
    return safe_float(row.get(base))

def detect_addressee_from_text(*values: Any) -> str | None:
    raw = "\n".join(str(v or "") for v in values)
    text = norm_text(raw)
    explicit_patterns = (
        ("administration", (
            "dieser lauf betrifft nur den normadressaten verwaltung",
            "normadressat administration",
            "normadressat `administration`",
            '"normadressat": "administration"',
            '"norm_addressee": "administration"',
        )),
        ("business", (
            "dieser lauf betrifft nur den normadressaten wirtschaft",
            "normadressat business",
            "normadressat `business`",
            '"normadressat": "business"',
            '"norm_addressee": "business"',
        )),
        ("citizens", (
            "dieser lauf betrifft nur den normadressaten buergerinnen und buerger",
            "dieser lauf betrifft nur den normadressaten buerger",
            "normadressat citizens",
            "normadressat `citizens`",
            '"normadressat": "citizens"',
            '"norm_addressee": "citizens"',
        )),
    )
    raw_lower = raw.lower()
    for addressee, patterns in explicit_patterns:
        if any(pattern in text or pattern in raw_lower for pattern in patterns):
            return addressee
    return None

def answer_addressee(answer: dict[str, Any]) -> str | None:
    raw = answer.get("norm_addressee")
    if raw in ADDRESSEES:
        return raw
    metadata = parse_json_maybe(answer.get("metadata"))
    if isinstance(metadata, dict):
        raw_meta = metadata.get("norm_addressee") or metadata.get("normadressat")
        if raw_meta in ADDRESSEES:
            return str(raw_meta)
    parsed = classify_json_answer(answer.get("answer_text"), str(answer.get("prompt_id") or "")).get("data")
    if isinstance(parsed, dict):
        raw_echo = parsed.get("normadressat") or parsed.get("norm_addressee")
        if raw_echo in ADDRESSEES:
            return str(raw_echo)
    return detect_addressee_from_text(answer.get("prompt_text"))

def strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()

def brace_state(text: str) -> dict[str, Any]:
    curly = 0
    square = 0
    in_string = False
    escaped = False
    for ch in text:
        if escaped:
            escaped = False
            continue
        if ch == "\\" and in_string:
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            curly += 1
        elif ch == "}":
            curly -= 1
        elif ch == "[":
            square += 1
        elif ch == "]":
            square -= 1
    return {"curly": curly, "square": square, "in_string": in_string}

def classify_json_answer(answer_text: Any, prompt_id: str | None = None) -> dict[str, Any]:
    text = "" if answer_text is None else str(answer_text)
    cleaned = strip_code_fence(text)
    required = REQUIRED_TOP_LEVEL.get(str(prompt_id or ""))
    result = {
        "parse_class": "unknown",
        "syntax_class": "unknown",
        "schema_class": None,
        "extraction_method": None,
        "required_key": required,
        "data": None,
        "repair_suffix": None,
        "tail": cleaned[-240:],
        "error": None,
    }
    candidates = [cleaned]
    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first >= 0 and last > first:
        candidates.append(cleaned[first:last + 1])
    for candidate in candidates:
        try:
            data = json.loads(candidate)
            schema_class = required_shape_class(data, required)
            result["data"] = data
            result["syntax_class"] = "valid_json"
            result["schema_class"] = schema_class or ("valid_required_shape" if required else None)
            result["extraction_method"] = "direct" if candidate == cleaned else "extracted_json_object"
            result["parse_class"] = schema_class or "valid_json"
            return result
        except json.JSONDecodeError as exc:
            result["error"] = str(exc)

    start = cleaned.find("{")
    obj = cleaned[start:] if start >= 0 else cleaned
    state = brace_state(obj)
    if start >= 0 and state["curly"] >= 0 and state["square"] >= 0:
        if state["in_string"]:
            result["parse_class"] = "hard_mid_content_truncation"
            result["syntax_class"] = "hard_mid_content_truncation"
            return result
        suffix = ""
        suffix += "]" * max(0, int(state["square"]))
        suffix += "}" * max(0, int(state["curly"]))
        if 0 < len(suffix) <= 4:
            try:
                data = json.loads(obj + suffix)
                schema_class = required_shape_class(data, required)
                result["data"] = data
                result["repair_suffix"] = suffix
                result["syntax_class"] = "near_complete_missing_closer"
                result["schema_class"] = schema_class or ("valid_required_shape" if required else None)
                result["extraction_method"] = "repaired_missing_closer"
                result["parse_class"] = schema_class or "near_complete_missing_closer"
                return result
            except json.JSONDecodeError:
                pass
        if len(suffix) > 4 or re.search(r'["A-Za-z0-9,;:]\s*$', obj):
            result["parse_class"] = "hard_mid_content_truncation"
            result["syntax_class"] = "hard_mid_content_truncation"
            return result

    if first >= 0:
        result["parse_class"] = "invalid_json"
        result["syntax_class"] = "invalid_json"
    else:
        result["parse_class"] = "non_json_prose"
        result["syntax_class"] = "non_json_prose"
    return result

def required_shape_class(data: Any, required: str | None) -> str | None:
    if not required:
        return None
    if not isinstance(data, dict) or required not in data:
        return "wrong_top_level_key"
    value = data.get(required)
    if isinstance(value, list):
        return None if value else "empty_or_invalid_top_level"
    if isinstance(value, dict):
        return None if value else "empty_or_invalid_top_level"
    return "empty_or_invalid_top_level"

def iter_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for item in value:
            yield from iter_dicts(item)

def first_value(dct: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in dct and dct.get(key) not in (None, ""):
            return dct.get(key)
    return None

def change_status_of(dct: dict[str, Any]) -> str | None:
    value = first_value(dct, ("aenderungsstatus", "änderungsstatus", "change_status", "status"))
    if value is None:
        return None
    text = norm_text(value)
    if "eingefuehrt" in text or "neu" == text:
        return "eingefuehrt"
    if "abgeschafft" in text or "wegfall" in text:
        return "abgeschafft"
    if "geaendert" in text or "geandert" in text:
        return "geaendert"
    return text or None

def collect_case_groups(data: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    def walk(node: Any, process_ctx: dict[str, Any] | None = None, norm: str | None = None) -> None:
        if isinstance(node, dict):
            current_norm = norm or first_value(node, ("normadressat", "norm_addressee"))
            if current_norm not in ADDRESSEES:
                current_norm = norm
            process_keys = ("prozess_id", "process_id", "prozess_bezeichnung", "process")
            next_process = process_ctx
            if any(key in node for key in process_keys):
                next_process = {
                    "process_id": first_value(node, ("prozess_id", "process_id")),
                    "process_name": first_value(node, ("prozess_bezeichnung", "process", "prozess")),
                }
            has_group = any(key in node for key in (
                "fallgruppen_id", "fallgruppe_id", "case_group_id", "fallgruppe",
                "fallgruppen_bezeichnung", "case_group",
            ))
            if has_group:
                rows.append({
                    "case_group_id": first_value(node, ("fallgruppen_id", "fallgruppe_id", "case_group_id")),
                    "case_group": first_value(node, ("fallgruppe", "fallgruppen_bezeichnung", "case_group", "name")),
                    "description": first_value(node, ("beschreibung", "description")),
                    "change_status": change_status_of(node),
                    "norm_addressee": current_norm,
                    "process_id": (next_process or {}).get("process_id"),
                    "process_name": (next_process or {}).get("process_name"),
                    "raw": node,
                })
            for child in node.values():
                walk(child, next_process, current_norm)
        elif isinstance(node, list):
            for item in node:
                walk(item, process_ctx, norm)
    walk(data)
    return rows

def collect_steps(data: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    def walk(node: Any, case_ctx: dict[str, Any] | None = None, process_ctx: dict[str, Any] | None = None, norm: str | None = None) -> None:
        if isinstance(node, dict):
            current_norm = norm or first_value(node, ("normadressat", "norm_addressee"))
            if current_norm not in ADDRESSEES:
                current_norm = norm
            next_process = process_ctx
            if any(key in node for key in ("prozess_id", "process_id", "prozess_bezeichnung", "process")):
                next_process = {
                    "process_id": first_value(node, ("prozess_id", "process_id")),
                    "process_name": first_value(node, ("prozess_bezeichnung", "process", "prozess")),
                }
            next_case = case_ctx
            if any(key in node for key in ("fallgruppen_id", "fallgruppe_id", "case_group_id", "fallgruppe", "case_group")):
                next_case = {
                    "case_group_id": first_value(node, ("fallgruppen_id", "fallgruppe_id", "case_group_id")),
                    "case_group": first_value(node, ("fallgruppe", "fallgruppen_bezeichnung", "case_group", "name")),
                }
            has_step = any(key in node for key in (
                "schritt_id", "step_id", "taetigkeit", "tätigkeit", "prozessschritt",
                "step", "schritt",
            ))
            if has_step and first_value(node, ("taetigkeit", "tätigkeit", "prozessschritt", "step", "schritt")):
                rows.append({
                    "step_id": first_value(node, ("schritt_id", "step_id")),
                    "step": first_value(node, ("taetigkeit", "tätigkeit", "prozessschritt", "step", "schritt")),
                    "description": first_value(node, ("beschreibung", "description")),
                    "change_status": change_status_of(node),
                    "norm_addressee": current_norm,
                    "process_id": (next_process or {}).get("process_id"),
                    "process_name": (next_process or {}).get("process_name"),
                    "case_group_id": (next_case or {}).get("case_group_id"),
                    "case_group": (next_case or {}).get("case_group"),
                    "raw": node,
                })
            for child in node.values():
                walk(child, next_case, next_process, current_norm)
        elif isinstance(node, list):
            for item in node:
                walk(item, case_ctx, process_ctx, norm)
    walk(data)
    return rows

def collect_processes(data: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dct in iter_dicts(data):
        if any(key in dct for key in ("prozess_id", "process_id", "prozess_bezeichnung", "process", "prozess")):
            name = first_value(dct, ("prozess_bezeichnung", "process", "prozess", "name"))
            if name:
                rows.append({
                    "process_id": first_value(dct, ("prozess_id", "process_id")),
                    "process": name,
                    "description": first_value(dct, ("beschreibung", "description")),
                    "change_status": change_status_of(dct),
                    "norm_addressee": first_value(dct, ("normadressat", "norm_addressee")),
                    "raw": dct,
                })
    return rows

def collect_change_metric_entities(data: Any) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    for group in collect_case_groups(data):
        raw = group["raw"]
        entities.append({
            **{k: group.get(k) for k in ("case_group_id", "case_group", "norm_addressee", "process_id")},
            "entity_type": "case_group",
            "entity_name": group.get("case_group"),
            "change_status": group.get("change_status"),
            "current_value": metric_value(raw, "current"),
            "proposed_value": metric_value(raw, "proposed"),
        })
    for step in collect_steps(data):
        raw = step["raw"]
        entities.append({
            **{k: step.get(k) for k in ("step_id", "step", "case_group_id", "norm_addressee")},
            "entity_type": "process_step",
            "entity_name": step.get("step"),
            "change_status": step.get("change_status"),
            "current_value": effort_value(raw, "current"),
            "proposed_value": effort_value(raw, "proposed"),
        })
    return entities

def metric_value(raw: dict[str, Any], period: str) -> float | None:
    keys = {
        "current": (
            "cases_current", "faelle_gueltig", "fälle_gültig", "fallzahl_gueltig",
            "anzahl_faelle_gueltig", "anzahl_betroffene_gueltig",
        ),
        "proposed": (
            "cases_proposed", "faelle_vorschlag", "fälle_vorschlag",
            "fallzahl_vorschlag", "anzahl_faelle_vorschlag",
            "anzahl_betroffene_vorschlag",
        ),
    }[period]
    direct = safe_float(first_value(raw, keys))
    if direct is not None:
        return direct
    if period == "current":
        addressees = safe_float(first_value(raw, ("addressees_current", "anzahl_betroffene_gueltig")))
        freq = safe_float(first_value(raw, ("annual_frequency_current", "haeufigkeit_pro_jahr_gueltig")))
    else:
        addressees = safe_float(first_value(raw, ("addressees_proposed", "anzahl_betroffene_vorschlag")))
        freq = safe_float(first_value(raw, ("annual_frequency_proposed", "haeufigkeit_pro_jahr_vorschlag")))
    if addressees is not None and freq is not None:
        return addressees * freq
    return None

def effort_value(raw: dict[str, Any], period: str) -> float | None:
    suffixes = ("current", "gueltig", "gültig") if period == "current" else ("proposed", "vorschlag")
    total = 0.0
    found = False
    for key, value in raw.items():
        nkey = norm_text(key)
        if not any(suf in nkey for suf in suffixes):
            continue
        if any(part in nkey for part in ("zeit", "time", "min", "expense", "kosten", "sachaufwand")):
            num = safe_float(value)
            if num is not None:
                total += num
                found = True
    return total if found else None

def case_group_cases(row: dict[str, Any], period: str) -> float | None:
    if period == "current":
        direct = effective(row, "cases_current", "cases_current_edited")
        if direct is not None:
            return direct
        a = effective(row, "addressees_current", "addressees_current_edited")
        f = effective(row, "annual_frequency_current", "annual_frequency_current_edited")
    else:
        direct = effective(row, "cases_proposed", "cases_proposed_edited")
        if direct is not None:
            return direct
        a = effective(row, "addressees_proposed", "addressees_proposed_edited")
        f = effective(row, "annual_frequency_proposed", "annual_frequency_proposed_edited")
    if a is not None and f is not None:
        return a * f
    return None

def persisted_step_effort(row: dict[str, Any], period: str) -> float | None:
    total = 0.0
    found = False
    for key in ("a", "b", "c", "d"):
        value = safe_float(row.get(f"time_required_in_min_{key}_{period}"))
        if value is not None:
            total += value
            found = True
    expense = safe_float(row.get(f"expenses_{period}"))
    if expense is not None:
        total += expense
        found = True
    return total if found else None

def status_inconsistency(status: str | None, current: float | None, proposed: float | None) -> str | None:
    if not status or current is None or proposed is None:
        return None
    eps = 1e-9
    if status == "eingefuehrt" and current > eps and proposed <= eps:
        return "introduced_but_current_positive_and_proposed_zero"
    if status == "eingefuehrt" and current > eps:
        return "introduced_but_current_positive"
    if status == "abgeschafft" and proposed > eps:
        return "abolished_but_proposed_positive"
    if status == "geaendert" and abs(current - proposed) <= eps:
        return "changed_but_values_equal"
    return None

def law_pair_key(session: dict[str, Any]) -> str:
    return f"{session.get('current_law_id') or 'none'}->{session.get('proposed_law_id') or 'none'}"

def normalize_status(value: Any) -> str | None:
    return change_status_of({"change_status": value})

def collect_regulation_like(data: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dct in iter_dicts(data):
        if not any(key in dct for key in ("normzitat", "legal_citation", "vorgaben_id", "beschreibung", "description")):
            continue
        citation = first_value(dct, ("normzitat", "legal_citation", "citation"))
        description = first_value(dct, ("beschreibung", "description"))
        normadressaten = first_value(dct, ("normadressaten", "normadressat", "addressees"))
        norm_text_value = norm_text(normadressaten)
        applies_business = (
            truthy(dct.get("applies_to_business"))
            or "business" in norm_text_value
            or "wirtschaft" in norm_text_value
            or "unternehmen" in norm_text_value
        )
        ip_value = first_value(dct, (
            "ist_informationspflicht_wirtschaft",
            "informationspflicht_wirtschaft",
            "is_business_information_obligation",
        ))
        rows.append({
            "regulation_id": first_value(dct, ("vorgaben_id", "regulation_id")),
            "legal_citation": citation,
            "description": description,
            "applies_to_business": applies_business,
            "is_business_information_obligation": truthy(ip_value),
            "change_status": change_status_of(dct),
        })
    return rows
