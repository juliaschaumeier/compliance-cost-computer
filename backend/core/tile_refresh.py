from __future__ import annotations

from backend.core import db
from backend.core.models import Tile


def _case_group_description(group: dict) -> str:
    effective = db.resolve_effective_case_group_metrics(group)
    return (effective.get("description") or "").strip()


def _step_description(step: dict) -> str:
    return (step.get("description") or "").strip()


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


def _with_step_metrics(meta_information: dict, step: dict) -> dict:
    effective = db.resolve_effective_process_step_metrics(step)
    updated = dict(meta_information)
    updated["description"] = effective.get("description")
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


def refresh_case_group_tiles(session_id: int, case_groups: list[dict]) -> None:
    tiles = {tile.id: tile for tile in db.fetch_tiles(session_id=session_id)}
    for group in case_groups:
        tile_id = f"case_group_{group['case_group_id']}"
        tile = tiles.get(tile_id)
        if not tile:
            continue
        updated = Tile(
            id=tile.id,
            title=tile.title,
            text=_case_group_description(group),
            meta_information=_with_case_group_metrics(
                _apply_change_status(tile, group.get("change_status")),
                group,
            ),
            column=tile.column,
            row=tile.row,
            deletable=tile.deletable,
            link_from_tile=tile.link_from_tile,
        )
        db.upsert_tile(updated, session_id=session_id)


def refresh_step_tiles(session_id: int, steps: list[dict]) -> None:
    tiles = {tile.id: tile for tile in db.fetch_tiles(session_id=session_id)}
    for step in steps:
        tile_id = f"step_{step['step_id']}"
        tile = tiles.get(tile_id)
        if not tile:
            continue
        updated = Tile(
            id=tile.id,
            title=tile.title,
            text=_step_description(step),
            meta_information=_with_step_metrics(
                _apply_change_status(tile, step.get("change_status")),
                step,
            ),
            column=tile.column,
            row=tile.row,
            deletable=tile.deletable,
            link_from_tile=tile.link_from_tile,
        )
        db.upsert_tile(updated, session_id=session_id)
