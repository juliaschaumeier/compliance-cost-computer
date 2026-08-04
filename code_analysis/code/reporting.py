from __future__ import annotations

import datetime as dt
import html
import math
from pathlib import Path
import re
from typing import Any, Iterable

from common import *
from entities import *
from issues import *

DEFAULT_FEATURE_MARKERS = [
    {
        "date": "2026-04-24",
        "week": "2026-W17",
        "label": "Multiple norm addressees",
        "area": "Workflow / domain model",
        "affects": ["issue_02_unnecessary_addressee_steps", "issue_05_structure_consistency", "issue_06_cost_variance"],
        "git_sha": "326fcf3",
        "notes": "The app moved beyond Verwaltung-only analysis to administration/business/citizens, changing prompt count and addressee-specific persistence.",
    },
    {
        "date": "2026-05-13",
        "week": "2026-W20",
        "label": "Addressee-specific prompt rules",
        "area": "Prompt semantics",
        "affects": ["issue_02_unnecessary_addressee_steps", "issue_05_structure_consistency"],
        "git_sha": "2b14ee1/002e296",
        "notes": "Norm-addressee prompt rendering and separate addressee rules were cleaned up, likely changing which entities are produced per addressee.",
    },
    {
        "date": "2026-05-20",
        "week": "2026-W21",
        "label": "Deep Research for case metrics",
        "area": "Case counts",
        "affects": ["issue_06_cost_variance", "issue_07_case_count_driven_variance"],
        "git_sha": "380fc10",
        "notes": "Opt-in Deep Research for case-group metrics can shift case-count assumptions and therefore final costs.",
    },
    {
        "date": "2026-06-13",
        "week": "2026-W24",
        "label": "Row-based effort model",
        "area": "Effort/cost persistence",
        "affects": ["issue_04_change_status_inconsistency", "issue_06_cost_variance", "issue_08_bureaucracy_cost"],
        "git_sha": "bb8d031/638253c",
        "notes": "Personnel effort moved into child rows and cost computation from those rows, changing persisted cost/value surfaces.",
    },
    {
        "date": "2026-06-29",
        "week": "2026-W27",
        "label": "Atomic addressee workflow",
        "area": "Run-all / step execution",
        "affects": ["retry_pressure", "issue_02_unnecessary_addressee_steps", "issue_05_structure_consistency"],
        "git_sha": "c25fced",
        "notes": "Workflow step runs became atomic across administration/business/citizens; this can change retries, partial-state behavior, and addressee-specific outputs.",
    },
    {
        "date": "2026-06-29",
        "week": "2026-W27",
        "label": "Empty process no-op accepted",
        "area": "Parser / workflow semantics",
        "affects": ["issue_02_unnecessary_addressee_steps", "issue_03_json_truncation"],
        "git_sha": "0c30258",
        "notes": "Empty process results can be valid no-op outcomes instead of automatic failures.",
    },
    {
        "date": "2026-07-02",
        "week": "2026-W27",
        "label": "JSON object response mode",
        "area": "LLM structured output",
        "affects": ["issue_03_json_truncation", "retry_pressure"],
        "git_sha": "024a632",
        "notes": "Introduced structured-output handling using provider response_format json_object where supported.",
    },
    {
        "date": "2026-07-02",
        "week": "2026-W27",
        "label": "Required prozesse envelope",
        "area": "Parser/schema gate",
        "affects": ["issue_03_json_truncation", "process_step_shape"],
        "git_sha": "3321a69",
        "notes": "Parsers consistently require the expected top-level envelope such as prozesse.",
    },
    {
        "date": "2026-07-02",
        "week": "2026-W27",
        "label": "Hard normadressat/step-5 guards",
        "area": "Parser / integrity checks",
        "affects": ["issue_03_json_truncation", "retry_pressure", "process_step_shape"],
        "git_sha": "c26ce5f",
        "notes": "Normadressat mismatches and incomplete step-5 output became hard validation failures.",
    },
    {
        "date": "2026-07-03",
        "week": "2026-W27",
        "label": "Recurring-only effort",
        "area": "Prompt semantics",
        "affects": ["issue_05_structure_consistency", "issue_06_cost_variance", "issue_07_case_count_driven_variance"],
        "git_sha": "cdc716d",
        "notes": "Prompt rules shifted toward yearly recurring effort only, reducing one-off implementation/onboarding effort.",
    },
    {
        "date": "2026-07-07",
        "week": "2026-W28",
        "label": "Business IP flag cleanup/display",
        "area": "Information obligations",
        "affects": ["issue_08_bureaucracy_cost"],
        "git_sha": "958544d/fc64fc9",
        "notes": "Business information-obligation handling and display were tightened; this can shift bureaucracy-cost split diagnostics.",
    },
    {
        "date": "2026-07-09",
        "week": "2026-W28",
        "label": "Flat step-5 skeleton",
        "area": "Prompt/output contract",
        "affects": ["issue_01_duplicate_fallgruppen", "issue_03_json_truncation", "process_step_shape"],
        "git_sha": "361c9ca",
        "notes": "Process-step output changed to a flat prefilled Fallgruppen skeleton to prevent duplicate Fallgruppe chains.",
    },
    {
        "date": "2026-07-10",
        "week": "2026-W28",
        "label": "Atomic retry on 422",
        "area": "Run-all retry behavior",
        "affects": ["retry_pressure", "issue_03_json_truncation"],
        "git_sha": "158da04",
        "notes": "Run-all began retrying atomic model-output validation errors once.",
    },
    {
        "date": "2026-07-11",
        "week": "2026-W28",
        "label": "Model-dependent retry limit",
        "area": "Run-all retry behavior",
        "affects": ["retry_pressure"],
        "git_sha": "df7f5c5",
        "notes": "Atomic-step retry limits became model-dependent, which can create visible retry-pressure shifts.",
    },
    {
        "date": "2026-07-11",
        "week": "2026-W28",
        "label": "Prompt JSON schema for all structured prompts",
        "area": "Prompt contract",
        "affects": ["issue_03_json_truncation", "process_step_shape", "retry_pressure"],
        "git_sha": "2b650ca",
        "notes": "Prompt-level JSON schema text expanded across structured prompts.",
    },
    {
        "date": "2026-07-16",
        "week": "2026-W29",
        "label": "Prompt JSON schema for step 6",
        "area": "Prompt contract",
        "affects": ["issue_03_json_truncation", "retry_pressure", "issue_06_cost_variance"],
        "git_sha": "10802a6",
        "notes": "Prompt-level JSON schema text introduced for cases_calculation and effort_calculation structured outputs.",
    },
    {
        "date": "2026-07-16",
        "week": "2026-W29",
        "label": "Flat step-6 skeleton",
        "area": "Prompt/output contract",
        "affects": ["issue_01_duplicate_fallgruppen", "issue_03_json_truncation", "issue_06_cost_variance", "issue_07_case_count_driven_variance"],
        "git_sha": "82a48de",
        "notes": "Cases and effort output changed to flat prefilled skeletons to prevent duplicate Fallgruppe/step chains.",
    },
    {
        "date": "2026-07-16",
        "week": "2026-W29",
        "label": "Prompt JSON schema for remaining prompts",
        "area": "Prompt contract",
        "affects": ["issue_03_json_truncation", "process_step_shape", "retry_pressure"],
        "git_sha": "05f23ba",
        "notes": "Prompt-level JSON schema text completed for the remaining structured prompts.",
    },
    {
        "date": "2026-07-17",
        "week": "2026-W29",
        "label": "Response-format observability",
        "area": "LLM monitoring",
        "affects": ["issue_03_json_truncation", "retry_pressure"],
        "git_sha": "9bfe4d4",
        "notes": "Monitor UI started surfacing response_format use/fallback metadata, making provider/object/schema shifts easier to audit.",
    },
    {
        "date": "2026-07-20",
        "week": "2026-W30",
        "label": "Preserve valid step-6 pairs",
        "area": "Step 6 retry/persistence",
        "affects": ["retry_pressure", "issue_06_cost_variance", "issue_07_case_count_driven_variance"],
        "git_sha": "a997852",
        "notes": "Valid paired step-6 answers are preserved across retries, reducing unnecessary recomputation after one half of the pair succeeds.",
    },
]

ANALYZERS = (
    analyze_issue_01,
    analyze_issue_02,
    analyze_issue_03,
    analyze_issue_04,
    analyze_issue_05,
    analyze_issue_06,
    analyze_issue_07,
    analyze_issue_08,
    analyze_issue_09,
)

def analyze(out_dir: Path, config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    data = load_extracted(out_dir, config)
    all_findings: list[dict[str, Any]] = []
    analyze_retry_pressure(data, out_dir)
    for analyzer in ANALYZERS:
        all_findings.extend(analyzer(data, out_dir))
    review_index = write_adjudication_packets(out_dir, data, all_findings)
    findings_dir = out_dir / "findings"
    write_jsonl(findings_dir / "findings.jsonl", all_findings)
    write_csv(findings_dir / "findings.csv", all_findings, [
        "issue_id", "issue_name", "classification", "severity", "session_id",
        "app_session_id", "week", "session_created_at", "law_pair", "model",
        "answer_id", "answer_created_at", "answer_week", "prompt_id",
        "norm_addressee", "evidence_summary", "evidence_hash", "evidence",
    ])
    write_csv(out_dir / "reports" / "review_packet_index.csv", review_index)
    return all_findings

def aggregate(out_dir: Path, config: dict[str, Any] | None = None) -> dict[str, Any]:
    data = load_extracted(out_dir, config)
    findings = read_jsonl(out_dir / "findings" / "findings.jsonl")
    review_index = write_adjudication_packets(out_dir, data, findings)
    findings_by_session: dict[int, list[dict[str, Any]]] = {}
    for row in findings:
        sid = int_or_none(row.get("session_id"))
        if sid is not None and row.get("classification") == "bad":
            findings_by_session.setdefault(sid, []).append(row)
    session_rows = []
    for session in data["sessions"]:
        sid = int(session["session_id"])
        session_findings = findings_by_session.get(sid, [])
        hard_findings = [row for row in session_findings if finding_session_judgement(row) == "hard_failure"]
        diagnostic_findings = [row for row in session_findings if finding_session_judgement(row) != "hard_failure"]
        depth = completion_depth(data, sid)
        if hard_findings:
            label = "bad"
        elif diagnostic_findings:
            label = "diagnostic_only"
        elif has_any_evidence(data, sid):
            label = "good"
        else:
            label = "unknown_or_incomplete"
        issue_flags = {issue_id: any(f["issue_id"] == issue_id for f in session_findings) for issue_id in ISSUES}
        session_rows.append({
            "session_id": sid,
            "app_session_id": session.get("app_session_id"),
            "week": iso_week(session.get("created_at")),
            "created_at": session.get("created_at"),
            "law_pair": law_pair_key(session),
            "model": session.get("llm_model"),
            "completion_depth": depth,
            "quality_label": label,
            "bad_issue_count": len({f["issue_id"] for f in hard_findings}),
            "diagnostic_issue_count": len({f["issue_id"] for f in diagnostic_findings}),
            **issue_flags,
        })
    write_csv(out_dir / "reports" / "session_quality.csv", session_rows)
    weekly = weekly_counts(session_rows)
    write_csv(out_dir / "reports" / "weekly_session_quality.csv", weekly)
    answer_quality = read_csv_dicts(out_dir / "findings" / "issue_03_answer_quality.csv")
    issue_02_wordings = read_csv_dicts(out_dir / "findings" / "issue_02_not_applicable_wordings.csv")
    issue_02_wording_summary_rows = issue_02_wording_summary(issue_02_wordings)
    write_csv(out_dir / "reports" / "issue_02_not_applicable_wording_summary.csv", issue_02_wording_summary_rows)
    weekly_answer = weekly_answer_quality(answer_quality)
    write_csv(out_dir / "reports" / "weekly_answer_quality.csv", weekly_answer)
    weekly_answer_syntax = weekly_answer_syntax_quality(answer_quality)
    write_csv(out_dir / "reports" / "weekly_answer_syntax_quality.csv", weekly_answer_syntax)
    weekly_answer_model = weekly_answer_quality_by_model(answer_quality)
    write_csv(out_dir / "reports" / "weekly_answer_quality_by_model.csv", weekly_answer_model)
    prompt_contract_summary_rows = prompt_contract_summary(answer_quality)
    write_csv(out_dir / "reports" / "prompt_contract_summary.csv", prompt_contract_summary_rows)
    backend_rejection_summary_rows = backend_rejection_summary(answer_quality)
    write_csv(out_dir / "reports" / "backend_rejection_summary.csv", backend_rejection_summary_rows)
    process_step_shape = read_csv_dicts(out_dir / "findings" / "issue_03_process_step_shape.csv")
    weekly_process_step_shape = weekly_process_step_shapes(process_step_shape)
    write_csv(out_dir / "reports" / "weekly_process_step_shape.csv", weekly_process_step_shape)
    weekly_process_step_shape_model = weekly_process_step_shapes_by_model(process_step_shape)
    write_csv(out_dir / "reports" / "weekly_process_step_shape_by_model.csv", weekly_process_step_shape_model)
    step_6_shape = read_csv_dicts(out_dir / "findings" / "issue_03_step_6_shape.csv")
    weekly_step_6_shape = weekly_step_6_shapes_by_prompt(step_6_shape)
    write_csv(out_dir / "reports" / "weekly_step_6_shape.csv", weekly_step_6_shape)
    weekly_step_6_shape_model = weekly_step_6_shapes_by_model(step_6_shape)
    write_csv(out_dir / "reports" / "weekly_step_6_shape_by_model.csv", weekly_step_6_shape_model)
    compliance_export_quality = read_csv_dicts(out_dir / "findings" / "issue_09_compliance_export_quality.csv")
    compliance_export_summary_rows = compliance_export_summary(compliance_export_quality)
    write_csv(out_dir / "reports" / "compliance_export_quality_summary.csv", compliance_export_summary_rows)
    raw_change_status_quality = read_csv_dicts(out_dir / "findings" / "issue_04_raw_change_status_quality.csv")
    weekly_raw_change_status_quality = weekly_raw_change_status_checks(raw_change_status_quality)
    write_csv(out_dir / "reports" / "weekly_raw_change_status_quality.csv", weekly_raw_change_status_quality)
    raw_change_status_summary_rows = raw_change_status_summary(raw_change_status_quality)
    write_csv(out_dir / "reports" / "raw_change_status_quality_summary.csv", raw_change_status_summary_rows)
    change_status_quality = read_csv_dicts(out_dir / "findings" / "issue_04_change_status_quality.csv")
    weekly_change_status_quality = weekly_change_status_checks(change_status_quality)
    write_csv(out_dir / "reports" / "weekly_change_status_quality.csv", weekly_change_status_quality)
    change_status_hierarchy = read_csv_dicts(out_dir / "findings" / "issue_04_change_status_hierarchy.csv")
    weekly_change_status_hierarchy = weekly_change_status_hierarchy_checks(change_status_hierarchy)
    write_csv(out_dir / "reports" / "weekly_change_status_hierarchy.csv", weekly_change_status_hierarchy)
    bureaucracy_cost_quality = read_csv_dicts(out_dir / "findings" / "issue_08_bureaucracy_cost_quality.csv")
    weekly_bureaucracy_cost_quality = weekly_bureaucracy_cost_checks(bureaucracy_cost_quality)
    write_csv(out_dir / "reports" / "weekly_bureaucracy_cost_quality.csv", weekly_bureaucracy_cost_quality)
    structure_pairs = read_csv_dicts(out_dir / "findings" / "issue_05_pairwise_structure_similarity.csv")
    weekly_structure_pairs = weekly_structure_pair_checks(structure_pairs)
    write_csv(out_dir / "reports" / "weekly_structure_pair_checks.csv", weekly_structure_pairs)
    cost_variance_groups = read_csv_dicts(out_dir / "findings" / "issue_06_cost_variance_groups.csv")
    weekly_cost_variance_groups = weekly_cost_variance_checks(cost_variance_groups)
    write_csv(out_dir / "reports" / "weekly_cost_variance_checks.csv", weekly_cost_variance_groups)
    case_count_candidates = read_csv_dicts(out_dir / "findings" / "issue_07_case_count_variance.csv")
    weekly_case_count_candidates = weekly_case_count_checks(case_count_candidates)
    write_csv(out_dir / "reports" / "weekly_case_count_checks.csv", weekly_case_count_candidates)
    retry_pressure = read_csv_dicts(out_dir / "findings" / "retry_pressure.csv")
    weekly_retry = weekly_retry_pressure(retry_pressure)
    write_csv(out_dir / "reports" / "weekly_retry_pressure.csv", weekly_retry)
    weekly_session_retry = weekly_session_retry_pressure(retry_pressure)
    write_csv(out_dir / "reports" / "weekly_session_retry_pressure.csv", weekly_session_retry)
    retry_summary = retry_pressure_summary(retry_pressure)
    write_csv(out_dir / "reports" / "retry_pressure_summary.csv", retry_summary)
    weekly_retry_causes = weekly_retry_cause_groups(retry_pressure)
    write_csv(out_dir / "reports" / "weekly_retry_cause_groups.csv", weekly_retry_causes)
    retry_cause_summary_rows = retry_cause_summary(retry_pressure)
    write_csv(out_dir / "reports" / "retry_cause_summary.csv", retry_cause_summary_rows)
    session_cost_case_points_rows = session_cost_case_points(data)
    write_csv(out_dir / "reports" / "session_cost_case_points.csv", session_cost_case_points_rows)
    issue_detail_rows = weekly_issue_details(findings)
    write_csv(out_dir / "reports" / "weekly_issue_details.csv", issue_detail_rows)
    write_report_md(out_dir, session_rows, weekly, findings)
    write_csv(out_dir / "reports" / "review_packet_index.csv", review_index)
    return {
        "session_quality": session_rows,
        "issue_02_wording_summary": issue_02_wording_summary_rows,
        "weekly": weekly,
        "weekly_answer": weekly_answer,
        "weekly_answer_syntax": weekly_answer_syntax,
        "weekly_answer_model": weekly_answer_model,
        "prompt_contract_summary": prompt_contract_summary_rows,
        "backend_rejection_summary": backend_rejection_summary_rows,
        "weekly_process_step_shape": weekly_process_step_shape,
        "weekly_process_step_shape_model": weekly_process_step_shape_model,
        "weekly_step_6_shape": weekly_step_6_shape,
        "weekly_step_6_shape_model": weekly_step_6_shape_model,
        "compliance_export_summary": compliance_export_summary_rows,
        "weekly_raw_change_status_quality": weekly_raw_change_status_quality,
        "raw_change_status_summary": raw_change_status_summary_rows,
        "weekly_change_status_quality": weekly_change_status_quality,
        "weekly_change_status_hierarchy": weekly_change_status_hierarchy,
        "weekly_bureaucracy_cost_quality": weekly_bureaucracy_cost_quality,
        "weekly_structure_pair_checks": weekly_structure_pairs,
        "weekly_cost_variance_checks": weekly_cost_variance_groups,
        "weekly_case_count_checks": weekly_case_count_candidates,
        "weekly_retry_pressure": weekly_retry,
        "weekly_session_retry_pressure": weekly_session_retry,
        "retry_pressure_summary": retry_summary,
        "weekly_retry_cause_groups": weekly_retry_causes,
        "retry_cause_summary": retry_cause_summary_rows,
        "session_cost_case_points": session_cost_case_points_rows,
        "weekly_issue_details": issue_detail_rows,
        "review_packet_index": review_index,
    }

def completion_depth(data: dict[str, list[dict[str, Any]]], sid: int) -> str:
    if any(int_or_none(c.get("session_id")) == sid for c in data["costs"]):
        return "total_cost_ready"
    if any(int_or_none(s.get("session_id")) == sid and (safe_float(s.get("cost_current")) is not None or safe_float(s.get("cost_proposed")) is not None) for s in data["process_steps"]):
        return "effort_ready"
    if any(int_or_none(s.get("session_id")) == sid for s in data["process_steps"]):
        return "process_steps_ready"
    if any(int_or_none(g.get("session_id")) == sid for g in data["case_groups"]):
        return "case_groups_ready"
    if any(int_or_none(p.get("session_id")) == sid for p in data["processes"]):
        return "processes_ready"
    if any(int_or_none(r.get("session_id")) == sid for r in data["regulations"]):
        return "regulations_ready"
    if any(int_or_none(a.get("session_id")) == sid for a in data["llm_answers"]):
        return "llm_answers_only"
    return "empty"

def has_any_evidence(data: dict[str, list[dict[str, Any]]], sid: int) -> bool:
    return completion_depth(data, sid) != "empty"

def weekly_counts(session_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_week: dict[str, list[dict[str, Any]]] = {}
    for row in session_rows:
        by_week.setdefault(str(row.get("week") or "unknown"), []).append(row)
    weekly = []
    for week, rows in sorted(by_week.items()):
        out: dict[str, Any] = {
            "week": week,
            "total_sessions": len(rows),
            "good_sessions": sum(1 for r in rows if r.get("quality_label") == "good"),
            "bad_sessions": sum(1 for r in rows if r.get("quality_label") == "bad"),
            "diagnostic_only_sessions": sum(1 for r in rows if r.get("quality_label") == "diagnostic_only"),
            "unknown_or_incomplete": sum(1 for r in rows if r.get("quality_label") == "unknown_or_incomplete"),
        }
        for issue_id in ISSUES:
            out[issue_id] = sum(1 for r in rows if r.get(issue_id) is True)
        weekly.append(out)
    return weekly

def finding_session_judgement(row: dict[str, Any]) -> str:
    """Classify whether a finding should make the whole session bad.

    Repeated-run variance is a quality signal, but without adjudication it does
    not prove which session is wrong. Those findings are kept visible as
    diagnostics while avoiding an over-strong session-level bad label.
    """
    issue_id = str(row.get("issue_id") or "")
    evidence = row.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
    if issue_id in {
        "issue_01_duplicate_fallgruppen",
        "issue_03_json_truncation",
    }:
        if issue_id == "issue_03_json_truncation":
            evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
            if evidence.get("parse_class") == "empty_or_invalid_top_level":
                return "review_signal"
        return "hard_failure"
    if issue_id == "issue_04_change_status_inconsistency":
        if evidence.get("reason") == "changed_but_values_equal":
            return "review_signal"
        return "hard_failure"
    if issue_id == "issue_02_unnecessary_addressee_steps":
        bucket = evidence.get("classification_bucket")
        if bucket in {"no_applies_but_downstream_prompted", "no_applies_but_tiles_shown", "no_applies_prompt_and_tile"}:
            return "hard_failure"
        return "review_signal"
    if issue_id == "issue_08_bureaucracy_cost":
        if evidence.get("reason") in {"raw_ip_not_persisted", "ip_present_bureaucracy_missing_or_zero"}:
            return "hard_failure"
        return "review_signal"
    if issue_id == "issue_09_compliance_export_quality":
        if evidence.get("quality_class") in {"empty_export", "leaked_prompt_or_json_artifact"}:
            return "hard_failure"
        return "review_signal"
    if issue_id in {
        "issue_05_structure_consistency",
        "issue_06_cost_variance",
        "issue_07_case_count_driven_variance",
    }:
        return "instability_signal"
    return "review_signal"

def write_adjudication_packets(
    out_dir: Path,
    data: dict[str, list[dict[str, Any]]],
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    clear_generated_files(out_dir / "review_packets", ("*.json",))
    rows: list[dict[str, Any]] = []
    seen_packet_ids: set[str] = set()
    for row in findings:
        question = review_question(row)
        if not question:
            continue
        packet_id = review_packet_id(row)
        if packet_id in seen_packet_ids:
            continue
        seen_packet_ids.add(packet_id)
        payload = review_payload(data, row)
        write_review_packet(out_dir, row, question, payload)
        rows.append({
            "packet_id": packet_id,
            "issue_id": row.get("issue_id"),
            "session_id": row.get("session_id"),
            "app_session_id": row.get("app_session_id"),
            "week": row.get("week"),
            "model": row.get("model"),
            "law_pair": row.get("law_pair"),
            "answer_id": row.get("answer_id"),
            "judgement": finding_session_judgement(row),
            "detail_keys": finding_detail_keys(row),
            "question": question,
            "evidence_hash": row.get("evidence_hash"),
        })
    return rows

def review_packet_id(row: dict[str, Any]) -> str:
    return f"{row['issue_id']}_session_{row.get('session_id')}_answer_{row.get('answer_id') or 'none'}_{row['evidence_hash'][:10]}"

def review_question(row: dict[str, Any]) -> str | None:
    issue_id = str(row.get("issue_id") or "")
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    judgement = finding_session_judgement(row)
    if issue_id == "issue_01_duplicate_fallgruppen":
        return "Are these case groups genuine duplicates that would distort downstream steps or costs, rather than harmless aliases?"
    if issue_id == "issue_02_unnecessary_addressee_steps":
        bucket = evidence.get("classification_bucket")
        if bucket == "applies_but_downstream_says_not_applicable":
            return "Does the downstream answer/tile correctly conclude that this addressee has no relevant work despite applicable regulations, or is this an applicability/prompting failure?"
        if bucket in {"no_applies_but_downstream_prompted", "no_applies_but_tiles_shown", "no_applies_prompt_and_tile"}:
            return "Is there any legal reason to show prompts or tiles for this addressee despite zero applicable regulations, or is this unnecessary workflow execution?"
        if str(bucket).startswith("no_applies_prompt_only"):
            return "Was this prompt-only zero-applicability case merely a failed/reverted/form attempt, or did it create meaningful downstream analysis despite no applicable regulations?"
        if bucket == "missing_regulation_context_but_downstream_work":
            return "Is the missing regulation context caused by an incomplete/reverted session state, or does this reveal downstream work running without a valid applicability base?"
    if issue_id == "issue_03_json_truncation" and evidence.get("parse_class") == "empty_or_invalid_top_level":
        return "Is this empty required payload a legitimate 'nothing to analyse' answer, or did the model fail to return the expected entities?"
    if issue_id == "issue_04_change_status_inconsistency" and evidence.get("reason") == "changed_but_values_equal":
        return "Is 'changed' legally meaningful here despite equal current/proposed numeric values, or should this be treated as an inconsistent status?"
    if issue_id == "issue_05_structure_consistency":
        return "Are the structural differences between these same-law-pair/same-model runs legally justifiable, or evidence of unstable model/prompt behavior?"
    if issue_id == "issue_06_cost_variance":
        return "Is the final-cost variance legally explainable, or caused by inconsistent model assumptions or prompting?"
    if issue_id == "issue_07_case_count_driven_variance":
        return "Is this cost variance mainly caused by case-count assumptions rather than legal interpretation?"
    if issue_id == "issue_08_bureaucracy_cost":
        reason = evidence.get("reason")
        if reason == "suspicious_all_business_cost_marked_bureaucracy":
            return "Should nearly all business cost be counted as bureaucracy cost here, or has general compliance effort been mixed into the bureaucracy-cost bucket?"
        if reason == "raw_ip_not_persisted":
            return "Did the raw answer correctly identify business information obligations that were lost in persistence, or are the raw flags false positives?"
        if reason == "ip_present_bureaucracy_missing_or_zero":
            return "Is zero/missing bureaucracy cost defensible despite business information obligations, or is this a cost-separation failure?"
    if issue_id == "issue_09_compliance_export_quality":
        return "Does this compliance export contain usable Markdown text, or did the model return an empty/leaky artefact?"
    if judgement in {"review_signal", "instability_signal"}:
        return "Does this diagnostic signal represent a true quality problem, or a defensible outcome for this legal change?"
    return None

def review_payload(data: dict[str, list[dict[str, Any]]], row: dict[str, Any]) -> dict[str, Any]:
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    session_ids = related_session_ids(row)
    answer_id = int_or_none(row.get("answer_id"))
    payload: dict[str, Any] = {
        "finding": compact_finding(row),
        "judgement": finding_session_judgement(row),
        "detail_keys": finding_detail_keys(row),
        "sessions": [session_review_context(data, sid) for sid in session_ids],
        "related_answers": answer_review_contexts(data, session_ids, answer_id),
    }
    if evidence:
        payload["evidence"] = evidence
    return payload

def compact_finding(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "issue_id": row.get("issue_id"),
        "classification": row.get("classification"),
        "severity": row.get("severity"),
        "session_id": row.get("session_id"),
        "app_session_id": row.get("app_session_id"),
        "week": row.get("week"),
        "law_pair": row.get("law_pair"),
        "model": row.get("model"),
        "answer_id": row.get("answer_id"),
        "prompt_id": row.get("prompt_id"),
        "norm_addressee": row.get("norm_addressee"),
        "evidence_summary": row.get("evidence_summary"),
        "evidence_hash": row.get("evidence_hash"),
    }

def related_session_ids(row: dict[str, Any]) -> list[int]:
    ids: list[int] = []
    for key in ("session_id",):
        sid = int_or_none(row.get(key))
        if sid is not None and sid not in ids:
            ids.append(sid)
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    for key in ("left_session_id", "right_session_id", "low_session_id", "high_session_id"):
        sid = int_or_none(evidence.get(key))
        if sid is not None and sid not in ids:
            ids.append(sid)
    return ids

def session_review_context(data: dict[str, list[dict[str, Any]]], sid: int) -> dict[str, Any]:
    session = next((s for s in data["sessions"] if int_or_none(s.get("session_id")) == sid), {"session_id": sid})
    counts = {
        "regulations": sum(1 for r in data["regulations"] if int_or_none(r.get("session_id")) == sid),
        "processes": sum(1 for r in data["processes"] if int_or_none(r.get("session_id")) == sid),
        "case_groups": sum(1 for r in data["case_groups"] if int_or_none(r.get("session_id")) == sid),
        "process_steps": sum(1 for r in data["process_steps"] if int_or_none(r.get("session_id")) == sid),
        "cost_rows": sum(1 for r in data["costs"] if int_or_none(r.get("session_id")) == sid),
        "llm_answers": sum(1 for r in data["llm_answers"] if int_or_none(r.get("session_id")) == sid),
    }
    return {
        "session": {
            "session_id": sid,
            "app_session_id": session.get("app_session_id"),
            "created_at": session.get("created_at"),
            "law_pair": law_pair_key(session),
            "model": session.get("llm_model"),
            "completion_depth": completion_depth(data, sid),
            "cc_cost": session.get("cc_cost"),
        },
        "counts": counts,
        "costs": [
            {
                "norm_addressee": row.get("norm_addressee"),
                "total_cost": row.get("total_cost"),
                "bureaucracy_cost": row.get("bureaucracy_cost"),
                "total_expenses": row.get("total_expenses"),
                "total_time_minutes": row.get("total_time_minutes"),
            }
            for row in data["costs"]
            if int_or_none(row.get("session_id")) == sid
        ],
        "sample_entities": sample_session_entities(data, sid),
    }

def sample_session_entities(data: dict[str, list[dict[str, Any]]], sid: int) -> dict[str, list[dict[str, Any]]]:
    return {
        "regulations": [
            pick(row, ("regulation_id", "legal_citation", "description", "change_status", "applies_to_administration", "applies_to_business", "applies_to_citizens", "is_business_information_obligation"))
            for row in data["regulations"] if int_or_none(row.get("session_id")) == sid
        ][:8],
        "processes": [
            pick(row, ("process_id", "norm_addressee", "process", "change_status"))
            for row in data["processes"] if int_or_none(row.get("session_id")) == sid
        ][:8],
        "case_groups": [
            pick(row, ("case_group_id", "process_id", "norm_addressee", "case_group", "change_status", "cases_current", "cases_proposed", "cost"))
            for row in data["case_groups"] if int_or_none(row.get("session_id")) == sid
        ][:8],
        "process_steps": [
            pick(row, ("step_id", "case_group_id", "norm_addressee", "step", "change_status", "cost_current", "cost_proposed"))
            for row in data["process_steps"] if int_or_none(row.get("session_id")) == sid
        ][:8],
    }

def answer_review_contexts(
    data: dict[str, list[dict[str, Any]]],
    session_ids: list[int],
    answer_id: int | None,
) -> list[dict[str, Any]]:
    answers = []
    if answer_id is not None:
        answers = [row for row in data["llm_answers"] if int_or_none(row.get("answer_id")) == answer_id]
    if not answers:
        session_set = set(session_ids)
        answers = [
            row for row in data["llm_answers"]
            if int_or_none(row.get("session_id")) in session_set
            and row.get("prompt_id") in {"regulations_identification", "process_compilation", "case_group_development", "process_step_analysis", "cases_calculation", "effort_calculation"}
        ][:10]
    return [answer_review_context(row) for row in answers]

def answer_review_context(row: dict[str, Any]) -> dict[str, Any]:
    text = str(row.get("answer_text") or "")
    prompt = str(row.get("prompt_text") or "")
    return {
        "answer_id": row.get("answer_id"),
        "session_id": row.get("session_id"),
        "created_at": row.get("created_at"),
        "prompt_id": row.get("prompt_id"),
        "model": row.get("model"),
        "norm_addressee": row.get("norm_addressee") or answer_addressee(row),
        "answer_excerpt": excerpt(text, 1600),
        "answer_tail": text[-800:],
        "prompt_excerpt": excerpt(prompt, 1000),
    }

def pick(row: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: row.get(key) for key in keys if row.get(key) not in (None, "")}

def excerpt(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = max(0, limit // 2)
    tail = max(0, limit - head)
    return text[:head] + "\n...\n" + text[-tail:]

def weekly_answer_quality(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_week: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_week.setdefault(str(row.get("answer_week") or "unknown"), []).append(row)
    out_rows = []
    classes = [
        "valid_json", "wrong_top_level_key", "empty_or_invalid_top_level",
        "near_complete_missing_closer", "hard_mid_content_truncation",
        "invalid_json", "non_json_prose",
    ]
    for week, items in sorted(by_week.items()):
        out = {"week": week, "total_answers": len(items)}
        for cls in classes:
            out[cls] = sum(1 for item in items if item.get("parse_class") == cls)
        out_rows.append(out)
    return out_rows

def issue_02_wording_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row.get("applicability_context") or "unknown"),
            str(row.get("source_type") or "unknown"),
            str(row.get("wording_bucket") or "unknown"),
            str(row.get("matched_phrase") or "unknown"),
        )
        buckets.setdefault(key, []).append(row)
    out_rows = []
    for (context, source_type, bucket, phrase), items in sorted(buckets.items(), key=lambda item: (-len(item[1]), item[0])):
        out_rows.append({
            "applicability_context": context,
            "source_type": source_type,
            "wording_bucket": bucket,
            "matched_phrase": phrase,
            "count": len(items),
            "example_sessions": ", ".join(str(item.get("session_id")) for item in items[:8]),
            "example_match_path": first_nonempty(items, "match_path"),
            "example_excerpt": first_nonempty(items, "excerpt"),
        })
    return out_rows

def weekly_answer_syntax_quality(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_week: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_week.setdefault(str(row.get("answer_week") or "unknown"), []).append(row)
    classes = [
        "valid_json",
        "near_complete_missing_closer",
        "hard_mid_content_truncation",
        "invalid_json",
        "non_json_prose",
    ]
    out_rows = []
    for week, items in sorted(by_week.items()):
        out = {"week": week, "total_answers": len(items)}
        for cls in classes:
            out[cls] = sum(1 for item in items if (item.get("syntax_class") or item.get("parse_class")) == cls)
        out_rows.append(out)
    return out_rows

def weekly_answer_quality_by_model(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_group: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        model = str(row.get("model") or "unknown")
        week = str(row.get("answer_week") or "unknown")
        by_group.setdefault((model, week), []).append(row)
    out_rows = []
    classes = json_quality_classes()
    for (model, week), items in sorted(by_group.items()):
        out = {"model": model, "week": week, "total_answers": len(items)}
        for cls in classes:
            out[cls] = sum(1 for item in items if item.get("parse_class") == cls)
        out_rows.append(out)
    return out_rows

def prompt_contract_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row.get("prompt_id") or "unknown"),
            str(row.get("prompt_contract_kind") or "unknown"),
            str(row.get("prompt_required_root_key") or ""),
        )
        buckets.setdefault(key, []).append(row)
    out_rows = []
    for (prompt_id, kind, root), items in sorted(buckets.items()):
        out_rows.append({
            "prompt_id": prompt_id,
            "prompt_contract_kind": kind,
            "prompt_required_root_key": root,
            "total_answers": len(items),
            "provider_response_format_metadata_rows": sum(
                1 for item in items
                if item.get("provider_response_format_requested") or item.get("provider_response_format_used")
            ),
            "wrong_top_level_key": sum(1 for item in items if item.get("parse_class") == "wrong_top_level_key"),
            "answer_matches_prompt_root": sum(1 for item in items if item.get("answer_matches_prompt_root") == "yes"),
            "current_checker_contract_mismatch": sum(1 for item in items if item.get("prompt_contract_matches_current_checker") == "no"),
            "accepted_wrong_top_level_key": sum(
                1 for item in items
                if item.get("parse_class") == "wrong_top_level_key"
                and item.get("db_outcome") == "accepted_into_session_state"
            ),
            "rejected_wrong_top_level_key": sum(
                1 for item in items
                if item.get("parse_class") == "wrong_top_level_key"
                and item.get("db_outcome") == "rejected_by_session_update"
            ),
        })
    return out_rows

def backend_rejection_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        group = str(row.get("backend_rejection_group") or "")
        if not group:
            continue
        key = (
            str(row.get("prompt_id") or "unknown"),
            str(row.get("db_outcome") or "unknown"),
            group,
        )
        buckets.setdefault(key, []).append(row)
    return [
        {
            "prompt_id": prompt_id,
            "db_outcome": db_outcome,
            "backend_rejection_group": group,
            "count": len(items),
            "example_answer_ids": ", ".join(str(item.get("answer_id")) for item in items[:6]),
            "example_state_reason": first_nonempty(items, "state_reason"),
        }
        for (prompt_id, db_outcome, group), items in sorted(buckets.items())
    ]

def compliance_export_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row.get("model") or "unknown"),
            str(row.get("quality_class") or "unknown"),
        )
        buckets.setdefault(key, []).append(row)
    return [
        {
            "model": model,
            "quality_class": quality_class,
            "count": len(items),
            "example_answer_ids": ", ".join(str(item.get("answer_id")) for item in items[:6]),
            "median_text_length": median([safe_float(item.get("text_length")) for item in items]),
            "with_section_4_heading": sum(1 for item in items if truthy(item.get("has_section_four_heading"))),
            "with_markdown_table": sum(1 for item in items if truthy(item.get("has_markdown_table"))),
        }
        for (model, quality_class), items in sorted(buckets.items())
    ]

def weekly_raw_change_status_checks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_week: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_week.setdefault(str(row.get("answer_week") or "unknown"), []).append(row)
    out_rows = []
    classes = raw_change_status_classes()
    for week, items in sorted(by_week.items()):
        out = {"week": week, "total_status_entities": len(items)}
        for cls in classes:
            out[cls] = sum(1 for item in items if item.get("status_bucket") == cls)
        out_rows.append(out)
    return out_rows

def raw_change_status_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row.get("prompt_id") or "unknown"),
            str(row.get("entity_type") or "unknown"),
            str(row.get("status_bucket") or "unknown"),
        )
        buckets.setdefault(key, []).append(row)
    return [
        {
            "prompt_id": prompt_id,
            "entity_type": entity_type,
            "status_bucket": bucket,
            "count": len(items),
            "example_answer_ids": ", ".join(unique_strings(item.get("answer_id") for item in items)[:6]),
            "example_status_values": ", ".join(sorted({
                str(item.get("raw_status_value"))
                for item in items
                if item.get("raw_status_value") not in (None, "")
            }))[:180],
        }
        for (prompt_id, entity_type, bucket), items in sorted(buckets.items())
    ]

def unique_strings(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out

def median(values: list[float | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return None
    return statistics.median(clean)

def json_quality_classes() -> list[str]:
    return [
        "valid_json", "wrong_top_level_key", "empty_or_invalid_top_level",
        "near_complete_missing_closer", "hard_mid_content_truncation",
        "invalid_json", "non_json_prose",
    ]

def process_step_shape_classes() -> list[str]:
    return [
        "expected_flat_fallgruppen",
        "expected_nested_prozesse",
        "fallback_reachable_flat_fallgruppen",
        "prozesse_present_but_no_steps",
        "flat_fallgruppen_without_steps",
        "other_json_no_prozesse",
        "top_level_list",
        "unparseable",
    ]

def step_6_shape_classes() -> list[str]:
    return [
        "expected_flat_fallgruppen",
        "legacy_nested_prozesse",
        "flat_fallgruppen_without_metrics",
        "prozesse_present_without_metrics",
        "other_json_no_fallgruppen",
        "top_level_list",
        "unparseable",
    ]

def raw_change_status_classes() -> list[str]:
    return [
        "present_valid",
        "missing",
        "present_unrecognized",
    ]

def weekly_process_step_shapes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_week: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_week.setdefault(str(row.get("answer_week") or "unknown"), []).append(row)
    return process_step_shape_aggregate_rows(by_week)

def weekly_process_step_shapes_by_model(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_group: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        by_group.setdefault((str(row.get("model") or "unknown"), str(row.get("answer_week") or "unknown")), []).append(row)
    out_rows = []
    for (model, week), items in sorted(by_group.items()):
        row = process_step_shape_count_row(items)
        row["model"] = model
        row["week"] = week
        out_rows.append(row)
    return out_rows

def weekly_step_6_shapes_by_prompt(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_group: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        by_group.setdefault((str(row.get("prompt_id") or "unknown"), str(row.get("answer_week") or "unknown")), []).append(row)
    out_rows = []
    for (prompt_id, week), items in sorted(by_group.items()):
        row = step_6_shape_count_row(items)
        row["prompt_id"] = prompt_id
        row["week"] = week
        out_rows.append(row)
    return out_rows

def weekly_step_6_shapes_by_model(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_group: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row.get("prompt_id") or "unknown"),
            str(row.get("model") or "unknown"),
            str(row.get("answer_week") or "unknown"),
        )
        by_group.setdefault(key, []).append(row)
    out_rows = []
    for (prompt_id, model, week), items in sorted(by_group.items()):
        row = step_6_shape_count_row(items)
        row["prompt_id"] = prompt_id
        row["model"] = model
        row["week"] = week
        out_rows.append(row)
    return out_rows

def weekly_change_status_checks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_week: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_week.setdefault(str(row.get("week") or "unknown"), []).append(row)
    out_rows = []
    for week, items in sorted(by_week.items()):
        evaluable = [item for item in items if truthy(item.get("evaluable"))]
        out: dict[str, Any] = {
            "issue_id": "issue_04_change_status_inconsistency",
            "week": week,
            "total_change_status_checks": len(evaluable),
            "consistent_change_status": sum(1 for item in evaluable if item.get("check_result") == "consistent"),
            "not_evaluable": len(items) - len(evaluable),
        }
        for item in evaluable:
            result = str(item.get("check_result") or "")
            if result == "consistent":
                continue
            key = f"{status_group(item.get('change_status'))}__{safe_key(result)}"
            out[key] = int(out.get(key) or 0) + 1
        out_rows.append(out)
    return out_rows

def weekly_change_status_hierarchy_checks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_week: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_week.setdefault(str(row.get("week") or "unknown"), []).append(row)
    out_rows = []
    for week, items in sorted(by_week.items()):
        out: dict[str, Any] = {
            "issue_id": "issue_04_change_status_inconsistency",
            "week": week,
            "total_hierarchy_checks": len(items),
            "consistent_hierarchy": sum(1 for item in items if item.get("check_result") == "consistent"),
        }
        for item in items:
            result = str(item.get("check_result") or "")
            if result == "consistent":
                continue
            out[safe_key(result)] = int(out.get(safe_key(result)) or 0) + 1
        out_rows.append(out)
    return out_rows

def weekly_bureaucracy_cost_checks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_week: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_week.setdefault(str(row.get("week") or "unknown"), []).append(row)
    out_rows = []
    for week, items in sorted(by_week.items()):
        out: dict[str, Any] = {
            "issue_id": "issue_08_bureaucracy_cost",
            "week": week,
            "total_sessions_checked": len(items),
            "sessions_with_raw_business_ip": sum(1 for item in items if num(item.get("raw_business_ip_count")) > 0),
            "sessions_with_persisted_business_ip": sum(1 for item in items if num(item.get("persisted_business_ip_count")) > 0),
        }
        for item in items:
            bucket = str(item.get("chart_bucket") or "unknown_bureaucracy_bucket")
            if bucket == "no_business_ip":
                continue
            out[bucket] = int(out.get(bucket) or 0) + 1
        out_rows.append(out)
    return out_rows

def weekly_structure_pair_checks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_week: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_week.setdefault(iso_week(row.get("right_created_at")), []).append(row)
    out_rows = []
    for week, items in sorted(by_week.items()):
        out_rows.append({
            "issue_id": "issue_05_structure_consistency",
            "week": week,
            "total_structure_pairs": len(items),
        })
    return out_rows

def weekly_cost_variance_checks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_week: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_week.setdefault(str(row.get("latest_week") or "unknown"), []).append(row)
    out_rows = []
    for week, items in sorted(by_week.items()):
        out_rows.append({
            "issue_id": "issue_06_cost_variance",
            "week": week,
            "total_cost_variance_groups": len(items),
        })
    return out_rows

def weekly_case_count_checks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_week: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_week.setdefault(str(row.get("high_week") or "unknown"), []).append(row)
    out_rows = []
    for week, items in sorted(by_week.items()):
        out_rows.append({
            "issue_id": "issue_07_case_count_driven_variance",
            "week": week,
            "total_case_count_candidates": len(items),
        })
    return out_rows

def weekly_retry_pressure(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        buckets.setdefault((str(row.get("week") or "unknown"), str(row.get("step_key") or "unknown")), []).append(row)
    out_rows = []
    for (week, step_key), items in sorted(buckets.items()):
        succeeded = [item for item in items if truthy(item.get("succeeded"))]
        retry_values = [num(item.get("retry_rounds_to_success")) for item in succeeded]
        out_rows.append({
            "week": week,
            "step_key": step_key,
            "step_label": first_nonempty(items, "step_label") or step_key,
            "total_step_units": len(items),
            "succeeded_units": len(succeeded),
            "succeeded_without_retry_units": sum(1 for item in succeeded if num(item.get("retry_rounds_to_success")) <= 0),
            "succeeded_after_retry_units": sum(1 for item in succeeded if num(item.get("retry_rounds_to_success")) > 0),
            "failed_without_success_units": len(items) - len(succeeded),
            "total_retry_rounds_to_success": sum(retry_values),
            "max_retry_rounds_to_success": max(retry_values) if retry_values else 0,
            "mean_retry_rounds_to_success": round(sum(retry_values) / len(retry_values), 3) if retry_values else 0,
            "post_success_attempts": sum(num(item.get("post_success_attempt_count")) for item in items),
        })
    return out_rows

def weekly_session_retry_pressure(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sessions: dict[str, dict[str, Any]] = {}
    for row in rows:
        sid = str(row.get("session_id") or "unknown")
        item = sessions.setdefault(sid, {
            "session_id": sid,
            "week": str(row.get("session_created_week") or row.get("week") or "unknown"),
            "total_retry_rounds": 0.0,
            "step_retry_rounds": {},
            "failed_units_without_success": 0,
        })
        step_key = str(row.get("step_key") or "unknown")
        retry_rounds = num(row.get("retry_rounds_to_success")) if truthy(row.get("succeeded")) else 0.0
        item["total_retry_rounds"] += retry_rounds
        item["step_retry_rounds"][step_key] = item["step_retry_rounds"].get(step_key, 0.0) + retry_rounds
        if not truthy(row.get("succeeded")):
            item["failed_units_without_success"] += 1

    by_week: dict[str, list[dict[str, Any]]] = {}
    for item in sessions.values():
        by_week.setdefault(str(item.get("week") or "unknown"), []).append(item)

    out_rows = []
    for week, items in sorted(by_week.items()):
        total_sessions = len(items)
        retrying = [item for item in items if num(item.get("total_retry_rounds")) > 0]
        out = {
            "week": week,
            "total_sessions": total_sessions,
            "no_retry_sessions": 0,
            "other_step_retry_sessions": 0,
            "step_5_retry_sessions": 0,
            "step_6_retry_sessions": 0,
            "step_5_and_6_retry_sessions": 0,
            "sessions_with_any_retry": len(retrying),
            "sessions_with_failed_units_without_success": sum(1 for item in items if num(item.get("failed_units_without_success")) > 0),
            "total_retry_rounds": sum(num(item.get("total_retry_rounds")) for item in items),
            "avg_retry_rounds_per_session": 0,
            "avg_retry_rounds_per_retrying_session": 0,
            "avg_step_5_retry_rounds_per_session": 0,
            "avg_step_6_retry_rounds_per_session": 0,
            "avg_other_step_retry_rounds_per_session": 0,
        }
        for item in items:
            step_rounds = item.get("step_retry_rounds") if isinstance(item.get("step_retry_rounds"), dict) else {}
            has_retry = num(item.get("total_retry_rounds")) > 0
            has_step_5 = num(step_rounds.get("step_5_process_steps")) > 0
            has_step_6 = num(step_rounds.get("step_6_effort")) > 0
            if not has_retry:
                out["no_retry_sessions"] += 1
            elif has_step_5 and has_step_6:
                out["step_5_and_6_retry_sessions"] += 1
            elif has_step_5:
                out["step_5_retry_sessions"] += 1
            elif has_step_6:
                out["step_6_retry_sessions"] += 1
            else:
                out["other_step_retry_sessions"] += 1
            out["avg_step_5_retry_rounds_per_session"] += num(step_rounds.get("step_5_process_steps"))
            out["avg_step_6_retry_rounds_per_session"] += num(step_rounds.get("step_6_effort"))
            out["avg_other_step_retry_rounds_per_session"] += sum(
                num(value) for key, value in step_rounds.items()
                if key not in {"step_5_process_steps", "step_6_effort"}
            )
        if total_sessions:
            for key in ("avg_step_5_retry_rounds_per_session", "avg_step_6_retry_rounds_per_session", "avg_other_step_retry_rounds_per_session"):
                out[key] = round(num(out[key]) / total_sessions, 3)
            out["avg_retry_rounds_per_session"] = round(num(out["total_retry_rounds"]) / total_sessions, 3)
        if retrying:
            out["avg_retry_rounds_per_retrying_session"] = round(num(out["total_retry_rounds"]) / len(retrying), 3)
        out_rows.append(out)
    return out_rows

def retry_pressure_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_step: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_step.setdefault(str(row.get("step_key") or "unknown"), []).append(row)
    out_rows = []
    for step_key, items in sorted(by_step.items()):
        succeeded = [item for item in items if truthy(item.get("succeeded"))]
        retry_values = [num(item.get("retry_rounds_to_success")) for item in succeeded]
        out_rows.append({
            "step_key": step_key,
            "step_label": first_nonempty(items, "step_label") or step_key,
            "total_step_units": len(items),
            "succeeded_units": len(succeeded),
            "succeeded_after_retry_units": sum(1 for item in succeeded if num(item.get("retry_rounds_to_success")) > 0),
            "failed_without_success_units": len(items) - len(succeeded),
            "total_retry_rounds_to_success": sum(retry_values),
            "max_retry_rounds_to_success": max(retry_values) if retry_values else 0,
            "mean_retry_rounds_to_success": round(sum(retry_values) / len(retry_values), 3) if retry_values else 0,
            "post_success_attempts": sum(num(item.get("post_success_attempt_count")) for item in items),
        })
    return out_rows

def weekly_retry_cause_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        buckets.setdefault((str(row.get("week") or "unknown"), str(row.get("step_key") or "unknown")), []).append(row)
    out_rows = []
    for (week, step_key), items in sorted(buckets.items()):
        problem_items = [item for item in items if retry_problem_unit(item)]
        out: dict[str, Any] = {
            "week": week,
            "step_key": step_key,
            "step_label": first_nonempty(items, "step_label") or step_key,
            "total_step_units": len(items),
            "total_retry_or_failure_units": len(problem_items),
        }
        for item in problem_items:
            cause = str(item.get("primary_retry_cause") or "unknown_retry_cause")
            out[cause] = int(out.get(cause) or 0) + 1
        out_rows.append(out)
    return out_rows

def retry_cause_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        if not retry_problem_unit(row):
            continue
        buckets.setdefault((str(row.get("step_key") or "unknown"), str(row.get("primary_retry_cause") or "unknown_retry_cause")), []).append(row)
    out_rows = []
    for (step_key, cause), items in sorted(buckets.items()):
        out_rows.append({
            "step_key": step_key,
            "step_label": first_nonempty(items, "step_label") or step_key,
            "primary_retry_cause": cause,
            "unit_count": len(items),
            "succeeded_after_retry_units": sum(1 for item in items if truthy(item.get("succeeded")) and num(item.get("retry_rounds_to_success")) > 0),
            "failed_without_success_units": sum(1 for item in items if not truthy(item.get("succeeded"))),
            "total_retry_rounds_to_success": sum(num(item.get("retry_rounds_to_success")) for item in items),
            "db_state_reason_groups": sorted_json_values(items, "db_state_reason_groups"),
            "example_session_ids": ", ".join(str(item.get("session_id")) for item in items[:8]),
        })
    return out_rows

def retry_problem_unit(row: dict[str, Any]) -> bool:
    if not truthy(row.get("succeeded")):
        return str(row.get("primary_retry_cause") or "") != "no_failed_attempt_before_success"
    return num(row.get("retry_rounds_to_success")) > 0

def sorted_json_values(rows: list[dict[str, Any]], key: str) -> str:
    values: set[str] = set()
    for row in rows:
        raw = row.get(key)
        parsed = parse_json_maybe(raw)
        if isinstance(parsed, list):
            values.update(str(item) for item in parsed)
        elif raw not in (None, ""):
            values.add(str(raw))
    return ", ".join(sorted(values))

def first_nonempty(rows: list[dict[str, Any]], key: str) -> Any:
    for row in rows:
        if row.get(key) not in (None, ""):
            return row.get(key)
    return None

def session_cost_case_points(data: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for session in sorted(data["sessions"], key=lambda row: str(row.get("created_at") or "")):
        sid = int_or_none(session.get("session_id"))
        if sid is None:
            continue
        total_cost = session_total_cost(data, sid)
        if total_cost is None:
            continue
        proposed_cases = session_case_total(data, sid, "proposed")
        current_cases = session_case_total(data, sid, "current")
        rows.append({
            "session_id": sid,
            "app_session_id": session.get("app_session_id"),
            "created_at": session.get("created_at"),
            "week": iso_week(session.get("created_at")),
            "law_pair": law_pair_key(session),
            "model": session.get("llm_model"),
            "total_cost": total_cost,
            "proposed_case_total": proposed_cases,
            "current_case_total": current_cases,
            "deep_research_enabled": int(session_deep_research_enabled(data, session)),
        })
    return rows

def session_case_total(data: dict[str, list[dict[str, Any]]], sid: int, period: str) -> float | None:
    total = 0.0
    found = False
    for row in data["case_groups"]:
        if int_or_none(row.get("session_id")) != sid:
            continue
        value = case_group_cases(row, period)
        if value is not None:
            total += value
            found = True
    return total if found else None

def process_step_shape_aggregate_rows(by_week: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    out_rows = []
    for week, items in sorted(by_week.items()):
        row = process_step_shape_count_row(items)
        row["week"] = week
        out_rows.append(row)
    return out_rows

def process_step_shape_count_row(items: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"total_process_step_answers": len(items)}
    for cls in process_step_shape_classes():
        out[cls] = sum(1 for item in items if item.get("shape_class") == cls)
    out["current_code_accept"] = sum(1 for item in items if item.get("current_code_acceptance") == "accept")
    out["current_code_reject"] = sum(1 for item in items if item.get("current_code_acceptance") == "reject")
    out["persisted_applied"] = sum(1 for item in items if item.get("persisted_outcome") == "applied")
    return out

def step_6_shape_count_row(items: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"total_step_6_answers": len(items)}
    for cls in step_6_shape_classes():
        out[cls] = sum(1 for item in items if item.get("shape_class") == cls)
    out["current_code_accept"] = sum(1 for item in items if item.get("current_code_acceptance") == "accept")
    out["current_code_reject"] = sum(1 for item in items if item.get("current_code_acceptance") == "reject")
    out["persisted_applied"] = sum(1 for item in items if item.get("persisted_outcome") == "applied")
    return out

def weekly_issue_details(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], dict[str, Any]] = {}
    for finding_row in findings:
        if finding_row.get("classification") not in {"bad", "ambiguous"}:
            continue
        issue_id = str(finding_row.get("issue_id") or "unknown")
        week = str(finding_row.get("week") or "unknown")
        row = buckets.setdefault((issue_id, week), {"issue_id": issue_id, "week": week})
        for detail in finding_detail_keys(finding_row):
            row[detail] = int(row.get(detail) or 0) + 1
    return [row for _key, row in sorted(buckets.items())]

def finding_detail_keys(row: dict[str, Any]) -> list[str]:
    issue_id = str(row.get("issue_id") or "")
    evidence = row.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
    if issue_id == "issue_01_duplicate_fallgruppen":
        source = str(evidence.get("source") or "unknown_source")
        handoff = evidence.get("handoff_issue")
        if isinstance(handoff, dict) and handoff.get("type"):
            return [f"{source}__{safe_key(handoff.get('type'))}"]
        return [source]
    if issue_id == "issue_02_unnecessary_addressee_steps":
        bucket = str(evidence.get("classification_bucket") or "unknown")
        if bucket == "applies_but_downstream_says_not_applicable":
            has_answers = bool(evidence.get("not_applicable_answer_ids"))
            has_tiles = bool(evidence.get("not_applicable_tile_ids"))
            if has_answers and has_tiles:
                return ["applies_but_answer_and_tile_say_not_applicable"]
            if has_tiles:
                return ["applies_but_tile_says_not_applicable"]
            return ["applies_but_answer_says_not_applicable"]
        if bucket == "no_applies_but_downstream_prompted":
            return ["no_applies_but_prompt_called"]
        if bucket == "no_applies_but_tiles_shown":
            return ["no_applies_but_tile_shown"]
        if bucket in {
            "no_applies_prompt_and_tile",
            "no_applies_prompt_only_applied_no_counted_tile",
            "no_applies_prompt_only_query_or_form_failure",
            "no_applies_prompt_only_session_update_failed",
            "no_applies_prompt_only_reverted_or_superseded",
            "no_applies_prompt_only_no_tile",
            "missing_regulation_context_but_downstream_work",
        }:
            return [bucket]
        return [bucket]
    if issue_id == "issue_03_json_truncation":
        return [str(evidence.get("parse_class") or "unknown_json_quality")]
    if issue_id == "issue_04_change_status_inconsistency":
        status = status_group(evidence.get("change_status"))
        reason = safe_key(evidence.get("reason") or "unknown_reason")
        return [f"{status}__{reason}"]
    if issue_id == "issue_05_structure_consistency":
        layers = []
        for layer in ("regulations", "processes", "case_groups", "process_steps"):
            value = safe_float(evidence.get(f"{layer}_similarity"))
            if value is not None and value < 0.65:
                layers.append(f"{layer}_diverge")
        return layers or ["mean_structure_similarity_below_threshold"]
    if issue_id == "issue_06_cost_variance":
        keys = []
        cv = safe_float(evidence.get("coefficient_of_variation"))
        ratio = safe_float(evidence.get("max_min_ratio"))
        if cv is not None and cv > 0.5:
            keys.append("high_coefficient_of_variation")
        if ratio is not None and ratio > 2.0:
            keys.append("max_min_ratio_above_2")
        return keys or ["cost_variance_threshold_met"]
    if issue_id == "issue_07_case_count_driven_variance":
        return ["similar_structure_with_case_count_delta"]
    if issue_id == "issue_08_bureaucracy_cost":
        return [safe_key(evidence.get("reason") or "unknown_bureaucracy_reason")]
    if issue_id == "issue_09_compliance_export_quality":
        return [safe_key(evidence.get("quality_class") or "unknown_export_quality")]
    return ["unknown"]

def safe_key(value: Any) -> str:
    text = str(value or "unknown").strip().lower()
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "unknown"

def status_group(value: Any) -> str:
    text = safe_key(value)
    if "eingefuehrt" in text or text in {"new", "neu"}:
        return "introduced"
    if "abgeschafft" in text or "abolished" in text or "wegfall" in text:
        return "abolished"
    if "geaendert" in text or "changed" in text or "geandert" in text:
        return "changed"
    return "unknown_status"

def write_report_md(out_dir: Path, session_rows: list[dict[str, Any]], weekly: list[dict[str, Any]], findings: list[dict[str, Any]]) -> None:
    issue_counts = {issue_id: sum(1 for f in findings if f.get("issue_id") == issue_id and f.get("classification") == "bad") for issue_id in ISSUES}
    lines = [
        "# Historical Quality Report",
        "",
        "Incomplete sessions are not treated as bad unless concrete raw-answer or persisted-state evidence is present.",
        "",
        "## Summary",
        "",
        f"- Sessions analysed: {len(session_rows)}",
        f"- Good sessions: {sum(1 for r in session_rows if r.get('quality_label') == 'good')}",
        f"- Bad sessions with hard failures: {sum(1 for r in session_rows if r.get('quality_label') == 'bad')}",
        f"- Diagnostic-only sessions: {sum(1 for r in session_rows if r.get('quality_label') == 'diagnostic_only')}",
        f"- Unknown/incomplete sessions: {sum(1 for r in session_rows if r.get('quality_label') == 'unknown_or_incomplete')}",
        f"- Findings: {len(findings)}",
        "",
        "## Findings By Issue",
        "",
    ]
    for issue_id, name in ISSUES.items():
        lines.append(f"- `{issue_id}`: {issue_counts.get(issue_id, 0)} bad findings ({name})")
    lines.extend([
        "",
        "## Outputs",
        "",
        "- `reports/session_quality.csv`",
        "- `reports/weekly_session_quality.csv`",
        "- `reports/issue_02_not_applicable_wording_summary.csv`",
        "- `reports/weekly_answer_quality.csv`",
        "- `reports/weekly_answer_syntax_quality.csv`",
        "- `reports/weekly_answer_quality_by_model.csv`",
        "- `reports/prompt_contract_summary.csv`",
        "- `reports/backend_rejection_summary.csv`",
        "- `reports/weekly_process_step_shape.csv`",
        "- `reports/weekly_process_step_shape_by_model.csv`",
        "- `reports/weekly_step_6_shape.csv`",
        "- `reports/weekly_step_6_shape_by_model.csv`",
        "- `reports/compliance_export_quality_summary.csv`",
        "- `reports/weekly_change_status_quality.csv`",
        "- `reports/weekly_change_status_hierarchy.csv`",
        "- `reports/weekly_bureaucracy_cost_quality.csv`",
        "- `reports/weekly_structure_pair_checks.csv`",
        "- `reports/weekly_cost_variance_checks.csv`",
        "- `reports/weekly_case_count_checks.csv`",
        "- `reports/weekly_retry_pressure.csv`",
        "- `reports/weekly_session_retry_pressure.csv`",
        "- `reports/retry_pressure_summary.csv`",
        "- `reports/weekly_retry_cause_groups.csv`",
        "- `reports/retry_cause_summary.csv`",
        "- `reports/session_cost_case_points.csv`",
        "- `reports/weekly_issue_details.csv`",
        "- `findings/issue_02_not_applicable_wordings.csv`",
        "- `findings/retry_pressure.csv`",
        "- `findings/issue_03_process_step_shape.csv`",
        "- `findings/issue_03_step_6_shape.csv`",
        "- `findings/issue_09_compliance_export_quality.csv`",
        "- `findings/issue_04_change_status_quality.csv`",
        "- `findings/issue_08_bureaucracy_cost_quality.csv`",
        "- `findings/findings.csv` / `findings/findings.jsonl`",
        "- `visuals/index.html`",
        "- `review_packets/*.json` for ambiguous cases",
    ])
    (out_dir / "reports" / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

def visualize(out_dir: Path, markers: list[dict[str, Any]], config: dict[str, Any] | None = None) -> None:
    configure_analysis(config or load_run_config(out_dir))
    markers = merged_feature_markers(markers)
    weekly = read_csv_dicts(out_dir / "reports" / "weekly_session_quality.csv")
    issue_02_wording_summary_rows = read_csv_dicts(out_dir / "reports" / "issue_02_not_applicable_wording_summary.csv")
    weekly_answer = read_csv_dicts(out_dir / "reports" / "weekly_answer_quality.csv")
    weekly_answer_syntax = read_csv_dicts(out_dir / "reports" / "weekly_answer_syntax_quality.csv")
    weekly_answer_model = read_csv_dicts(out_dir / "reports" / "weekly_answer_quality_by_model.csv")
    prompt_contract_summary_rows = read_csv_dicts(out_dir / "reports" / "prompt_contract_summary.csv")
    backend_rejection_summary_rows = read_csv_dicts(out_dir / "reports" / "backend_rejection_summary.csv")
    weekly_process_step_shape = read_csv_dicts(out_dir / "reports" / "weekly_process_step_shape.csv")
    weekly_process_step_shape_model = read_csv_dicts(out_dir / "reports" / "weekly_process_step_shape_by_model.csv")
    weekly_step_6_shape = read_csv_dicts(out_dir / "reports" / "weekly_step_6_shape.csv")
    weekly_step_6_shape_model = read_csv_dicts(out_dir / "reports" / "weekly_step_6_shape_by_model.csv")
    compliance_export_summary_rows = read_csv_dicts(out_dir / "reports" / "compliance_export_quality_summary.csv")
    weekly_raw_change_status_quality = read_csv_dicts(out_dir / "reports" / "weekly_raw_change_status_quality.csv")
    raw_change_status_summary_rows = read_csv_dicts(out_dir / "reports" / "raw_change_status_quality_summary.csv")
    weekly_change_status_quality = read_csv_dicts(out_dir / "reports" / "weekly_change_status_quality.csv")
    weekly_change_status_hierarchy = read_csv_dicts(out_dir / "reports" / "weekly_change_status_hierarchy.csv")
    weekly_bureaucracy_cost_quality = read_csv_dicts(out_dir / "reports" / "weekly_bureaucracy_cost_quality.csv")
    weekly_structure_pairs = read_csv_dicts(out_dir / "reports" / "weekly_structure_pair_checks.csv")
    weekly_cost_variance_groups = read_csv_dicts(out_dir / "reports" / "weekly_cost_variance_checks.csv")
    weekly_case_count_candidates = read_csv_dicts(out_dir / "reports" / "weekly_case_count_checks.csv")
    weekly_retry = read_csv_dicts(out_dir / "reports" / "weekly_retry_pressure.csv")
    weekly_session_retry = read_csv_dicts(out_dir / "reports" / "weekly_session_retry_pressure.csv")
    retry_summary = read_csv_dicts(out_dir / "reports" / "retry_pressure_summary.csv")
    weekly_retry_causes = read_csv_dicts(out_dir / "reports" / "weekly_retry_cause_groups.csv")
    retry_cause_summary_rows = read_csv_dicts(out_dir / "reports" / "retry_cause_summary.csv")
    cost_case_points = read_csv_dicts(out_dir / "reports" / "session_cost_case_points.csv")
    weekly_issue_detail = read_csv_dicts(out_dir / "reports" / "weekly_issue_details.csv")
    adjudication_decisions = read_csv_dicts(out_dir / "adjudication" / "decisions.csv")
    scope_note = analysis_scope_note(out_dir)
    body = "\n".join(report_charts(
        markers=markers,
        weekly=weekly,
        weekly_answer=weekly_answer,
        weekly_answer_syntax=weekly_answer_syntax,
        weekly_answer_model=weekly_answer_model,
        prompt_contract_summary_rows=prompt_contract_summary_rows,
        backend_rejection_summary_rows=backend_rejection_summary_rows,
        weekly_process_step_shape=weekly_process_step_shape,
        weekly_process_step_shape_model=weekly_process_step_shape_model,
        weekly_step_6_shape=weekly_step_6_shape,
        weekly_step_6_shape_model=weekly_step_6_shape_model,
        compliance_export_summary_rows=compliance_export_summary_rows,
        weekly_raw_change_status_quality=weekly_raw_change_status_quality,
        raw_change_status_summary_rows=raw_change_status_summary_rows,
        weekly_change_status_quality=weekly_change_status_quality,
        weekly_change_status_hierarchy=weekly_change_status_hierarchy,
        weekly_bureaucracy_cost_quality=weekly_bureaucracy_cost_quality,
        weekly_structure_pairs=weekly_structure_pairs,
        weekly_cost_variance_groups=weekly_cost_variance_groups,
        weekly_case_count_candidates=weekly_case_count_candidates,
        weekly_retry=weekly_retry,
        weekly_session_retry=weekly_session_retry,
        retry_summary=retry_summary,
        weekly_retry_causes=weekly_retry_causes,
        retry_cause_summary_rows=retry_cause_summary_rows,
        cost_case_points=cost_case_points,
        weekly_issue_detail=weekly_issue_detail,
        issue_02_wording_summary_rows=issue_02_wording_summary_rows,
        adjudication_decisions=adjudication_decisions,
    ))
    page = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Historical CCC Quality Report</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; color: #172033; }}
    h1 {{ margin-bottom: 4px; }}
    .report-section > h2 {{ margin-top: 42px; border-top: 1px solid #d9dee7; padding-top: 22px; }}
    .chart h2 {{ margin: 0 0 8px; border: 0; padding: 0; font-size: 20px; }}
    .section-intro {{ max-width: 980px; color: #475467; font-size: 14px; line-height: 1.45; margin-top: -4px; }}
    .chart {{ margin: 28px 0 40px; }}
    .compact {{ margin-top: 8px; }}
    .chart-note {{ max-width: 980px; margin: 0 0 12px; color: #475467; font-size: 13px; line-height: 1.45; }}
    .overview {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; max-width: 980px; margin: 18px 0 26px; }}
    .metric {{ border: 1px solid #d9dee7; padding: 12px; background: #fff; }}
    .metric-title {{ color: #475467; font-size: 12px; margin-bottom: 6px; }}
    .metric-value {{ font-size: 24px; font-weight: 650; }}
    .metric-note {{ color: #475467; font-size: 12px; line-height: 1.35; margin-top: 6px; }}
    details {{ max-width: 1120px; border-top: 1px solid #e4e7ec; padding: 16px 0; }}
    summary {{ cursor: pointer; font-weight: 650; font-size: 16px; }}
    .details-note {{ max-width: 980px; color: #475467; font-size: 13px; line-height: 1.45; margin: 8px 0 18px; }}
    .legend {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 8px 0 12px; font-size: 12px; }}
    .legend span {{ display: inline-flex; align-items: center; gap: 4px; }}
    .swatch {{ display: inline-block; width: 10px; height: 10px; margin-right: 5px; vertical-align: -1px; }}
    .dr-outline-swatch {{ display: inline-block; width: 10px; height: 10px; border: 2px solid #000; background: #fff; margin-right: 5px; vertical-align: -2px; }}
    .shape-icon {{ width: 18px; height: 14px; vertical-align: -2px; }}
    .subplots {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 18px 22px; align-items: start; }}
    .subplot {{ border: 1px solid #d9dee7; padding: 10px 10px 6px; background: #fff; }}
    .subplot h3 {{ font-size: 13px; margin: 0 0 6px; font-weight: 600; }}
    details h3 {{ margin-top: 18px; }}
    table {{ border-collapse: collapse; font-size: 13px; }}
    th, td {{ border: 1px solid #d9dee7; padding: 6px 8px; text-align: left; }}
    th {{ background: #f5f7fb; }}
  </style>
</head>
<body>
  <h1>Historical CCC Quality Report</h1>
  <p>Deterministic analysis of historical CCC sessions. Missing later workflow steps are not bad by default.</p>
  {scope_note}
  {body}
</body>
</html>
"""
    (out_dir / "visuals" / "index.html").write_text(page, encoding="utf-8")

def report_charts(
    *,
    markers: list[dict[str, Any]],
    weekly: list[dict[str, Any]],
    weekly_answer: list[dict[str, Any]],
    weekly_answer_syntax: list[dict[str, Any]],
    weekly_answer_model: list[dict[str, Any]],
    prompt_contract_summary_rows: list[dict[str, Any]],
    backend_rejection_summary_rows: list[dict[str, Any]],
    weekly_process_step_shape: list[dict[str, Any]],
    weekly_process_step_shape_model: list[dict[str, Any]],
    weekly_step_6_shape: list[dict[str, Any]],
    weekly_step_6_shape_model: list[dict[str, Any]],
    compliance_export_summary_rows: list[dict[str, Any]],
    weekly_raw_change_status_quality: list[dict[str, Any]],
    raw_change_status_summary_rows: list[dict[str, Any]],
    weekly_change_status_quality: list[dict[str, Any]],
    weekly_change_status_hierarchy: list[dict[str, Any]],
    weekly_bureaucracy_cost_quality: list[dict[str, Any]],
    weekly_structure_pairs: list[dict[str, Any]],
    weekly_cost_variance_groups: list[dict[str, Any]],
    weekly_case_count_candidates: list[dict[str, Any]],
    weekly_retry: list[dict[str, Any]],
    weekly_session_retry: list[dict[str, Any]],
    retry_summary: list[dict[str, Any]],
    weekly_retry_causes: list[dict[str, Any]],
    retry_cause_summary_rows: list[dict[str, Any]],
    cost_case_points: list[dict[str, Any]],
    weekly_issue_detail: list[dict[str, Any]],
    issue_02_wording_summary_rows: list[dict[str, Any]],
    adjudication_decisions: list[dict[str, Any]],
) -> list[str]:
    issue_chart_args = (
        weekly_issue_detail,
        weekly_answer,
        weekly_change_status_quality,
        weekly_bureaucracy_cost_quality,
        weekly_structure_pairs,
        weekly_cost_variance_groups,
        weekly_case_count_candidates,
    )
    sections = [
        report_section(
            "1. Overall App Health",
            "Start here. This section shows whether scoped sessions are becoming more or less usable over time.",
            [
                dashboard_overview_cards(weekly, weekly_answer, weekly_session_retry),
                stacked_bar_svg(
                    "Weekly Session Outcome",
                    (
                        "Each bar is one ISO week based on session creation date. Green means the available evidence "
                        "contains no concrete quality finding; it does not require the session to have reached final cost. "
                        "Red means at least one hard failure was observed, such as unusable JSON, status/value mismatch, "
                        "or addressee work despite zero applicable regulations. Blue means diagnostic instability only. "
                        "Grey means too little evidence to judge. Missing later workflow steps alone are not treated as bad."
                    ),
                    weekly,
                    "week",
                    [
                        ("good_sessions", "#2ca25f", "good"),
                        ("bad_sessions", "#de2d26", "hard failure"),
                        ("diagnostic_only_sessions", "#3182bd", "diagnostic only"),
                        ("unknown_or_incomplete", "#bdbdbd", "unknown/incomplete"),
                    ],
                    y_label="sessions",
                ),
            ],
        ),
        report_section(
            "2. Raw LLM Output Quality",
            "These charts isolate model/provider/prompt-format behavior before deeper legal interpretation.",
            [
                stacked_bar_svg(
                    "Weekly Raw Answer JSON Quality",
                    (
                        "Each bar is one ISO week based on LLM answer creation time. This is the primary model/output "
                        "format chart: it separates usable JSON from wrong envelopes, empty payloads, truncation, invalid "
                        "JSON, and answers with no JSON object at all. Use this to judge whether output-format reliability "
                        "is improving or deteriorating."
                    ),
                    weekly_answer,
                    "week",
                    json_quality_series(),
                    y_label="answers",
                ),
                small_multiples_stacked_bar_svg(
                    "Raw Answer JSON Quality By Model",
                    (
                        "The same JSON-quality classification split by model. This prevents model adoption changes "
                        "from being mistaken for quality changes in the overall timeline."
                    ),
                    weekly_answer_model,
                    "model",
                    "week",
                    json_quality_series(),
                    y_label="answers",
                ),
                stacked_bar_svg(
                    "Tätigkeiten Answer Shape",
                    (
                        "Only `process_step_analysis` answers are included. The expected shape is "
                        "a flat top-level `fallgruppen` array whose objects contain `taetigkeiten`. Legacy nested "
                        "`prozesse -> fallgruppen -> taetigkeiten` remains visible separately for older sessions. "
                        "This checks the raw answer shape only; missing or duplicate IDs are still shown through "
                        "the backend rejection summary because the backend owns completeness validation."
                    ),
                    weekly_process_step_shape,
                    "week",
                    process_step_shape_series(),
                    y_label="answers",
                ),
                small_multiples_stacked_bar_svg(
                    "Step 6 Answer Shape By Prompt",
                    (
                        "`cases_calculation` and `effort_calculation` should now use the same flat top-level "
                        "`fallgruppen` envelope. This diagnostic shows whether any model still returns legacy "
                        "nested `prozesse` or structurally empty metric answers. It does not decide whether the "
                        "individual case numbers or effort values are legally plausible."
                    ),
                    weekly_step_6_shape,
                    "prompt_id",
                    "week",
                    step_6_shape_series(),
                    y_label="answers",
                ),
                small_multiples_stacked_bar_svg(
                    "Step 6 Answer Shape By Model",
                    (
                        "The same Step 6 shape diagnostic split by model. This helps detect whether a specific "
                        "model returns legacy nested or empty metric payloads while others follow the flat contract."
                    ),
                    weekly_step_6_shape_model,
                    "model",
                    "week",
                    step_6_shape_series(),
                    y_label="answers",
                ),
            ],
        ),
        report_section(
            "3. Retry Pressure",
            "These charts show whether users have to rerun workflow steps more often, and where those retries come from.",
            [
                stacked_bar_svg(
                    "Weekly Sessions By Retry Need",
                    (
                        "Each bar is sessions by creation week. A retry is an extra non-rollback execution round before "
                        "the same workflow/addressee episode reaches `session_updated`. Undo/reset starts a fresh episode "
                        "and does not inflate retry counts."
                    ),
                    weekly_session_retry,
                    "week",
                    session_retry_category_series(),
                    y_label="sessions",
                ),
                stacked_bar_svg(
                    "Weekly Average Retry Rounds Per Session",
                    (
                        "Zero is ideal. The stacked height is the mean number of extra execution rounds per session. "
                        "Colors are additive contributions from step 5, step 6, and earlier prompt-backed steps; they "
                        "are not percentages. This is retry pressure within a session: automatic retries or manual "
                        "reruns needed before progress succeeded. It is separate from repeated-run stability below."
                    ),
                    weekly_session_retry,
                    "week",
                    average_session_retry_series(),
                    y_label="avg extra retry rounds/session",
                ),
                small_multiples_stacked_bar_svg(
                    "Retry Cause Groups By Workflow Step",
                    (
                        "Failed/retried episodes are grouped by inferred cause, split by workflow step. This is the "
                        "most useful retry diagnostic because step-5 structure failures and step-6 value/provider failures "
                        "need different fixes."
                    ),
                    weekly_retry_causes,
                    "step_label",
                    "week",
                    retry_cause_series(),
                    y_label="workflow/addressee episodes",
                ),
            ],
        ),
        report_section(
            "4. Workflow Correctness",
            "These are app-level correctness checks where a deterministic rule can often identify a concrete problem.",
            [
                issue_detail_chart("issue_02_unnecessary_addressee_steps", *issue_chart_args),
                issue_detail_chart("issue_04_change_status_inconsistency", *issue_chart_args),
                issue_detail_chart("issue_08_bureaucracy_cost", *issue_chart_args),
            ],
        ),
        report_section(
            "5. Repeated-Run Stability",
            (
                "These views compare separate completed sessions with the same law pair, model, and Deep Research "
                "mode. They need at least two comparable sessions in that exact group; one-off matrix runs can "
                "therefore legitimately show no data here. They show spread and drift, but do not decide which "
                "run is legally right."
            ),
            [
                scatter_svg(
                    "Final Cost Scatter Over Time",
                    (
                        "Each point is one session with a final cost. Color identifies model and shape identifies law pair. "
                        "A black outline marks sessions where Deep Research case metrics were enabled. Use this to "
                        "spot unstable cost estimates, outliers, and model/law-pair clusters over time."
                    ),
                    cost_case_points,
                    "total_cost",
                    "final cost",
                    log_scale=True,
                ),
                scatter_svg(
                    "Proposed Case Count Scatter Over Time",
                    (
                        "Each point is one session with persisted proposed case counts summed across case groups. "
                        "A black outline marks Deep Research sessions. Compare this with final cost: if both move "
                        "together, variance is likely driven by case-count assumptions rather than only legal "
                        "decomposition."
                    ),
                    cost_case_points,
                    "proposed_case_total",
                    "proposed cases",
                    log_scale=True,
                ),
            ],
        ),
        report_section(
            "Appendix",
            "Detailed supporting diagnostics. These sections are collapsed by default so the main report stays readable.",
            [
                details_section("Feature Markers", "Dates and code changes used as visual context.", [render_markers(markers)]),
                details_section("Reading Guide", "Definitions for report labels and diagnostic terms.", [dashboard_glossary()]),
                details_section("JSON Syntax And Contract Details", "Lower-level JSON diagnostics kept out of the main flow.", [
                    stacked_bar_svg(
                        "Weekly Raw Answer JSON Syntax Quality",
                        (
                            "This separates pure JSON syntax/completeness from schema shape. A response can parse as "
                            "JSON but still miss the required top-level contract; those contract failures appear in "
                            "the main JSON-quality chart."
                        ),
                        weekly_answer_syntax,
                        "week",
                        json_syntax_series(),
                        y_label="answers",
                    ),
                    json_quality_explanation_table(),
                    prompt_contract_summary_table(prompt_contract_summary_rows),
                    backend_rejection_summary_table(backend_rejection_summary_rows),
                    compliance_export_summary_table(compliance_export_summary_rows),
                ]),
                details_section("Raw Change-Status Output", "Whether structural prompts explicitly returned a usable lifecycle status before persistence and value checks.", [
                    stacked_bar_svg(
                        "Weekly Raw Change-Status Output",
                        (
                            "This scans raw `process_compilation`, `case_group_development`, and "
                            "`process_step_analysis` answers for the actual status fields emitted by the model. "
                            "Green means an expected value such as `eingefuehrt`, `abgeschafft`, `geaendert`, or "
                            "`unveraendert` was present. Grey means the entity had no status field. Red means a "
                            "status was present but outside the expected vocabulary. This helps distinguish missing "
                            "model output from later persisted status/value inconsistencies."
                        ),
                        weekly_raw_change_status_quality,
                        "week",
                        raw_change_status_series(),
                        y_label="raw entities",
                    ),
                    raw_change_status_summary_table(raw_change_status_summary_rows),
                ]),
                details_section("Addressee Wording Evidence", "Exact heuristic phrases behind the 'nothing to do' addressee review.", [
                    issue_02_wording_summary_table(issue_02_wording_summary_rows),
                ]),
                details_section("Retry Episode Details", "Granular retry-volume charts and summary tables.", [
                    stacked_bar_svg(
                        "Workflow/Addressee Episodes Needing Retry Before Success",
                        retry_episode_explanation(),
                        retry_pressure_chart_rows(weekly_retry, "succeeded_after_retry_units", include_total=True),
                        "week",
                        retry_step_series(),
                        y_label="workflow/addressee episodes",
                    ),
                    stacked_bar_svg(
                        "Retry Rounds Before Success By Workflow Step",
                        (
                            "This uses the same episode definition as the previous chart, but counts volume rather "
                            "than episodes. One episode that fails twice and then succeeds contributes 1 episode to "
                            "the previous chart but 2 retry rounds here."
                        ),
                        retry_pressure_chart_rows(weekly_retry, "total_retry_rounds_to_success", include_total=False),
                        "week",
                        retry_step_series(),
                        y_label="retry rounds",
                    ),
                    retry_pressure_summary_table(retry_summary),
                    retry_cause_summary_table(retry_cause_summary_rows),
                ]),
                details_section("Additional Workflow Diagnostics", "Useful checks that are too detailed for the main story.", [
                    stacked_bar_svg(
                        "Change-Status Hierarchy Consistency",
                        (
                            "Persisted parent-child lifecycle consistency. This complements the main status/value chart; "
                            "for example, an abolished process whose child steps are marked changed appears here."
                        ),
                        weekly_change_status_hierarchy,
                        "week",
                        change_status_hierarchy_series(),
                        y_label="hierarchy checks",
                    ),
                    issue_detail_chart("issue_01_duplicate_fallgruppen", *issue_chart_args),
                ]),
                details_section("Repeated-Run Threshold Diagnostics", "Threshold-count views behind the stability scatter plots.", [
                    issue_detail_chart("issue_05_structure_consistency", *issue_chart_args),
                    issue_detail_chart("issue_06_cost_variance", *issue_chart_args),
                    issue_detail_chart("issue_07_case_count_driven_variance", *issue_chart_args),
                ]),
                details_section("Model-Specific Tätigkeiten Shape", "Use only when the main Tätigkeiten chart suggests a model-specific format issue.", [
                    small_multiples_stacked_bar_svg(
                        "Tätigkeiten Answer Shape By Model",
                        "The process-step answer-shape diagnostic split by model.",
                        weekly_process_step_shape_model,
                        "model",
                        "week",
                        process_step_shape_series(),
                        y_label="answers",
                    ),
                ]),
                details_section("Adjudication", "Optional review-packet adjudication results. Deterministic rules do not replace human/legal review.", [
                    adjudication_summary_chart(adjudication_decisions),
                ]),
            ],
        ),
    ]
    return sections

def report_section(title: str, intro: str, parts: list[str]) -> str:
    return (
        f"<section class='report-section'><h2>{html.escape(title)}</h2>"
        f"<p class='section-intro'>{html.escape(intro)}</p>"
        + "\n".join(parts)
        + "</section>"
    )

def details_section(title: str, intro: str, parts: list[str]) -> str:
    return (
        f"<details><summary>{html.escape(title)}</summary>"
        f"<p class='details-note'>{html.escape(intro)}</p>"
        + "\n".join(parts)
        + "</details>"
    )

def dashboard_overview_cards(
    weekly: list[dict[str, Any]],
    weekly_answer: list[dict[str, Any]],
    weekly_session_retry: list[dict[str, Any]],
) -> str:
    latest_week = latest_row(weekly, "week")
    previous_week = previous_row(weekly, "week")
    latest_json = latest_row(weekly_answer, "week")
    previous_json = previous_row(weekly_answer, "week")
    latest_retry = latest_row(weekly_session_retry, "week")
    previous_retry = previous_row(weekly_session_retry, "week")
    total_sessions = sum(num(row.get("total_sessions")) for row in weekly)
    latest_label = str((latest_week or {}).get("week") or "unknown")
    cards = [
        metric_card(
            "Scoped sessions",
            format_tick(total_sessions),
            "after law-pair filtering",
        ),
        metric_card(
            f"Hard-failure sessions in {axis_label(latest_label)}",
            percent(rate(latest_week, "bad_sessions", "total_sessions")),
            ratio_trend_note(latest_week, "bad_sessions", "total_sessions", previous_week, lower_is_better=True),
        ),
        metric_card(
            f"JSON issue rate in {axis_label(str((latest_json or {}).get('week') or latest_label))}",
            percent(json_issue_rate(latest_json)),
            json_ratio_trend_note(latest_json, previous_json),
        ),
        metric_card(
            f"Retrying sessions in {axis_label(str((latest_retry or {}).get('week') or latest_label))}",
            percent(rate(latest_retry, "sessions_with_any_retry", "total_sessions")),
            ratio_trend_note(latest_retry, "sessions_with_any_retry", "total_sessions", previous_retry, lower_is_better=True),
        ),
        metric_card(
            "Latest avg retry rounds/session",
            compact_number(num((latest_retry or {}).get("avg_retry_rounds_per_session"))),
            "0 means no repeated execution rounds",
        ),
    ]
    return "<section class='overview' aria-label='Overview metrics'>" + "".join(cards) + "</section>"

def metric_card(title: str, value: str, note: str) -> str:
    return (
        "<div class='metric'>"
        f"<div class='metric-title'>{html.escape(title)}</div>"
        f"<div class='metric-value'>{html.escape(value)}</div>"
        f"<div class='metric-note'>{html.escape(note)}</div>"
        "</div>"
    )

def latest_row(rows: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    return sorted(rows, key=lambda row: str(row.get(key) or ""))[-1] if rows else None

def previous_row(rows: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    ordered = sorted(rows, key=lambda row: str(row.get(key) or ""))
    return ordered[-2] if len(ordered) >= 2 else None

def rate(row: dict[str, Any] | None, numerator: str, denominator: str) -> float | None:
    if not row:
        return None
    den = num(row.get(denominator))
    return num(row.get(numerator)) / den if den else None

def json_issue_rate(row: dict[str, Any] | None) -> float | None:
    if not row:
        return None
    total = num(row.get("total_answers"))
    if not total:
        return None
    return (total - num(row.get("valid_json"))) / total

def percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.0f}%"

def trend_note(current: float | None, previous: float | None, lower_is_better: bool) -> str:
    if current is None or previous is None:
        return "no prior week comparison"
    delta = current - previous
    if abs(delta) < 0.005:
        return "roughly unchanged vs previous week"
    improved = delta < 0 if lower_is_better else delta > 0
    direction = "improved" if improved else "worsened"
    return f"{direction} by {abs(delta) * 100:.0f} percentage points vs previous week"

def ratio_trend_note(
    current_row: dict[str, Any] | None,
    numerator: str,
    denominator: str,
    previous_row: dict[str, Any] | None,
    lower_is_better: bool,
) -> str:
    if not current_row:
        return "no current-week data"
    shown = f"{format_tick(num(current_row.get(numerator)))}/{format_tick(num(current_row.get(denominator)))}"
    trend = trend_note(
        rate(current_row, numerator, denominator),
        rate(previous_row, numerator, denominator),
        lower_is_better=lower_is_better,
    )
    return f"{shown}; {trend}"

def json_ratio_trend_note(current_row: dict[str, Any] | None, previous_row: dict[str, Any] | None) -> str:
    if not current_row:
        return "no current-week data"
    total = num(current_row.get("total_answers"))
    issues = total - num(current_row.get("valid_json"))
    return f"{format_tick(issues)}/{format_tick(total)} answers; {trend_note(json_issue_rate(current_row), json_issue_rate(previous_row), lower_is_better=True)}"

def retry_episode_explanation() -> str:
    return (
        "An episode is one attempted unit of workflow progress within a session: one global step, or one "
        "norm-addressee-specific step. In a complete session where administration, business, and citizens all "
        "apply, there are 14 possible episodes: 2 global episodes (summary and regulations) plus 4 addressee-"
        "specific workflow steps times 3 addressees (processes, case groups, Taetigkeiten, and effort for "
        "administration/business/citizens). Step 6 still counts as one episode per addressee, although each "
        "execution round contains two prompts: `cases_calculation` and `effort_calculation`. A label such as "
        "14/17 means 14 observed workflow/addressee episodes needed a retry before success, out of 17 observed "
        "prompt-backed episodes that week."
    )

def analysis_scope_note(out_dir: Path) -> str:
    rows = read_csv_dicts(out_dir / "extracted" / "analysis_scope.csv")
    if not rows:
        return (
            "<p class='chart-note'><strong>Analysis scope:</strong> included law pairs are "
            "1-&gt;2 and 9-&gt;10 (e-sports), 3-&gt;4 and 7-&gt;8 (arbeitstagepauschale), and "
            "5-&gt;6 and 11-&gt;12 (491 bgb). Reversed, missing-law, and ad-hoc test pairs are excluded.</p>"
        )
    row = rows[0]
    return (
        "<p class='chart-note'><strong>Analysis scope:</strong> included law pairs are "
        "1-&gt;2 and 9-&gt;10 (e-sports), 3-&gt;4 and 7-&gt;8 (arbeitstagepauschale), and "
        "5-&gt;6 and 11-&gt;12 (491 bgb). "
        f"Included sessions: {html.escape(str(row.get('included_session_count') or ''))}; "
        f"excluded sessions: {html.escape(str(row.get('excluded_session_count') or ''))}.</p>"
    )

def color_for_issue(issue_id: str) -> str:
    palette = {
        "issue_01_duplicate_fallgruppen": "#e6550d",
        "issue_02_unnecessary_addressee_steps": "#3182bd",
        "issue_03_json_truncation": "#de2d26",
        "issue_04_change_status_inconsistency": "#756bb1",
        "issue_05_structure_consistency": "#31a354",
        "issue_06_cost_variance": "#636363",
        "issue_07_case_count_driven_variance": "#fd8d3c",
        "issue_08_bureaucracy_cost": "#6baed6",
        "issue_09_compliance_export_quality": "#2ca25f",
    }
    return palette.get(issue_id, "#969696")

def readable_issue_label(issue_id: str) -> str:
    labels = {
        "issue_01_duplicate_fallgruppen": "Duplicate case groups",
        "issue_02_unnecessary_addressee_steps": "Addressee applicability",
        "issue_03_json_truncation": "JSON quality",
        "issue_04_change_status_inconsistency": "Change status",
        "issue_05_structure_consistency": "Repeated-run structure drift",
        "issue_06_cost_variance": "Cost variance",
        "issue_07_case_count_driven_variance": "Case-count variance",
        "issue_08_bureaucracy_cost": "Bureaucracy cost split",
        "issue_09_compliance_export_quality": "Compliance export quality",
    }
    return labels.get(issue_id, issue_id)

def json_quality_series() -> list[tuple[str, str, str]]:
    return [
        ("valid_json", "#009e73", "valid JSON"),
        ("wrong_top_level_key", "#0072b2", "root contract mismatch"),
        ("empty_or_invalid_top_level", "#e69f00", "empty/missing payload"),
        ("near_complete_missing_closer", "#f0e442", "missing final closer"),
        ("hard_mid_content_truncation", "#d55e00", "mid-content truncation"),
        ("invalid_json", "#cc79a7", "invalid JSON"),
        ("non_json_prose", "#4d4d4d", "no JSON object found"),
    ]

def dashboard_glossary() -> str:
    rows = [
        ("Green session", "A session with some usable evidence and no concrete finding in the completed/available parts. It need not have reached final costs."),
        ("Status/value mismatch", "`eingefuehrt`, `abgeschafft`, or `geaendert` contradicts current/proposed values, e.g. abolished but proposed value remains positive."),
        ("Retry pressure", "Extra execution rounds inside one session before a step/addressee succeeds. This can come from automatic retry or from pressing a step again after a failed attempt."),
        ("Repeated-run structure drift", "Separate sessions with the same law pair, model, and Deep Research mode were run more than once, and their persisted structure fingerprints differ. The suite builds normalized sets for regulations, processes, case groups, and generated Tätigkeiten, computes Jaccard similarity for each layer, then averages the four layer scores. A pair is flagged when mean similarity is below 0.65; layer-specific buckets show which layer also fell below 0.65. It does not mean one button was clicked twice."),
        ("Cost variance", "Separate sessions with the same law pair, model, and Deep Research mode produced materially different final total costs; this is instability evidence, not automatic proof that one value is wrong."),
        ("Invalid JSON", "JSON-looking output that cannot be parsed and is not classified as near-complete missing closure or hard mid-content truncation."),
        ("Root contract mismatch", "The JSON parses, but the required payload key inferred from the prompt/schema is absent. This is separate from provider JSON object/schema mode."),
        ("No JSON object found", "No extractable `{...}` JSON object was found in the raw answer, so the response is prose/error text rather than malformed JSON."),
    ]
    body = "".join(
        "<tr>"
        f"<td>{html.escape(term)}</td>"
        f"<td>{html.escape(desc)}</td>"
        "</tr>"
        for term, desc in rows
    )
    return f"<section class='chart compact'><h3>Reading Guide</h3><table><tr><th>Term</th><th>Meaning</th></tr>{body}</table></section>"

def json_syntax_series() -> list[tuple[str, str, str]]:
    return [
        ("valid_json", "#009e73", "syntactically valid JSON"),
        ("near_complete_missing_closer", "#f0e442", "missing final closer"),
        ("hard_mid_content_truncation", "#d55e00", "mid-content truncation"),
        ("invalid_json", "#cc79a7", "invalid JSON"),
        ("non_json_prose", "#4d4d4d", "no JSON object found"),
    ]

def json_quality_explanation_table() -> str:
    descriptions = {
        "valid_json": "The answer parsed as JSON and contained the required top-level payload for that prompt.",
        "wrong_top_level_key": "The raw answer parsed as JSON, but the expected root payload key inferred from the prompt/schema was absent. This is the suite's raw-answer contract check, not the DB `state_reason`.",
        "empty_or_invalid_top_level": "The expected top-level key exists, but its value is empty or not a usable list/object. This is why `{\"prozesse\": []}` is not counted as a successful process answer.",
        "near_complete_missing_closer": "Appending only final brackets/braces repairs the JSON shape. This catches the common one- or two-character truncation case.",
        "hard_mid_content_truncation": "The answer appears to stop inside a string or needs more than final closers; this is stronger evidence of true truncation.",
        "invalid_json": "The answer starts like JSON but cannot be parsed or repaired by the near-complete closer rule.",
        "non_json_prose": "The raw LLM answer contained no extractable JSON object at all; often an error message, refusal, or plain-language response.",
    }
    body = "".join(
        "<tr>"
        f"<td><span class='swatch' style='background:{color}'></span>{html.escape(label)}</td>"
        f"<td>{html.escape(descriptions.get(key, ''))}</td>"
        "</tr>"
        for key, color, label in json_quality_series()
    )
    return f"<section class='chart compact'><h3>JSON Quality Legend</h3><table><tr><th>Legend</th><th>Meaning</th></tr>{body}</table></section>"

def prompt_contract_summary_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<section class='chart compact'><h3>Prompt Contract Summary</h3><p>No prompt contract rows.</p></section>"
    limited = rows[:24]
    body = "".join(
        "<tr>"
        f"<td>{html.escape(str(row.get('prompt_id') or ''))}</td>"
        f"<td>{html.escape(str(row.get('prompt_contract_kind') or ''))}</td>"
        f"<td>{html.escape(str(row.get('prompt_required_root_key') or ''))}</td>"
        f"<td>{format_tick(num(row.get('total_answers')))}</td>"
        f"<td>{format_tick(num(row.get('provider_response_format_metadata_rows')))}</td>"
        f"<td>{format_tick(num(row.get('wrong_top_level_key')))}</td>"
        f"<td>{format_tick(num(row.get('answer_matches_prompt_root')))}</td>"
        f"<td>{format_tick(num(row.get('current_checker_contract_mismatch')))}</td>"
        f"<td>{format_tick(num(row.get('accepted_wrong_top_level_key')))}</td>"
        f"<td>{format_tick(num(row.get('rejected_wrong_top_level_key')))}</td>"
        "</tr>"
        for row in limited
    )
    return (
        "<section class='chart compact'><h3>Prompt Contract Summary</h3>"
        "<p class='chart-note'>This table distinguishes the contract visible in the prompt from provider "
        "response-format metadata persisted on the answer. `provider_json_object` means metadata recorded "
        "a JSON-object response format; `prompt_level_json_schema` means the schema requirement was inferred "
        "from the prompt text. The accepted/rejected root-mismatch columns show whether historical DB state "
        "accepted a raw answer that the current contract checker would classify as missing the expected root key. "
        "`Current checker mismatch` is important for historical runs whose prompt asked for a different envelope "
        "than the current parser expects.</p>"
        "<table><tr><th>Prompt</th><th>Contract kind</th><th>Required root</th><th>Answers</th>"
        "<th>Provider metadata rows</th><th>Root mismatches</th><th>Answers matching prompt root</th>"
        "<th>Current checker mismatch</th><th>Accepted mismatches</th>"
        "<th>Rejected mismatches</th></tr>"
        f"{body}</table></section>"
    )

def backend_rejection_summary_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<section class='chart compact'><h3>Backend Rejection Summary</h3><p>No backend rejection rows.</p></section>"
    limited = rows[:24]
    body = "".join(
        "<tr>"
        f"<td>{html.escape(str(row.get('prompt_id') or ''))}</td>"
        f"<td>{html.escape(str(row.get('db_outcome') or ''))}</td>"
        f"<td>{html.escape(str(row.get('backend_rejection_group') or ''))}</td>"
        f"<td>{format_tick(num(row.get('count')))}</td>"
        f"<td>{html.escape(str(row.get('example_answer_ids') or ''))}</td>"
        f"<td>{html.escape(str(row.get('example_state_reason') or '')[:420])}</td>"
        "</tr>"
        for row in limited
    )
    return (
        "<section class='chart compact'><h3>Backend Rejection Summary</h3>"
        "<p class='chart-note'>This summarizes parser/session-update rejections recorded in `state_reason`. "
        "It replaces brittle prompt-text entity counts with the backend's own completeness and ID validation "
        "signals.</p>"
        "<table><tr><th>Prompt</th><th>DB outcome</th><th>Rejection group</th><th>Count</th>"
        "<th>Example answers</th><th>Example state_reason</th></tr>"
        f"{body}</table></section>"
    )

def compliance_export_summary_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<section class='chart compact'><h3>Compliance Export Quality</h3><p>No compliance export rows.</p></section>"
    limited = rows[:24]
    body = "".join(
        "<tr>"
        f"<td>{html.escape(str(row.get('model') or ''))}</td>"
        f"<td>{html.escape(str(row.get('quality_class') or ''))}</td>"
        f"<td>{format_tick(num(row.get('count')))}</td>"
        f"<td>{html.escape(str(row.get('example_answer_ids') or ''))}</td>"
        f"<td>{format_tick(num(row.get('median_text_length')))}</td>"
        f"<td>{format_tick(num(row.get('with_section_4_heading')))}</td>"
        f"<td>{format_tick(num(row.get('with_markdown_table')))}</td>"
        "</tr>"
        for row in limited
    )
    return (
        "<section class='chart compact'><h3>Compliance Export Quality</h3>"
        "<p class='chart-note'>Compliance text extraction is Markdown/prose, not JSON. This lightweight check "
        "keeps it out of raw JSON failure counts while still surfacing empty exports and obvious leaked prompt "
        "or JSON artefacts. It is a smoke test for renderable output shape, not a legal review of whether "
        "section 4 is substantively Leitfaden-compliant.</p>"
        "<table><tr><th>Model</th><th>Quality class</th><th>Count</th><th>Example answers</th>"
        "<th>Median length</th><th>With section 4 heading</th><th>With Markdown table</th></tr>"
        f"{body}</table></section>"
    )

def raw_change_status_summary_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<section class='chart compact'><h3>Raw Change-Status Output Summary</h3><p>No raw status entities.</p></section>"
    limited = rows[:30]
    body = "".join(
        "<tr>"
        f"<td>{html.escape(str(row.get('prompt_id') or ''))}</td>"
        f"<td>{html.escape(str(row.get('entity_type') or ''))}</td>"
        f"<td>{html.escape(str(row.get('status_bucket') or ''))}</td>"
        f"<td>{format_tick(num(row.get('count')))}</td>"
        f"<td>{html.escape(str(row.get('example_status_values') or ''))}</td>"
        f"<td>{html.escape(str(row.get('example_answer_ids') or ''))}</td>"
        "</tr>"
        for row in limited
    )
    return (
        "<section class='chart compact'><h3>Raw Change-Status Output Summary</h3>"
        "<p class='chart-note'>This table groups the raw model output before app normalization. "
        "If `missing` appears here, the model did not provide a lifecycle status for that raw entity. "
        "If `present_unrecognized` appears, the model did provide something, but it was outside the "
        "expected vocabulary and should be reviewed as prompt/model output quality.</p>"
        "<table><tr><th>Prompt</th><th>Entity</th><th>Status bucket</th><th>Count</th>"
        "<th>Example raw values</th><th>Example answers</th></tr>"
        f"{body}</table></section>"
    )

def issue_02_wording_summary_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<section class='chart compact'><h3>Issue 2 Nothing-To-Do Wordings</h3><p>No matched wording evidence.</p></section>"
    limited = rows[:18]
    body = "".join(
        "<tr>"
        f"<td>{html.escape(str(row.get('applicability_context') or ''))}</td>"
        f"<td>{html.escape(str(row.get('source_type') or ''))}</td>"
        f"<td>{html.escape(str(row.get('wording_bucket') or ''))}</td>"
        f"<td>{html.escape(str(row.get('example_match_path') or ''))}</td>"
        f"<td>{html.escape(str(row.get('matched_phrase') or ''))}</td>"
        f"<td>{format_tick(num(row.get('count')))}</td>"
        f"<td>{html.escape(str(row.get('example_sessions') or ''))}</td>"
        f"<td>{html.escape(str(row.get('example_excerpt') or '')[:360])}</td>"
        "</tr>"
        for row in limited
    )
    return (
        "<section class='chart compact'><h3>Issue 2 Nothing-To-Do Wordings</h3>"
        "<p class='chart-note'>This table lists exact heuristic phrase matches from raw answers and tiles. "
        "`entity_absence_wording` means wording such as 'keine Fallgruppen' or 'keine Taetigkeiten' appeared; "
        "it does not mean no prompt was issued. `metric_explanation_wording` means the phrase occurred inside "
        "case-count/metric explanations, which is weaker evidence for a 'nothing to do' conclusion. It is "
        "evidence for review, not a legal judgement. If the wording is too diverse, this is the place where "
        "an LLM adjudication step should replace or supplement deterministic matching.</p>"
        "<table><tr><th>Applicability</th><th>Source</th><th>Bucket</th><th>Example JSON path</th><th>Matched phrase</th>"
        "<th>Count</th><th>Example sessions</th><th>Example excerpt</th></tr>"
        f"{body}</table></section>"
    )

def adjudication_summary_chart(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return (
            "<section class='chart compact'><h3>Adjudication Results</h3>"
            "<p class='chart-note'>No adjudication decisions were found. Run `historical_quality.py adjudicate --mode rules` to populate this section.</p></section>"
        )
    buckets: dict[str, dict[str, Any]] = {}
    for row in rows:
        issue_id = str(row.get("issue_id") or "unknown")
        out = buckets.setdefault(issue_id, {"issue_id": issue_id})
        status = str(row.get("adjudication_status") or "unknown")
        decision = str(row.get("decision") or "")
        if status == "pending_review":
            key = "pending_review"
        elif decision == "quality_issue":
            key = "quality_issue"
        elif decision == "instability_signal":
            key = "instability_signal"
        elif decision == "historical_contract_mismatch":
            key = "historical_contract_mismatch"
        else:
            key = "reviewed_other"
        out[key] = num(out.get(key)) + 1
    chart_rows = [row for _key, row in sorted(buckets.items())]
    return stacked_bar_svg(
        "Adjudication Results By Issue",
        (
            "This summarizes the optional deterministic adjudication layer. Reviewed quality issues are clear "
            "machine-checkable problems. Instability signals are confirmed diagnostics, not legal decisions. "
            "Pending review means the packet still needs human or fixed-prompt LLM judgement."
        ),
        chart_rows,
        "issue_id",
        adjudication_series(),
        y_label="review packets",
        bottom_padding=96,
    )

def adjudication_series() -> list[tuple[str, str, str]]:
    return [
        ("quality_issue", "#de2d26", "reviewed: quality issue"),
        ("instability_signal", "#3182bd", "reviewed: instability signal"),
        ("historical_contract_mismatch", "#756bb1", "reviewed: historical contract mismatch"),
        ("reviewed_other", "#636363", "reviewed: other"),
        ("pending_review", "#bdbdbd", "pending review"),
    ]

def process_step_shape_series() -> list[tuple[str, str, str]]:
    return [
        ("expected_flat_fallgruppen", "#009e73", "expected flat groups"),
        ("expected_nested_prozesse", "#66c2a5", "legacy nested shape"),
        ("fallback_reachable_flat_fallgruppen", "#f0e442", "fallback-reachable flat groups"),
        ("prozesse_present_but_no_steps", "#e69f00", "prozesse present but no steps"),
        ("flat_fallgruppen_without_steps", "#8c6bb1", "flat groups without steps"),
        ("other_json_no_prozesse", "#0072b2", "other JSON without prozesse"),
        ("top_level_list", "#6baed6", "top-level list"),
        ("unparseable", "#cc79a7", "unparseable"),
    ]

def step_6_shape_series() -> list[tuple[str, str, str]]:
    return [
        ("expected_flat_fallgruppen", "#009e73", "expected flat groups"),
        ("legacy_nested_prozesse", "#66c2a5", "legacy nested shape"),
        ("flat_fallgruppen_without_metrics", "#8c6bb1", "flat groups without metrics"),
        ("prozesse_present_without_metrics", "#e69f00", "prozesse present without metrics"),
        ("other_json_no_fallgruppen", "#0072b2", "other JSON without fallgruppen"),
        ("top_level_list", "#6baed6", "top-level list"),
        ("unparseable", "#cc79a7", "unparseable"),
    ]

def raw_change_status_series() -> list[tuple[str, str, str]]:
    return [
        ("present_valid", "#2ca25f", "status present and valid"),
        ("missing", "#bdbdbd", "status missing"),
        ("present_unrecognized", "#de2d26", "status unrecognized"),
    ]

def retry_step_series() -> list[tuple[str, str, str]]:
    return [
        ("step_1_summary", "#66c2a5", "Step 1 summary"),
        ("step_2_regulations", "#3288bd", "Step 2 regulations"),
        ("step_3_processes", "#5e4fa2", "Step 3 processes"),
        ("step_4_case_groups", "#abdda4", "Step 4 case groups"),
        ("step_5_process_steps", "#f46d43", "Step 5 process steps"),
        ("step_6_effort", "#9e0142", "Step 6 effort"),
    ]

def session_retry_category_series() -> list[tuple[str, str, str]]:
    return [
        ("no_retry_sessions", "#2ca25f", "no retry"),
        ("other_step_retry_sessions", "#756bb1", "retry only before step 5"),
        ("step_5_retry_sessions", "#f46d43", "step 5 retry"),
        ("step_6_retry_sessions", "#9e0142", "step 6 retry"),
        ("step_5_and_6_retry_sessions", "#4d4d4d", "step 5 and 6 retry"),
    ]

def average_session_retry_series() -> list[tuple[str, str, str]]:
    return [
        ("avg_other_step_retry_rounds_per_session", "#756bb1", "other steps"),
        ("avg_step_5_retry_rounds_per_session", "#f46d43", "step 5"),
        ("avg_step_6_retry_rounds_per_session", "#9e0142", "step 6"),
    ]

def retry_pressure_chart_rows(rows: list[dict[str, Any]], value_key: str, include_total: bool) -> list[dict[str, Any]]:
    by_week: dict[str, dict[str, Any]] = {}
    for item in rows:
        week = str(item.get("week") or "unknown")
        step_key = str(item.get("step_key") or "unknown")
        row = by_week.setdefault(week, {"week": week})
        row[step_key] = num(row.get(step_key)) + num(item.get(value_key))
        if include_total:
            row["total_step_units"] = num(row.get("total_step_units")) + num(item.get("total_step_units"))
    return [row for _week, row in sorted(by_week.items())]

def retry_pressure_summary_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<section class='chart compact'><h3>Retry Pressure Summary</h3><p>No data.</p></section>"
    body = "".join(
        "<tr>"
        f"<td>{html.escape(str(row.get('step_label') or row.get('step_key') or ''))}</td>"
        f"<td>{format_tick(num(row.get('total_step_units')))}</td>"
        f"<td>{format_tick(num(row.get('succeeded_after_retry_units')))}</td>"
        f"<td>{format_tick(num(row.get('failed_without_success_units')))}</td>"
        f"<td>{format_tick(num(row.get('total_retry_rounds_to_success')))}</td>"
        f"<td>{format_tick(num(row.get('mean_retry_rounds_to_success')))}</td>"
        f"<td>{format_tick(num(row.get('max_retry_rounds_to_success')))}</td>"
        "</tr>"
        for row in rows
    )
    return (
        "<section class='chart compact'><h3>Retry Pressure Summary</h3>"
        "<p class='chart-note'>Counts are deterministic from raw `llm_answers`. "
        "`failed without success` means no non-rollback `active:session_updated` answer appeared in that episode.</p>"
        "<table><tr><th>Step</th><th>Episodes</th><th>Episodes with retry</th><th>Failed without success</th>"
        "<th>Total retry rounds</th><th>Mean retry rounds</th><th>Max retry rounds</th></tr>"
        f"{body}</table></section>"
    )

def retry_cause_series() -> list[tuple[str, str, str]]:
    return [
        ("root_contract_mismatch", "#0072b2", "root contract mismatch"),
        ("near_complete_json_truncation", "#f0e442", "near-complete JSON truncation"),
        ("hard_json_truncation", "#a63603", "hard JSON truncation"),
        ("invalid_json", "#cc79a7", "invalid JSON"),
        ("provider_or_query_failure", "#00a6d6", "provider/query failure"),
        ("case_group_id_integrity_mismatch", "#756bb1", "case-group id mismatch"),
        ("process_step_missing_expected_steps", "#e6550d", "missing expected steps"),
        ("process_step_no_steps_returned", "#fd8d3c", "no process steps returned"),
        ("case_group_metrics_missing", "#9e9ac8", "case metrics missing"),
        ("unknown_qualification_value", "#31a354", "unknown qualification value"),
        ("empty_required_payload", "#e69f00", "empty required payload"),
        ("cancelled_before_apply", "#6baed6", "cancelled before apply"),
        ("valid_json_but_db_validation_failed", "#636363", "valid JSON, DB rejected"),
        ("superseded_previous_attempt_unknown", "#bdbdbd", "superseded, cause unknown"),
        ("unclassified_invalid_attempt", "#969696", "unclassified invalid attempt"),
    ]

def retry_cause_chart_rows(rows: list[dict[str, Any]], include_total: bool) -> list[dict[str, Any]]:
    by_week: dict[str, dict[str, Any]] = {}
    cause_keys = {key for key, _color, _label in retry_cause_series()}
    for item in rows:
        week = str(item.get("week") or "unknown")
        row = by_week.setdefault(week, {"week": week})
        for key in cause_keys:
            row[key] = num(row.get(key)) + num(item.get(key))
        if include_total:
            row["total_step_units"] = num(row.get("total_step_units")) + num(item.get("total_step_units"))
    return [row for _week, row in sorted(by_week.items())]

def retry_cause_summary_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<section class='chart compact'><h3>Retry Cause Summary</h3><p>No data.</p></section>"
    labels = {key: label for key, _color, label in retry_cause_series()}
    body = "".join(
        "<tr>"
        f"<td>{html.escape(str(row.get('step_label') or row.get('step_key') or ''))}</td>"
        f"<td>{html.escape(labels.get(str(row.get('primary_retry_cause')), str(row.get('primary_retry_cause') or '')))}</td>"
        f"<td>{format_tick(num(row.get('unit_count')))}</td>"
        f"<td>{format_tick(num(row.get('succeeded_after_retry_units')))}</td>"
        f"<td>{format_tick(num(row.get('failed_without_success_units')))}</td>"
        f"<td>{format_tick(num(row.get('total_retry_rounds_to_success')))}</td>"
        f"<td>{html.escape(str(row.get('db_state_reason_groups') or ''))}</td>"
        f"<td>{html.escape(str(row.get('example_session_ids') or ''))}</td>"
        "</tr>"
        for row in rows
    )
    return (
        "<section class='chart compact'><h3>Retry Cause Summary</h3>"
        "<p class='chart-note'>Cause is inferred from failed raw answers before success when possible. "
        "The DB reason column is retained to show where the persisted symptom differs from the likely cause.</p>"
        "<table><tr><th>Step</th><th>Inferred cause</th><th>Episodes</th><th>Retried then succeeded</th>"
        "<th>Failed without success</th><th>Retry rounds</th><th>DB reason groups</th><th>Example sessions</th></tr>"
        f"{body}</table></section>"
    )

def change_status_hierarchy_series() -> list[tuple[str, str, str]]:
    return [
        ("consistent_hierarchy", "#2ca25f", "consistent parent-child status"),
        ("introduced_parent_has_case_group_with_other_status", "#756bb1", "introduced process, child group differs"),
        ("abolished_parent_has_case_group_with_other_status", "#e6550d", "abolished process, child group differs"),
        ("introduced_parent_has_process_step_with_other_status", "#9e9ac8", "introduced case group, child step differs"),
        ("abolished_parent_has_process_step_with_other_status", "#fd8d3c", "abolished case group, child step differs"),
    ]

def scatter_svg(
    title: str,
    description: str,
    rows: list[dict[str, Any]],
    y_key: str,
    y_label: str,
    log_scale: bool = False,
) -> str:
    points = [
        row for row in rows
        if parse_datetime(row.get("created_at")) is not None and safe_float(row.get(y_key)) is not None
    ]
    if not points:
        return f"<section class='chart'><h2>{html.escape(title)}</h2><p class='chart-note'>{html.escape(description)}</p><p>No data.</p></section>"
    points.sort(key=lambda row: parse_datetime(row.get("created_at")) or dt.datetime.min)
    width = 980
    height = 360
    left = 78
    right = 28
    top = 24
    bottom = 58
    chart_w = width - left - right
    chart_h = height - top - bottom
    times = [(parse_datetime(row.get("created_at")) or dt.datetime.min).timestamp() for row in points]
    min_t, max_t = min(times), max(times)
    raw_values = [safe_float(row.get(y_key)) or 0.0 for row in points]
    signed_log = log_scale and any(value < 0 for value in raw_values)
    values = [scatter_transform(value, log_scale, signed_log) for value in raw_values]
    min_v, max_v = min(values), max(values)
    if abs(max_v - min_v) < 1e-12:
        max_v = min_v + 1
    models = sorted({str(row.get("model") or "unknown") for row in points})
    law_pairs = sorted({str(row.get("law_pair") or "unknown") for row in points})
    law_groups = scatter_law_groups(law_pairs)
    law_group_shapes = {group: idx % 4 for idx, (group, _pairs) in enumerate(law_groups)}
    model_colors = scatter_model_colors(models)
    parts = [
        f"<section class='chart'><h2>{html.escape(title)}</h2>",
        f"<p class='chart-note'>{html.escape(description)}</p>",
        "<div class='legend'><span><strong>Model color:</strong></span>" + "".join(
            f"<span><span class='swatch' style='background:{model_colors[model]}'></span>{html.escape(model)}</span>"
            for model in models
        ) + "</div>",
        "<div class='legend'><span><strong>Law group shape:</strong></span>" + "".join(
            f"<span>{scatter_shape_icon(idx % 4)}{html.escape(group)} ({html.escape(', '.join(pairs))})</span>"
            for idx, (group, pairs) in enumerate(law_groups)
        ) + "</div>",
        "<div class='legend'><span><strong>Deep Research:</strong></span>"
        "<span><span class='dr-outline-swatch'></span>enabled</span></div>",
    ]
    svg = [f"<svg width='{width}' height='{height}' role='img' aria-label='{html.escape(title)}'>"]
    svg.append(
        f"<text x='14' y='{top + chart_h / 2:.1f}' font-size='11' text-anchor='middle' "
        f"fill='#475467' transform='rotate(-90 14,{top + chart_h / 2:.1f})'>{html.escape(y_label)}{' (signed log10)' if signed_log else ' (log10)' if log_scale else ''}</text>"
    )
    for idx in range(5):
        frac = idx / 4
        y = top + chart_h - frac * chart_h
        value = min_v + frac * (max_v - min_v)
        display = scatter_inverse(value, log_scale, signed_log)
        svg.append(f"<line x1='{left}' y1='{y:.1f}' x2='{width-right}' y2='{y:.1f}' stroke='{'#667085' if idx == 0 else '#e4e7ec'}'/>")
        svg.append(f"<text x='{left-8}' y='{y+4:.1f}' font-size='10' text-anchor='end' fill='#475467'>{html.escape(compact_number(display))}</text>")
    svg.append(f"<line x1='{left}' y1='{top}' x2='{left}' y2='{height-bottom}' stroke='#667085'/>")
    svg.append(f"<line x1='{left}' y1='{height-bottom}' x2='{width-right}' y2='{height-bottom}' stroke='#667085'/>")
    tick_count = min(8, len({row.get("week") for row in points}))
    weeks = sorted({str(row.get("week") or "unknown") for row in points})
    for idx, week in enumerate(weeks):
        if tick_count and idx % max(1, math.ceil(len(weeks) / tick_count)) != 0:
            continue
        week_points = [i for i, row in enumerate(points) if row.get("week") == week]
        if not week_points:
            continue
        x = point_x(sum(times[i] for i in week_points) / len(week_points), min_t, max_t, left, chart_w)
        svg.append(f"<text x='{x:.1f}' y='{height-28}' font-size='10' text-anchor='end' transform='rotate(-45 {x:.1f},{height-28})'>{html.escape(axis_label(week))}</text>")
    for row, timestamp, value, raw in zip(points, times, values, raw_values):
        x = point_x(timestamp, min_t, max_t, left, chart_w)
        y = top + chart_h - ((value - min_v) / (max_v - min_v) * chart_h)
        color = model_colors.get(str(row.get("model") or "unknown"), "#636363")
        law_pair = str(row.get("law_pair") or "unknown")
        law_group = law_pair_group(law_pair)
        shape_idx = law_group_shapes.get(law_group, 0)
        uses_deep_research = truthy(row.get("deep_research_enabled"))
        research_note = " | Deep Research" if uses_deep_research else ""
        title_text = f"session {row.get('session_id')} | {row.get('week')} | {row.get('model')} | law group {law_group} | law pair {law_pair}{research_note} | {y_label}: {raw:g}"
        svg.append(scatter_marker(x, y, color, shape_idx, title_text, outlined=uses_deep_research))
    svg.append("</svg>")
    parts.append("".join(svg))
    parts.append("<p class='chart-note'>Color identifies the model. Shape identifies the law group shown in the legend; the tooltip gives the exact law pair.</p>")
    parts.append("</section>")
    return "\n".join(parts)

def scatter_law_groups(law_pairs: list[str]) -> list[tuple[str, list[str]]]:
    preferred = ["e-sports", "arbeitstagepauschale", "491 bgb"]
    grouped: dict[str, list[str]] = {}
    for pair in law_pairs:
        grouped.setdefault(law_pair_group(pair), []).append(pair)
    ordered = [group for group in preferred if group in grouped]
    ordered.extend(sorted(group for group in grouped if group not in ordered))
    return [(group, sorted(grouped[group])) for group in ordered]

def law_pair_group(law_pair: str) -> str:
    return law_pair_label(law_pair)

def point_x(timestamp: float, min_t: float, max_t: float, left: int, chart_w: int) -> float:
    if abs(max_t - min_t) < 1e-12:
        return left + chart_w / 2
    return left + ((timestamp - min_t) / (max_t - min_t) * chart_w)

def scatter_transform(value: float, log_scale: bool, signed_log: bool) -> float:
    if not log_scale:
        return value
    if signed_log:
        if value == 0:
            return 0.0
        return math.copysign(math.log10(abs(value) + 1.0), value)
    return math.log10(max(value, 1.0))

def scatter_inverse(value: float, log_scale: bool, signed_log: bool) -> float:
    if not log_scale:
        return value
    if signed_log:
        if value == 0:
            return 0.0
        return math.copysign((10 ** abs(value)) - 1.0, value)
    return 10 ** value

def scatter_model_colors(models: list[str]) -> dict[str, str]:
    palette = ["#0072b2", "#d55e00", "#009e73", "#cc79a7", "#e69f00", "#5e4fa2", "#4d4d4d", "#56b4e9"]
    return {model: palette[idx % len(palette)] for idx, model in enumerate(models)}

def scatter_marker(
    x: float,
    y: float,
    color: str,
    shape_idx: int,
    title_text: str,
    *,
    outlined: bool = False,
) -> str:
    title = f"<title>{html.escape(title_text)}</title>"
    stroke = " stroke='#000' stroke-width='2.1'" if outlined else ""
    if shape_idx == 1:
        return f"<rect x='{x-4:.1f}' y='{y-4:.1f}' width='8' height='8' fill='{color}' opacity='0.82'{stroke}>{title}</rect>"
    if shape_idx == 2:
        points = f"{x:.1f},{y-5:.1f} {x-5:.1f},{y+4:.1f} {x+5:.1f},{y+4:.1f}"
        return f"<polygon points='{points}' fill='{color}' opacity='0.82'{stroke}>{title}</polygon>"
    if shape_idx == 3:
        points = f"{x:.1f},{y-5:.1f} {x+5:.1f},{y:.1f} {x:.1f},{y+5:.1f} {x-5:.1f},{y:.1f}"
        return f"<polygon points='{points}' fill='{color}' opacity='0.82'{stroke}>{title}</polygon>"
    return f"<circle cx='{x:.1f}' cy='{y:.1f}' r='4.2' fill='{color}' opacity='0.82'{stroke}>{title}</circle>"

def scatter_shape_icon(shape_idx: int) -> str:
    if shape_idx == 1:
        return "<svg class='shape-icon' viewBox='0 0 18 14' aria-hidden='true'><rect x='5' y='3' width='8' height='8' fill='none' stroke='#172033' stroke-width='1.8'/></svg>"
    if shape_idx == 2:
        return "<svg class='shape-icon' viewBox='0 0 18 14' aria-hidden='true'><polygon points='9,2.5 4,11 14,11' fill='none' stroke='#172033' stroke-width='1.8'/></svg>"
    if shape_idx == 3:
        return "<svg class='shape-icon' viewBox='0 0 18 14' aria-hidden='true'><polygon points='9,2 14,7 9,12 4,7' fill='none' stroke='#172033' stroke-width='1.8'/></svg>"
    return "<svg class='shape-icon' viewBox='0 0 18 14' aria-hidden='true'><circle cx='9' cy='7' r='4.3' fill='none' stroke='#172033' stroke-width='1.8'/></svg>"

def compact_number(value: float) -> str:
    sign = "-" if value < 0 else ""
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return f"{sign}{abs_value / 1_000_000:.1f}M"
    if abs_value >= 1_000:
        return f"{sign}{abs_value / 1_000:.1f}k"
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.2g}"

def issue_detail_charts(
    rows: list[dict[str, Any]],
    weekly_answer: list[dict[str, Any]] | None = None,
    weekly_change_status_quality: list[dict[str, Any]] | None = None,
    weekly_bureaucracy_cost_quality: list[dict[str, Any]] | None = None,
    weekly_structure_pairs: list[dict[str, Any]] | None = None,
    weekly_cost_variance_groups: list[dict[str, Any]] | None = None,
    weekly_case_count_candidates: list[dict[str, Any]] | None = None,
) -> list[str]:
    charts: list[str] = []
    for issue_id in ISSUES:
        charts.append(issue_detail_chart(
            issue_id,
            rows,
            weekly_answer,
            weekly_change_status_quality,
            weekly_bureaucracy_cost_quality,
            weekly_structure_pairs,
            weekly_cost_variance_groups,
            weekly_case_count_candidates,
        ))
    return charts

def issue_detail_chart(
    issue_id: str,
    rows: list[dict[str, Any]],
    weekly_answer: list[dict[str, Any]] | None = None,
    weekly_change_status_quality: list[dict[str, Any]] | None = None,
    weekly_bureaucracy_cost_quality: list[dict[str, Any]] | None = None,
    weekly_structure_pairs: list[dict[str, Any]] | None = None,
    weekly_cost_variance_groups: list[dict[str, Any]] | None = None,
    weekly_case_count_candidates: list[dict[str, Any]] | None = None,
) -> str:
    if issue_id == "issue_03_json_truncation" and weekly_answer is not None:
        issue_rows = merge_weekly_denominators(
            [row for row in rows if row.get("issue_id") == issue_id],
            weekly_answer,
            ("total_answers",),
        )
    elif issue_id == "issue_04_change_status_inconsistency" and weekly_change_status_quality is not None:
        issue_rows = weekly_change_status_quality
    elif issue_id == "issue_05_structure_consistency" and weekly_structure_pairs is not None:
        issue_rows = merge_weekly_denominators(
            [row for row in rows if row.get("issue_id") == issue_id],
            weekly_structure_pairs,
            ("total_structure_pairs",),
        )
    elif issue_id == "issue_06_cost_variance" and weekly_cost_variance_groups is not None:
        issue_rows = merge_weekly_denominators(
            [row for row in rows if row.get("issue_id") == issue_id],
            weekly_cost_variance_groups,
            ("total_cost_variance_groups",),
        )
    elif issue_id == "issue_07_case_count_driven_variance" and weekly_case_count_candidates is not None:
        issue_rows = merge_weekly_denominators(
            [row for row in rows if row.get("issue_id") == issue_id],
            weekly_case_count_candidates,
            ("total_case_count_candidates",),
        )
    elif issue_id == "issue_08_bureaucracy_cost" and weekly_bureaucracy_cost_quality is not None:
        issue_rows = weekly_bureaucracy_cost_quality
    else:
        issue_rows = [row for row in rows if row.get("issue_id") == issue_id]
    return stacked_bar_svg(
        f"{readable_issue_label(issue_id)} Detail",
        issue_detail_description(issue_id),
        issue_rows,
        "week",
        issue_detail_series(issue_id, issue_rows),
        y_label=issue_y_label(issue_id),
    )

def merge_weekly_denominators(
    issue_rows: list[dict[str, Any]],
    denominator_rows: list[dict[str, Any]],
    keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    by_week = {str(row.get("week") or "unknown"): row for row in issue_rows}
    for denom in denominator_rows:
        week = str(denom.get("week") or "unknown")
        row = by_week.setdefault(week, {"issue_id": denom.get("issue_id"), "week": week})
        for key in keys:
            if denom.get(key) not in (None, ""):
                row[key] = denom.get(key)
    return [row for _week, row in sorted(by_week.items())]

def issue_y_label(issue_id: str) -> str:
    return {
        "issue_01_duplicate_fallgruppen": "findings",
        "issue_02_unnecessary_addressee_steps": "findings",
        "issue_03_json_truncation": "answers",
        "issue_04_change_status_inconsistency": "checks",
        "issue_05_structure_consistency": "pairwise layer findings",
        "issue_06_cost_variance": "threshold findings",
        "issue_07_case_count_driven_variance": "candidate findings",
        "issue_08_bureaucracy_cost": "sessions",
        "issue_09_compliance_export_quality": "exports",
    }.get(issue_id, "count")

def issue_detail_series(issue_id: str, rows: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    configured = issue_detail_palette().get(issue_id, [])
    present = {
        key for row in rows for key, value in row.items()
        if not is_chart_helper_key(key) and num(value) > 0
    }
    series = [item for item in configured if item[0] in present or not rows]
    configured_keys = {item[0] for item in configured}
    extras = sorted(present - configured_keys)
    fallback_colors = ("#8c6bb1", "#41ab5d", "#969696", "#3182bd", "#e6550d")
    for idx, key in enumerate(extras):
        series.append((key, fallback_colors[idx % len(fallback_colors)], key.replace("_", " ")))
    return series

def issue_detail_palette() -> dict[str, list[tuple[str, str, str]]]:
    return {
        "issue_01_duplicate_fallgruppen": [
            ("raw_case_group_development", "#fd8d3c", "raw case-group answer duplicated a group"),
            ("case_group_to_step_handoff__single_upstream_group_multiple_downstream_refs", "#e6550d", "single upstream group became multiple step refs"),
            ("raw_process_step_analysis", "#a63603", "raw step answer duplicated group refs"),
            ("raw_process_step_analysis__same_id_multiple_names", "#756bb1", "same case-group id had multiple names"),
            ("raw_process_step_analysis__same_name_multiple_ids", "#9e9ac8", "same case-group name had multiple ids"),
            ("persisted_case_groups", "#636363", "duplicate persisted DB case groups"),
        ],
        "issue_02_unnecessary_addressee_steps": [
            ("no_applies_prompt_and_tile", "#de2d26", "prompt and tile despite zero applicable regulations"),
            ("no_applies_prompt_only_applied_no_counted_tile", "#fdae6b", "prompt applied but no counted tile"),
            ("no_applies_prompt_only_session_update_failed", "#756bb1", "prompt only, DB update failed"),
            ("no_applies_prompt_only_query_or_form_failure", "#cc79a7", "prompt only, query/form failure"),
            ("no_applies_prompt_only_reverted_or_superseded", "#969696", "prompt only, reverted/superseded"),
            ("no_applies_prompt_only_no_tile", "#bdbdbd", "prompt only, no tile"),
            ("missing_regulation_context_but_downstream_work", "#e69f00", "downstream work but regulation context missing"),
            ("no_applies_but_prompt_called", "#de2d26", "legacy: prompt called despite zero applicable regulations"),
            ("no_applies_but_tile_shown", "#fb6a4a", "legacy: tile shown despite zero applicable regulations"),
            ("applies_but_answer_says_not_applicable", "#3182bd", "raw downstream answer says not applicable"),
            ("applies_but_tile_says_not_applicable", "#6baed6", "tile says not applicable"),
            ("applies_but_answer_and_tile_say_not_applicable", "#08519c", "answer and tile say not applicable"),
        ],
        "issue_03_json_truncation": json_quality_series(),
        "issue_04_change_status_inconsistency": [
            ("consistent_change_status", "#2ca25f", "consistent status/value check"),
            ("introduced__introduced_but_current_positive", "#6a51a3", "introduced but current value positive"),
            ("introduced__introduced_but_current_positive_and_proposed_zero", "#9e9ac8", "introduced but looks abolished"),
            ("abolished__abolished_but_proposed_positive", "#e6550d", "abolished but proposed value positive"),
            ("changed__changed_but_values_equal", "#0072b2", "changed but values equal"),
        ],
        "issue_05_structure_consistency": [
            ("regulations_diverge", "#756bb1", "regulation set differs"),
            ("processes_diverge", "#3182bd", "process set differs"),
            ("case_groups_diverge", "#fd8d3c", "case-group set differs"),
            ("process_steps_diverge", "#de2d26", "step set differs"),
            ("mean_structure_similarity_below_threshold", "#636363", "mean similarity below threshold"),
        ],
        "issue_06_cost_variance": [
            ("high_coefficient_of_variation", "#636363", "coefficient of variation > 0.5"),
            ("max_min_ratio_above_2", "#de2d26", "max/min total cost ratio > 2"),
        ],
        "issue_07_case_count_driven_variance": [
            ("similar_structure_with_case_count_delta", "#e6550d", "similar structure, large case-count delta"),
        ],
        "issue_08_bureaucracy_cost": [
            ("raw_ip_persisted_bureaucracy_cost_nonzero", "#2ca25f", "raw IP persisted, bureaucracy cost nonzero"),
            ("raw_ip_not_persisted", "#756bb1", "raw IP flag present in LLM answer but not persisted"),
            ("persisted_ip_without_raw_flag", "#8c6bb1", "persisted IP without raw flag"),
            ("ip_present_bureaucracy_missing_or_zero", "#de2d26", "IP present but bureaucracy cost zero/missing"),
            ("suspicious_all_business_cost_marked_bureaucracy", "#fd8d3c", "nearly all business cost marked bureaucracy"),
            ("ip_present_no_business_cost_row", "#e69f00", "IP present but no business cost row"),
            ("ip_present_cost_not_evaluable", "#bdbdbd", "IP present but cost not evaluable"),
            ("ip_present_bureaucracy_cost_nonzero", "#6baed6", "IP persisted, bureaucracy cost nonzero"),
        ],
        "issue_09_compliance_export_quality": [
            ("expected_markdown", "#2ca25f", "expected Markdown"),
            ("markdown_needs_review", "#3182bd", "Markdown needs review"),
            ("leaked_prompt_or_json_artifact", "#de2d26", "leaked prompt/JSON artefact"),
            ("empty_export", "#636363", "empty export"),
        ],
    }

def issue_detail_description(issue_id: str) -> str:
    descriptions = {
        "issue_01_duplicate_fallgruppen": (
            "This is a case-group identity diagnostic. It can fire when the raw case-group answer repeats "
            "a normalized Fallgruppe, when a single upstream Fallgruppe is duplicated during step generation, "
            "or when duplicate groups are persisted. A flagged session is bad only if the duplicate changes "
            "the process/cost structure; harmless naming aliases may need review. Likely time drivers: flat "
            "step-5/step-6 skeletons were introduced specifically to reduce duplicate Fallgruppe chains."
        ),
        "issue_02_unnecessary_addressee_steps": (
            "This checks whether addressee-specific work was performed when applicability says it should not "
            "have been, and the inverse case where an addressee applies but downstream answers or tiles say "
            "there is nothing to do. The strongest bucket is prompt-and-tile despite zero applicable persisted "
            "regulations. Prompt-only buckets are split by whether the answer was applied, rejected by DB update, "
            "failed as a query/form issue, or was later reverted/superseded. Missing regulation context is shown "
            "separately because that is not the same as a clean zero-applicability finding. Likely time drivers: "
            "multiple norm addressees and atomic addressee execution increased the observable surface area."
        ),
        "issue_03_json_truncation": (
            "This repeats the JSON quality classification as an issue-specific plot. A structured prompt is "
            "flagged when the raw answer cannot be used as a complete schema-shaped response. This issue-detail "
            "chart shows only flagged failure categories; valid raw answers are omitted here and shown in the "
            "full `Weekly Raw Answer JSON Quality` chart above. When shown/total appears above a bar, the "
            "denominator is all raw LLM answers that week. Likely time drivers: response_format object mode, "
            "required envelopes, prompt-level schema text, and flat skeleton contracts."
        ),
        "issue_04_change_status_inconsistency": (
            "This splits all evaluable status/value checks by outcome, so the green segment shows cases where "
            "the status matched the current/proposed values and the colored segments show inconsistency types. "
            "The number above each bar is the total evaluable checks for that week; non-evaluable rows are kept "
            "in `weekly_change_status_quality.csv` but not plotted. Introduced should normally have no current "
            "burden, abolished should normally have no proposed burden, and changed should normally differ between "
            "current and proposed values. `Unveraendert` can be valid when the per-case activity is unchanged but "
            "case counts or frequencies change elsewhere; this chart is therefore a review signal for lifecycle "
            "labels, not final legal judgement. Likely time drivers: row-based effort/cost persistence and stricter "
            "parsing increased the number of evaluable persisted value/status combinations."
        ),
        "issue_05_structure_consistency": (
            "This is pairwise consistency for repeated runs with the same law pair, same model, and same Deep "
            "Research mode. If the batch only ran one session for each law/model/DR combination, this diagnostic "
            "will have no pair to compare. The later session is flagged when its persisted regulation/process/case-group/generated-Taetigkeit "
            "fingerprint has low similarity to an earlier run. Similarity is Jaccard overlap for each of "
            "the four persisted layers, averaged across layers; mean similarity below 0.65 is the threshold. "
            "Layer-specific buckets show which layer also fell below 0.65. It is evidence of instability, "
            "not proof that either session is legally wrong. The chart shows only divergent pairwise findings; "
            "similar/good repeated-run pairs are omitted. When shown/total appears above a bar, the denominator "
            "is all same-law-pair/same-model pair comparisons assigned to that week. Likely time drivers: "
            "prompt semantic changes such as recurring-only effort and addressee-specific rules can legitimately shift structures."
        ),
        "issue_06_cost_variance": (
            "This is repeated-run final-cost spread for the same law pair, model, and Deep Research mode. If the "
            "batch only ran one session for each law/model/DR combination, this diagnostic will have no variance "
            "group to compare. The thresholds are "
            "coefficient of variation above 0.5 or max/min total cost ratio above 2. It shows instability, "
            "not automatically a prompt failure. The chart shows only law-pair/model groups that crossed the "
            "variance thresholds; stable groups are omitted. When shown/total appears above a bar, the "
            "denominator is all repeated law-pair/model cost groups evaluable that week. Likely time drivers: "
            "case-count prompts, Deep Research case metrics, recurring-only effort, and step-6 retry/pair fixes."
        ),
        "issue_07_case_count_driven_variance": (
            "This narrows cost variance to cases where structures are similar but proposed case-count totals "
            "differ materially. That suggests the variance comes from assumptions about affected cases rather "
            "than different legal decomposition. It also needs repeated sessions with the same law pair, model, "
            "and Deep Research mode. The chart shows only flagged case-count-driven variance "
            "signals; unflagged comparisons are omitted. When shown/total appears above a bar, the denominator "
            "is all high-cost-variance groups checked for case-count attribution that week. Likely time drivers: "
            "Deep Research and changed case-count prompt contracts."
        ),
        "issue_08_bureaucracy_cost": (
            "This compares business information-obligation flags in the raw regulations answer with persisted "
            "regulation flags and the final business bureaucracy-cost row. Green means the raw IP flag survived "
            "persistence and a nonzero bureaucracy cost exists. Purple means the raw LLM answer had an IP flag "
            "that was lost before persistence. Red/orange buckets show persisted IP flags whose cost separation "
            "looks missing or suspicious. Bar labels use shown/total sessions checked, so omitted sessions are "
            "those without a plotted business-IP/cost-separation bucket. Likely time drivers: business IP flag "
            "cleanup/display and bureaucracy-cost binding changes."
        ),
        "issue_09_compliance_export_quality": (
            "This is a lightweight Markdown/prose export check. Compliance exports are not schema JSON, so they "
            "are excluded from raw JSON-quality failures. This issue only flags empty exports or obvious leaked "
            "prompt/JSON artefacts; heading/table presence is reported as supporting detail."
        ),
    }
    return descriptions.get(issue_id, "")

def is_chart_helper_key(key: str) -> bool:
    if key in {"issue_id", "week", "model"}:
        return True
    if key.startswith("total_"):
        return True
    return key in {
        "current_code_accept",
        "current_code_reject",
        "persisted_applied",
        "not_evaluable",
        "sessions_with_raw_business_ip",
        "sessions_with_persisted_business_ip",
    }

def stacked_bar_svg(
    title: str,
    description: str,
    rows: list[dict[str, Any]],
    x_key: str,
    series: list[tuple],
    y_label: str = "count",
    bottom_padding: int = 54,
) -> str:
    if not rows:
        return f"<section class='chart'><h2>{html.escape(title)}</h2><p class='chart-note'>{html.escape(description)}</p><p>No data.</p></section>"
    width = max(720, len(rows) * 54 + 160)
    height = 320
    left = 78
    bottom = bottom_padding
    top = 24
    chart_h = height - top - bottom
    bar_w = max(18, min(42, (width - left - 40) // max(len(rows), 1) - 8))
    items = normalize_series(series)
    item_names = {name for name, _color, _label in items}
    totals = [sum(num(row.get(name)) for name, _color, _label in items) for row in rows]
    ymax = max(totals) if totals else 1
    axis_max, ticks = chart_axis(ymax)
    parts = [
        f"<section class='chart'><h2>{html.escape(title)}</h2>",
        f"<p class='chart-note'>{html.escape(description)}</p>",
    ]
    parts.append("<div class='legend'>" + "".join(
        f"<span><span class='swatch' style='background:{color}'></span>{html.escape(legend_label_with_total(label, name, rows))}</span>"
        for name, color, label in items
    ) + "</div>")
    svg = [f"<svg width='{width}' height='{height}' role='img' aria-label='{html.escape(title)}'>"]
    svg.append(
        f"<text x='14' y='{top + chart_h / 2:.1f}' font-size='11' text-anchor='middle' "
        f"fill='#475467' transform='rotate(-90 14,{top + chart_h / 2:.1f})'>{html.escape(y_label)}</text>"
    )
    for tick in ticks:
        y = height - bottom - (tick / axis_max * chart_h)
        color = "#667085" if tick == 0 else "#e4e7ec"
        svg.append(f"<line x1='{left}' y1='{y:.1f}' x2='{width-20}' y2='{y:.1f}' stroke='{color}'/>")
        svg.append(f"<text x='{left-8}' y='{y+4:.1f}' font-size='10' text-anchor='end' fill='#475467'>{format_tick(tick)}</text>")
    svg.append(f"<line x1='{left}' y1='{top}' x2='{left}' y2='{height-bottom}' stroke='#667085'/>")
    svg.append(f"<line x1='{left}' y1='{height-bottom}' x2='{width-20}' y2='{height-bottom}' stroke='#667085'/>")
    for idx, row in enumerate(rows):
        x = left + 16 + idx * ((width - left - 60) / max(len(rows), 1))
        y_cursor = height - bottom
        total = totals[idx]
        for name, color, label_text in items:
            value = num(row.get(name))
            if value <= 0:
                continue
            h = value / axis_max * chart_h
            y_cursor -= h
            svg.append(f"<rect x='{x:.1f}' y='{y_cursor:.1f}' width='{bar_w}' height='{h:.1f}' fill='{color}'><title>{html.escape(str(row.get(x_key)))} {html.escape(label_text)}: {value:g}</title></rect>")
        if total > 0:
            total_y = max(top + 10, height - bottom - (total / axis_max * chart_h) - 5)
            svg.append(f"<text x='{x + bar_w/2:.1f}' y='{total_y:.1f}' font-size='10' text-anchor='middle' fill='#172033'>{html.escape(bar_total_label(row, total, item_names))}</text>")
        label = axis_label(row.get(x_key))
        svg.append(f"<text x='{x + bar_w/2:.1f}' y='{height-30}' font-size='10' text-anchor='end' transform='rotate(-45 {x + bar_w/2:.1f},{height-30})'>{html.escape(label)}</text>")
    svg.append("</svg>")
    parts.append("".join(svg))
    parts.append("</section>")
    return "\n".join(parts)

def chart_axis(max_value: float, tick_count: int = 5) -> tuple[float, list[float]]:
    if max_value <= 0:
        return 1.0, [0.0, 1.0]
    if max_value <= tick_count:
        axis_max = max(1, math.ceil(max_value))
        return float(axis_max), [float(idx) for idx in range(axis_max + 1)]
    raw_step = max_value / max(tick_count, 1)
    magnitude = 10 ** math.floor(math.log10(raw_step)) if raw_step > 0 else 1
    normalized = raw_step / magnitude
    if normalized <= 1:
        step = 1 * magnitude
    elif normalized <= 2:
        step = 2 * magnitude
    elif normalized <= 5:
        step = 5 * magnitude
    else:
        step = 10 * magnitude
    axis_max = max(step, math.ceil(max_value / step) * step)
    ticks = [idx * step for idx in range(int(round(axis_max / step)) + 1)]
    return float(axis_max), ticks

def format_tick(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:g}"

def axis_label(value: Any) -> str:
    text = str(value or "")
    match = re.fullmatch(r"\d{4}-(W\d{2})", text)
    if match:
        return match.group(1)
    return text

def bar_total_label(row: dict[str, Any], shown_total: float, item_names: set[str]) -> str:
    denominator = chart_denominator(row, shown_total, item_names)
    shown = format_tick(shown_total)
    if denominator is None:
        return shown
    return f"{shown}/{format_tick(denominator)}"

def chart_denominator(row: dict[str, Any], shown_total: float, item_names: set[str]) -> float | None:
    session_quality_names = {
        "good_sessions",
        "bad_sessions",
        "diagnostic_only_sessions",
        "unknown_or_incomplete",
    }
    candidates: list[str] = []
    if item_names and item_names <= session_quality_names:
        candidates.append("total_sessions")
    candidates.extend([
        "total_answers",
        "total_process_step_answers",
        "total_change_status_checks",
        "total_sessions_checked",
        "total_step_units",
        "total_structure_pairs",
        "total_cost_variance_groups",
        "total_case_count_candidates",
    ])
    for key in candidates:
        denominator = num(row.get(key))
        if denominator > 0 and denominator > shown_total + 1e-9:
            return denominator
    return None

def normalize_series(series: list[tuple]) -> list[tuple[str, str, str]]:
    items = []
    for item in series:
        if len(item) == 2:
            name, color = item
            label = str(name)
        else:
            name, color, label = item[:3]
        items.append((str(name), str(color), str(label)))
    return items

def legend_label_with_total(label: str, key: str, rows: list[dict[str, Any]]) -> str:
    total = sum(num(row.get(key)) for row in rows)
    if total <= 0:
        return label
    return f"{label} ({format_tick(total)})"

def small_multiples_stacked_bar_svg(
    title: str,
    description: str,
    rows: list[dict[str, Any]],
    group_key: str,
    x_key: str,
    series: list[tuple],
    y_label: str = "count",
) -> str:
    if not rows:
        return f"<section class='chart'><h2>{html.escape(title)}</h2><p class='chart-note'>{html.escape(description)}</p><p>No data.</p></section>"
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row.get(group_key) or "unknown"), []).append(row)
    items = normalize_series(series)
    parts = [
        f"<section class='chart'><h2>{html.escape(title)}</h2>",
        f"<p class='chart-note'>{html.escape(description)}</p>",
        "<div class='legend'>" + "".join(
            f"<span><span class='swatch' style='background:{color}'></span>{html.escape(legend_label_with_total(label, name, rows))}</span>"
            for name, color, label in items
        ) + "</div>",
        "<div class='subplots'>",
    ]
    for group, group_rows in sorted(groups.items(), key=lambda item: (-sum(sum(num(r.get(name)) for name, _color, _label in items) for r in item[1]), item[0])):
        parts.append("<div class='subplot'>")
        parts.append(f"<h3>{html.escape(group)}</h3>")
        parts.append(stacked_bar_svg_inner(group_rows, x_key, items, width=420, height=220, y_label=y_label))
        parts.append("</div>")
    parts.append("</div></section>")
    return "\n".join(parts)

def stacked_bar_svg_inner(
    rows: list[dict[str, Any]],
    x_key: str,
    items: list[tuple[str, str, str]],
    width: int,
    height: int,
    y_label: str = "count",
) -> str:
    left = 52
    bottom = 46
    top = 18
    chart_h = height - top - bottom
    bar_w = max(10, min(26, (width - left - 34) // max(len(rows), 1) - 4))
    totals = [sum(num(row.get(name)) for name, _color, _label in items) for row in rows]
    item_names = {name for name, _color, _label in items}
    ymax = max(totals) if totals else 1
    axis_max, ticks = chart_axis(ymax)
    svg = [f"<svg width='{width}' height='{height}' role='img'>"]
    svg.append(
        f"<text x='10' y='{top + chart_h / 2:.1f}' font-size='8' text-anchor='middle' "
        f"fill='#475467' transform='rotate(-90 10,{top + chart_h / 2:.1f})'>{html.escape(y_label)}</text>"
    )
    for tick in ticks:
        y = height - bottom - (tick / axis_max * chart_h)
        color = "#667085" if tick == 0 else "#e4e7ec"
        svg.append(f"<line x1='{left}' y1='{y:.1f}' x2='{width-12}' y2='{y:.1f}' stroke='{color}'/>")
        svg.append(f"<text x='{left-6}' y='{y+3:.1f}' font-size='8' text-anchor='end' fill='#475467'>{format_tick(tick)}</text>")
    svg.append(f"<line x1='{left}' y1='{top}' x2='{left}' y2='{height-bottom}' stroke='#667085'/>")
    svg.append(f"<line x1='{left}' y1='{height-bottom}' x2='{width-12}' y2='{height-bottom}' stroke='#667085'/>")
    for idx, row in enumerate(rows):
        x = left + 10 + idx * ((width - left - 34) / max(len(rows), 1))
        y_cursor = height - bottom
        total = totals[idx]
        for name, color, label_text in items:
            value = num(row.get(name))
            if value <= 0:
                continue
            h = value / axis_max * chart_h
            y_cursor -= h
            svg.append(f"<rect x='{x:.1f}' y='{y_cursor:.1f}' width='{bar_w}' height='{h:.1f}' fill='{color}'><title>{html.escape(str(row.get(x_key)))} {html.escape(label_text)}: {value:g}</title></rect>")
        if total > 0:
            total_y = max(top + 8, height - bottom - (total / axis_max * chart_h) - 4)
            svg.append(f"<text x='{x + bar_w/2:.1f}' y='{total_y:.1f}' font-size='8' text-anchor='middle' fill='#172033'>{html.escape(bar_total_label(row, total, item_names))}</text>")
        label = axis_label(row.get(x_key))
        svg.append(f"<text x='{x + bar_w/2:.1f}' y='{height-26}' font-size='9' text-anchor='end' transform='rotate(-45 {x + bar_w/2:.1f},{height-26})'>{html.escape(label)}</text>")
    svg.append("</svg>")
    return "".join(svg)

def render_markers(markers: list[dict[str, Any]]) -> str:
    if not markers:
        return "<p>No feature markers supplied.</p>"
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(m.get('date', '')))}</td>"
        f"<td>{html.escape(str(m.get('week') or iso_week(m.get('date'))))}</td>"
        f"<td>{html.escape(str(m.get('label', '')))}</td>"
        f"<td>{html.escape(str(m.get('area', '')))}</td>"
        f"<td>{html.escape(', '.join(m.get('affects', []) if isinstance(m.get('affects'), list) else []))}</td>"
        f"<td>{html.escape(str(m.get('git_sha', '')))}</td>"
        f"<td>{html.escape(str(m.get('notes', '')))}</td>"
        "</tr>"
        for m in markers
    )
    return f"<h3>Feature Markers</h3><table><tr><th>Date</th><th>Week</th><th>Label</th><th>Area</th><th>Affects</th><th>Git SHA</th><th>Notes</th></tr>{rows}</table>"

def merged_feature_markers(markers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    combined = [dict(marker) for marker in DEFAULT_FEATURE_MARKERS]
    seen = {
        (str(marker.get("date") or ""), str(marker.get("label") or ""))
        for marker in combined
    }
    for marker in markers:
        key = (str(marker.get("date") or ""), str(marker.get("label") or ""))
        if key in seen:
            continue
        combined.append(dict(marker))
        seen.add(key)
    return sorted(combined, key=lambda marker: (str(marker.get("date") or ""), str(marker.get("label") or "")))

def run_all(
    db_path: Path,
    out_dir: Path,
    markers_path: Path | None,
    config: dict[str, Any] | None = None,
) -> None:
    config = configure_analysis(config or load_run_config(out_dir))
    ensure_run_dirs(out_dir)
    markers = load_feature_markers(markers_path)
    snapshot_path = snapshot_db(db_path, out_dir)
    build_manifest(db_path, snapshot_path, out_dir, markers, config)
    extract(snapshot_path, out_dir, config)
    analyze(out_dir, config)
    aggregate(out_dir, config)
    visualize(out_dir, markers, config)
