from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core import db
from backend.core.models import Tile
from backend.core.tile_refresh import refresh_case_group_tiles, refresh_step_tiles


router = APIRouter(prefix="/costs", tags=["costs"])


class CostComputationRequest(BaseModel):
    app_session_id: str


def _safe_number(value: float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _compute_step_cost(step: dict, suffix: str) -> float:
    total = 0.0
    for key in ["a", "b", "c", "d"]:
        rate = _safe_number(step.get(f"hourly_rate_{key}_{suffix}"))
        minutes = _safe_number(step.get(f"time_required_in_min_{key}_{suffix}"))
        total += rate * (minutes / 60.0)
    total += _safe_number(step.get(f"expenses_{suffix}"))
    return total


def _has_step_cost_inputs(step: dict, suffix: str) -> bool:
    for key in ["a", "b", "c", "d"]:
        if (
            step.get(f"hourly_rate_{key}_{suffix}") is not None
            and step.get(f"time_required_in_min_{key}_{suffix}") is not None
        ):
            return True
    return step.get(f"expenses_{suffix}") is not None


def _has_case_inputs(group: dict, suffix: str) -> bool:
    return (
        group.get(f"addressees_{suffix}") is not None
        and group.get(f"annual_frequency_{suffix}") is not None
    )


def _compute_cases(group: dict, suffix: str) -> float:
    return _safe_number(group.get(f"addressees_{suffix}")) * _safe_number(
        group.get(f"annual_frequency_{suffix}")
    )


def _last_step_ids(steps: list[dict]) -> list[int]:
    steps_by_group: dict[int, dict[int, dict]] = {}
    for step in steps:
        steps_by_group.setdefault(int(step["case_group_id"]), {})[
            int(step["step_id"])
        ] = step

    last_ids: list[int] = []
    for step_map in steps_by_group.values():
        candidates = [sid for sid, s in step_map.items() if s.get("next_id") is None]
        if candidates:
            last_ids.extend(candidates)
            continue
        last_ids.append(max(step_map.keys()))
    return last_ids


def _refresh_process_tiles(
    session_id: int,
    processes: list[dict],
    costs: dict[int, float],
) -> None:
    tiles = {tile.id: tile for tile in db.fetch_tiles(session_id=session_id)}
    for process in processes:
        process_id = int(process["process_id"])
        tile_id = f"process_{process_id}"
        tile = tiles.get(tile_id)
        if not tile:
            continue
        cost = costs.get(process_id)
        text = db.build_process_tile_text(
            description=process.get("description") or "",
            cost=cost,
        )
        updated = Tile(
            id=tile.id,
            title=tile.title,
            text=text,
            meta_information={
                **dict(tile.meta_information or {}),
                "cost": cost,
            },
            column=tile.column,
            row=tile.row,
            deletable=tile.deletable,
            link_from_tile=tile.link_from_tile,
        )
        db.upsert_tile(updated, session_id=session_id)


@router.post("/compute")
async def compute_costs(payload: CostComputationRequest) -> dict:
    session = db.get_session_by_app_id(payload.app_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session_id = int(session["session_id"])

    case_groups = db.list_case_groups_for_session(session_id)
    processes = db.list_processes_for_session(session_id)
    steps = db.list_process_steps_for_session(session_id)
    if not case_groups:
        raise HTTPException(status_code=400, detail="No case groups for session")
    if not steps:
        raise HTTPException(status_code=400, detail="No process steps for session")

    missing_case_groups = [
        str(group["case_group_id"])
        for group in case_groups
        if not (_has_case_inputs(group, "current") or _has_case_inputs(group, "proposed"))
    ]
    if missing_case_groups:
        raise HTTPException(
            status_code=422,
            detail="Missing case group metrics for case_group_id: "
            + ", ".join(missing_case_groups),
        )
    missing_steps = [
        str(step["step_id"])
        for step in steps
        if not (
            _has_step_cost_inputs(step, "current")
            or _has_step_cost_inputs(step, "proposed")
        )
    ]
    if missing_steps:
        raise HTTPException(
            status_code=422,
            detail="Missing step cost metrics for step_id: " + ", ".join(missing_steps),
        )

    with db.transaction():
        step_costs_current: dict[int, float] = {}
        step_costs_proposed: dict[int, float] = {}
        per_case_flags: dict[int, bool] = {}
        for step in steps:
            cost_current = _compute_step_cost(step, "current")
            cost_proposed = _compute_step_cost(step, "proposed")
            step_id = int(step["step_id"])
            step_costs_current[step_id] = cost_current
            step_costs_proposed[step_id] = cost_proposed
            step["cost_current"] = cost_current
            step["cost_proposed"] = cost_proposed
            raw_flag = step.get("execution_per_case")
            per_case_flags[step_id] = bool(raw_flag) if raw_flag is not None else True
            db.update_process_step_cost(session_id, step_id, cost_current, cost_proposed)

        steps_by_group: dict[int, list[int]] = {}
        for step in steps:
            steps_by_group.setdefault(int(step["case_group_id"]), []).append(
                int(step["step_id"])
            )

        case_group_costs: dict[int, float] = {}
        for group in case_groups:
            case_group_id = int(group["case_group_id"])
            case_steps = steps_by_group.get(case_group_id, [])
            cases_current = _compute_cases(group, "current")
            cases_proposed = _compute_cases(group, "proposed")
            db.update_case_group_metrics(
                session_id,
                case_group_id,
                group.get("addressees_current"),
                group.get("annual_frequency_current"),
                group.get("addressees_proposed"),
                group.get("annual_frequency_proposed"),
                cases_current,
                cases_proposed,
            )
            cost_current = 0.0
            cost_proposed = 0.0
            for step_id in case_steps:
                step_cost_current = step_costs_current.get(step_id, 0.0)
                step_cost_proposed = step_costs_proposed.get(step_id, 0.0)
                if per_case_flags.get(step_id, True):
                    cost_current += step_cost_current * cases_current
                    cost_proposed += step_cost_proposed * cases_proposed
                else:
                    cost_current += step_cost_current
                    cost_proposed += step_cost_proposed
            cost_delta = cost_proposed - cost_current
            group["cases_current"] = cases_current
            group["cases_proposed"] = cases_proposed
            group["cost"] = cost_delta
            case_group_costs[case_group_id] = cost_delta
            db.update_case_group_cost(session_id, case_group_id, cost_delta)

        groups_by_process: dict[int, list[int]] = {}
        for group in case_groups:
            groups_by_process.setdefault(int(group["process_id"]), []).append(
                int(group["case_group_id"])
            )

        process_costs: dict[int, float] = {}
        for process in processes:
            process_id = int(process["process_id"])
            group_ids = groups_by_process.get(process_id, [])
            total = sum(case_group_costs.get(group_id, 0.0) for group_id in group_ids)
            process_costs[process_id] = total
            db.update_process_cost(session_id, process_id, total)

        total_cost = sum(process_costs.values())
        db.update_session_cost(session_id, total_cost)
        refresh_case_group_tiles(session_id, case_groups)
        refresh_step_tiles(session_id, steps)
        _refresh_process_tiles(session_id, processes, process_costs)

        tiles = db.fetch_tiles(session_id=session_id)
        step_tiles = [tile for tile in tiles if tile.id.startswith("step_")]
        max_step_col = max((tile.column for tile in step_tiles), default=None)
        max_col = max((tile.column for tile in tiles), default=0)
        total_col = (max_step_col if max_step_col is not None else max_col) + 1
        link_from = [f"step_{step_id}" for step_id in _last_step_ids(steps)]
        total_tile = Tile(
            id="total_cost",
            title="Jährliche Kosten",
            text=db.format_currency(total_cost),
            meta_information={"app_session_id": payload.app_session_id},
            column=total_col,
            row=0,
            deletable=True,
            link_from_tile=link_from,
        )
        db.upsert_tile(total_tile, session_id=session_id)

    return {"total_cost": total_cost}
