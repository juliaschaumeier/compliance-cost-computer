from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core import db
from backend.core.cost_aggregation import aggregate_addressee_costs
from backend.core.db_formatting import format_currency, format_number
from backend.core.models import Tile
from backend.core.norm_addressees import (
    ADMINISTRATION,
    BUSINESS,
    CITIZENS,
)
from backend.core.session_activity import (
    SessionActivityConflict,
    SessionActivityUnavailable,
    use_existing_session_activity,
)
from backend.core.tile_refresh import refresh_case_group_tiles, refresh_step_tiles
from backend.routers._norm_addressee import normalize_norm_addressee_or_422
from backend.routers._session_activity_guard import (
    raise_session_activity_conflict,
    raise_session_activity_unavailable,
)


router = APIRouter(prefix="/costs", tags=["costs"])


class CostComputationRequest(BaseModel):
    app_session_id: str
    norm_addressee: str | None = None
    ea_activity_id: str | None = None


def _build_cost_response(
    *,
    norm_addressee: str,
    total_cost: float | None,
    bureaucracy_cost: float | None,
    total_time_minutes: float | None,
    total_expenses: float | None,
) -> dict:
    return {
        "norm_addressee": norm_addressee,
        "total_cost": total_cost,
        "bureaucracy_cost": bureaucracy_cost if norm_addressee == BUSINESS else None,
        "other_cost": (
            total_cost - bureaucracy_cost
            if norm_addressee == BUSINESS and total_cost is not None and bureaucracy_cost is not None
            else None
        ),
        "total_time_minutes": total_time_minutes,
        "total_time_hours": (
            total_time_minutes / 60.0 if total_time_minutes is not None else None
        ),
        "total_expenses": total_expenses,
    }


def _skipped_cost_response(norm_addressee: str) -> dict:
    return _build_cost_response(
        norm_addressee=norm_addressee,
        total_cost=None,
        bureaucracy_cost=None,
        total_time_minutes=None,
        total_expenses=None,
    )


def _build_total_meta(
    *,
    app_session_id: str,
    norm_addressee: str,
    total_cost: float | None,
    bureaucracy_cost: float | None,
    total_time_minutes: float | None,
    total_expenses: float | None,
) -> dict:
    return {
        "app_session_id": app_session_id,
        "bureaucracy_cost": bureaucracy_cost if norm_addressee == BUSINESS else None,
        "other_cost": (
            total_cost - bureaucracy_cost
            if norm_addressee == BUSINESS and total_cost is not None and bureaucracy_cost is not None
            else None
        ),
        "total_time_minutes": total_time_minutes,
        "total_time_hours": (
            total_time_minutes / 60.0 if total_time_minutes is not None else None
        ),
        "total_expenses": total_expenses,
    }


def _build_total_tile_text(
    *,
    norm_addressee: str,
    total_cost: float | None,
    total_time_minutes: float | None,
    total_expenses: float | None,
) -> str:
    if norm_addressee == CITIZENS:
        lines: list[str] = []
        if total_time_minutes is not None:
            lines.append(f"Zeit: {format_number(total_time_minutes / 60.0)} Std.")
        if total_expenses is not None:
            lines.append(f"Sachaufwand: {format_currency(total_expenses)}")
        return "\n".join(lines).strip()
    return format_currency(total_cost or 0.0)


def _refresh_process_tiles(
    session_id: int,
    processes: list[dict],
    costs: dict[int, float],
    norm_addressee: str = ADMINISTRATION,
) -> None:
    tiles = {
        tile.id: tile
        for tile in db.fetch_tiles(session_id=session_id, norm_addressee=norm_addressee)
    }
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
        db.upsert_tile(updated, session_id=session_id, norm_addressee=norm_addressee)


def _persist_step_costs(
    *,
    session_id: int,
    steps: list[dict],
    norm_addressee: str,
    step_costs_current: dict[int, float],
    step_costs_proposed: dict[int, float],
    step_bureaucracy_current: dict[int, float],
    step_bureaucracy_proposed: dict[int, float],
) -> None:
    for idx, step in enumerate(steps):
        step_id = int(step["step_id"])
        cost_current = step_costs_current[step_id]
        cost_proposed = step_costs_proposed[step_id]
        steps[idx]["cost_current"] = cost_current
        steps[idx]["cost_proposed"] = cost_proposed
        db.upsert_process_step_cost_by_addressee(
            session_id,
            step_id,
            norm_addressee,
            cost_current,
            cost_proposed,
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


def compute_total_cost_for_session(
    app_session_id: str,
    norm_addressee: str | None = None,
) -> dict:
    session = db.get_session_by_app_id(app_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session_id = int(session["session_id"])
    norm_addressee = normalize_norm_addressee_or_422(norm_addressee)

    agg = aggregate_addressee_costs(session_id, norm_addressee, apply_user_edits=True)
    if agg.get("skipped"):
        return _skipped_cost_response(norm_addressee)

    processes = agg["processes"]
    case_groups = agg["case_groups"]
    steps = agg["steps"]
    case_group_costs = agg["case_group_costs"]
    process_costs = agg["process_costs"]
    total_cost = agg["total_cost"]
    bureaucracy_cost = agg["bureaucracy_cost"]
    total_time_minutes = agg["total_time_minutes"]
    total_expenses = agg["total_expenses"]

    with db.transaction():
        _persist_step_costs(
            session_id=session_id,
            steps=steps,
            norm_addressee=norm_addressee,
            step_costs_current=agg["step_costs_current"],
            step_costs_proposed=agg["step_costs_proposed"],
            step_bureaucracy_current=agg["step_bureaucracy_current"],
            step_bureaucracy_proposed=agg["step_bureaucracy_proposed"],
        )
        for case_group_id, case_group_cost in case_group_costs.items():
            db.upsert_case_group_cost_by_addressee(
                session_id, case_group_id, norm_addressee, case_group_cost
            )
        for process_id, process_cost in process_costs.items():
            db.update_process_cost(session_id, process_id, process_cost)
        db.upsert_session_total_costs_by_addressee(
            session_id=session_id,
            norm_addressee=norm_addressee,
            total_cost=total_cost,
            bureaucracy_cost=bureaucracy_cost,
            total_time_minutes=total_time_minutes,
            total_expenses=total_expenses,
        )
        refresh_case_group_tiles(session_id, case_groups, norm_addressee=norm_addressee)
        refresh_step_tiles(session_id, steps, norm_addressee=norm_addressee)
        _refresh_process_tiles(
            session_id,
            processes,
            process_costs,
            norm_addressee=norm_addressee,
        )

        tiles = db.fetch_tiles(session_id=session_id, norm_addressee=norm_addressee)
        step_tiles = [tile for tile in tiles if tile.id.startswith("step_")]
        max_step_col = max((tile.column for tile in step_tiles), default=None)
        max_col = max((tile.column for tile in tiles), default=0)
        total_col = (max_step_col if max_step_col is not None else max_col) + 1
        link_from = [f"step_{step_id}" for step_id in _last_step_ids(steps)]
        total_tile = Tile(
            id="total_cost",
            title=(
                "Jährlicher Erfüllungsaufwand"
                if norm_addressee == CITIZENS
                else "Jährliche Kosten"
            ),
            text=_build_total_tile_text(
                norm_addressee=norm_addressee,
                total_cost=total_cost,
                total_time_minutes=total_time_minutes,
                total_expenses=total_expenses,
            ),
            meta_information=_build_total_meta(
                app_session_id=app_session_id,
                norm_addressee=norm_addressee,
                total_cost=total_cost,
                bureaucracy_cost=bureaucracy_cost,
                total_time_minutes=total_time_minutes,
                total_expenses=total_expenses,
            ),
            column=total_col,
            row=0,
            deletable=True,
            link_from_tile=link_from,
        )
        db.upsert_tile(total_tile, session_id=session_id, norm_addressee=norm_addressee)

    return _build_cost_response(
        norm_addressee=norm_addressee,
        total_cost=total_cost,
        bureaucracy_cost=bureaucracy_cost,
        total_time_minutes=total_time_minutes,
        total_expenses=total_expenses,
    )


@router.post("/compute")
async def compute_costs(payload: CostComputationRequest) -> dict:
    session_id = db.get_session_id_by_app_id(payload.app_session_id)
    if session_id is None:
        raise HTTPException(status_code=404, detail="Session not found")
    active_activity = db.get_session_activity(session_id)
    requires_ea_owner = payload.ea_activity_id or (
        active_activity is not None and active_activity["activity_type"] == "ea_edit"
    )
    if requires_ea_owner:
        try:
            use_existing_session_activity(
                session_id=session_id,
                activity_id=payload.ea_activity_id,
                activity_type="ea_edit",
            )
        except SessionActivityConflict as exc:
            raise_session_activity_conflict(exc)
        except SessionActivityUnavailable as exc:
            raise_session_activity_unavailable(exc)
    return compute_total_cost_for_session(
        app_session_id=payload.app_session_id,
        norm_addressee=payload.norm_addressee,
    )
