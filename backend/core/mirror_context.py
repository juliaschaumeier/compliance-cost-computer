from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException

from backend.core.auth import ApiKeys
from backend.core.llm_json import parse_json_object
from backend.core.llm_service import query_llm
from backend.core.parsing import parse_first_int
from backend.core.norm_addressees import (
    ADMINISTRATION,
    ALL_NORM_ADDRESSEES,
    BUSINESS,
    CITIZENS,
)


def render_mirror_prompt_context(
    session_id: int,
    norm_addressee: str,
    stage: str,
) -> str:
    from backend.core import db

    clusters = build_mirror_clusters_for_prompt(
        session_id=session_id,
        norm_addressee=norm_addressee,
        stage=stage,
    )
    matching_rows = [
        row
        for row in db.list_mirror_matches(session_id)
        if str(row.get("source_norm_addressee") or "") == norm_addressee
        or str(row.get("target_norm_addressee") or "") == norm_addressee
    ]
    if not clusters and not matching_rows:
        return ""
    payload = json.dumps(
        {
            "mirror_clusters": clusters,
            "mirror_matches": matching_rows,
        },
        ensure_ascii=False,
    )
    return (
        "Zusaetzlicher strukturierter Spiegelkontext zur Stabilisierung der "
        "fachlichen Zuordnung. Nutzen Sie diesen Kontext nur fuer die "
        "Konsistenz ueber Normadressaten hinweg; erzeugen Sie keine neuen "
        f"Spiegelsachverhalte: {payload}"
    )


async def ensure_mirror_matching(
    *,
    session_id: int,
    model: str,
    provider: str | None,
    api_keys: ApiKeys,
    query_fn=query_llm,
) -> list[dict[str, Any]]:
    from backend.core import db
    from backend.core.llm_attempts import mark_llm_answer_applied
    from backend.core.prompts import PromptId, render_prompt
    from backend.routers._llm_router_utils import (
        query_and_stage_or_http,
        run_with_answer_apply_guard,
    )

    existing = db.list_mirror_matches(session_id)
    if existing:
        return existing

    clusters = build_mirror_clusters_for_matching(session_id)
    if not clusters:
        return []

    prompt = render_prompt(
        PromptId.MIRROR_MATCHING,
        session_id=session_id,
        mirror_clusters_json=json.dumps(clusters, ensure_ascii=False),
    )
    answer_id, llm_result = await query_and_stage_or_http(
        session_id=session_id,
        prompt_id=PromptId.MIRROR_MATCHING,
        prompt=prompt,
        api_keys=api_keys,
        model=model,
        provider=provider,
        query_fn=query_fn,
    )

    def _apply() -> list[dict[str, Any]]:
        parsed = parse_mirror_matching_payload(llm_result.text)
        db.replace_mirror_matches(session_id, parsed)
        mark_llm_answer_applied(
            answer_id=answer_id,
            session_id=session_id,
            prompt_id=PromptId.MIRROR_MATCHING,
        )
        return db.list_mirror_matches(session_id)

    return run_with_answer_apply_guard(answer_id=answer_id, apply_fn=_apply)


def build_mirror_clusters_for_prompt(
    session_id: int,
    norm_addressee: str,
    stage: str,
) -> list[dict[str, Any]]:
    from backend.core import db

    regulations = db.list_regulations_for_session_and_addressee(session_id, norm_addressee)
    mirrored = [
        row for row in regulations
        if str(row.get("mirror_anchor_key") or "").strip()
    ]
    if not mirrored:
        return []

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in mirrored:
        grouped.setdefault(str(row["mirror_anchor_key"]), []).append(row)

    clusters: list[dict[str, Any]] = []
    for anchor_key, source_rows in grouped.items():
        target_addressees = sorted(
            {
                addressee
                for row in source_rows
                for addressee, enabled in (
                    (ADMINISTRATION, row.get("mirror_applies_to_administration")),
                    (BUSINESS, row.get("mirror_applies_to_business")),
                    (CITIZENS, row.get("mirror_applies_to_citizens")),
                )
                if enabled and addressee != norm_addressee
            }
        )
        if not target_addressees:
            continue

        cluster: dict[str, Any] = {
            "mirror_anchor_key": anchor_key,
            "source_norm_addressee": norm_addressee,
            "source_regulations": [_serialize_regulation_brief(row) for row in source_rows],
            "target_addressees": target_addressees,
        }
        mirror_descriptions = sorted(
            {
                str(row.get("mirror_description") or "").strip()
                for row in source_rows
                if str(row.get("mirror_description") or "").strip()
            }
        )
        if mirror_descriptions:
            cluster["mirror_descriptions"] = mirror_descriptions

        related_by_addressee: dict[str, Any] = {}
        for target_addressee in ALL_NORM_ADDRESSEES:
            if target_addressee not in target_addressees:
                continue
            related = _build_related_addressee_context(
                session_id=session_id,
                target_addressee=target_addressee,
                anchor_key=anchor_key,
                stage=stage,
            )
            if related:
                related_by_addressee[target_addressee] = related
        if related_by_addressee:
            cluster["related_addressees"] = related_by_addressee
        clusters.append(cluster)
    return clusters


def build_mirror_clusters_for_matching(session_id: int) -> list[dict[str, Any]]:
    clusters_by_anchor: dict[str, dict[str, Any]] = {}
    for norm_addressee in ALL_NORM_ADDRESSEES:
        clusters = build_mirror_clusters_for_prompt(
            session_id=session_id,
            norm_addressee=norm_addressee,
            stage="case_groups",
        )
        for cluster in clusters:
            anchor_key = str(cluster["mirror_anchor_key"])
            merged = clusters_by_anchor.setdefault(
                anchor_key,
                {
                    "mirror_anchor_key": anchor_key,
                    "norm_addressees": {},
                },
            )
            merged["norm_addressees"][norm_addressee] = {
                "source_regulations": cluster.get("source_regulations", []),
                "mirror_descriptions": cluster.get("mirror_descriptions", []),
                "related_addressees": cluster.get("related_addressees", {}),
            }
    return list(clusters_by_anchor.values())


def parse_mirror_matching_payload(payload: str) -> list[dict[str, Any]]:
    data = parse_json_object(payload)
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="No mirror analyses parsed")
    analyses = data.get("analyses")
    if not isinstance(analyses, list):
        raise HTTPException(status_code=422, detail="No mirror analyses parsed")
    parsed: list[dict[str, Any]] = []
    for analysis in analyses:
        if not isinstance(analysis, dict):
            continue
        anchor_key = str(analysis.get("mirror_anchor_key") or "").strip()
        shared_situation = str(analysis.get("shared_situation") or "").strip()
        matches = analysis.get("matches")
        if not anchor_key or not isinstance(matches, list):
            continue
        for match in matches:
            if not isinstance(match, dict):
                continue
            source_norm_addressee = str(match.get("source_norm_addressee") or "").strip()
            target_norm_addressee = str(match.get("target_norm_addressee") or "").strip()
            relation_type = str(match.get("relation_type") or "").strip()
            if not source_norm_addressee or not target_norm_addressee or not relation_type:
                continue
            parsed.append(
                {
                    "mirror_anchor_key": anchor_key,
                    "shared_situation": shared_situation,
                    "source_norm_addressee": source_norm_addressee,
                    "target_norm_addressee": target_norm_addressee,
                    "source_process_id": parse_first_int(match, "source_process_id"),
                    "target_process_id": parse_first_int(match, "target_process_id"),
                    "source_case_group_id": parse_first_int(match, "source_case_group_id"),
                    "target_case_group_id": parse_first_int(match, "target_case_group_id"),
                    "relation_type": relation_type,
                    "sync_addressees": _parse_binary_flag(match.get("sync_addressees")),
                    "sync_frequency": _parse_binary_flag(match.get("sync_frequency")),
                    "sync_cases": _parse_binary_flag(match.get("sync_cases")),
                    "reason": str(match.get("reason") or "").strip(),
                }
            )
    return parsed


def apply_deterministic_mirror_case_group_sync(
    session_id: int,
    norm_addressee: str,
    parsed_cases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    overrides = get_deterministic_mirror_case_group_metrics(
        session_id=session_id,
        norm_addressee=norm_addressee,
    )
    if not overrides:
        return parsed_cases
    synced: list[dict[str, Any]] = []
    for entry in parsed_cases:
        case_group_id = int(entry["case_group_id"])
        override = overrides.get(case_group_id)
        if not override:
            synced.append(entry)
            continue
        updated = dict(entry)
        updated["addressees_current"] = override["addressees_current"]
        updated["annual_frequency_current"] = override["annual_frequency_current"]
        updated["addressees_proposed"] = override["addressees_proposed"]
        updated["annual_frequency_proposed"] = override["annual_frequency_proposed"]
        updated["mirror_sync_source"] = override["source_norm_addressee"]
        synced.append(updated)
    return synced


def get_deterministic_mirror_case_group_metrics(
    session_id: int,
    norm_addressee: str,
) -> dict[int, dict[str, Any]]:
    from backend.core import db

    if norm_addressee == ADMINISTRATION:
        return {}

    overrides: dict[int, dict[str, Any]] = {}
    matches = db.list_mirror_matches(session_id)
    for match in matches:
        if not bool(match.get("sync_cases")):
            continue
        if str(match.get("target_norm_addressee") or "") != norm_addressee:
            continue
        target_case_group_id = match.get("target_case_group_id")
        source_case_group_id = match.get("source_case_group_id")
        source_norm_addressee = str(match.get("source_norm_addressee") or "")
        if target_case_group_id is None or source_case_group_id is None:
            continue
        source_groups = db.list_case_groups_for_session_and_addressee(
            session_id, source_norm_addressee
        )
        source_group = next(
            (
                group
                for group in source_groups
                if int(group["case_group_id"]) == int(source_case_group_id)
            ),
            None,
        )
        if not source_group:
            continue
        resolved = db.resolve_effective_case_group_metrics(source_group)
        metrics = {
            "addressees_current": resolved.get("addressees_current_effective"),
            "annual_frequency_current": resolved.get("annual_frequency_current_effective"),
            "addressees_proposed": resolved.get("addressees_proposed_effective"),
            "annual_frequency_proposed": resolved.get("annual_frequency_proposed_effective"),
        }
        if not all(value is not None for value in metrics.values()):
            continue
        overrides[int(target_case_group_id)] = {
            **metrics,
            "source_norm_addressee": source_norm_addressee,
        }

    if overrides:
        return overrides

    source_groups = db.list_case_groups_for_session_and_addressee(session_id, norm_addressee)
    source_by_anchor = _group_case_groups_by_anchor(
        session_id=session_id,
        norm_addressee=norm_addressee,
        case_groups=source_groups,
    )

    for anchor_key, current_groups in source_by_anchor.items():
        if len(current_groups) != 1:
            continue
        target_candidates: list[dict[str, Any]] = []
        for target_addressee in ALL_NORM_ADDRESSEES:
            if target_addressee == norm_addressee:
                continue
            target_groups = db.list_case_groups_for_session_and_addressee(session_id, target_addressee)
            target_by_anchor = _group_case_groups_by_anchor(
                session_id=session_id,
                norm_addressee=target_addressee,
                case_groups=target_groups,
            )
            anchored_target_groups = target_by_anchor.get(anchor_key, [])
            if len(anchored_target_groups) != 1:
                continue
            resolved = db.resolve_effective_case_group_metrics(anchored_target_groups[0])
            metrics = {
                "addressees_current": resolved.get("addressees_current_effective"),
                "annual_frequency_current": resolved.get("annual_frequency_current_effective"),
                "addressees_proposed": resolved.get("addressees_proposed_effective"),
                "annual_frequency_proposed": resolved.get("annual_frequency_proposed_effective"),
            }
            if not all(value is not None for value in metrics.values()):
                continue
            target_candidates.append({**metrics, "source_norm_addressee": target_addressee})
        if len(target_candidates) != 1:
            continue
        overrides[int(current_groups[0]["case_group_id"])] = target_candidates[0]
    return overrides


def _group_case_groups_by_anchor(
    session_id: int,
    norm_addressee: str,
    case_groups: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    from backend.core import db

    regulations = db.list_regulations_for_session_and_addressee(session_id, norm_addressee)
    anchor_by_process_id: dict[int, set[str]] = {}
    for row in regulations:
        anchor_key = str(row.get("mirror_anchor_key") or "").strip()
        process_id = row.get("process_id")
        if not anchor_key or process_id is None:
            continue
        anchor_by_process_id.setdefault(int(process_id), set()).add(anchor_key)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for group in case_groups:
        process_id = int(group["process_id"])
        anchors = anchor_by_process_id.get(process_id, set())
        if len(anchors) != 1:
            continue
        anchor_key = next(iter(anchors))
        grouped.setdefault(anchor_key, []).append(group)
    return grouped


def _build_related_addressee_context(
    session_id: int,
    target_addressee: str,
    anchor_key: str,
    stage: str,
) -> dict[str, Any]:
    from backend.core import db

    regulations = [
        row
        for row in db.list_regulations_for_session_and_addressee(session_id, target_addressee)
        if str(row.get("mirror_anchor_key") or "").strip() == anchor_key
    ]
    if not regulations:
        return {}
    context: dict[str, Any] = {
        "regulations": [_serialize_regulation_brief(row) for row in regulations]
    }
    process_ids = sorted(
        {
            int(row["process_id"])
            for row in regulations
            if row.get("process_id") is not None
        }
    )
    if not process_ids:
        return context

    processes = [
        row
        for row in db.list_processes_for_session_and_addressee(session_id, target_addressee)
        if int(row["process_id"]) in process_ids
    ]
    if processes:
        context["processes"] = [
            {
                "process_id": int(row["process_id"]),
                "prozess_bezeichnung": str(row.get("process") or ""),
                "prozess_beschreibung": str(row.get("description") or ""),
                "aenderungsstatus": str(row.get("change_status") or ""),
            }
            for row in processes
        ]

    if stage not in {"case_groups", "steps", "cases"}:
        return context

    case_groups = [
        row
        for row in db.list_case_groups_for_session_and_addressee(session_id, target_addressee)
        if int(row["process_id"]) in process_ids
    ]
    if case_groups:
        context["fallgruppen"] = [
            {
                "fallgruppen_id": int(row["case_group_id"]),
                "fallgruppe_bezeichnung": str(row.get("case_group") or ""),
                "fallgruppe_beschreibung": str(row.get("description") or ""),
                "aenderungsstatus": str(row.get("change_status") or ""),
                **(
                    {
                        "anzahl_betroffene_current": row.get("addressees_current"),
                        "haeufigkeit_pro_jahr_current": row.get("annual_frequency_current"),
                        "anzahl_betroffene_proposed": row.get("addressees_proposed"),
                        "haeufigkeit_pro_jahr_proposed": row.get("annual_frequency_proposed"),
                    }
                    if stage == "cases"
                    else {}
                ),
            }
            for row in case_groups
        ]

    if stage != "steps" or not case_groups:
        return context

    case_group_ids = {int(row["case_group_id"]) for row in case_groups}
    steps = [
        row
        for row in db.list_process_steps_for_session_and_addressee(session_id, target_addressee)
        if int(row["case_group_id"]) in case_group_ids
    ]
    if steps:
        context["taetigkeiten"] = [
            {
                "step_id": int(row["step_id"]),
                "case_group_id": int(row["case_group_id"]),
                "taetigkeit": str(row.get("step") or ""),
                "beschreibung": str(row.get("description") or ""),
                "aenderungsstatus": str(row.get("change_status") or ""),
            }
            for row in steps
        ]
    return context


def _serialize_regulation_brief(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "regulation_id": int(row["regulation_id"]),
        "normzitat": str(row.get("legal_citation") or ""),
        "beschreibung": str(row.get("description") or ""),
        "aenderungsstatus": str(row.get("change_status") or ""),
    }


def _parse_binary_flag(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip() in {"1", "true", "True", "ja", "yes"}
    return False
