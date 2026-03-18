from __future__ import annotations

import sqlite3
from collections.abc import Callable

from .edit_audit import insert_edit_audit_row, value_changed

CASE_GROUP_FIELDS = (
    "addressees_current",
    "annual_frequency_current",
    "addressees_proposed",
    "annual_frequency_proposed",
)

PROCESS_STEP_FIELDS = (
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


def _effective_value(base_value: object, edited_value: object) -> object:
    return base_value if edited_value is None else edited_value


def _normalize_edited_value(
    *,
    field_name: str,
    payload: dict,
    previous: dict,
) -> object:
    edited_key = f"{field_name}_edited"
    if field_name not in payload:
        return previous.get(edited_key)
    incoming = payload.get(field_name)
    if incoming is None:
        return None
    base_value = previous.get(field_name)
    if not value_changed(incoming, base_value):
        return None
    return incoming


def list_editable_case_groups(
    rows: list[dict],
    *,
    resolve_effective_case_group_metrics: Callable[[dict], dict],
) -> list[dict]:
    return [resolve_effective_case_group_metrics(group) for group in rows]


def bulk_update_case_group_edits(
    cur: sqlite3.Cursor,
    session_id: int,
    rows: list[dict],
) -> tuple[int, list[int]]:
    if not rows:
        return 0, []
    case_group_ids = [int(row["case_group_id"]) for row in rows if row.get("case_group_id") is not None]
    if not case_group_ids:
        return 0, []
    unique_case_group_ids = sorted(set(case_group_ids))
    placeholders = ", ".join("?" for _ in unique_case_group_ids)
    cur.execute(
        f"""
        SELECT case_group_id,
               addressees_current,
               annual_frequency_current,
               addressees_proposed,
               annual_frequency_proposed,
               addressees_current_edited,
               annual_frequency_current_edited,
               addressees_proposed_edited,
               annual_frequency_proposed_edited
        FROM case_groups
        WHERE session_id = ?
          AND case_group_id IN ({placeholders})
        """,
        (session_id, *unique_case_group_ids),
    )
    existing = {int(row["case_group_id"]): dict(row) for row in cur.fetchall()}
    missing_ids = [case_group_id for case_group_id in unique_case_group_ids if case_group_id not in existing]
    if missing_ids:
        return 0, missing_ids

    updated = 0
    for row in rows:
        case_group_id = int(row["case_group_id"])
        previous = existing[case_group_id]

        next_edited: dict[str, object] = {}
        for field_name in CASE_GROUP_FIELDS:
            next_edited[field_name] = _normalize_edited_value(
                field_name=field_name,
                payload=row,
                previous=previous,
            )

        changed = any(
            value_changed(previous.get(f"{field_name}_edited"), next_edited[field_name])
            for field_name in CASE_GROUP_FIELDS
        )
        if not changed:
            continue

        for field_name in CASE_GROUP_FIELDS:
            old_effective = _effective_value(
                previous.get(field_name),
                previous.get(f"{field_name}_edited"),
            )
            new_effective = _effective_value(
                previous.get(field_name),
                next_edited[field_name],
            )
            insert_edit_audit_row(
                cur,
                session_id=session_id,
                entity_type="case_group",
                entity_id=case_group_id,
                field_name=field_name,
                old_value=old_effective,
                new_value=new_effective,
            )

        addressees_current_edited = next_edited["addressees_current"]
        annual_frequency_current_edited = next_edited["annual_frequency_current"]
        addressees_proposed_edited = next_edited["addressees_proposed"]
        annual_frequency_proposed_edited = next_edited["annual_frequency_proposed"]

        cases_current_edited = (
            float(addressees_current_edited) * float(annual_frequency_current_edited)
            if addressees_current_edited is not None and annual_frequency_current_edited is not None
            else None
        )
        cases_proposed_edited = (
            float(addressees_proposed_edited) * float(annual_frequency_proposed_edited)
            if addressees_proposed_edited is not None and annual_frequency_proposed_edited is not None
            else None
        )

        cur.execute(
            """
            UPDATE case_groups
            SET addressees_current_edited = ?,
                annual_frequency_current_edited = ?,
                cases_current_edited = ?,
                addressees_proposed_edited = ?,
                annual_frequency_proposed_edited = ?,
                cases_proposed_edited = ?,
                last_edited_at = current_timestamp
            WHERE case_group_id = ? AND session_id = ?
            """,
            (
                addressees_current_edited,
                annual_frequency_current_edited,
                cases_current_edited,
                addressees_proposed_edited,
                annual_frequency_proposed_edited,
                cases_proposed_edited,
                case_group_id,
                session_id,
            ),
        )
        updated += 1
    return updated, []


def list_editable_process_steps(
    rows: list[dict],
    *,
    resolve_effective_process_step_metrics: Callable[[dict], dict],
    case_group_id: int | None = None,
) -> list[dict]:
    local_rows = rows
    if case_group_id is not None:
        local_rows = [row for row in local_rows if int(row["case_group_id"]) == int(case_group_id)]
    return [resolve_effective_process_step_metrics(row) for row in local_rows]


def bulk_update_process_step_edits(
    cur: sqlite3.Cursor,
    session_id: int,
    rows: list[dict],
) -> tuple[int, list[int]]:
    if not rows:
        return 0, []
    step_ids = [int(row["step_id"]) for row in rows if row.get("step_id") is not None]
    if not step_ids:
        return 0, []
    unique_step_ids = sorted(set(step_ids))
    placeholders = ", ".join("?" for _ in unique_step_ids)
    cur.execute(
        f"""
        SELECT step_id,
               time_required_in_min_a_current,
               time_required_in_min_b_current,
               time_required_in_min_c_current,
               time_required_in_min_d_current,
               expenses_current,
               time_required_in_min_a_proposed,
               time_required_in_min_b_proposed,
               time_required_in_min_c_proposed,
               time_required_in_min_d_proposed,
               expenses_proposed,
               time_required_in_min_a_current_edited,
               time_required_in_min_b_current_edited,
               time_required_in_min_c_current_edited,
               time_required_in_min_d_current_edited,
               expenses_current_edited,
               time_required_in_min_a_proposed_edited,
               time_required_in_min_b_proposed_edited,
               time_required_in_min_c_proposed_edited,
               time_required_in_min_d_proposed_edited,
               expenses_proposed_edited
        FROM process_steps
        WHERE session_id = ?
          AND step_id IN ({placeholders})
        """,
        (session_id, *unique_step_ids),
    )
    existing = {int(row["step_id"]): dict(row) for row in cur.fetchall()}
    missing_ids = [step_id for step_id in unique_step_ids if step_id not in existing]
    if missing_ids:
        return 0, missing_ids

    updated = 0
    for row in rows:
        step_id = int(row["step_id"])
        previous = existing[step_id]

        next_edited: dict[str, object] = {}
        for field_name in PROCESS_STEP_FIELDS:
            next_edited[field_name] = _normalize_edited_value(
                field_name=field_name,
                payload=row,
                previous=previous,
            )

        changed = any(
            value_changed(previous.get(f"{field_name}_edited"), next_edited[field_name])
            for field_name in PROCESS_STEP_FIELDS
        )
        if not changed:
            continue

        for field_name in PROCESS_STEP_FIELDS:
            old_effective = _effective_value(
                previous.get(field_name),
                previous.get(f"{field_name}_edited"),
            )
            new_effective = _effective_value(
                previous.get(field_name),
                next_edited[field_name],
            )
            insert_edit_audit_row(
                cur,
                session_id=session_id,
                entity_type="process_step",
                entity_id=step_id,
                field_name=field_name,
                old_value=old_effective,
                new_value=new_effective,
            )

        cur.execute(
            """
            UPDATE process_steps
            SET time_required_in_min_a_current_edited = ?,
                time_required_in_min_b_current_edited = ?,
                time_required_in_min_c_current_edited = ?,
                time_required_in_min_d_current_edited = ?,
                expenses_current_edited = ?,
                time_required_in_min_a_proposed_edited = ?,
                time_required_in_min_b_proposed_edited = ?,
                time_required_in_min_c_proposed_edited = ?,
                time_required_in_min_d_proposed_edited = ?,
                expenses_proposed_edited = ?,
                last_edited_at = current_timestamp
            WHERE step_id = ? AND session_id = ?
            """,
            (
                next_edited["time_required_in_min_a_current"],
                next_edited["time_required_in_min_b_current"],
                next_edited["time_required_in_min_c_current"],
                next_edited["time_required_in_min_d_current"],
                next_edited["expenses_current"],
                next_edited["time_required_in_min_a_proposed"],
                next_edited["time_required_in_min_b_proposed"],
                next_edited["time_required_in_min_c_proposed"],
                next_edited["time_required_in_min_d_proposed"],
                next_edited["expenses_proposed"],
                step_id,
                session_id,
            ),
        )
        updated += 1
    return updated, []
