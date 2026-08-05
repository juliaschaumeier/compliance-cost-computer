from __future__ import annotations

import json
from pathlib import Path
import re
import statistics
from typing import Any

from common import *
from entities import *

NOT_APPLICABLE_PHRASES = (
    "nicht anwendbar", "nicht betroffen", "keine relevanten vorgaben",
    "kein erfuellungsaufwand", "keine prozesse", "keine fallgruppen",
    "keine taetigkeiten", "no applicable", "not applicable",
)
STRUCTURAL_NORM_PROMPTS = {"process_compilation", "case_group_development", "process_step_analysis"}
CHANGE_STATUS_KEYS = ("aenderungsstatus", "änderungsstatus", "change_status", "status_change", "status")
VALID_RAW_CHANGE_STATUSES = {"eingefuehrt", "neu", "abgeschafft", "wegfall", "geaendert", "unveraendert"}

def session_maps(data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    sessions = {int(row["session_id"]): row for row in data["sessions"] if row.get("session_id") is not None}
    answers_by_session: dict[int, list[dict[str, Any]]] = {}
    for row in data["llm_answers"]:
        sid = row.get("session_id")
        if sid is not None:
            answers_by_session.setdefault(int(sid), []).append(row)
    for rows in answers_by_session.values():
        rows.sort(key=lambda r: str(r.get("created_at") or ""))
    return {"sessions": sessions, "answers_by_session": answers_by_session}

def finding(
    issue_id: str,
    session: dict[str, Any] | None,
    classification: str,
    severity: str,
    summary: str,
    evidence: dict[str, Any],
    answer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session = session or {}
    sid = session.get("session_id") or evidence.get("session_id")
    created_at = session.get("created_at")
    row = {
        "issue_id": issue_id,
        "issue_name": ISSUES.get(issue_id, issue_id),
        "classification": classification,
        "severity": severity,
        "session_id": sid,
        "app_session_id": session.get("app_session_id"),
        "week": iso_week(created_at),
        "session_created_at": created_at,
        "law_pair": law_pair_key(session),
        "model": session.get("llm_model") or (answer or {}).get("model"),
        "answer_id": (answer or {}).get("answer_id"),
        "answer_created_at": (answer or {}).get("created_at"),
        "answer_week": iso_week((answer or {}).get("created_at")) if answer else None,
        "prompt_id": (answer or {}).get("prompt_id"),
        "norm_addressee": evidence.get("norm_addressee") or (answer_addressee(answer) if answer else None),
        "evidence_summary": summary,
        "evidence": evidence,
    }
    row["evidence_hash"] = stable_hash({k: row.get(k) for k in ("issue_id", "session_id", "answer_id", "evidence")})
    return row

def write_review_packet(out_dir: Path, row: dict[str, Any], question: str, payload: dict[str, Any]) -> None:
    packet_id = f"{row['issue_id']}_session_{row.get('session_id')}_answer_{row.get('answer_id') or 'none'}_{row['evidence_hash'][:10]}"
    packet = {
        "packet_id": packet_id,
        "issue_id": row["issue_id"],
        "session": {
            "session_id": row.get("session_id"),
            "app_session_id": row.get("app_session_id"),
            "week": row.get("week"),
            "law_pair": row.get("law_pair"),
            "model": row.get("model"),
        },
        "rule_based_classification": row.get("classification"),
        "evidence_summary": row.get("evidence_summary"),
        "question_for_reviewer": question,
        "deterministic_evidence_hash": row.get("evidence_hash"),
        "payload": payload,
    }
    write_json(out_dir / "review_packets" / f"{packet_id}.json", packet)

def analyze_issue_01(data: dict[str, list[dict[str, Any]]], out_dir: Path) -> list[dict[str, Any]]:
    maps = session_maps(data)
    findings: list[dict[str, Any]] = []
    parsed_case_answers: dict[tuple[int, str | None], list[dict[str, Any]]] = {}
    for ans in data["llm_answers"]:
        if ans.get("prompt_id") != "case_group_development" or ans.get("session_id") is None:
            continue
        cls = classify_json_answer(ans.get("answer_text"), "case_group_development")
        if isinstance(cls.get("data"), (dict, list)):
            parsed_case_answers[(int(ans["session_id"]), answer_addressee(ans))] = collect_case_groups(cls["data"])
    for ans in data["llm_answers"]:
        prompt = ans.get("prompt_id")
        if prompt not in {"case_group_development", "process_step_analysis"}:
            continue
        sid = int(ans["session_id"])
        session = maps["sessions"].get(sid, {"session_id": sid})
        cls = classify_json_answer(ans.get("answer_text"), str(prompt))
        if not isinstance(cls.get("data"), (dict, list)):
            continue
        groups = collect_case_groups(cls["data"])
        steps = collect_steps(cls["data"])
        if prompt == "case_group_development":
            parsed_case_answers[(sid, answer_addressee(ans))] = groups
            for dup in duplicate_groups(groups, ("norm_addressee", "process_id"), "case_group"):
                row = finding(
                    "issue_01_duplicate_fallgruppen", session, "bad", "high",
                    "Duplicate case-group names in raw case_group_development answer.",
                    {"duplicate": dup, "source": "raw_case_group_development"},
                    ans,
                )
                findings.append(row)
        if prompt == "process_step_analysis":
            upstream = parsed_case_answers.get((sid, answer_addressee(ans))) or parsed_case_answers.get((sid, None)) or []
            for issue in case_group_handoff_issues(upstream, groups, steps):
                row = finding(
                    "issue_01_duplicate_fallgruppen", session, "bad", "high",
                    "Case group appears once upstream but multiple times or inconsistently during step generation.",
                    {"handoff_issue": issue, "source": "case_group_to_step_handoff"},
                    ans,
                )
                findings.append(row)
            step_sets = step_sets_by_case_ref(steps)
            for dup in duplicate_groups(groups, ("norm_addressee", "process_id"), "case_group"):
                row = finding(
                    "issue_01_duplicate_fallgruppen", session, "bad", "high",
                    "Duplicate case-group references in raw process_step_analysis answer.",
                    {"duplicate": dup, "step_sets": step_sets, "source": "raw_process_step_analysis"},
                    ans,
                )
                findings.append(row)
            for issue in inconsistent_step_case_refs(groups, steps):
                row = finding(
                    "issue_01_duplicate_fallgruppen", session, "bad", "high",
                    "Inconsistent case-group references or divergent step sets during step generation.",
                    {"handoff_issue": issue, "source": "raw_process_step_analysis"},
                    ans,
                )
                findings.append(row)
    for sid, rows in group_by(data["case_groups"], "session_id").items():
        session = maps["sessions"].get(int(sid), {"session_id": sid})
        for dup in duplicate_groups(rows, ("norm_addressee", "process_id"), "case_group"):
            related_steps = [s for s in data["process_steps"] if s.get("case_group_id") in dup.get("entity_ids", [])]
            step_names = sorted({str(s.get("step")) for s in related_steps if s.get("step")})
            row = finding(
                "issue_01_duplicate_fallgruppen", session, "bad", "high",
                "Duplicate case-group names persisted in DB.",
                {"duplicate": dup, "persisted_step_names": step_names, "source": "persisted_case_groups"},
            )
            findings.append(row)
    return findings

def duplicate_groups(rows: list[dict[str, Any]], context_keys: tuple[str, ...], name_key: str) -> list[dict[str, Any]]:
    buckets: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        name = norm_text(row.get(name_key))
        if not name:
            continue
        ctx = tuple(row.get(key) for key in context_keys) + (name,)
        buckets.setdefault(ctx, []).append(row)
    duplicates = []
    for ctx, items in buckets.items():
        if len(items) < 2:
            continue
        duplicates.append({
            "context": ctx[:-1],
            "normalized_name": ctx[-1],
            "count": len(items),
            "entity_ids": [item.get("case_group_id") for item in items],
            "names": [item.get(name_key) for item in items],
            "descriptions": [item.get("description") for item in items],
        })
    return duplicates

def case_group_handoff_issues(upstream_groups: list[dict[str, Any]], downstream_groups: list[dict[str, Any]], steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    downstream_refs = [
        group for group in downstream_groups
        if norm_text(group.get("case_group")) or group.get("case_group_id") is not None
    ]
    step_sets = step_sets_by_case_ref(steps)
    for upstream in upstream_groups:
        upstream_name = norm_text(upstream.get("case_group"))
        if not upstream_name:
            continue
        exact = [group for group in downstream_refs if norm_text(group.get("case_group")) == upstream_name]
        near = [
            group for group in downstream_refs
            if group not in exact and similarity(group.get("case_group"), upstream.get("case_group")) >= 0.92
        ]
        matches = exact + near
        unique_refs = {
            str(group.get("case_group_id") or norm_text(group.get("case_group")))
            for group in matches
        }
        if len(matches) > 1 and len(unique_refs) > 1:
            ids = [group.get("case_group_id") for group in matches]
            issue_step_sets = {
                str(group.get("case_group_id") or norm_text(group.get("case_group"))): step_sets.get(str(group.get("case_group_id") or norm_text(group.get("case_group"))), [])
                for group in matches
            }
            issues.append({
                "type": "single_upstream_group_multiple_downstream_refs",
                "upstream_case_group_id": upstream.get("case_group_id"),
                "upstream_case_group": upstream.get("case_group"),
                "downstream_case_group_ids": ids,
                "downstream_case_group_names": [group.get("case_group") for group in matches],
                "step_sets": issue_step_sets,
            })
    return issues

def step_sets_by_case_ref(steps: list[dict[str, Any]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for step in steps:
        key = str(step.get("case_group_id") or norm_text(step.get("case_group")) or "unknown")
        result.setdefault(key, []).append(str(step.get("step") or ""))
    return {key: sorted({norm_text(name) for name in names if norm_text(name)}) for key, names in result.items()}

def inconsistent_step_case_refs(groups: list[dict[str, Any]], steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    id_names: dict[str, set[str]] = {}
    for group in groups:
        gid = group.get("case_group_id")
        name = norm_text(group.get("case_group"))
        if gid and name:
            id_names.setdefault(str(gid), set()).add(name)
    for gid, names in id_names.items():
        if len(names) > 1:
            issues.append({"type": "same_id_multiple_names", "case_group_id": gid, "names": sorted(names)})
    names_to_ids: dict[str, set[str]] = {}
    for group in groups:
        gid = group.get("case_group_id")
        name = norm_text(group.get("case_group"))
        if gid and name:
            names_to_ids.setdefault(name, set()).add(str(gid))
    for name, ids in names_to_ids.items():
        if len(ids) > 1:
            step_sets = {gid: step_sets_by_case_ref([s for s in steps if str(s.get("case_group_id")) == gid]).get(gid, []) for gid in ids}
            issues.append({"type": "same_name_multiple_ids", "name": name, "ids": sorted(ids), "step_sets": step_sets})
    return issues

def has_not_applicable_text(*values: Any) -> bool:
    text = norm_text(" ".join(str(v or "") for v in values))
    return any(phrase in text for phrase in NOT_APPLICABLE_PHRASES)

def analyze_issue_02(data: dict[str, list[dict[str, Any]]], out_dir: Path) -> list[dict[str, Any]]:
    maps = session_maps(data)
    findings: list[dict[str, Any]] = []
    wording_rows: list[dict[str, Any]] = []
    regs_by_session = group_by(data["regulations"], "session_id")
    rows_by_table = {
        "processes": data["processes"],
        "case_groups": data["case_groups"],
        "process_steps": data["process_steps"],
        "costs": data["costs"],
        "tiles": data["tiles"],
    }
    for sid, session in maps["sessions"].items():
        regs = regs_by_session.get(sid, [])
        applies_columns_available = all(
            has_source_column(data, "regulations", col)
            for col in ("applies_to_administration", "applies_to_business", "applies_to_citizens")
        )
        applies = {
            "administration": sum(1 for r in regs if truthy(r.get("applies_to_administration"))),
            "business": sum(1 for r in regs if truthy(r.get("applies_to_business"))),
            "citizens": sum(1 for r in regs if truthy(r.get("applies_to_citizens"))),
        }
        has_regulation_context = bool(regs)
        answers = maps["answers_by_session"].get(sid, [])
        for addressee in ADDRESSEES:
            prompt_calls = [
                ans for ans in answers
                if ans.get("prompt_id") in NORM_PROMPTS and answer_addressee(ans) == addressee
            ]
            row_counts = {
                table: len([r for r in rows if int_or_none(r.get("session_id")) == sid and (r.get("norm_addressee") or "administration") == addressee])
                for table, rows in rows_by_table.items()
            }
            tile_hits = [
                t for t in data["tiles"]
                if int_or_none(t.get("session_id")) == sid
                and (t.get("norm_addressee") or "administration") == addressee
                and str(t.get("id") or "").startswith(("process_", "case_group_", "step_", "total_cost"))
            ]
            downstream_not_app = [
                ans.get("answer_id") for ans in prompt_calls
                if answer_indicates_no_downstream_work(ans)
            ]
            tile_not_app = [
                t.get("id") for t in tile_hits
                if has_not_applicable_text(t.get("title"), t.get("text"))
            ]
            applicability_context = (
                "unknown_applicability"
                if not applies_columns_available or not has_regulation_context
                else "zero_applicable_regulations"
                if applies[addressee] == 0
                else "positive_applicable_regulations"
            )
            for ans in prompt_calls:
                wording_rows.extend(not_applicable_wording_rows(
                    session=session,
                    addressee=addressee,
                    applicable_regulation_count=applies.get(addressee),
                    applicability_context=applicability_context,
                    source_type="llm_answer",
                    source_id=ans.get("answer_id"),
                    prompt_id=ans.get("prompt_id"),
                    model=ans.get("model") or session.get("llm_model"),
                    title=None,
                    text=ans.get("answer_text"),
                ))
            for tile in tile_hits:
                wording_rows.extend(not_applicable_wording_rows(
                    session=session,
                    addressee=addressee,
                    applicable_regulation_count=applies.get(addressee),
                    applicability_context=applicability_context,
                    source_type="tile",
                    source_id=tile.get("id"),
                    prompt_id=None,
                    model=session.get("llm_model"),
                    title=tile.get("title"),
                    text=tile.get("text"),
                ))
            prompt_outcome = classify_zero_applies_prompt_outcome(prompt_calls, tile_hits)
            if applies_columns_available and not has_regulation_context and (prompt_calls or tile_hits):
                findings.append(finding(
                    "issue_02_unnecessary_addressee_steps", session, "ambiguous", "low",
                    "Downstream addressee work exists, but no persisted regulation context is available to determine applicability.",
                    {
                        "norm_addressee": addressee,
                        "prompt_ids_called": sorted({str(a.get("prompt_id")) for a in prompt_calls}),
                        "prompt_attempt_count": len(prompt_calls),
                        "prompt_answer_states": prompt_outcome["answer_states"],
                        "prompt_state_reasons": prompt_outcome["state_reasons"],
                        "prompt_parse_classes": prompt_outcome["parse_classes"],
                        "row_counts": row_counts,
                        "tile_count": len(tile_hits),
                        "classification_bucket": "missing_regulation_context_but_downstream_work",
                    },
                ))
            if applies_columns_available and has_regulation_context and applies[addressee] == 0 and prompt_calls:
                findings.append(finding(
                    "issue_02_unnecessary_addressee_steps", session, "bad", "high",
                    "Norm-addressee prompt calls exist although no regulations apply.",
                    {
                        "norm_addressee": addressee,
                        "applicable_regulation_count": 0,
                        "prompt_ids_called": sorted({str(a.get("prompt_id")) for a in prompt_calls}),
                        "prompt_attempt_count": len(prompt_calls),
                        "prompt_answer_states": prompt_outcome["answer_states"],
                        "prompt_state_reasons": prompt_outcome["state_reasons"],
                        "prompt_parse_classes": prompt_outcome["parse_classes"],
                        "row_counts": row_counts,
                        "tile_count": len(tile_hits),
                        "classification_bucket": prompt_outcome["bucket"],
                    },
                ))
            if applies_columns_available and has_regulation_context and applies[addressee] == 0 and tile_hits:
                findings.append(finding(
                    "issue_02_unnecessary_addressee_steps", session, "bad", "medium",
                    "Tiles exist for an addressee with no applicable regulations.",
                    {
                        "norm_addressee": addressee,
                        "tile_ids": [t.get("id") for t in tile_hits[:20]],
                        "tile_count": len(tile_hits),
                        "classification_bucket": "no_applies_but_tiles_shown",
                    },
                ))
            if applies_columns_available and applies[addressee] > 0 and (downstream_not_app or tile_not_app):
                findings.append(finding(
                    "issue_02_unnecessary_addressee_steps", session, "bad", "medium",
                    "Addressee applies, but downstream content says it is not applicable.",
                    {
                        "norm_addressee": addressee,
                        "applicable_regulation_count": applies[addressee],
                        "not_applicable_answer_ids": downstream_not_app,
                        "not_applicable_tile_ids": tile_not_app,
                        "classification_bucket": "applies_but_downstream_says_not_applicable",
                    },
                ))
    if out_dir is not None:
        write_csv(out_dir / "findings" / "issue_02_not_applicable_wordings.csv", wording_rows, issue_02_wording_fieldnames())
    return findings

def not_applicable_wording_rows(
    *,
    session: dict[str, Any],
    addressee: str,
    applicable_regulation_count: int | None,
    applicability_context: str,
    source_type: str,
    source_id: Any,
    prompt_id: Any,
    model: Any,
    title: Any,
    text: Any,
) -> list[dict[str, Any]]:
    raw = " ".join(str(value or "") for value in (title, text))
    matches = matched_not_applicable_occurrences(raw, prompt_id=str(prompt_id or "") if source_type == "llm_answer" else None)
    rows = []
    for match in matches:
        phrase = str(match.get("phrase") or "")
        rows.append({
            "session_id": session.get("session_id"),
            "app_session_id": session.get("app_session_id"),
            "week": iso_week(session.get("created_at")),
            "law_pair": law_pair_key(session),
            "model": model,
            "norm_addressee": addressee,
            "applicable_regulation_count": applicable_regulation_count,
            "applicability_context": applicability_context,
            "source_type": source_type,
            "source_id": source_id,
            "prompt_id": prompt_id,
            "matched_phrase": phrase,
            "wording_bucket": wording_bucket(phrase, str(match.get("text") or raw), str(match.get("path") or "")),
            "match_path": match.get("path"),
            "excerpt": phrase_excerpt(match.get("text") or raw, phrase),
        })
    return rows

def matched_not_applicable_phrases(value: Any) -> list[str]:
    return [str(match["phrase"]) for match in matched_not_applicable_occurrences(value)]

def matched_not_applicable_occurrences(value: Any, prompt_id: str | None = None) -> list[dict[str, str]]:
    fragments = wording_fragments(value, prompt_id)
    matches: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for path, fragment in fragments:
        text = norm_text(fragment)
        for phrase in NOT_APPLICABLE_PHRASES:
            if phrase in text:
                key = (phrase, path, text[:500])
                if key in seen:
                    continue
                seen.add(key)
                matches.append({"phrase": phrase, "path": path, "text": str(fragment or "")})
    return matches

def wording_fragments(value: Any, prompt_id: str | None = None) -> list[tuple[str, str]]:
    if prompt_id:
        cls = classify_json_answer(value, prompt_id)
        data = cls.get("data")
        if isinstance(data, (dict, list)):
            return semantic_text_fragments(data)
        for fenced in reversed(re.findall(r"```(?:json)?\s*(.*?)```", str(value or ""), flags=re.IGNORECASE | re.DOTALL)):
            fenced_cls = classify_json_answer(fenced, prompt_id)
            fenced_data = fenced_cls.get("data")
            if isinstance(fenced_data, (dict, list)):
                return semantic_text_fragments(fenced_data)
    parsed = parse_json_maybe(value)
    if isinstance(parsed, (dict, list)):
        return semantic_text_fragments(parsed)
    return [("raw_text", str(value or ""))]

def semantic_text_fragments(value: Any, path: str = "$") -> list[tuple[str, str]]:
    fragments: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if isinstance(child, str):
                fragments.append((child_path, child))
            elif isinstance(child, (dict, list)):
                fragments.extend(semantic_text_fragments(child, child_path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            fragments.extend(semantic_text_fragments(child, f"{path}[{idx}]"))
    elif isinstance(value, str):
        fragments.append((path, value))
    return fragments

def wording_bucket(phrase: str, raw: str, path: str = "") -> str:
    text = norm_text(raw)
    path_text = norm_text(path)
    if any(marker in path_text for marker in ("erklaerungen", "confidence")):
        return "metric_explanation_wording"
    if "kein erfuellungsaufwand" in text:
        return "no_compliance_effort"
    if "keine prozesse" in text or "keine fallgruppen" in text or "keine taetigkeiten" in text:
        return "entity_absence_wording"
    if "keine relevanten vorgaben" in text:
        return "no_relevant_regulations"
    if "nicht anwendbar" in text or "not applicable" in text or "no applicable" in text:
        return "not_applicable"
    if "nicht betroffen" in text:
        return "not_affected"
    return "other_nothing_to_do_wording"

def phrase_excerpt(raw: Any, phrase: str, radius: int = 220) -> str:
    text = re.sub(r"\s+", " ", norm_text(raw)).strip()
    idx = text.find(phrase)
    if idx < 0:
        return text[: radius * 2]
    start = max(0, idx - radius)
    end = min(len(text), idx + len(phrase) + radius)
    return text[start:end]

def issue_02_wording_fieldnames() -> list[str]:
    return [
        "session_id", "app_session_id", "week", "law_pair", "model",
        "norm_addressee", "applicable_regulation_count",
        "applicability_context", "source_type", "source_id", "prompt_id",
        "matched_phrase", "wording_bucket", "match_path", "excerpt",
    ]

def answer_indicates_no_downstream_work(ans: dict[str, Any]) -> bool:
    prompt_id = str(ans.get("prompt_id") or "")
    if prompt_id not in STRUCTURAL_NORM_PROMPTS:
        return False
    text = ans.get("answer_text")
    if not has_not_applicable_text(text):
        return False
    cls = classify_json_answer(text, prompt_id)
    data = cls.get("data")
    if prompt_id == "process_compilation":
        return len(collect_processes(data)) == 0
    if prompt_id == "case_group_development":
        groups = collect_case_groups(data)
        if not groups:
            return True
        return all(has_not_applicable_text(group.get("case_group"), group.get("description")) for group in groups)
    if prompt_id == "process_step_analysis":
        steps = collect_steps(data)
        if not steps:
            return True
        return all(has_not_applicable_text(step.get("step"), step.get("description")) for step in steps)
    return False

def classify_zero_applies_prompt_outcome(
    prompt_calls: list[dict[str, Any]],
    tile_hits: list[dict[str, Any]],
) -> dict[str, Any]:
    states = sorted({
        f"{a.get('answer_state') or 'unknown'}:{a.get('state_reason') or 'unknown'}"
        for a in prompt_calls
    })
    reasons = sorted({str(a.get("state_reason") or "unknown") for a in prompt_calls})
    parse_classes = sorted({
        str(classify_answer_by_prompt_contract(a)[0].get("parse_class"))
        for a in prompt_calls
    })
    if tile_hits:
        bucket = "no_applies_prompt_and_tile"
    elif any(a.get("answer_state") == "active" and a.get("state_reason") == "session_updated" for a in prompt_calls):
        bucket = "no_applies_prompt_only_applied_no_counted_tile"
    elif any("query_failed" in str(a.get("state_reason") or "") for a in prompt_calls) or any(cls == "non_json_prose" for cls in parse_classes):
        bucket = "no_applies_prompt_only_query_or_form_failure"
    elif any("session_update_failed" in str(a.get("state_reason") or "") for a in prompt_calls):
        bucket = "no_applies_prompt_only_session_update_failed"
    elif prompt_calls and all(
        any(marker in str(a.get("state_reason") or "") for marker in ("session_reverted", "superseded_by_new_attempt"))
        for a in prompt_calls
    ):
        bucket = "no_applies_prompt_only_reverted_or_superseded"
    elif prompt_calls:
        bucket = "no_applies_prompt_only_no_tile"
    else:
        bucket = "no_applies_no_prompt"
    return {
        "bucket": bucket,
        "answer_states": states,
        "state_reasons": reasons,
        "parse_classes": parse_classes,
    }

STEP_PROMPTS = {
    "step_1_summary": ("law_summary",),
    "step_2_regulations": ("regulations_identification",),
    "step_3_processes": ("process_compilation",),
    "step_4_case_groups": ("case_group_development",),
    "step_5_process_steps": ("process_step_analysis",),
    "step_6_effort": ("cases_calculation", "effort_calculation"),
}

PROMPT_TO_STEP = {
    prompt_id: step_key
    for step_key, prompt_ids in STEP_PROMPTS.items()
    for prompt_id in prompt_ids
}

STEP_LABELS = {
    "step_1_summary": "Step 1 summary",
    "step_2_regulations": "Step 2 regulations",
    "step_3_processes": "Step 3 processes",
    "step_4_case_groups": "Step 4 case groups",
    "step_5_process_steps": "Step 5 process steps",
    "step_6_effort": "Step 6 effort",
}

GLOBAL_STEPS = {"step_1_summary", "step_2_regulations"}

def analyze_retry_pressure(data: dict[str, list[dict[str, Any]]], out_dir: Path | None) -> list[dict[str, Any]]:
    """Measure non-rollback retry pressure per session/step/addressee episode.

    This is a workflow-friction metric, not an issue finding. Episodes are split
    at `session_reverted` so user rollbacks do not inflate retries. For step 6,
    the two paired prompts count as one required round; extra rounds are retries.
    """
    maps = session_maps(data)
    grouped: dict[tuple[int, str, str], list[dict[str, Any]]] = {}
    for ans in data["llm_answers"]:
        sid = int_or_none(ans.get("session_id"))
        step_key = PROMPT_TO_STEP.get(str(ans.get("prompt_id") or ""))
        if sid is None or step_key is None:
            continue
        addressee = "global" if step_key in GLOBAL_STEPS else (answer_addressee(ans) or "unknown")
        grouped.setdefault((sid, step_key, addressee), []).append(ans)

    rows: list[dict[str, Any]] = []
    for (sid, step_key, addressee), answers in sorted(grouped.items()):
        session = maps["sessions"].get(sid, {"session_id": sid})
        for idx, episode in enumerate(split_retry_episodes(answers), start=1):
            if not episode:
                continue
            if step_key == "step_6_effort":
                row = effort_retry_row(session, sid, step_key, addressee, idx, episode, data)
            else:
                row = simple_retry_row(session, sid, step_key, addressee, idx, episode, data)
            rows.append(row)
    if out_dir is not None:
        write_csv(out_dir / "findings" / "retry_pressure.csv", rows, retry_pressure_fieldnames())
    return rows

def split_retry_episodes(answers: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    episodes: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for ans in sorted(answers, key=lambda row: str(row.get("created_at") or "")):
        if is_user_rollback_answer(ans):
            if current:
                episodes.append(current)
                current = []
            continue
        current.append(ans)
    if current:
        episodes.append(current)
    return episodes

def is_user_rollback_answer(ans: dict[str, Any]) -> bool:
    return "session_reverted" in str(ans.get("state_reason") or "")

def is_successful_step_answer(ans: dict[str, Any]) -> bool:
    return ans.get("answer_state") == "active" and ans.get("state_reason") == "session_updated"

def simple_retry_row(
    session: dict[str, Any],
    sid: int,
    step_key: str,
    addressee: str,
    episode_index: int,
    episode: list[dict[str, Any]],
    data: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    success_idx = next((idx for idx, ans in enumerate(episode) if is_successful_step_answer(ans)), None)
    attempts_to_success = len(episode) if success_idx is None else success_idx + 1
    succeeded = success_idx is not None
    return retry_row_base(
        session=session,
        sid=sid,
        step_key=step_key,
        addressee=addressee,
        episode_index=episode_index,
        episode=episode,
        succeeded=succeeded,
        attempt_count=len(episode),
        required_prompt_count=1,
        attempt_rounds=attempts_to_success,
        retry_rounds=max(0, attempts_to_success - 1) if succeeded else None,
        success_at=episode[success_idx].get("created_at") if succeeded and success_idx is not None else None,
        data=data,
        post_success_attempt_count=(len(episode) - success_idx - 1) if succeeded and success_idx is not None else 0,
    )

def effort_retry_row(
    session: dict[str, Any],
    sid: int,
    step_key: str,
    addressee: str,
    episode_index: int,
    episode: list[dict[str, Any]],
    data: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    case_success_idx = next((idx for idx, ans in enumerate(episode) if ans.get("prompt_id") == "cases_calculation" and is_successful_step_answer(ans)), None)
    effort_success_idx = next((idx for idx, ans in enumerate(episode) if ans.get("prompt_id") == "effort_calculation" and is_successful_step_answer(ans)), None)
    succeeded = case_success_idx is not None and effort_success_idx is not None
    if succeeded:
        terminal_idx = max(case_success_idx or 0, effort_success_idx or 0)
        terminal_answers = episode[:terminal_idx + 1]
    else:
        terminal_answers = episode
    case_attempts = sum(1 for ans in terminal_answers if ans.get("prompt_id") == "cases_calculation")
    effort_attempts = sum(1 for ans in terminal_answers if ans.get("prompt_id") == "effort_calculation")
    attempt_rounds = max(case_attempts, effort_attempts)
    success_at = None
    if succeeded:
        success_times = [str(episode[idx].get("created_at") or "") for idx in (case_success_idx, effort_success_idx) if idx is not None]
        success_at = max(success_times) if success_times else None
    return retry_row_base(
        session=session,
        sid=sid,
        step_key=step_key,
        addressee=addressee,
        episode_index=episode_index,
        episode=episode,
        succeeded=succeeded,
        attempt_count=len(episode),
        required_prompt_count=2,
        attempt_rounds=attempt_rounds,
        retry_rounds=max(0, attempt_rounds - 1) if succeeded else None,
        success_at=success_at,
        data=data,
        cases_attempt_count=case_attempts,
        effort_attempt_count=effort_attempts,
        post_success_attempt_count=(len(episode) - terminal_idx - 1) if succeeded else 0,
    )

def retry_row_base(
    session: dict[str, Any],
    sid: int,
    step_key: str,
    addressee: str,
    episode_index: int,
    episode: list[dict[str, Any]],
    succeeded: bool,
    attempt_count: int,
    required_prompt_count: int,
    attempt_rounds: int,
    retry_rounds: int | None,
    success_at: Any,
    data: dict[str, list[dict[str, Any]]],
    cases_attempt_count: int | None = None,
    effort_attempt_count: int | None = None,
    post_success_attempt_count: int | None = None,
) -> dict[str, Any]:
    if post_success_attempt_count is None:
        success_seen = False
        post_success_attempt_count = 0
        for ans in episode:
            if success_seen:
                post_success_attempt_count += 1
            if is_successful_step_answer(ans):
                success_seen = True
    terminal_state = "succeeded_after_retry" if succeeded and retry_rounds and retry_rounds > 0 else "succeeded_without_retry" if succeeded else "not_successful_without_rollback"
    failed_attempts = retry_failed_attempts(episode, success_at)
    cause = classify_retry_cause(step_key, failed_attempts)
    row = {
        "session_id": sid,
        "app_session_id": session.get("app_session_id"),
        "week": iso_week(success_at or episode[-1].get("created_at") or session.get("created_at")),
        "session_created_week": iso_week(session.get("created_at")),
        "law_pair": law_pair_key(session),
        "model": session.get("llm_model") or first_present(episode, "model"),
        "step_key": step_key,
        "step_label": STEP_LABELS.get(step_key, step_key),
        "norm_addressee": addressee,
        "episode_index": episode_index,
        "first_attempt_at": episode[0].get("created_at"),
        "last_attempt_at": episode[-1].get("created_at"),
        "success_at": success_at,
        "succeeded": succeeded,
        "terminal_state": terminal_state,
        "next_state_reached": next_step_state_present(data, sid, step_key, addressee) if succeeded else False,
        "prompt_attempt_count": attempt_count,
        "required_prompt_count": required_prompt_count,
        "attempt_rounds_to_success_or_terminal": attempt_rounds,
        "retry_rounds_to_success": retry_rounds,
        "post_success_attempt_count": post_success_attempt_count,
        "cases_attempt_count": cases_attempt_count,
        "effort_attempt_count": effort_attempt_count,
        "prompt_ids": sorted({str(ans.get("prompt_id") or "") for ans in episode}),
        "answer_ids": [ans.get("answer_id") for ans in episode],
        "answer_states": sorted({f"{ans.get('answer_state') or 'unknown'}:{ans.get('state_reason') or 'unknown'}" for ans in episode}),
        "parse_classes": sorted({str(classify_answer_by_prompt_contract(ans)[0].get("parse_class")) for ans in episode}),
        "primary_retry_cause": cause["primary_retry_cause"],
        "retry_cause_groups": cause["retry_cause_groups"],
        "retry_cause_evidence": cause["retry_cause_evidence"],
        "db_state_reason_groups": cause["db_state_reason_groups"],
        "failed_answer_ids_before_success": [ans.get("answer_id") for ans in failed_attempts],
    }
    return row

def retry_failed_attempts(episode: list[dict[str, Any]], success_at: Any) -> list[dict[str, Any]]:
    failed = []
    success_text = str(success_at or "")
    for ans in episode:
        if is_successful_step_answer(ans):
            continue
        if success_text and str(ans.get("created_at") or "") > success_text:
            continue
        failed.append(ans)
    return failed

def classify_retry_cause(step_key: str, failed_attempts: list[dict[str, Any]]) -> dict[str, Any]:
    groups: list[str] = []
    evidence: list[str] = []
    db_groups: list[str] = []
    for ans in failed_attempts:
        state_reason = str(ans.get("state_reason") or "")
        parse, _contract = classify_answer_by_prompt_contract(ans)
        parse_class = str(parse.get("parse_class") or "unknown")
        if state_reason:
            db_groups.append(db_reason_group(state_reason))
        for group, detail in infer_answer_retry_causes(step_key, ans, parse, state_reason, parse_class):
            if group not in groups:
                groups.append(group)
            evidence.append(detail)
    primary = primary_cause(groups)
    return {
        "primary_retry_cause": primary,
        "retry_cause_groups": groups,
        "retry_cause_evidence": evidence[:12],
        "db_state_reason_groups": sorted(set(db_groups)),
    }

def infer_answer_retry_causes(
    step_key: str,
    ans: dict[str, Any],
    parse: dict[str, Any],
    state_reason: str,
    parse_class: str,
) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    reason_norm = norm_text(state_reason)
    answer_id = ans.get("answer_id")
    if "query_failed" in state_reason or parse_class == "non_json_prose":
        out.append(("provider_or_query_failure", f"answer {answer_id}: query failure or no extractable JSON"))
    if parse_class == "near_complete_missing_closer":
        out.append(("near_complete_json_truncation", f"answer {answer_id}: JSON repairs by appending final closers"))
    if parse_class == "hard_mid_content_truncation":
        out.append(("hard_json_truncation", f"answer {answer_id}: answer stops mid-content"))
    if parse_class == "invalid_json":
        out.append(("invalid_json", f"answer {answer_id}: JSON could not be parsed or repaired"))
    if parse_class == "wrong_top_level_key" or "expected top level key" in reason_norm:
        out.append(("root_contract_mismatch", f"answer {answer_id}: expected root key missing"))
    if parse_class == "empty_or_invalid_top_level":
        out.append(("empty_required_payload", f"answer {answer_id}: required payload empty or unusable"))
    if step_key == "step_5_process_steps":
        shape = process_step_shape_class(parse.get("data"), parse_class)
        if shape in {"prozesse_present_but_no_steps", "flat_fallgruppen_without_steps"}:
            out.append(("process_step_no_steps_returned", f"answer {answer_id}: process-step payload contains no usable steps"))
        if "no process steps parsed" in reason_norm or "missing process steps" in reason_norm:
            out.append(("process_step_missing_expected_steps", f"answer {answer_id}: DB validator reported missing process steps"))
        if "unknown fallgruppen id" in reason_norm or "duplicate fallgruppen id" in reason_norm:
            out.append(("case_group_id_integrity_mismatch", f"answer {answer_id}: fallgruppen_id mismatch in step payload"))
    if step_key == "step_6_effort":
        if "no case group metrics parsed" in reason_norm:
            out.append(("case_group_metrics_missing", f"answer {answer_id}: no case-group metrics parsed"))
        if "unbekannte qualifikation" in reason_norm or "unknown qualifikation" in reason_norm or "unknown qualification" in reason_norm:
            out.append(("unknown_qualification_value", f"answer {answer_id}: unknown qualification value"))
        if "cancelled before applying" in reason_norm:
            out.append(("cancelled_before_apply", f"answer {answer_id}: step was cancelled before applying answer"))
    if not out and "superseded_by_new_attempt" in state_reason:
        out.append(("superseded_previous_attempt_unknown", f"answer {answer_id}: previous attempt superseded; raw cause not recoverable from state reason"))
    if not out and ans.get("answer_state") == "invalid":
        if parse_class == "valid_json":
            out.append(("valid_json_but_db_validation_failed", f"answer {answer_id}: raw JSON valid but DB/update did not accept it"))
        else:
            out.append(("unclassified_invalid_attempt", f"answer {answer_id}: invalid attempt with parse class {parse_class}"))
    return out

def process_step_shape_class(data: Any, parse_class: str) -> str:
    if parse_class == "near_complete_missing_closer":
        return "accept_after_json_repair"
    nested_step_count = 0
    top_level_flat_step_count = 0
    has_prozesse_key = False
    has_top_level_fallgruppen_key = False
    if isinstance(data, dict):
        has_prozesse_key = "prozesse" in data
        processes = data.get("prozesse")
        if isinstance(processes, list):
            for process in processes:
                if not isinstance(process, dict):
                    continue
                fallgruppen = process.get("fallgruppen")
                if not isinstance(fallgruppen, list):
                    continue
                for fallgruppe in fallgruppen:
                    if not isinstance(fallgruppe, dict):
                        continue
                    taetigkeiten = fallgruppe.get("taetigkeiten") or fallgruppe.get("tätigkeiten")
                    if isinstance(taetigkeiten, list):
                        nested_step_count += len([item for item in taetigkeiten if isinstance(item, dict)])
        top_level_fallgruppen = data.get("fallgruppen")
        has_top_level_fallgruppen_key = isinstance(top_level_fallgruppen, list)
        if isinstance(top_level_fallgruppen, list):
            for fallgruppe in top_level_fallgruppen:
                if not isinstance(fallgruppe, dict):
                    continue
                taetigkeiten = fallgruppe.get("taetigkeiten") or fallgruppe.get("tätigkeiten")
                if isinstance(taetigkeiten, list):
                    top_level_flat_step_count += len([item for item in taetigkeiten if isinstance(item, dict)])
        if top_level_flat_step_count and not has_prozesse_key:
            return "expected_flat_fallgruppen"
        if nested_step_count:
            return "expected_nested_prozesse"
        if has_prozesse_key and top_level_flat_step_count:
            return "fallback_reachable_flat_fallgruppen"
        if has_prozesse_key:
            return "prozesse_present_but_no_steps"
        if has_top_level_fallgruppen_key:
            return "flat_fallgruppen_without_steps"
        return "other_json_no_prozesse"
    if isinstance(data, list):
        return "top_level_list"
    return "unparseable"

def db_reason_group(state_reason: str) -> str:
    text = norm_text(state_reason)
    if "superseded by new attempt" in text:
        return "db_superseded_by_new_attempt"
    if "query failed" in text:
        return "db_query_failed"
    if "session update failed" in text:
        return "db_session_update_failed"
    if "waiting for paired retry" in text:
        return "db_waiting_for_paired_retry"
    if "session reverted" in text:
        return "db_session_reverted"
    return retry_safe_key(state_reason)[:80] or "db_unknown"

def retry_safe_key(value: Any) -> str:
    text = norm_text(value)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "unknown"

def primary_cause(groups: list[str]) -> str:
    if not groups:
        return "no_failed_attempt_before_success"
    priority = [
        "unknown_qualification_value",
        "case_group_metrics_missing",
        "case_group_id_integrity_mismatch",
        "process_step_missing_expected_steps",
        "process_step_no_steps_returned",
        "root_contract_mismatch",
        "near_complete_json_truncation",
        "hard_json_truncation",
        "invalid_json",
        "provider_or_query_failure",
        "empty_required_payload",
        "cancelled_before_apply",
        "valid_json_but_db_validation_failed",
        "superseded_previous_attempt_unknown",
        "unclassified_invalid_attempt",
    ]
    for candidate in priority:
        if candidate in groups:
            return candidate
    return groups[0]

def next_step_state_present(data: dict[str, list[dict[str, Any]]], sid: int, step_key: str, addressee: str) -> bool:
    if step_key == "step_1_summary":
        return any(int_or_none(row.get("session_id")) == sid for row in data["regulations"])
    if step_key == "step_2_regulations":
        return any(int_or_none(row.get("session_id")) == sid for row in data["processes"])
    if step_key == "step_3_processes":
        return any(int_or_none(row.get("session_id")) == sid and same_addressee(row.get("norm_addressee"), addressee) for row in data["case_groups"])
    if step_key == "step_4_case_groups":
        return any(int_or_none(row.get("session_id")) == sid and same_addressee(row.get("norm_addressee"), addressee) for row in data["process_steps"])
    if step_key == "step_5_process_steps":
        return any(int_or_none(row.get("session_id")) == sid and same_addressee(row.get("norm_addressee"), addressee) for row in data["process_steps"])
    if step_key == "step_6_effort":
        return any(
            int_or_none(row.get("session_id")) == sid
            and same_addressee(row.get("norm_addressee"), addressee)
            and (safe_float(row.get("cost_current")) is not None or safe_float(row.get("cost_proposed")) is not None)
            for row in data["process_steps"]
        )
    return False

def same_addressee(left: Any, right: Any) -> bool:
    if right in (None, "", "global", "unknown"):
        return True
    return str(left or "") == str(right)

def first_present(rows: list[dict[str, Any]], key: str) -> Any:
    for row in rows:
        if row.get(key) not in (None, ""):
            return row.get(key)
    return None

def retry_pressure_fieldnames() -> list[str]:
    return [
        "session_id", "app_session_id", "week", "session_created_week", "law_pair",
        "model", "step_key", "step_label", "norm_addressee", "episode_index",
        "first_attempt_at", "last_attempt_at", "success_at", "succeeded",
        "terminal_state", "next_state_reached", "prompt_attempt_count",
        "required_prompt_count", "attempt_rounds_to_success_or_terminal",
        "retry_rounds_to_success", "post_success_attempt_count",
        "cases_attempt_count", "effort_attempt_count", "prompt_ids", "answer_ids",
        "answer_states", "parse_classes",
        "primary_retry_cause", "retry_cause_groups", "retry_cause_evidence",
        "db_state_reason_groups", "failed_answer_ids_before_success",
    ]

def analyze_issue_03(data: dict[str, list[dict[str, Any]]], out_dir: Path) -> list[dict[str, Any]]:
    maps = session_maps(data)
    findings: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    process_step_shape_rows: list[dict[str, Any]] = []
    step_6_shape_rows: list[dict[str, Any]] = []
    raw_change_status_rows: list[dict[str, Any]] = []
    for ans in data["llm_answers"]:
        if ans.get("prompt_id") not in REQUIRED_TOP_LEVEL:
            continue
        sid = int_or_none(ans.get("session_id"))
        session = maps["sessions"].get(sid or -1, {"session_id": sid})
        cls, contract = classify_answer_by_prompt_contract(ans)
        quality_row = {
            "answer_id": ans.get("answer_id"),
            "session_id": sid,
            "app_session_id": session.get("app_session_id"),
            "answer_week": iso_week(ans.get("created_at")),
            "prompt_id": ans.get("prompt_id"),
            "model": ans.get("model"),
            "norm_addressee": answer_addressee(ans),
            "answer_state": ans.get("answer_state"),
            "state_reason": ans.get("state_reason"),
            "db_outcome": answer_db_outcome(ans),
            "prompt_contract_kind": contract["prompt_contract_kind"],
            "prompt_required_root_key": contract["prompt_required_root_key"],
            "prompt_contract_matches_current_checker": contract_matches_current_checker(contract["prompt_required_root_key"], cls.get("required_key")),
            "answer_matches_prompt_root": answer_matches_prompt_root(cls.get("data"), contract["prompt_required_root_key"]),
            "prompt_requests_json_only": contract["prompt_requests_json_only"],
            "prompt_mentions_json_schema": contract["prompt_mentions_json_schema"],
            "provider_response_format_requested": contract["provider_response_format_requested"],
            "provider_response_format_used": contract["provider_response_format_used"],
            "provider_response_format_downgraded": contract["provider_response_format_downgraded"],
            "provider_response_schema_name": contract["provider_response_schema_name"],
            "provider_response_schema_root_key": contract["provider_response_schema_root_key"],
            "provider_response_schema_sha256": contract["provider_response_schema_sha256"],
            "parse_class": cls["parse_class"],
            "syntax_class": cls.get("syntax_class"),
            "schema_class": cls.get("schema_class"),
            "extraction_method": cls.get("extraction_method"),
            "required_key": cls.get("required_key"),
            "backend_rejection_group": backend_rejection_group(ans.get("state_reason")),
            "repair_suffix": cls.get("repair_suffix"),
            "tail": cls.get("tail"),
        }
        quality_rows.append(quality_row)
        if ans.get("prompt_id") == "process_step_analysis":
            shape_row = process_step_shape_row(ans, session, cls)
            process_step_shape_rows.append(shape_row)
        if ans.get("prompt_id") in STRUCTURAL_NORM_PROMPTS:
            raw_change_status_rows.extend(raw_change_status_quality_rows(ans, session, cls))
        if ans.get("prompt_id") in {"cases_calculation", "effort_calculation"}:
            step_6_shape_rows.append(step_6_shape_row(ans, session, cls))
        if cls["parse_class"] not in {"valid_json"}:
            severity = "high" if cls["parse_class"] in {"wrong_top_level_key", "empty_or_invalid_top_level", "hard_mid_content_truncation", "invalid_json"} else "medium"
            classification = "bad"
            if (
                cls["parse_class"] == "wrong_top_level_key"
                and quality_row.get("prompt_contract_matches_current_checker") == "no"
                and quality_row.get("answer_matches_prompt_root") == "yes"
            ):
                classification = "diagnostic"
                severity = "low"
            findings.append(finding(
                "issue_03_json_truncation", session, classification, severity,
                f"Raw LLM answer JSON quality issue: {cls['parse_class']}.",
                quality_row,
                ans,
            ))
    write_csv(out_dir / "findings" / "issue_03_answer_quality.csv", quality_rows)
    write_csv(out_dir / "findings" / "issue_03_process_step_shape.csv", process_step_shape_rows)
    write_csv(out_dir / "findings" / "issue_03_step_6_shape.csv", step_6_shape_rows)
    write_csv(out_dir / "findings" / "issue_04_raw_change_status_quality.csv", raw_change_status_rows)
    return findings

def raw_change_status_quality_rows(
    ans: dict[str, Any],
    session: dict[str, Any],
    cls: dict[str, Any],
) -> list[dict[str, Any]]:
    data = cls.get("data")
    if not isinstance(data, dict):
        return []
    rows = []
    for entity in raw_change_status_entities(str(ans.get("prompt_id") or ""), data):
        key, raw_value = raw_change_status_value(entity["raw"])
        bucket = raw_change_status_bucket(raw_value)
        rows.append({
            "answer_id": ans.get("answer_id"),
            "session_id": ans.get("session_id"),
            "app_session_id": session.get("app_session_id"),
            "answer_week": iso_week(ans.get("created_at")),
            "created_at": ans.get("created_at"),
            "prompt_id": ans.get("prompt_id"),
            "model": ans.get("model"),
            "norm_addressee": entity.get("norm_addressee") or answer_addressee(ans),
            "answer_state": ans.get("answer_state"),
            "state_reason": ans.get("state_reason"),
            "entity_type": entity.get("entity_type"),
            "entity_name": entity.get("entity_name"),
            "raw_status_key": key,
            "raw_status_value": raw_value,
            "normalized_raw_status": norm_text(raw_value),
            "status_bucket": bucket,
        })
    return rows

def raw_change_status_entities(prompt_id: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    if prompt_id == "process_compilation":
        rows = []
        for process in collect_processes(data):
            rows.append({
                "entity_type": "process",
                "entity_name": process.get("process"),
                "norm_addressee": process.get("norm_addressee"),
                "raw": process["raw"],
            })
        return rows
    if prompt_id == "case_group_development":
        return [
            {
                "entity_type": "case_group",
                "entity_name": group.get("case_group"),
                "norm_addressee": group.get("norm_addressee"),
                "raw": group["raw"],
            }
            for group in collect_case_groups(data)
        ]
    if prompt_id == "process_step_analysis":
        return [
            {
                "entity_type": "process_step",
                "entity_name": step.get("step"),
                "norm_addressee": step.get("norm_addressee"),
                "raw": step["raw"],
            }
            for step in collect_steps(data)
        ]
    return []

def raw_change_status_value(raw: dict[str, Any]) -> tuple[str, Any]:
    for key in CHANGE_STATUS_KEYS:
        if key in raw:
            return key, raw.get(key)
    return "", None

def raw_change_status_bucket(raw_value: Any) -> str:
    if raw_value in (None, ""):
        return "missing"
    normalized = norm_text(raw_value)
    if normalized in VALID_RAW_CHANGE_STATUSES:
        return "present_valid"
    return "present_unrecognized"

def classify_answer_by_prompt_contract(ans: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = prompt_contract_info(ans)
    required_key = contract["prompt_required_root_key"]
    cls = classify_json_answer(
        ans.get("answer_text"),
        str(ans.get("prompt_id") or ""),
        required_key=str(required_key) if required_key else None,
    )
    return cls, contract

def answer_db_outcome(ans: dict[str, Any]) -> str:
    state = str(ans.get("answer_state") or "")
    reason = str(ans.get("state_reason") or "")
    if state == "active" and reason == "session_updated":
        return "accepted_into_session_state"
    if "session_update_failed" in reason:
        return "rejected_by_session_update"
    if "query_failed" in reason:
        return "query_or_provider_failed"
    if "superseded_by_new_attempt" in reason:
        return "superseded_by_retry"
    if "session_reverted" in reason:
        return "reverted_by_user"
    if "waiting_for_paired_retry" in reason:
        return "waiting_for_paired_retry"
    if state == "invalid":
        return "invalid_other"
    return "unknown"

def backend_rejection_group(state_reason: Any) -> str:
    raw = str(state_reason or "").lower()
    text = norm_text(state_reason)
    if not text:
        return ""
    if (
        "session_update_failed" not in raw
        and "session update failed" not in text
        and "apply_failed" not in raw
        and "apply failed" not in text
        and "query_failed" not in raw
        and "query failed" not in text
    ):
        return ""
    if "duplicate" in text and ("fallgruppen_id" in raw or "fallgruppen id" in text or "case_group" in raw or "case group" in text):
        return "duplicate_case_group_ids"
    if "duplicate" in text and ("taetigkeiten_id" in raw or "taetigkeiten id" in text or "step" in text):
        return "duplicate_step_ids"
    if "unknown" in text and ("fallgruppen_id" in raw or "fallgruppen id" in text or "case_group" in raw or "case group" in text):
        return "unknown_case_group_ids"
    if "unknown" in text and ("taetigkeiten_id" in raw or "taetigkeiten id" in text or "step" in text):
        return "unknown_step_ids"
    if "missing" in text and ("fallgruppen_id" in raw or "fallgruppen id" in text or "case_group" in raw or "case group" in text):
        return "missing_case_group_ids"
    if "missing" in text and ("taetigkeiten_id" in raw or "taetigkeiten id" in text or "process step" in text or "step" in text):
        return "missing_step_ids"
    if "no case group metrics parsed" in text:
        return "no_case_group_metrics"
    if "no effort metrics parsed" in text:
        return "no_effort_metrics"
    if "no process steps parsed" in text:
        return "no_process_steps"
    if "no processes parsed" in text:
        return "no_processes"
    if "expected top level key" in text or "top_level" in text:
        return "root_contract_mismatch"
    if "provider" in text or "quota" in text or "api key" in text:
        return "provider_or_credentials"
    return "other_session_update_rejection"

def prompt_contract_info(ans: dict[str, Any]) -> dict[str, Any]:
    prompt_id = str(ans.get("prompt_id") or "")
    prompt_text = str(ans.get("prompt_text") or "")
    metadata = parse_json_maybe(ans.get("metadata"))
    if not isinstance(metadata, dict):
        metadata = {}
    requested = metadata.get("response_format_requested")
    used = metadata.get("response_format_used")
    downgraded = metadata.get("response_format_downgraded")
    prompt_requests_json_only = bool(re.search(
        r"nur\s+und\s+ausschliesslich\s+json|nur\s+und\s+ausschließlich\s+json|only\s+json",
        prompt_text,
        flags=re.IGNORECASE,
    ))
    prompt_mentions_schema = bool(re.search(
        r"json[-_ ]?schema|schema",
        prompt_text,
        flags=re.IGNORECASE,
    ))
    required_root = (
        response_format_root_key(used)
        or response_format_root_key(requested)
        or str(metadata.get("response_schema_root_key") or "").strip()
        or infer_prompt_required_root_key(prompt_text)
        or REQUIRED_TOP_LEVEL.get(prompt_id)
    )
    if response_format_type(used) == "json_schema" or response_format_type(requested) == "json_schema":
        kind = "provider_json_schema"
    elif response_format_type(used) == "json_object" or response_format_type(requested) == "json_object":
        kind = "provider_json_object"
    elif prompt_mentions_schema:
        kind = "prompt_level_json_schema"
    elif prompt_requests_json_only or required_root:
        kind = "prompt_level_json_object"
    else:
        kind = "no_structured_json_contract_detected"
    return {
        "prompt_contract_kind": kind,
        "prompt_required_root_key": required_root,
        "prompt_requests_json_only": int(prompt_requests_json_only),
        "prompt_mentions_json_schema": int(prompt_mentions_schema),
        "provider_response_format_requested": compact_json_value(requested),
        "provider_response_format_used": compact_json_value(used),
        "provider_response_format_downgraded": compact_json_value(downgraded),
        "provider_response_schema_name": str(metadata.get("response_schema_name") or ""),
        "provider_response_schema_root_key": str(metadata.get("response_schema_root_key") or ""),
        "provider_response_schema_sha256": str(metadata.get("response_schema_sha256") or ""),
    }

def response_format_type(value: Any) -> str | None:
    if isinstance(value, str):
        parsed = parse_json_maybe(value)
        if isinstance(parsed, dict):
            value = parsed
        else:
            return value.strip() or None
    if isinstance(value, dict):
        direct = value.get("type")
        if isinstance(direct, str):
            return direct
        nested = value.get("format")
        if isinstance(nested, dict) and isinstance(nested.get("type"), str):
            return str(nested.get("type"))
    return None

def response_format_root_key(value: Any) -> str | None:
    if isinstance(value, str):
        parsed = parse_json_maybe(value)
        if isinstance(parsed, dict):
            value = parsed
        else:
            return None
    if not isinstance(value, dict):
        return None
    schema = value.get("schema")
    nested = value.get("json_schema")
    if not isinstance(schema, dict) and isinstance(nested, dict):
        schema = nested.get("schema")
    if not isinstance(schema, dict):
        return None
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return None
    for key in ("vorgaben", "prozesse", "fallgruppen", "taetigkeiten"):
        if key in properties:
            return key
    return None

def compact_json_value(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)

def infer_prompt_required_root_key(prompt_text: str) -> str | None:
    if not prompt_text:
        return None
    marker_matches = list(re.finditer(
        r"Geben Sie nur und ausschliesslich JSON(?:\s+(?:im folgenden Format|in genau dieser Struktur))?\s+zurueck:?|Geben Sie nur und ausschließlich JSON(?:\s+(?:im folgenden Format|in genau dieser Struktur))?\s+zurück:?",
        prompt_text,
        flags=re.IGNORECASE,
    ))
    if marker_matches:
        marker_match = marker_matches[-1]
        sample = prompt_text[marker_match.end(): marker_match.end() + 2400]
    else:
        sample = prompt_text
    sample = sample.replace("{{", "{").replace("}}", "}")
    first_brace = sample.find("{")
    if first_brace >= 0:
        sample = sample[first_brace:first_brace + 1400]
    positions = {
        key: sample.find(f'"{key}"')
        for key in ("vorgaben", "prozesse", "fallgruppen", "taetigkeiten")
        if sample.find(f'"{key}"') >= 0
    }
    if not positions:
        return None
    return min(positions.items(), key=lambda item: item[1])[0]

def contract_matches_current_checker(prompt_required_root: Any, current_required_root: Any) -> str:
    prompt_root = str(prompt_required_root or "")
    current_root = str(current_required_root or "")
    if not prompt_root or not current_root:
        return ""
    return "yes" if prompt_root == current_root else "no"

def answer_matches_prompt_root(data: Any, prompt_required_root: Any) -> str:
    root = str(prompt_required_root or "")
    if not root:
        return ""
    if isinstance(data, dict):
        return "yes" if root in data else "no"
    return "no"

def process_step_shape_row(
    ans: dict[str, Any],
    session: dict[str, Any],
    cls: dict[str, Any],
) -> dict[str, Any]:
    data = cls.get("data")
    nested_step_count = 0
    top_level_flat_step_count = 0
    has_prozesse_key = False
    has_top_level_fallgruppen_key = False
    shape_class = "unparseable"
    if isinstance(data, dict):
        has_prozesse_key = "prozesse" in data
        processes = data.get("prozesse")
        if isinstance(processes, list):
            for process in processes:
                if not isinstance(process, dict):
                    continue
                fallgruppen = process.get("fallgruppen")
                if not isinstance(fallgruppen, list):
                    continue
                for fallgruppe in fallgruppen:
                    if not isinstance(fallgruppe, dict):
                        continue
                    taetigkeiten = fallgruppe.get("taetigkeiten") or fallgruppe.get("tätigkeiten")
                    if isinstance(taetigkeiten, list):
                        nested_step_count += len([item for item in taetigkeiten if isinstance(item, dict)])
        top_level_fallgruppen = data.get("fallgruppen")
        has_top_level_fallgruppen_key = isinstance(top_level_fallgruppen, list)
        if isinstance(top_level_fallgruppen, list):
            for fallgruppe in top_level_fallgruppen:
                if not isinstance(fallgruppe, dict):
                    continue
                taetigkeiten = fallgruppe.get("taetigkeiten") or fallgruppe.get("tätigkeiten")
                if isinstance(taetigkeiten, list):
                    top_level_flat_step_count += len([item for item in taetigkeiten if isinstance(item, dict)])

        if top_level_flat_step_count and not has_prozesse_key:
            shape_class = "expected_flat_fallgruppen"
        elif nested_step_count:
            shape_class = "expected_nested_prozesse"
        elif has_prozesse_key and top_level_flat_step_count:
            shape_class = "fallback_reachable_flat_fallgruppen"
        elif has_prozesse_key:
            shape_class = "prozesse_present_but_no_steps"
        elif has_top_level_fallgruppen_key:
            shape_class = "flat_fallgruppen_without_steps"
        else:
            shape_class = "other_json_no_prozesse"
    elif isinstance(data, list):
        shape_class = "top_level_list"

    current_code_acceptance = "reject"
    if shape_class in {"expected_flat_fallgruppen", "expected_nested_prozesse", "fallback_reachable_flat_fallgruppen"}:
        current_code_acceptance = "accept"
    elif shape_class == "unparseable" and cls.get("parse_class") == "near_complete_missing_closer":
        current_code_acceptance = "accept_after_json_repair"

    persisted_outcome = "not_applied"
    if ans.get("answer_state") == "active" and ans.get("state_reason") == "session_updated":
        persisted_outcome = "applied"
    elif ans.get("answer_state") == "invalid":
        persisted_outcome = "invalid_or_reverted"

    return {
        "answer_id": ans.get("answer_id"),
        "session_id": ans.get("session_id"),
        "app_session_id": session.get("app_session_id"),
        "answer_week": iso_week(ans.get("created_at")),
        "created_at": ans.get("created_at"),
        "model": ans.get("model"),
        "norm_addressee": answer_addressee(ans),
        "answer_state": ans.get("answer_state"),
        "state_reason": ans.get("state_reason"),
        "parse_class": cls.get("parse_class"),
        "shape_class": shape_class,
        "current_code_acceptance": current_code_acceptance,
        "persisted_outcome": persisted_outcome,
        "has_prozesse_key": has_prozesse_key,
        "has_top_level_fallgruppen_key": has_top_level_fallgruppen_key,
        "nested_step_count": nested_step_count,
        "top_level_flat_step_count": top_level_flat_step_count,
        "tail": cls.get("tail"),
    }

def step_6_shape_row(
    ans: dict[str, Any],
    session: dict[str, Any],
    cls: dict[str, Any],
) -> dict[str, Any]:
    data = cls.get("data")
    prompt_id = str(ans.get("prompt_id") or "")
    has_prozesse_key = False
    has_top_level_fallgruppen_key = False
    flat_group_count = 0
    legacy_nested_group_count = 0
    metric_entity_count = 0
    shape_class = "unparseable"
    if isinstance(data, dict):
        has_prozesse_key = "prozesse" in data
        top_level_fallgruppen = data.get("fallgruppen")
        has_top_level_fallgruppen_key = isinstance(top_level_fallgruppen, list)
        if isinstance(top_level_fallgruppen, list):
            flat_group_count = len([item for item in top_level_fallgruppen if isinstance(item, dict)])
        processes = data.get("prozesse")
        if isinstance(processes, list):
            for process in processes:
                if not isinstance(process, dict):
                    continue
                groups = process.get("fallgruppen")
                if isinstance(groups, list):
                    legacy_nested_group_count += len([item for item in groups if isinstance(item, dict)])
        metric_entity_count = len(collect_change_metric_entities(data))
        if has_top_level_fallgruppen_key and metric_entity_count:
            shape_class = "expected_flat_fallgruppen"
        elif has_top_level_fallgruppen_key:
            shape_class = "flat_fallgruppen_without_metrics"
        elif has_prozesse_key and metric_entity_count:
            shape_class = "legacy_nested_prozesse"
        elif has_prozesse_key:
            shape_class = "prozesse_present_without_metrics"
        else:
            shape_class = "other_json_no_fallgruppen"
    elif isinstance(data, list):
        shape_class = "top_level_list"

    current_code_acceptance = "accept" if shape_class in {"expected_flat_fallgruppen", "legacy_nested_prozesse"} else "reject"
    if shape_class == "unparseable" and cls.get("parse_class") == "near_complete_missing_closer":
        current_code_acceptance = "accept_after_json_repair"
    persisted_outcome = "not_applied"
    if ans.get("answer_state") == "active" and ans.get("state_reason") == "session_updated":
        persisted_outcome = "applied"
    elif ans.get("answer_state") == "invalid":
        persisted_outcome = "invalid_or_reverted"

    return {
        "answer_id": ans.get("answer_id"),
        "session_id": ans.get("session_id"),
        "app_session_id": session.get("app_session_id"),
        "answer_week": iso_week(ans.get("created_at")),
        "created_at": ans.get("created_at"),
        "prompt_id": prompt_id,
        "model": ans.get("model"),
        "norm_addressee": answer_addressee(ans),
        "answer_state": ans.get("answer_state"),
        "state_reason": ans.get("state_reason"),
        "parse_class": cls.get("parse_class"),
        "shape_class": shape_class,
        "current_code_acceptance": current_code_acceptance,
        "persisted_outcome": persisted_outcome,
        "has_prozesse_key": has_prozesse_key,
        "has_top_level_fallgruppen_key": has_top_level_fallgruppen_key,
        "flat_group_count": flat_group_count,
        "legacy_nested_group_count": legacy_nested_group_count,
        "metric_entity_count": metric_entity_count,
        "tail": cls.get("tail"),
    }

def analyze_issue_09(data: dict[str, list[dict[str, Any]]], out_dir: Path) -> list[dict[str, Any]]:
    maps = session_maps(data)
    findings: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for ans in data["llm_answers"]:
        if ans.get("prompt_id") != "compliance_text_extraction":
            continue
        sid = int_or_none(ans.get("session_id"))
        session = maps["sessions"].get(sid or -1, {"session_id": sid})
        row = compliance_export_quality_row(ans, session)
        rows.append(row)
        if row["quality_class"] in {"empty_export", "leaked_prompt_or_json_artifact"}:
            findings.append(finding(
                "issue_09_compliance_export_quality",
                session,
                "bad",
                "medium" if row["quality_class"] == "leaked_prompt_or_json_artifact" else "high",
                f"Compliance export Markdown quality issue: {row['quality_class']}.",
                row,
                ans,
            ))
    write_csv(out_dir / "findings" / "issue_09_compliance_export_quality.csv", rows)
    return findings

def compliance_export_quality_row(ans: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
    text = str(ans.get("answer_text") or "")
    stripped = text.strip()
    lower = stripped.lower()
    has_expected_heading = bool(re.search(r"^\s*#\s*e\.\s*erf(?:ü|u|ue)llungsaufwand", stripped, flags=re.IGNORECASE))
    has_section_four = bool(re.search(r"(^|\n)\s*#{1,6}\s*4\.", stripped))
    has_markdown_table = "|" in stripped and "lfd" in norm_text(stripped)
    leaked_json = bool(re.search(r"```json|\"session_json\"|\"prompt\"|\"arbeitsauftrag\"", lower))
    leaked_template = bool(re.search(r"\{[a-z_]+\}", stripped))
    if not stripped:
        quality_class = "empty_export"
    elif leaked_json or leaked_template:
        quality_class = "leaked_prompt_or_json_artifact"
    elif has_expected_heading:
        quality_class = "expected_markdown"
    else:
        quality_class = "markdown_needs_review"
    return {
        "answer_id": ans.get("answer_id"),
        "session_id": ans.get("session_id"),
        "app_session_id": session.get("app_session_id"),
        "answer_week": iso_week(ans.get("created_at")),
        "created_at": ans.get("created_at"),
        "model": ans.get("model"),
        "answer_state": ans.get("answer_state"),
        "state_reason": ans.get("state_reason"),
        "quality_class": quality_class,
        "has_expected_heading": has_expected_heading,
        "has_section_four_heading": has_section_four,
        "has_markdown_table": has_markdown_table,
        "leaked_json_or_prompt_marker": leaked_json,
        "leaked_template_marker": leaked_template,
        "text_length": len(stripped),
    }

def analyze_issue_04(data: dict[str, list[dict[str, Any]]], out_dir: Path) -> list[dict[str, Any]]:
    maps = session_maps(data)
    findings: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    hierarchy_rows: list[dict[str, Any]] = []
    for ans in data["llm_answers"]:
        if ans.get("prompt_id") not in {"case_group_development", "process_step_analysis", "cases_calculation", "effort_calculation"}:
            continue
        cls = classify_json_answer(ans.get("answer_text"), str(ans.get("prompt_id") or ""))
        if not cls.get("data"):
            continue
        sid = int_or_none(ans.get("session_id"))
        session = maps["sessions"].get(sid or -1, {"session_id": sid})
        for entity in collect_change_metric_entities(cls["data"]):
            reason = status_inconsistency(entity.get("change_status"), entity.get("current_value"), entity.get("proposed_value"))
            quality_rows.append(change_status_quality_row(
                session=session,
                source="raw_llm_answer",
                entity=entity,
                current=entity.get("current_value"),
                proposed=entity.get("proposed_value"),
                reason=reason,
                answer=ans,
            ))
            if reason:
                findings.append(finding(
                    "issue_04_change_status_inconsistency", session, "bad", "medium",
                    "Raw answer change status conflicts with current/proposed values.",
                    {
                        **entity,
                        "reason": reason,
                        "source": "raw_llm_answer",
                        "parser_persistence_discrepancy": None,
                    },
                    ans,
                ))
    for row in data["case_groups"]:
        session = maps["sessions"].get(int_or_none(row.get("session_id")) or -1, {"session_id": row.get("session_id")})
        current = case_group_cases(row, "current")
        proposed = case_group_cases(row, "proposed")
        reason = status_inconsistency(normalize_status(row.get("change_status")), current, proposed)
        entity = {
            "entity_type": "case_group",
            "entity_id": row.get("case_group_id"),
            "entity_name": row.get("case_group"),
            "norm_addressee": row.get("norm_addressee"),
            "change_status": normalize_status(row.get("change_status")),
        }
        quality_rows.append(change_status_quality_row(
            session=session,
            source="persisted_case_groups",
            entity=entity,
            current=current,
            proposed=proposed,
            reason=reason,
        ))
        if reason:
            findings.append(finding(
                "issue_04_change_status_inconsistency", session, "bad", "medium",
                "Persisted case-group change status conflicts with current/proposed values.",
                {
                    **entity,
                    "persisted_current_metrics": current,
                    "persisted_proposed_metrics": proposed,
                    "reason": reason,
                    "source": "persisted_case_groups",
                },
            ))
    for row in data["process_steps"]:
        session = maps["sessions"].get(int_or_none(row.get("session_id")) or -1, {"session_id": row.get("session_id")})
        current = persisted_step_effort(row, "current")
        proposed = persisted_step_effort(row, "proposed")
        reason = status_inconsistency(normalize_status(row.get("change_status")), current, proposed)
        entity = {
            "entity_type": "process_step",
            "entity_id": row.get("step_id"),
            "entity_name": row.get("step"),
            "norm_addressee": row.get("norm_addressee"),
            "change_status": normalize_status(row.get("change_status")),
        }
        quality_rows.append(change_status_quality_row(
            session=session,
            source="persisted_process_steps",
            entity=entity,
            current=current,
            proposed=proposed,
            reason=reason,
        ))
        if reason:
            findings.append(finding(
                "issue_04_change_status_inconsistency", session, "bad", "medium",
                "Persisted process-step change status conflicts with current/proposed effort values.",
                {
                    **entity,
                    "persisted_current_metrics": current,
                    "persisted_proposed_metrics": proposed,
                    "reason": reason,
                    "source": "persisted_process_steps",
                },
            ))
    for row in change_status_hierarchy_rows(data, maps):
        hierarchy_rows.append(row)
        if row.get("check_result") != "consistent":
            session = maps["sessions"].get(int_or_none(row.get("session_id")) or -1, {"session_id": row.get("session_id")})
            findings.append(finding(
                "issue_04_change_status_inconsistency", session, "bad", "medium",
                "Persisted parent/child change statuses are inconsistent.",
                {
                    "source": "persisted_status_hierarchy",
                    "reason": row.get("check_result"),
                    "parent_type": row.get("parent_type"),
                    "parent_id": row.get("parent_id"),
                    "parent_name": row.get("parent_name"),
                    "parent_status": row.get("parent_status"),
                    "child_type": row.get("child_type"),
                    "child_status_counts": row.get("child_status_counts"),
                    "norm_addressee": row.get("norm_addressee"),
                },
            ))
    write_csv(out_dir / "findings" / "issue_04_change_status_quality.csv", quality_rows)
    write_csv(out_dir / "findings" / "issue_04_change_status_hierarchy.csv", hierarchy_rows)
    return findings

def change_status_hierarchy_rows(
    data: dict[str, list[dict[str, Any]]],
    maps: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    case_groups_by_process = group_by(data["case_groups"], "process_id")
    steps_by_group = group_by(data["process_steps"], "case_group_id")
    for process in data["processes"]:
        children = case_groups_by_process.get(process.get("process_id"), [])
        rows.extend(parent_child_status_rows(
            parent=process,
            children=children,
            session=maps["sessions"].get(int_or_none(process.get("session_id")) or -1, {"session_id": process.get("session_id")}),
            parent_type="process",
            parent_id_key="process_id",
            parent_name_key="process",
            child_type="case_group",
        ))
    for group in data["case_groups"]:
        children = steps_by_group.get(group.get("case_group_id"), [])
        rows.extend(parent_child_status_rows(
            parent=group,
            children=children,
            session=maps["sessions"].get(int_or_none(group.get("session_id")) or -1, {"session_id": group.get("session_id")}),
            parent_type="case_group",
            parent_id_key="case_group_id",
            parent_name_key="case_group",
            child_type="process_step",
        ))
    return rows

def parent_child_status_rows(
    *,
    parent: dict[str, Any],
    children: list[dict[str, Any]],
    session: dict[str, Any],
    parent_type: str,
    parent_id_key: str,
    parent_name_key: str,
    child_type: str,
) -> list[dict[str, Any]]:
    parent_status = normalize_status(parent.get("change_status"))
    parent_group = lifecycle_group(parent_status)
    child_counts: dict[str, int] = {}
    for child in children:
        child_group = lifecycle_group(normalize_status(child.get("change_status")))
        child_counts[child_group] = child_counts.get(child_group, 0) + 1
    if not children or parent_group not in {"introduced", "abolished"}:
        return []
    mismatching = {key: value for key, value in child_counts.items() if key not in {parent_group, "unknown"}}
    if mismatching:
        result = f"{parent_group}_parent_has_{child_type}_with_other_status"
    else:
        result = "consistent"
    return [{
        "session_id": session.get("session_id"),
        "app_session_id": session.get("app_session_id"),
        "week": iso_week(session.get("created_at")),
        "law_pair": law_pair_key(session),
        "model": session.get("llm_model"),
        "norm_addressee": parent.get("norm_addressee"),
        "parent_type": parent_type,
        "parent_id": parent.get(parent_id_key),
        "parent_name": parent.get(parent_name_key),
        "parent_status": parent_status,
        "parent_status_group": parent_group,
        "child_type": child_type,
        "child_count": len(children),
        "child_status_counts": child_counts,
        "check_result": result,
    }]

def lifecycle_group(value: Any) -> str:
    text = norm_text(value)
    if "eingefuehrt" in text or text in {"introduced", "new", "neu"}:
        return "introduced"
    if "abgeschafft" in text or "abolished" in text or "wegfall" in text:
        return "abolished"
    if "geaendert" in text or "changed" in text or "geandert" in text:
        return "changed"
    return "unknown"

def change_status_quality_row(
    *,
    session: dict[str, Any],
    source: str,
    entity: dict[str, Any],
    current: Any,
    proposed: Any,
    reason: str | None,
    answer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    status = entity.get("change_status")
    evaluable = bool(status) and safe_float(current) is not None and safe_float(proposed) is not None
    return {
        "session_id": session.get("session_id"),
        "app_session_id": session.get("app_session_id"),
        "week": iso_week((answer or {}).get("created_at") or session.get("created_at")),
        "session_created_at": session.get("created_at"),
        "law_pair": law_pair_key(session),
        "model": session.get("llm_model") or (answer or {}).get("model"),
        "answer_id": (answer or {}).get("answer_id"),
        "answer_created_at": (answer or {}).get("created_at"),
        "prompt_id": (answer or {}).get("prompt_id"),
        "source": source,
        "entity_type": entity.get("entity_type"),
        "entity_id": entity.get("entity_id") or entity.get("case_group_id") or entity.get("step_id"),
        "entity_name": entity.get("entity_name"),
        "norm_addressee": entity.get("norm_addressee") or (answer_addressee(answer) if answer else None),
        "change_status": status,
        "current_value": safe_float(current),
        "proposed_value": safe_float(proposed),
        "evaluable": evaluable,
        "check_result": reason or ("consistent" if evaluable else "not_evaluable"),
    }

def analyze_issue_05(data: dict[str, list[dict[str, Any]]], out_dir: Path) -> list[dict[str, Any]]:
    maps = session_maps(data)
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for session in data["sessions"]:
        key = (
            law_pair_key(session),
            str(session.get("llm_model") or "unknown"),
            session_deep_research_mode(data, session),
        )
        if "none" in key[0]:
            continue
        groups.setdefault(key, []).append(session)
    pair_rows: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for (law_pair, model, deep_research_mode), sessions in groups.items():
        if len(sessions) < 2:
            continue
        sessions = sorted(sessions, key=lambda s: str(s.get("created_at") or ""))
        fingerprints = {int(s["session_id"]): structure_fingerprint(data, int(s["session_id"])) for s in sessions}
        for i, left in enumerate(sessions):
            for right in sessions[i + 1:]:
                lsid = int(left["session_id"])
                rsid = int(right["session_id"])
                sims = {
                    layer: jaccard(fingerprints[lsid].get(layer, set()), fingerprints[rsid].get(layer, set()))
                    for layer in ("regulations", "processes", "case_groups", "process_steps")
                }
                mean_sim = statistics.mean(sims.values()) if sims else 1.0
                row = {
                    "law_pair": law_pair,
                    "model": model,
                    "deep_research_mode": deep_research_mode,
                    "left_session_id": lsid,
                    "right_session_id": rsid,
                    "left_created_at": left.get("created_at"),
                    "right_created_at": right.get("created_at"),
                    "mean_similarity": mean_sim,
                    **{f"{layer}_similarity": value for layer, value in sims.items()},
                    **{f"{layer}_left_count": len(fingerprints[lsid].get(layer, set())) for layer in sims},
                    **{f"{layer}_right_count": len(fingerprints[rsid].get(layer, set())) for layer in sims},
                }
                pair_rows.append(row)
                if mean_sim < 0.65:
                    findings.append(finding(
                        "issue_05_structure_consistency", right, "bad", "medium",
                        "Same law pair/model produced materially different persisted structures.",
                        row,
                    ))
    write_csv(out_dir / "findings" / "issue_05_pairwise_structure_similarity.csv", pair_rows)
    return findings

def structure_fingerprint(data: dict[str, list[dict[str, Any]]], sid: int) -> dict[str, set[str]]:
    process_names = {
        int(p["process_id"]): norm_text(p.get("process"))
        for p in data["processes"]
        if int_or_none(p.get("session_id")) == sid and p.get("process_id") is not None
    }
    case_group_names = {
        int(g["case_group_id"]): (
            norm_text(g.get("case_group")),
            process_names.get(int_or_none(g.get("process_id")) or -1, ""),
        )
        for g in data["case_groups"]
        if int_or_none(g.get("session_id")) == sid and g.get("case_group_id") is not None
    }
    regs = {
        norm_text(f"{r.get('legal_citation')} {r.get('description')}")
        for r in data["regulations"] if int_or_none(r.get("session_id")) == sid
    }
    processes = {
        norm_text(f"{p.get('norm_addressee')} {p.get('process')}")
        for p in data["processes"] if int_or_none(p.get("session_id")) == sid
    }
    groups = {
        norm_text(f"{g.get('norm_addressee')} {process_names.get(int_or_none(g.get('process_id')) or -1, '')} {g.get('case_group')}")
        for g in data["case_groups"] if int_or_none(g.get("session_id")) == sid
    }
    steps = {
        norm_text(
            f"{s.get('norm_addressee')} "
            f"{case_group_names.get(int_or_none(s.get('case_group_id')) or -1, ('', ''))[1]} "
            f"{case_group_names.get(int_or_none(s.get('case_group_id')) or -1, ('', ''))[0]} "
            f"{s.get('step')}"
        )
        for s in data["process_steps"] if int_or_none(s.get("session_id")) == sid
    }
    return {
        "regulations": {x for x in regs if x},
        "processes": {x for x in processes if x},
        "case_groups": {x for x in groups if x},
        "process_steps": {x for x in steps if x},
    }

def analyze_issue_06(data: dict[str, list[dict[str, Any]]], out_dir: Path) -> list[dict[str, Any]]:
    groups = repeated_session_groups(data)
    rows: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for (law_pair, model, deep_research_mode), sessions in groups.items():
        cost_sessions = [s for s in sessions if session_total_cost(data, int(s["session_id"])) is not None]
        if len(cost_sessions) < 2:
            continue
        totals = [session_total_cost(data, int(s["session_id"])) for s in cost_sessions]
        if sum(1 for t in totals if t is not None) < 2:
            continue
        nums = [float(t) for t in totals if t is not None]
        mean = statistics.mean(nums)
        stdev = statistics.pstdev(nums) if len(nums) > 1 else 0.0
        ratio = (max(nums) / min([n for n in nums if n > 0])) if any(n > 0 for n in nums) and min([n for n in nums if n > 0]) > 0 else None
        cv = stdev / mean if mean else None
        addressee_spreads = addressee_cost_spreads(data, cost_sessions)
        case_spreads = addressee_case_spreads(data, cost_sessions)
        latest = sorted(cost_sessions, key=lambda s: str(s.get("created_at") or ""))[-1]
        row = {
            "law_pair": law_pair,
            "model": model,
            "deep_research_mode": deep_research_mode,
            "latest_session_id": latest.get("session_id"),
            "latest_week": iso_week(latest.get("created_at")),
            "session_count": len(cost_sessions),
            "min_total_cost": min(nums),
            "max_total_cost": max(nums),
            "mean_total_cost": mean,
            "stdev_total_cost": stdev,
            "coefficient_of_variation": cv,
            "max_min_ratio": ratio,
            "addressee_cost_spreads": addressee_spreads,
            "addressee_case_spreads": case_spreads,
        }
        rows.append(row)
        if (cv is not None and cv > 0.5) or (ratio is not None and ratio > 2.0):
            findings.append(finding(
                "issue_06_cost_variance", latest, "bad", "medium",
                "Same law pair/model has high final-cost variance.",
                row,
            ))
    write_csv(out_dir / "findings" / "issue_06_cost_variance_groups.csv", rows)
    return findings

def repeated_session_groups(data: dict[str, list[dict[str, Any]]]) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for session in data["sessions"]:
        key = (
            law_pair_key(session),
            str(session.get("llm_model") or "unknown"),
            session_deep_research_mode(data, session),
        )
        if "none" in key[0]:
            continue
        groups.setdefault(key, []).append(session)
    return {k: v for k, v in groups.items() if len(v) >= 2}

def costs_for_session(data: dict[str, list[dict[str, Any]]], sid: int) -> list[dict[str, Any]]:
    return [c for c in data["costs"] if int_or_none(c.get("session_id")) == sid]

def session_total_cost(data: dict[str, list[dict[str, Any]]], sid: int) -> float | None:
    costs = costs_for_session(data, sid)
    if not costs:
        session = next((s for s in data["sessions"] if int_or_none(s.get("session_id")) == sid), None)
        return safe_float((session or {}).get("cc_cost"))
    total = 0.0
    found = False
    for row in costs:
        addressee = row.get("norm_addressee")
        if addressee == "citizens":
            # Citizens' time is not monetized in the same total.
            value = safe_float(row.get("total_expenses"))
        else:
            value = safe_float(row.get("total_cost"))
        if value is not None:
            total += value
            found = True
    return total if found else None

def addressee_cost_spreads(data: dict[str, list[dict[str, Any]]], sessions: list[dict[str, Any]]) -> dict[str, dict[str, float | None]]:
    result: dict[str, dict[str, float | None]] = {}
    for addressee in ADDRESSEES:
        values: list[float] = []
        for session in sessions:
            sid = int(session["session_id"])
            row = next((c for c in data["costs"] if int_or_none(c.get("session_id")) == sid and c.get("norm_addressee") == addressee), None)
            if row:
                value = safe_float(row.get("total_expenses" if addressee == "citizens" else "total_cost"))
                if value is not None:
                    values.append(value)
        result[addressee] = spread(values)
    return result

def addressee_case_spreads(data: dict[str, list[dict[str, Any]]], sessions: list[dict[str, Any]]) -> dict[str, dict[str, float | None]]:
    result: dict[str, dict[str, float | None]] = {}
    for addressee in ADDRESSEES:
        values = []
        for session in sessions:
            sid = int(session["session_id"])
            total = 0.0
            found = False
            for row in data["case_groups"]:
                if int_or_none(row.get("session_id")) == sid and row.get("norm_addressee") == addressee:
                    value = case_group_cases(row, "proposed")
                    if value is not None:
                        total += value
                        found = True
            if found:
                values.append(total)
        result[addressee] = spread(values)
    return result

def spread(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "max": None, "mean": None, "cv": None}
    mean = statistics.mean(values)
    return {
        "min": min(values),
        "max": max(values),
        "mean": mean,
        "cv": (statistics.pstdev(values) / mean if mean else None),
    }

def analyze_issue_07(data: dict[str, list[dict[str, Any]]], out_dir: Path) -> list[dict[str, Any]]:
    groups = repeated_session_groups(data)
    rows: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for (law_pair, model, deep_research_mode), sessions in groups.items():
        cost_sessions = [(s, session_total_cost(data, int(s["session_id"]))) for s in sessions]
        cost_sessions = [(s, c) for s, c in cost_sessions if c is not None]
        if len(cost_sessions) < 2:
            continue
        low, low_cost = min(cost_sessions, key=lambda pair: pair[1])
        high, high_cost = max(cost_sessions, key=lambda pair: pair[1])
        if not low_cost or high_cost / low_cost < 2:
            continue
        fp_low = structure_fingerprint(data, int(low["session_id"]))
        fp_high = structure_fingerprint(data, int(high["session_id"]))
        structure_sim = statistics.mean([
            jaccard(fp_low[layer], fp_high[layer])
            for layer in ("regulations", "processes", "case_groups", "process_steps")
        ])
        matched = matched_case_group_deltas(data, int(low["session_id"]), int(high["session_id"]))
        case_delta_sum = sum(abs(item["case_delta"]) for item in matched if item.get("case_delta") is not None)
        largest = sorted(matched, key=lambda item: abs(item.get("case_delta") or 0), reverse=True)[:10]
        row = {
            "law_pair": law_pair,
            "model": model,
            "deep_research_mode": deep_research_mode,
            "low_session_id": low.get("session_id"),
            "high_session_id": high.get("session_id"),
            "high_week": iso_week(high.get("created_at")),
            "low_cost": low_cost,
            "high_cost": high_cost,
            "cost_ratio": high_cost / low_cost if low_cost else None,
            "structure_similarity": structure_sim,
            "matched_case_group_count": len(matched),
            "sum_abs_case_delta": case_delta_sum,
            "largest_case_deltas": largest,
        }
        rows.append(row)
        if structure_sim >= 0.6 and case_delta_sum > 0:
            findings.append(finding(
                "issue_07_case_count_driven_variance", high, "bad", "medium",
                "High cost variance with similar structure and large case-count differences.",
                row,
            ))
        elif structure_sim >= 0.6:
            review = finding(
                "issue_07_case_count_driven_variance", high, "ambiguous", "low",
                "High cost variance with similar structure, but case-count attribution is unclear.",
                row,
            )
            write_review_packet(out_dir, review, "Is this cost variance mainly caused by case-count assumptions?", row)
    write_csv(out_dir / "findings" / "issue_07_case_count_variance.csv", rows)
    return findings

def matched_case_group_deltas(data: dict[str, list[dict[str, Any]]], low_sid: int, high_sid: int) -> list[dict[str, Any]]:
    low_groups = [g for g in data["case_groups"] if int_or_none(g.get("session_id")) == low_sid]
    high_groups = [g for g in data["case_groups"] if int_or_none(g.get("session_id")) == high_sid]
    high_by_name = {(g.get("norm_addressee"), norm_text(g.get("case_group"))): g for g in high_groups if norm_text(g.get("case_group"))}
    rows = []
    for low in low_groups:
        key = (low.get("norm_addressee"), norm_text(low.get("case_group")))
        high = high_by_name.get(key)
        if not high:
            continue
        low_cases = case_group_cases(low, "proposed")
        high_cases = case_group_cases(high, "proposed")
        rows.append({
            "norm_addressee": key[0],
            "case_group": low.get("case_group"),
            "low_cases": low_cases,
            "high_cases": high_cases,
            "case_delta": (high_cases - low_cases) if high_cases is not None and low_cases is not None else None,
            "low_cost": safe_float(low.get("cost")),
            "high_cost": safe_float(high.get("cost")),
        })
    return rows

def analyze_issue_08(data: dict[str, list[dict[str, Any]]], out_dir: Path) -> list[dict[str, Any]]:
    maps = session_maps(data)
    findings: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    regs_by_session = group_by(data["regulations"], "session_id")
    raw_ip_by_session: dict[int, list[dict[str, Any]]] = {}
    for ans in data["llm_answers"]:
        if ans.get("prompt_id") != "regulations_identification":
            continue
        sid = int_or_none(ans.get("session_id"))
        if sid is None:
            continue
        cls = classify_json_answer(ans.get("answer_text"), "regulations_identification")
        if not cls.get("data"):
            continue
        raw_ip = [
            row for row in collect_regulation_like(cls["data"])
            if row.get("applies_to_business") and row.get("is_business_information_obligation")
        ]
        if raw_ip:
            raw_ip_by_session.setdefault(sid, []).extend(raw_ip)
    for sid, session in maps["sessions"].items():
        regs = regs_by_session.get(sid, [])
        business_ip = [r for r in regs if truthy(r.get("applies_to_business")) and truthy(r.get("is_business_information_obligation"))]
        raw_business_ip = raw_ip_by_session.get(sid, [])
        business_cost = next((c for c in data["costs"] if int_or_none(c.get("session_id")) == sid and c.get("norm_addressee") == "business"), None)
        business_regs = [r for r in regs if truthy(r.get("applies_to_business"))]
        linked_steps = linked_business_ip_steps(data, sid, business_ip) if business_ip else []
        quality_row = bureaucracy_cost_quality_row(
            data=data,
            session=session,
            raw_business_ip=raw_business_ip,
            business_ip=business_ip,
            business_regs=business_regs,
            business_cost=business_cost,
            linked_steps=linked_steps,
        )
        quality_rows.append(quality_row)
        if raw_business_ip and not business_ip:
            findings.append(finding(
                "issue_08_bureaucracy_cost", session, "bad", "medium",
                "Raw LLM answer identified business information obligations, but none were persisted.",
                {
                    "session_id": sid,
                    "raw_business_ip_count": len(raw_business_ip),
                    "persisted_business_ip_count": 0,
                    "raw_examples": raw_business_ip[:5],
                    "reason": "raw_ip_not_persisted",
                },
            ))
        if not business_ip:
            continue
        if not business_cost:
            continue
        total = safe_float(business_cost.get("total_cost"))
        bureaucracy = safe_float(business_cost.get("bureaucracy_cost"))
        row = {
            "session_id": sid,
            "app_session_id": session.get("app_session_id"),
            "week": iso_week(session.get("created_at")),
            "law_pair": law_pair_key(session),
            "model": session.get("llm_model"),
            "business_ip_regulation_count": len(business_ip),
            "business_regulation_count": len(business_regs),
            "linked_ip_step_count": len(linked_steps),
            "business_total_cost": total,
            "business_bureaucracy_cost": bureaucracy,
            "bureaucracy_ratio": (bureaucracy / total if total else None),
        }
        rows.append(row)
        if total is not None and total > 0 and bureaucracy is None:
            findings.append(finding(
                "issue_08_bureaucracy_cost", session, "bad", "high",
                "Business information obligations exist, but bureaucracy cost is missing.",
                {**row, "reason": "ip_present_bureaucracy_missing"},
            ))
        elif bureaucracy == 0 and linked_steps:
            findings.append(finding(
                "issue_08_bureaucracy_cost", session, "diagnostic", "low",
                "Business information obligations are linked to process steps, but the bureaucracy-cost delta is zero.",
                {**row, "reason": "ip_present_zero_bureaucracy_cost"},
            ))
        elif total and bureaucracy is not None and total > 0 and bureaucracy / total >= 0.98 and len(business_regs) > len(business_ip):
            findings.append(finding(
                "issue_08_bureaucracy_cost", session, "bad", "medium",
                "All or nearly all business cost is marked bureaucracy despite mixed business regulations.",
                {**row, "reason": "suspicious_all_business_cost_marked_bureaucracy"},
            ))
    write_csv(out_dir / "findings" / "issue_08_bureaucracy_cost.csv", rows)
    write_csv(out_dir / "findings" / "issue_08_bureaucracy_cost_quality.csv", quality_rows)
    return findings

def bureaucracy_cost_quality_row(
    *,
    data: dict[str, list[dict[str, Any]]],
    session: dict[str, Any],
    raw_business_ip: list[dict[str, Any]],
    business_ip: list[dict[str, Any]],
    business_regs: list[dict[str, Any]],
    business_cost: dict[str, Any] | None,
    linked_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    total = safe_float((business_cost or {}).get("total_cost"))
    bureaucracy = safe_float((business_cost or {}).get("bureaucracy_cost"))
    if raw_business_ip and business_ip:
        raw_persisted_bucket = "raw_ip_persisted"
    elif raw_business_ip and not business_ip:
        raw_persisted_bucket = "raw_ip_not_persisted"
    elif business_ip and not raw_business_ip:
        raw_persisted_bucket = "persisted_ip_without_raw_flag"
    else:
        raw_persisted_bucket = "no_raw_or_persisted_ip"

    bureaucracy_sign = "none"
    if bureaucracy is None:
        bureaucracy_sign = "missing"
    elif bureaucracy > 0:
        bureaucracy_sign = "positive"
    elif bureaucracy < 0:
        bureaucracy_sign = "negative"
    else:
        bureaucracy_sign = "zero"

    cost_bucket = "no_business_ip"
    if business_ip and not business_cost:
        cost_bucket = "ip_present_missing_business_cost_row"
    elif business_ip and bureaucracy is None:
        cost_bucket = "ip_present_missing_bureaucracy_cost"
    elif business_ip and bureaucracy > 0:
        cost_bucket = "ip_present_positive_bureaucracy_cost"
    elif business_ip and bureaucracy < 0:
        cost_bucket = "ip_present_negative_bureaucracy_cost"
    elif business_ip and bureaucracy == 0:
        cost_bucket = "ip_present_zero_bureaucracy_cost"
    if business_ip and total and bureaucracy is not None and total > 0 and bureaucracy / total >= 0.98 and len(business_regs) > len(business_ip):
        cost_bucket = "suspicious_all_business_cost_marked_bureaucracy"

    chart_bucket = cost_bucket
    if raw_persisted_bucket == "raw_ip_not_persisted":
        chart_bucket = "raw_ip_not_persisted"

    return {
        "session_id": session.get("session_id"),
        "app_session_id": session.get("app_session_id"),
        "week": iso_week(session.get("created_at")),
        "session_created_at": session.get("created_at"),
        "law_pair": law_pair_key(session),
        "model": session.get("llm_model"),
        "raw_business_ip_count": len(raw_business_ip),
        "persisted_business_ip_count": len(business_ip),
        "business_regulation_count": len(business_regs),
        "linked_ip_step_count": len(linked_steps),
        "business_total_cost": total,
        "business_bureaucracy_cost": bureaucracy,
        "bureaucracy_sign": bureaucracy_sign,
        "bureaucracy_ratio": (bureaucracy / total if total else None),
        "raw_persisted_bucket": raw_persisted_bucket,
        "cost_bucket": cost_bucket,
        "chart_bucket": chart_bucket,
        "raw_examples": raw_business_ip[:3],
    }

def linked_business_ip_steps(data: dict[str, list[dict[str, Any]]], sid: int, ip_regs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ip_ids = {int(r["regulation_id"]) for r in ip_regs if r.get("regulation_id") is not None}
    step_ids = {
        int(link["step_id"]) for link in data["step_regulation_links"]
        if int_or_none(link.get("session_id")) == sid
        and link.get("norm_addressee") == "business"
        and int_or_none(link.get("regulation_id")) in ip_ids
        and link.get("step_id") is not None
    }
    return [s for s in data["process_steps"] if int_or_none(s.get("session_id")) == sid and int_or_none(s.get("step_id")) in step_ids]
