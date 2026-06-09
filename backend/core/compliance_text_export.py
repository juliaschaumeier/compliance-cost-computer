from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from backend.core import db
from backend.core.deep_research_cases import CASE_GROUP_RESEARCH_PURPOSE
from backend.core.norm_addressees import SUPPORTED_NORM_ADDRESSEES


USER_EDIT_REJECT = "reject_if_user_edits"
USER_EDIT_USE = "use_user_edits"
UserEditPolicy = Literal[
    "reject_if_user_edits",
    "use_user_edits",
]

_CASE_METRIC_KEYS = (
    "addressees_current",
    "annual_frequency_current",
    "cases_current",
    "addressees_proposed",
    "annual_frequency_proposed",
    "cases_proposed",
)
_CASE_EVIDENCE_KEYS = {
    "addressees_current": "anzahl_betroffene_gueltig",
    "annual_frequency_current": "haeufigkeit_pro_jahr_gueltig",
    "addressees_proposed": "anzahl_betroffene_vorschlag",
    "annual_frequency_proposed": "haeufigkeit_pro_jahr_vorschlag",
}
_STEP_EDITABLE_KEYS = (
    "time_required_in_min_a_current",
    "time_required_in_min_b_current",
    "time_required_in_min_c_current",
    "time_required_in_min_d_current",
    "expenses_current",
    "time_required_in_min_a_proposed",
    "time_required_in_min_b_proposed",
    "time_required_in_min_c_proposed",
    "time_required_in_min_d_proposed",
    "expenses_proposed",
)
_PAY_RATE_KEYS = ("a", "b", "c", "d")


@dataclass(frozen=True)
class ComplianceExportContext:
    snapshot: dict[str, Any]
    snapshot_json: str
    snapshot_sha256: str
    optional_deep_research_part_1_2: str
    deep_research_run_id: int | None
    deep_research_excerpt_status: str
    used_deep_research: bool
    has_user_edits: bool
    used_user_edits: bool
    examples: list[dict[str, Any]]
    metadata: dict[str, Any]


def normalize_user_edit_policy(value: str | None) -> UserEditPolicy:
    if value in {USER_EDIT_REJECT, USER_EDIT_USE}:
        return value  # type: ignore[return-value]
    return USER_EDIT_REJECT


def build_compliance_export_context(
    *,
    app_session_id: str,
    session_id: int,
    user_edit_policy: str | None = USER_EDIT_REJECT,
) -> ComplianceExportContext:
    policy = normalize_user_edit_policy(user_edit_policy)
    examples = db.list_compliance_text_examples(limit=3)
    session = db.get_session_by_id(session_id) or {}
    snapshot: dict[str, Any] = {
        "session": {
            "session_id": session_id,
            "app_session_id": app_session_id,
            "law_diff_title": session.get("law_diff_title"),
            "law_diff_blurb": session.get("law_diff_blurb"),
            "law_diff_summary": session.get("law_diff_summary"),
        },
        "user_edit_policy": policy,
        "prompt_examples": [_serialize_prompt_example(example) for example in examples],
        "normadressaten": [],
    }
    has_user_edits = False
    used_user_edits = policy == USER_EDIT_USE
    for addressee in SUPPORTED_NORM_ADDRESSEES:
        addressee_payload, addressee_has_edits = _build_addressee_payload(
            session_id,
            addressee,
            policy,
        )
        has_user_edits = has_user_edits or addressee_has_edits
        snapshot["normadressaten"].append(addressee_payload)

    research = _build_deep_research_context(session_id)
    snapshot["deep_research"] = research["snapshot"]
    snapshot_json = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
    snapshot_sha256 = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()
    metadata = {
        "app_session_id": app_session_id,
        "source_snapshot_sha256": snapshot_sha256,
        "user_edit_policy": policy,
        "has_user_edits": has_user_edits,
        "used_user_edits": used_user_edits and has_user_edits,
        "used_deep_research": research["used_deep_research"],
        "deep_research_run_id": research["deep_research_run_id"],
        "deep_research_report_excerpt_status": research["excerpt_status"],
        "example_slugs": [example.get("slug") for example in examples],
    }
    return ComplianceExportContext(
        snapshot=snapshot,
        snapshot_json=snapshot_json,
        snapshot_sha256=snapshot_sha256,
        optional_deep_research_part_1_2=research["excerpt"],
        deep_research_run_id=research["deep_research_run_id"],
        deep_research_excerpt_status=research["excerpt_status"],
        used_deep_research=research["used_deep_research"],
        has_user_edits=has_user_edits,
        used_user_edits=used_user_edits and has_user_edits,
        examples=examples,
        metadata=metadata,
    )


def _serialize_prompt_example(example: dict[str, Any]) -> dict[str, Any]:
    body_md = str(example.get("body_md") or "")
    return {
        "slug": example.get("slug"),
        "title": example.get("title"),
        "body_sha256": hashlib.sha256(body_md.encode("utf-8")).hexdigest(),
        "source_path": example.get("source_path"),
    }


def _build_addressee_payload(
    session_id: int,
    norm_addressee: str,
    policy: UserEditPolicy,
) -> tuple[dict[str, Any], bool]:
    regulations = db.list_regulations_for_session_and_addressee(session_id, norm_addressee)
    processes = db.list_processes_for_session_and_addressee(session_id, norm_addressee)
    case_groups = db.list_case_groups_for_session_and_addressee(session_id, norm_addressee)
    steps = db.list_process_steps_for_session_and_addressee(session_id, norm_addressee)
    totals = db.get_session_total_costs_by_addressee(session_id, norm_addressee)
    pay_rates = db.get_session_pay_rates_for_addressee(session_id, norm_addressee)

    groups_by_process: dict[int, list[dict[str, Any]]] = {}
    has_user_edits = False
    serialized_pay_rates, pay_rates_have_edits = _serialize_pay_rates(
        pay_rates,
        policy,
    )
    has_user_edits = has_user_edits or pay_rates_have_edits
    for group in case_groups:
        serialized, group_has_edits = _serialize_case_group(group, policy)
        has_user_edits = has_user_edits or group_has_edits
        groups_by_process.setdefault(int(group["process_id"]), []).append(serialized)

    steps_by_group: dict[int, list[dict[str, Any]]] = {}
    for step in steps:
        serialized, step_has_edits = _serialize_process_step(step, policy)
        has_user_edits = has_user_edits or step_has_edits
        steps_by_group.setdefault(int(step["case_group_id"]), []).append(serialized)

    for process_groups in groups_by_process.values():
        for group in process_groups:
            group["taetigkeiten"] = steps_by_group.get(int(group["fallgruppen_id"]), [])

    return {
        "normadressat": norm_addressee,
        "lohnsaetze": serialized_pay_rates,
        "vorgaben": [_serialize_regulation(row) for row in regulations],
        "prozesse": [
            {
                "prozess_id": int(process["process_id"]),
                "prozess_bezeichnung": process.get("process"),
                "prozess_beschreibung": process.get("description"),
                "aenderungsstatus": process.get("change_status"),
                "kosten": process.get("cost"),
                "fallgruppen": groups_by_process.get(int(process["process_id"]), []),
            }
            for process in processes
        ],
        "summen": totals or {},
    }, has_user_edits


def _serialize_pay_rates(
    pay_rates: dict[str, Any] | None,
    policy: UserEditPolicy,
) -> tuple[dict[str, Any], bool]:
    if not pay_rates:
        return {}, False
    defaults = pay_rates.get("defaults") or {}
    edited = pay_rates.get("edited") or {}
    active = pay_rates.get("active") or {}
    serialized = {
        "normadressat": pay_rates.get("norm_addressee"),
        "editable": bool(pay_rates.get("editable")),
        "verwaltungsebene": pay_rates.get("administration_level"),
        "werte": {},
    }
    has_edits = any(edited.get(key) is not None for key in _PAY_RATE_KEYS)
    for key in _PAY_RATE_KEYS:
        edited_value = edited.get(key)
        use_edit = policy == USER_EDIT_USE and edited_value is not None
        serialized["werte"][key] = {
            "wert": edited_value if use_edit else defaults.get(key),
            "originalwert": defaults.get(key) if use_edit else None,
            "active_session_value": active.get(key),
            "edited_value_available": edited_value is not None,
            "value_source": "user_edited" if use_edit else "generated",
        }
    return serialized, has_edits


def _serialize_regulation(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "vorgaben_id": int(row["regulation_id"]),
        "normzitat": row.get("legal_citation"),
        "beschreibung": row.get("description"),
        "aenderungsstatus": row.get("change_status"),
        "normadressaten": [
            addressee
            for addressee, applies in (
                ("administration", row.get("applies_to_administration")),
                ("business", row.get("applies_to_business")),
                ("citizens", row.get("applies_to_citizens")),
            )
            if applies
        ],
        "ist_informationspflicht_wirtschaft": bool(
            row.get("is_business_information_obligation")
        ),
    }


def _serialize_case_group(
    group: dict[str, Any],
    policy: UserEditPolicy,
) -> tuple[dict[str, Any], bool]:
    evidence = _parse_json_object(group.get("case_metric_research_json"))
    serialized = {
        "fallgruppen_id": int(group["case_group_id"]),
        "fallgruppe_bezeichnung": group.get("case_group"),
        "fallgruppe_beschreibung": group.get("description"),
        "aenderungsstatus": group.get("change_status"),
        "kosten": group.get("cost"),
        "kennzahlen": {},
        "taetigkeiten": [],
    }
    has_edits = any(group.get(f"{key}_edited") is not None for key in _CASE_METRIC_KEYS)
    for key in _CASE_METRIC_KEYS:
        serialized["kennzahlen"][key] = _metric_value(
            key=key,
            base_value=group.get(key),
            edited_value=group.get(f"{key}_edited"),
            policy=policy,
            evidence=evidence,
        )
    _recompute_case_totals(serialized["kennzahlen"], "current")
    _recompute_case_totals(serialized["kennzahlen"], "proposed")
    return serialized, has_edits


def _recompute_case_totals(metrics: dict[str, dict[str, Any]], suffix: str) -> None:
    addressees_key = f"addressees_{suffix}"
    frequency_key = f"annual_frequency_{suffix}"
    cases_key = f"cases_{suffix}"
    addressees = metrics.get(addressees_key, {}).get("wert")
    frequency = metrics.get(frequency_key, {}).get("wert")
    if addressees is None or frequency is None:
        return
    try:
        computed = float(addressees) * float(frequency)
    except (TypeError, ValueError):
        return
    cases_metric = metrics.get(cases_key)
    if not cases_metric:
        return
    cases_metric["wert"] = computed
    if (
        metrics[addressees_key].get("value_source") == "user_edited"
        or metrics[frequency_key].get("value_source") == "user_edited"
    ):
        cases_metric["value_source"] = "derived_from_user_edited"
        cases_metric["erklaerung"] = "überschrieben durch Anwender"
        cases_metric["confidence"] = None


def _metric_value(
    *,
    key: str,
    base_value: Any,
    edited_value: Any,
    policy: UserEditPolicy,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    use_edit = policy == USER_EDIT_USE and edited_value is not None
    evidence_key = _CASE_EVIDENCE_KEYS.get(key)
    confidence = None
    explanation = None
    if evidence_key:
        confidence_map = evidence.get("confidence")
        explanation_map = evidence.get("erklaerungen")
        if isinstance(confidence_map, dict):
            confidence = confidence_map.get(evidence_key)
        if isinstance(explanation_map, dict):
            explanation = explanation_map.get(evidence_key)
    if use_edit:
        return {
            "wert": edited_value,
            "originalwert": base_value,
            "value_source": "user_edited",
            "erklaerung": "überschrieben durch Anwender",
            "confidence": None,
        }
    return {
        "wert": base_value,
        "edited_value_available": edited_value is not None,
        "value_source": "generated",
        "erklaerung": explanation,
        "confidence": confidence,
    }


def _serialize_process_step(
    step: dict[str, Any],
    policy: UserEditPolicy,
) -> tuple[dict[str, Any], bool]:
    has_edits = any(step.get(f"{key}_edited") is not None for key in _STEP_EDITABLE_KEYS)
    metrics: dict[str, Any] = {}
    for key in _STEP_EDITABLE_KEYS:
        edited_value = step.get(f"{key}_edited")
        use_edit = policy == USER_EDIT_USE and edited_value is not None
        metrics[key] = {
            "wert": edited_value if use_edit else step.get(key),
            "originalwert": step.get(key) if use_edit else None,
            "edited_value_available": edited_value is not None,
            "value_source": "user_edited" if use_edit else "generated",
        }
    return {
        "taetigkeiten_id": int(step["step_id"]),
        "taetigkeit": step.get("step"),
        "beschreibung": step.get("description"),
        "aenderungsstatus": step.get("change_status"),
        "vorgaben_ids": step.get("regulation_ids") or [],
        "execution_per_case": step.get("execution_per_case"),
        "stundenloehne": {
            f"{slot}_{suffix}": step.get(f"hourly_rate_{slot}_{suffix}")
            for suffix in ("current", "proposed")
            for slot in ("a", "b", "c", "d")
        },
        "kennzahlen": metrics,
        "kosten": {
            "gueltig": step.get("cost_current"),
            "vorschlag": step.get("cost_proposed"),
        },
    }, has_edits


def _build_deep_research_context(session_id: int) -> dict[str, Any]:
    run = db.get_latest_deep_research_run(session_id, CASE_GROUP_RESEARCH_PURPOSE)
    if not run or str(run.get("status") or "") not in {"completed", "parsed"}:
        return {
            "used_deep_research": False,
            "deep_research_run_id": None,
            "excerpt_status": "not_available",
            "excerpt": "Kein Deep-Research-Bericht vorhanden.",
            "snapshot": {"available": False},
        }
    result_json = _parse_json_object(run.get("result_json"))
    report_md = str(run.get("report_md") or "")
    excerpt, excerpt_status = extract_deep_research_part_1_2(report_md)
    if excerpt_status != "extracted":
        excerpt = (
            "[Deep-Research-Bericht vorhanden, aber Teil 1 und Teil 2 konnten "
            "nicht zuverlässig extrahiert werden. Verwenden Sie ausschließlich "
            "deep_research_runs.result_json und die konsolidierte Session-JSON.]"
        )
    research_run_id = int(run["research_run_id"])
    return {
        "used_deep_research": True,
        "deep_research_run_id": research_run_id,
        "excerpt_status": excerpt_status,
        "excerpt": excerpt,
        "snapshot": {
            "available": True,
            "research_run_id": research_run_id,
            "status": run.get("status"),
            "result_json": result_json,
            "report_excerpt_status": excerpt_status,
        },
    }


def extract_deep_research_part_1_2(report_md: str) -> tuple[str, str]:
    text = report_md.strip()
    if not text:
        return "", "fallback"
    part1 = re.search(r"(?im)^#{0,6}\s*Teil\s+1\b.*$", text)
    part2 = re.search(r"(?im)^#{0,6}\s*Teil\s+2\b.*$", text)
    if not part1 or not part2:
        return "", "fallback"
    stop_candidates = [
        match.start()
        for pattern in (
            r"(?im)^#{0,6}\s*Teil\s+3\b.*$",
            r"(?im)^```json\s*$",
        )
        if (match := re.search(pattern, text[part2.start() :]))
    ]
    end = len(text)
    if stop_candidates:
        end = part2.start() + min(stop_candidates)
    return text[part1.start() : end].strip(), "extracted"


def _parse_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}
