from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from fastapi import HTTPException

from backend.core import cost_aggregation
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
_STEP_TIME_KEYS = tuple(
    key for key in _STEP_EDITABLE_KEYS if not key.startswith("expenses")
)
_PAY_RATE_KEYS = ("a", "b", "c", "d")
# Last-resort guard when neither Teil/Part headings nor a JSON boundary are usable.
DEEP_RESEARCH_FULL_REPORT_FALLBACK_MAX_CHARS = 50_000
# Guard for reports with a recognizable JSON boundary; normal reports should fit below this.
DEEP_RESEARCH_REPORT_BEFORE_JSON_FALLBACK_MAX_CHARS = 75_000


@dataclass(frozen=True)
class ComplianceExportContext:
    snapshot: dict[str, Any]
    snapshot_json: str
    snapshot_sha256: str
    optional_deep_research_report_text: str
    deep_research_run_id: int | None
    deep_research_excerpt_status: str
    deep_research_report_text_included: bool
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
        "deep_research_report_text_included": research["report_text_included"],
        "example_slugs": [example.get("slug") for example in examples],
    }
    return ComplianceExportContext(
        snapshot=snapshot,
        snapshot_json=snapshot_json,
        snapshot_sha256=snapshot_sha256,
        optional_deep_research_report_text=research["excerpt"],
        deep_research_run_id=research["deep_research_run_id"],
        deep_research_excerpt_status=research["excerpt_status"],
        deep_research_report_text_included=research["report_text_included"],
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

    # One cost source for the export and the app: the cost engine under the same
    # policy (use vs reject), so the totals and every per-step/-group/-process cost
    # cannot drift from what the user sees. Missing inputs (engine 404/422) degrade
    # to "no cost data" rather than crashing the export.
    apply_edits = policy == USER_EDIT_USE
    try:
        cost = cost_aggregation.aggregate_addressee_costs(
            session_id, norm_addressee, apply_user_edits=apply_edits
        )
        if cost.get("skipped") is not None:
            cost = None
    except HTTPException:
        cost = None
    step_costs_current = (cost or {}).get("step_costs_current") or {}
    step_costs_proposed = (cost or {}).get("step_costs_proposed") or {}
    case_group_costs = (cost or {}).get("case_group_costs") or {}
    process_costs = (cost or {}).get("process_costs") or {}
    totals = (
        {
            "session_id": session_id,
            "norm_addressee": norm_addressee,
            "total_cost": cost["total_cost"],
            "bureaucracy_cost": cost["bureaucracy_cost"],
            "verwaltung_bundesebene": cost["verwaltung_bundesebene"],
            "verwaltung_landesebene": cost["verwaltung_landesebene"],
            "total_time_minutes": cost["total_time_minutes"],
            "total_expenses": cost["total_expenses"],
        }
        if cost
        else {}
    )

    wage_overrides = db.get_session_wage_rate_overrides(session_id, norm_addressee)
    personnel_by_step: dict[int, list[dict[str, Any]]] = {}
    for row in db.list_process_step_personnel_effort(session_id, norm_addressee):
        personnel_by_step.setdefault(int(row["step_id"]), []).append(row)

    groups_by_process: dict[int, list[dict[str, Any]]] = {}
    has_user_edits = False
    serialized_pay_rates, pay_rates_have_edits = _serialize_pay_rates(
        session_id, norm_addressee, policy
    )
    has_user_edits = has_user_edits or pay_rates_have_edits
    for group in case_groups:
        serialized, group_has_edits = _serialize_case_group(
            group, policy, case_group_costs.get(int(group["case_group_id"]))
        )
        has_user_edits = has_user_edits or group_has_edits
        groups_by_process.setdefault(int(group["process_id"]), []).append(serialized)

    steps_by_group: dict[int, list[dict[str, Any]]] = {}
    for step in steps:
        step_id = int(step["step_id"])
        serialized, step_has_edits = _serialize_process_step(
            step,
            policy,
            personnel_rows=personnel_by_step.get(step_id, []),
            wage_overrides=wage_overrides,
            step_cost_current=step_costs_current.get(step_id),
            step_cost_proposed=step_costs_proposed.get(step_id),
        )
        has_user_edits = has_user_edits or step_has_edits
        steps_by_group.setdefault(int(step["case_group_id"]), []).append(serialized)

    for process_groups in groups_by_process.values():
        for group in process_groups:
            group["taetigkeiten"] = steps_by_group.get(int(group["fallgruppen_id"]), [])

    serialized_vorgaben = [_serialize_regulation(row) for row in regulations]
    vorgaben_by_process: dict[int, list[dict[str, Any]]] = {}
    for row, serialized in zip(regulations, serialized_vorgaben):
        process_id = row.get("process_id")
        if process_id is None:
            continue
        vorgaben_by_process.setdefault(int(process_id), []).append(serialized)

    return {
        "normadressat": norm_addressee,
        "lohnsaetze": serialized_pay_rates,
        "vorgaben": serialized_vorgaben,
        "prozesse": [
            {
                "prozess_id": int(process["process_id"]),
                "prozess_bezeichnung": process.get("process"),
                "prozess_beschreibung": process.get("description"),
                "aenderungsstatus": process.get("change_status"),
                "vorgaben": vorgaben_by_process.get(int(process["process_id"]), []),
                "kosten": process_costs.get(
                    int(process["process_id"]), process.get("cost")
                ),
                "fallgruppen": groups_by_process.get(int(process["process_id"]), []),
            }
            for process in processes
        ],
        "summen": totals,
    }, has_user_edits


def _value_cell(base: Any, edited: Any, policy: UserEditPolicy) -> dict[str, Any]:
    """One base/edited value under the user-edit policy (shared snapshot shape)."""
    use_edit = policy == USER_EDIT_USE and edited is not None
    return {
        "wert": edited if use_edit else base,
        "originalwert": base if use_edit else None,
        "edited_value_available": edited is not None,
        "value_source": "user_edited" if use_edit else "generated",
    }


def _serialize_pay_rates(
    session_id: int,
    norm_addressee: str,
    policy: UserEditPolicy,
) -> tuple[dict[str, Any], bool]:
    """Wage rates from the row-based store (session_wage_rate_overrides), mapped
    onto the a/b/c/d slot shape the export prompt expects.

    Reads the same override store the cost engine uses, so the displayed rate
    matches the rate the cost was computed with. ``hourly_rate_edited`` counts as a
    user edit. One source per session is the regular case; with mixed sources the
    first source per qualification is shown (the cost stays exact via the engine).
    """
    resolved = db.normalize_norm_addressee(norm_addressee)
    slot_by_qualification = db.PERSONNEL_SLOT_BY_QUALIFICATION.get(resolved, {})
    wage_rows = db.list_session_wage_rate_rows(session_id, resolved)
    if not wage_rows:
        # No personnel rows (legacy / citizens): fall back to the legacy slot
        # pay-rate store so old sessions still show their wage rates.
        return _serialize_pay_rates_slots(session_id, norm_addressee, policy)
    has_edits = any(row.get("hourly_rate_edited") is not None for row in wage_rows)
    werte: dict[str, Any] = {}
    sources: list[str] = []
    for row in wage_rows:
        slot = slot_by_qualification.get(row["qualification"])
        if slot is None or slot in werte:
            continue
        sources.append(row["wage_source_value"])
        edited = row.get("hourly_rate_edited")
        model = row.get("model_hourly_rate")
        use_edit = policy == USER_EDIT_USE and edited is not None
        werte[slot] = {
            "wert": edited if use_edit else model,
            "originalwert": model if use_edit else None,
            "active_session_value": edited if edited is not None else model,
            "edited_value_available": edited is not None,
            "value_source": "user_edited" if use_edit else "generated",
            "lohnquelle": row["wage_source_value"],
        }
    primary_source = max(set(sources), key=sources.count) if sources else None
    return {
        "normadressat": norm_addressee,
        "editable": True,
        "verwaltungsebene": primary_source,
        "werte": werte,
    }, has_edits


def _serialize_pay_rates_slots(
    session_id: int,
    norm_addressee: str,
    policy: UserEditPolicy,
) -> tuple[dict[str, Any], bool]:
    """Legacy slot-based pay rates for sessions without personnel rows."""
    pay_rates = db.get_session_pay_rates_for_addressee(session_id, norm_addressee)
    if not pay_rates:
        return {}, False
    defaults = pay_rates.get("defaults") or {}
    edited = pay_rates.get("edited") or {}
    active = pay_rates.get("active") or {}
    has_edits = any(edited.get(key) is not None for key in _PAY_RATE_KEYS)
    werte: dict[str, Any] = {}
    for key in _PAY_RATE_KEYS:
        edited_value = edited.get(key)
        use_edit = policy == USER_EDIT_USE and edited_value is not None
        werte[key] = {
            "wert": edited_value if use_edit else defaults.get(key),
            "originalwert": defaults.get(key) if use_edit else None,
            "active_session_value": active.get(key),
            "edited_value_available": edited_value is not None,
            "value_source": "user_edited" if use_edit else "generated",
        }
    return {
        "normadressat": pay_rates.get("norm_addressee"),
        "editable": bool(pay_rates.get("editable")),
        "verwaltungsebene": pay_rates.get("administration_level"),
        "werte": werte,
    }, has_edits


def _row_based_step_metrics(
    personnel_rows: list[dict[str, Any]],
    wage_overrides: dict,
    policy: UserEditPolicy,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Per-slot hourly rates and time cells derived from the personnel rows.

    Mirrors the cost engine under the same policy: time is ``edited ?? base``,
    rate is ``override ?? model``. Rows of one qualification/period are summed into
    their slot; the dominant (max-base-time) row supplies the displayed rate.
    """
    aggregated: dict[tuple[str, str], dict[str, Any]] = {}
    has_edits = False
    for row in personnel_rows:
        resolved = db.normalize_norm_addressee(row["norm_addressee"])
        slot = db.PERSONNEL_SLOT_BY_QUALIFICATION.get(resolved, {}).get(
            row["qualification"]
        )
        if slot is None:
            continue
        suffix = "current" if row["period"] == "current" else "proposed"
        base_time = row.get("time_required_in_min") or 0.0
        edited_time = row.get("time_required_in_min_edited")
        override = wage_overrides.get(
            (row["wage_source_kind"], row["wage_source_value"], row["qualification"])
        )
        if edited_time is not None or override is not None:
            has_edits = True
        cell = aggregated.setdefault(
            (slot, suffix),
            {
                "base": 0.0,
                "effective": 0.0,
                "any_edit": False,
                "rate_model": row.get("model_hourly_rate"),
                "rate_override": override,
                "dominant": -1.0,
            },
        )
        cell["base"] += base_time
        cell["effective"] += edited_time if edited_time is not None else base_time
        if edited_time is not None:
            cell["any_edit"] = True
        if base_time > cell["dominant"]:
            cell["dominant"] = base_time
            cell["rate_model"] = row.get("model_hourly_rate")
            cell["rate_override"] = override

    stundenloehne: dict[str, Any] = {}
    time_cells: dict[str, Any] = {}
    for (slot, suffix), cell in aggregated.items():
        use_time_edit = policy == USER_EDIT_USE and cell["any_edit"]
        time_cells[f"time_required_in_min_{slot}_{suffix}"] = {
            "wert": cell["effective"] if use_time_edit else cell["base"],
            "originalwert": cell["base"] if use_time_edit else None,
            "edited_value_available": cell["any_edit"],
            "value_source": "user_edited" if use_time_edit else "generated",
        }
        use_rate_edit = policy == USER_EDIT_USE and cell["rate_override"] is not None
        stundenloehne[f"{slot}_{suffix}"] = (
            cell["rate_override"] if use_rate_edit else cell["rate_model"]
        )
    return stundenloehne, time_cells, has_edits


def _slot_based_step_metrics(
    step: dict[str, Any],
    policy: UserEditPolicy,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Legacy slot path for steps without personnel rows (citizens / old sessions)."""
    stundenloehne = {
        f"{slot}_{suffix}": step.get(f"hourly_rate_{slot}_{suffix}")
        for suffix in ("current", "proposed")
        for slot in ("a", "b", "c", "d")
    }
    time_cells: dict[str, Any] = {}
    has_edits = False
    for key in _STEP_TIME_KEYS:
        edited = step.get(f"{key}_edited")
        if edited is not None:
            has_edits = True
        time_cells[key] = _value_cell(step.get(key), edited, policy)
    return stundenloehne, time_cells, has_edits


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
    case_cost: float | None = None,
) -> tuple[dict[str, Any], bool]:
    evidence = _parse_json_object(group.get("case_metric_research_json"))
    serialized = {
        "fallgruppen_id": int(group["case_group_id"]),
        "fallgruppe_bezeichnung": group.get("case_group"),
        "fallgruppe_beschreibung": group.get("description"),
        "aenderungsstatus": group.get("change_status"),
        "kosten": case_cost if case_cost is not None else group.get("cost"),
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
    *,
    personnel_rows: list[dict[str, Any]],
    wage_overrides: dict,
    step_cost_current: float | None,
    step_cost_proposed: float | None,
) -> tuple[dict[str, Any], bool]:
    """Serialize one step. Rates and times come from the personnel rows (row
    model) when present, else the legacy slots; the cost comes from the cost
    engine under the same policy, so rate x time and the cost never disagree."""
    if personnel_rows:
        stundenloehne, time_cells, has_edits = _row_based_step_metrics(
            personnel_rows, wage_overrides, policy
        )
    else:
        stundenloehne, time_cells, has_edits = _slot_based_step_metrics(step, policy)
    metrics: dict[str, Any] = dict(time_cells)
    for key in ("expenses_current", "expenses_proposed"):
        edited = step.get(f"{key}_edited")
        if edited is not None:
            has_edits = True
        metrics[key] = _value_cell(step.get(key), edited, policy)
    return {
        "taetigkeiten_id": int(step["step_id"]),
        "taetigkeit": step.get("step"),
        "beschreibung": step.get("description"),
        "aenderungsstatus": step.get("change_status"),
        "vorgaben_ids": step.get("regulation_ids") or [],
        "execution_per_case": step.get("execution_per_case"),
        "stundenloehne": stundenloehne,
        "kennzahlen": metrics,
        "kosten": {
            "gueltig": step_cost_current,
            "vorschlag": step_cost_proposed,
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
            "report_text_included": False,
            "snapshot": {"available": False},
        }
    result_json = _parse_json_object(run.get("result_json"))
    report_md = str(run.get("report_md") or "")
    excerpt, excerpt_status = extract_deep_research_report_text_for_export(report_md)
    if excerpt_status == "fallback":
        excerpt, excerpt_status = _build_full_report_fallback(report_md)
    report_text_included = excerpt_status not in {"fallback", "not_available"}
    research_run_id = int(run["research_run_id"])
    return {
        "used_deep_research": True,
        "deep_research_run_id": research_run_id,
        "excerpt_status": excerpt_status,
        "excerpt": excerpt,
        "report_text_included": report_text_included,
        "snapshot": {
            "available": True,
            "research_run_id": research_run_id,
            "status": run.get("status"),
            "result_json": result_json,
            "report_excerpt_status": excerpt_status,
            "report_text_included": report_text_included,
        },
    }


def extract_deep_research_report_text_for_export(report_md: str) -> tuple[str, str]:
    text = report_md.strip()
    if not text:
        return "", "fallback"
    part1 = _find_deep_research_part_heading(text, 1)
    part2 = _find_deep_research_part_heading(text, 2)
    if part1:
        start = part1.start()
        end = _first_report_boundary_after(
            text,
            start,
            part_numbers=(2, 3),
        )
        excerpt = text[start:end].strip()
        return (excerpt, "rich_report_extracted") if excerpt else ("", "fallback")
    if part2:
        start = 0
        end = part2.start()
        excerpt = text[start:end].strip()
        return (
            (excerpt, "inferred_rich_report_from_start")
            if excerpt
            else ("", "fallback")
        )
    return "", "fallback"


def extract_deep_research_part_1_2(report_md: str) -> tuple[str, str]:
    return extract_deep_research_report_text_for_export(report_md)


def _first_report_boundary_after(
    report_md: str,
    start: int,
    *,
    part_numbers: tuple[int, ...],
) -> int:
    patterns = [
        rf"(?im)^#{{0,6}}\s*(?:Teil|Part)\s+{part_number}\b.*$"
        for part_number in part_numbers
    ]
    patterns.append(r"(?im)^```json\s*$")
    candidates = [
        start + match.start()
        for pattern in patterns
        if (match := re.search(pattern, report_md[start:]))
    ]
    return min(candidates) if candidates else len(report_md)


def _find_deep_research_part_heading(
    report_md: str,
    part_number: int,
) -> re.Match[str] | None:
    return re.search(
        rf"(?im)^#{{0,6}}\s*(?:Teil|Part)\s+{part_number}\b.*$",
        report_md,
    )


def _build_full_report_fallback(report_md: str) -> tuple[str, str]:
    text = report_md.strip()
    if not text:
        return "Kein Deep-Research-Bericht vorhanden.", "fallback"
    json_block = re.search(r"(?im)^```json\s*$", text)
    if json_block:
        prose = text[: json_block.start()].strip()
        if prose:
            status = "full_report_fallback_before_json"
            if len(prose) > DEEP_RESEARCH_REPORT_BEFORE_JSON_FALLBACK_MAX_CHARS:
                prose = prose[
                    :DEEP_RESEARCH_REPORT_BEFORE_JSON_FALLBACK_MAX_CHARS
                ].rstrip()
                status = "full_report_fallback_before_json_truncated"
            note = (
                "[Hinweis: Der gegliederte Berichtsteil konnte aus dem "
                "Deep-Research-Bericht nicht zuverlaessig extrahiert werden. "
                "Der folgende Berichtsteil vor dem JSON-Block darf nur fuer Kontext, "
                "Herleitung, Plausibilisierung und Quellenbeschreibung verwendet "
                "werden. "
                "Fuer Zahlen und Berechnungen ist die konsolidierte "
                "Session-JSON massgeblich.]\n\n"
            )
            return note + prose, status
    status = "full_report_fallback"
    if len(text) > DEEP_RESEARCH_FULL_REPORT_FALLBACK_MAX_CHARS:
        text = text[:DEEP_RESEARCH_FULL_REPORT_FALLBACK_MAX_CHARS].rstrip()
        status = "full_report_fallback_truncated"
    note = (
        "[Hinweis: Der gegliederte Berichtsteil konnte aus dem "
        "Deep-Research-Bericht nicht zuverlaessig extrahiert werden. "
        "Der folgende vollstaendige Bericht "
        "darf nur fuer Kontext, Herleitung, Plausibilisierung und "
        "Quellenbeschreibung verwendet werden. Fuer Zahlen und Berechnungen "
        "ist die konsolidierte Session-JSON massgeblich.]\n\n"
    )
    return note + text, status


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
