from __future__ import annotations

from backend.core import db
from backend.core.models import Tile


def _build_case_group_tile_text(group: dict) -> str:
    return db.build_case_group_tile_text(
        description=group["description"],
        addressees_current=group.get("addressees_current"),
        annual_frequency_current=group.get("annual_frequency_current"),
        addressees_proposed=group.get("addressees_proposed"),
        annual_frequency_proposed=group.get("annual_frequency_proposed"),
        cases_current=group.get("cases_current"),
        cases_proposed=group.get("cases_proposed"),
    )


def _build_step_tile_text(step: dict) -> str:
    return db.build_process_step_tile_text(
        description=step["description"],
        hourly_rates_current={
            "a": step.get("hourly_rate_a_current"),
            "b": step.get("hourly_rate_b_current"),
            "c": step.get("hourly_rate_c_current"),
            "d": step.get("hourly_rate_d_current"),
        },
        time_required_current={
            "a": step.get("time_required_in_min_a_current"),
            "b": step.get("time_required_in_min_b_current"),
            "c": step.get("time_required_in_min_c_current"),
            "d": step.get("time_required_in_min_d_current"),
        },
        expenses_current=step.get("expenses_current"),
        cost_current=step.get("cost_current"),
        hourly_rates_proposed={
            "a": step.get("hourly_rate_a_proposed"),
            "b": step.get("hourly_rate_b_proposed"),
            "c": step.get("hourly_rate_c_proposed"),
            "d": step.get("hourly_rate_d_proposed"),
        },
        time_required_proposed={
            "a": step.get("time_required_in_min_a_proposed"),
            "b": step.get("time_required_in_min_b_proposed"),
            "c": step.get("time_required_in_min_c_proposed"),
            "d": step.get("time_required_in_min_d_proposed"),
        },
        expenses_proposed=step.get("expenses_proposed"),
        cost_proposed=step.get("cost_proposed"),
        execution_per_case=step.get("execution_per_case"),
    )


def _apply_change_status(tile: Tile, change_status: object) -> dict:
    meta_information = dict(tile.meta_information or {})
    if change_status:
        meta_information["change_status"] = change_status
    return meta_information


def _with_case_group_metrics(meta_information: dict, group: dict) -> dict:
    updated = dict(meta_information)
    updated["cases_current"] = group.get("cases_current")
    updated["cases_proposed"] = group.get("cases_proposed")
    return updated


def _with_step_cost_metrics(meta_information: dict, step: dict) -> dict:
    updated = dict(meta_information)
    updated["cost_current"] = step.get("cost_current")
    updated["cost_proposed"] = step.get("cost_proposed")
    updated["execution_per_case"] = step.get("execution_per_case")
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
            text=_build_case_group_tile_text(group),
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
            text=_build_step_tile_text(step),
            meta_information=_with_step_cost_metrics(
                _apply_change_status(tile, step.get("change_status")),
                step,
            ),
            column=tile.column,
            row=tile.row,
            deletable=tile.deletable,
            link_from_tile=tile.link_from_tile,
        )
        db.upsert_tile(updated, session_id=session_id)
