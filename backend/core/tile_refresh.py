from __future__ import annotations

from backend.core import db
from backend.core.db_formatting import (
    build_case_group_tile_text,
    build_process_step_tile_text,
    build_process_step_tile_text_from_rows,
)
from backend.core.models import Tile
from backend.core.norm_addressees import (
    ADMINISTRATION,
    EFFORT_GROUP_LABELS,
    personnel_provenance_label,
)


def _case_group_text(group: dict) -> str:
    effective = db.resolve_effective_case_group_metrics(group)
    return build_case_group_tile_text(
        description=effective.get("description") or "",
        addressees_current=effective.get("addressees_current_effective"),
        annual_frequency_current=effective.get("annual_frequency_current_effective"),
        addressees_proposed=effective.get("addressees_proposed_effective"),
        annual_frequency_proposed=effective.get("annual_frequency_proposed_effective"),
        cases_current=effective.get("cases_current_effective"),
        cases_proposed=effective.get("cases_proposed_effective"),
    )


def build_step_tile_text(session_id: int, step: dict, norm_addressee: str) -> str:
    """Step tile text, row-based when personnel rows exist (org steps with the
    redesigned model), else the legacy slot-based path (citizens, empty steps)."""
    effective = db.resolve_effective_process_step_metrics(step)
    rows = db.list_process_step_personnel_effort(session_id, norm_addressee, step["step_id"])
    if rows:
        overrides = db.get_session_wage_rate_overrides(session_id, norm_addressee)
        return build_process_step_tile_text_from_rows(
            description=effective.get("description") or "",
            norm_addressee=norm_addressee,
            current_rows=[r for r in rows if r["period"] == "current"],
            proposed_rows=[r for r in rows if r["period"] == "proposed"],
            expenses_current=effective.get("expenses_current_effective"),
            cost_current=step.get("cost_current"),
            expenses_proposed=effective.get("expenses_proposed_effective"),
            cost_proposed=step.get("cost_proposed"),
            execution_per_case=step.get("execution_per_case"),
            wage_overrides=overrides,
        )
    return build_process_step_tile_text(
        description=effective.get("description") or "",
        hourly_rates_current={
            "a": effective.get("hourly_rate_a_current"),
            "b": effective.get("hourly_rate_b_current"),
            "c": effective.get("hourly_rate_c_current"),
            "d": effective.get("hourly_rate_d_current"),
        },
        time_required_current={
            "a": effective.get("time_required_in_min_a_current_effective"),
            "b": effective.get("time_required_in_min_b_current_effective"),
            "c": effective.get("time_required_in_min_c_current_effective"),
            "d": effective.get("time_required_in_min_d_current_effective"),
        },
        expenses_current=effective.get("expenses_current_effective"),
        cost_current=step.get("cost_current"),
        hourly_rates_proposed={
            "a": effective.get("hourly_rate_a_proposed"),
            "b": effective.get("hourly_rate_b_proposed"),
            "c": effective.get("hourly_rate_c_proposed"),
            "d": effective.get("hourly_rate_d_proposed"),
        },
        time_required_proposed={
            "a": effective.get("time_required_in_min_a_proposed_effective"),
            "b": effective.get("time_required_in_min_b_proposed_effective"),
            "c": effective.get("time_required_in_min_c_proposed_effective"),
            "d": effective.get("time_required_in_min_d_proposed_effective"),
        },
        expenses_proposed=effective.get("expenses_proposed_effective"),
        cost_proposed=step.get("cost_proposed"),
        execution_per_case=step.get("execution_per_case"),
        group_labels=EFFORT_GROUP_LABELS.get(norm_addressee),
    )


def step_personnel_meta_rows(
    session_id: int, norm_addressee: str, step_id: int
) -> list[dict] | None:
    """Per-(qualification, source) personnel rows for the step tile metric table,
    labelled with the wage provenance and the effective minutes per period.

    Returns None when the step has no row-model data (citizens, legacy steps), so
    the tile keeps the slot-based table.
    """
    rows = db.list_process_step_personnel_effort(session_id, norm_addressee, step_id)
    if not rows:
        return None
    grouped: dict[tuple[str, str], dict] = {}
    order: list[tuple[str, str]] = []
    for row in rows:
        key = (row["qualification"], row["wage_source_value"])
        if key not in grouped:
            grouped[key] = {
                "label": personnel_provenance_label(
                    norm_addressee, row["wage_source_value"], row["qualification"]
                ),
                "current_min": None,
                "proposed_min": None,
            }
            order.append(key)
        edited = row.get("time_required_in_min_edited")
        minutes = edited if edited is not None else row.get("time_required_in_min")
        field = "current_min" if row["period"] == "current" else "proposed_min"
        grouped[key][field] = minutes
    return [grouped[key] for key in order]


def _apply_change_status(tile: Tile, change_status: object) -> dict:
    meta_information = dict(tile.meta_information or {})
    if change_status:
        meta_information["change_status"] = change_status
    return meta_information


def _with_case_group_metrics(meta_information: dict, group: dict) -> dict:
    effective = db.resolve_effective_case_group_metrics(group)
    updated = dict(meta_information)
    updated["description"] = effective.get("description")
    updated["addressees_current"] = effective.get("addressees_current_effective")
    updated["annual_frequency_current"] = effective.get("annual_frequency_current_effective")
    updated["cases_current"] = effective.get("cases_current_effective")
    updated["addressees_proposed"] = effective.get("addressees_proposed_effective")
    updated["annual_frequency_proposed"] = effective.get("annual_frequency_proposed_effective")
    updated["cases_proposed"] = effective.get("cases_proposed_effective")
    return updated


def _with_step_metrics(
    meta_information: dict, step: dict, session_id: int, norm_addressee: str
) -> dict:
    effective = db.resolve_effective_process_step_metrics(step)
    updated = dict(meta_information)
    updated["description"] = effective.get("description")
    updated["personnel_rows"] = step_personnel_meta_rows(
        session_id, norm_addressee, step["step_id"]
    )
    updated["time_required_current"] = {
        "a": effective.get("time_required_in_min_a_current_effective"),
        "b": effective.get("time_required_in_min_b_current_effective"),
        "c": effective.get("time_required_in_min_c_current_effective"),
        "d": effective.get("time_required_in_min_d_current_effective"),
    }
    updated["time_required_proposed"] = {
        "a": effective.get("time_required_in_min_a_proposed_effective"),
        "b": effective.get("time_required_in_min_b_proposed_effective"),
        "c": effective.get("time_required_in_min_c_proposed_effective"),
        "d": effective.get("time_required_in_min_d_proposed_effective"),
    }
    updated["expenses_current"] = effective.get("expenses_current_effective")
    updated["expenses_proposed"] = effective.get("expenses_proposed_effective")
    updated["cost_current"] = step.get("cost_current")
    updated["cost_proposed"] = step.get("cost_proposed")
    return updated


def _group_by_addressee(
    rows: list[dict],
    default_addressee: str,
) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        addressee = str(row.get("norm_addressee") or default_addressee)
        grouped.setdefault(addressee, []).append(row)
    return grouped


def refresh_case_group_tiles(
    session_id: int,
    case_groups: list[dict],
    norm_addressee: str = ADMINISTRATION,
) -> None:
    for addressee, groups in _group_by_addressee(case_groups, norm_addressee).items():
        tiles = {
            tile.id: tile
            for tile in db.fetch_tiles(session_id=session_id, norm_addressee=addressee)
        }
        for group in groups:
            tile_id = f"case_group_{group['case_group_id']}"
            tile = tiles.get(tile_id)
            if not tile:
                continue
            updated = Tile(
                id=tile.id,
                title=tile.title,
                text=_case_group_text(group),
                meta_information=_with_case_group_metrics(
                    _apply_change_status(tile, group.get("change_status")),
                    group,
                ),
                column=tile.column,
                row=tile.row,
                deletable=tile.deletable,
                link_from_tile=tile.link_from_tile,
            )
            db.upsert_tile(updated, session_id=session_id, norm_addressee=addressee)


def refresh_regulation_tiles(
    session_id: int,
    regulations: list[dict],
    norm_addressee: str = ADMINISTRATION,
) -> None:
    tiles = {
        tile.id: tile
        for tile in db.fetch_tiles(session_id=session_id, norm_addressee=norm_addressee)
    }
    for regulation in regulations:
        tile_id = f"regulation_{regulation['regulation_id']}"
        tile = tiles.get(tile_id)
        if not tile:
            continue
        meta_information = dict(tile.meta_information or {})
        meta_information["is_business_information_obligation"] = bool(
            regulation.get("is_business_information_obligation")
        )
        updated = Tile(
            id=tile.id,
            title=tile.title,
            text=tile.text,
            meta_information=meta_information,
            column=tile.column,
            row=tile.row,
            deletable=tile.deletable,
            link_from_tile=tile.link_from_tile,
        )
        db.upsert_tile(updated, session_id=session_id, norm_addressee=norm_addressee)


def refresh_step_tiles(
    session_id: int,
    steps: list[dict],
    norm_addressee: str = ADMINISTRATION,
) -> None:
    for addressee, addressee_steps in _group_by_addressee(steps, norm_addressee).items():
        tiles = {
            tile.id: tile
            for tile in db.fetch_tiles(session_id=session_id, norm_addressee=addressee)
        }
        for step in addressee_steps:
            tile_id = f"step_{step['step_id']}"
            tile = tiles.get(tile_id)
            if not tile:
                continue
            updated = Tile(
                id=tile.id,
                title=tile.title,
                text=build_step_tile_text(session_id, step, addressee),
                meta_information=_with_step_metrics(
                    _apply_change_status(tile, step.get("change_status")),
                    step,
                    session_id,
                    addressee,
                ),
                column=tile.column,
                row=tile.row,
                deletable=tile.deletable,
                link_from_tile=tile.link_from_tile,
            )
            db.upsert_tile(updated, session_id=session_id, norm_addressee=addressee)
