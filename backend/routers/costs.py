from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core import db
from backend.core.db_formatting import format_currency, format_number
from backend.core.models import Tile
from backend.core.norm_addressees import (
    ADMINISTRATION,
    BUSINESS,
    CITIZENS,
)
from backend.core.tile_refresh import refresh_case_group_tiles, refresh_step_tiles
from backend.routers._norm_addressee import normalize_norm_addressee_or_422


router = APIRouter(prefix="/costs", tags=["costs"])


class CostComputationRequest(BaseModel):
    app_session_id: str
    norm_addressee: str | None = None


def _skipped_cost_response(norm_addressee: str) -> dict:
    return _build_cost_response(
        norm_addressee=norm_addressee,
        total_cost=None,
        bureaucracy_cost=None,
        total_time_minutes=None,
        total_expenses=None,
    )


def _safe_number(value: float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _resolve_hourly_rate(
    step: dict,
    suffix: str,
    key: str,
    norm_addressee: str,
    active_rates: dict[str, float],
) -> float:
    if norm_addressee == CITIZENS:
        return 0.0
    value = step.get(f"hourly_rate_{key}_{suffix}")
    if value is not None:
        return float(value)
    if norm_addressee in {ADMINISTRATION, BUSINESS}:
        return _safe_number(active_rates.get(key))
    return 0.0


def _compute_step_cost(
    step: dict,
    suffix: str,
    norm_addressee: str,
    active_rates: dict[str, float],
) -> float:
    total = 0.0
    for key in ["a", "b", "c", "d"]:
        rate = _resolve_hourly_rate(step, suffix, key, norm_addressee, active_rates)
        minutes = _safe_number(step.get(f"time_required_in_min_{key}_{suffix}_effective"))
        total += rate * (minutes / 60.0)
    total += _safe_number(step.get(f"expenses_{suffix}_effective"))
    return total


def _compute_step_time_minutes(step: dict, suffix: str) -> float:
    total = 0.0
    for key in ["a", "b", "c", "d"]:
        total += _safe_number(step.get(f"time_required_in_min_{key}_{suffix}_effective"))
    return total


def _has_step_cost_inputs(step: dict, suffix: str, norm_addressee: str) -> bool:
    if norm_addressee == CITIZENS:
        for key in ["a", "b", "c", "d"]:
            if step.get(f"time_required_in_min_{key}_{suffix}_effective") is not None:
                return True
        return step.get(f"expenses_{suffix}_effective") is not None
    for key in ["a", "b", "c", "d"]:
        if step.get(f"time_required_in_min_{key}_{suffix}_effective") is None:
            continue
        if norm_addressee in {ADMINISTRATION, BUSINESS}:
            return True
        if step.get(f"hourly_rate_{key}_{suffix}") is not None:
            return True
    return step.get(f"expenses_{suffix}_effective") is not None


def _has_case_inputs(group: dict, suffix: str) -> bool:
    return (
        group.get(f"addressees_{suffix}_effective") is not None
        and group.get(f"annual_frequency_{suffix}_effective") is not None
    )


def _compute_cases(group: dict, suffix: str) -> float:
    return _safe_number(group.get(f"addressees_{suffix}_effective")) * _safe_number(
        group.get(f"annual_frequency_{suffix}_effective")
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


def _load_structure_rows(session_id: int, norm_addressee: str) -> tuple[list[dict], list[dict], list[dict]]:
    processes = db.list_processes_for_session_and_addressee(session_id, norm_addressee)
    case_groups = db.list_case_groups_for_session_and_addressee(session_id, norm_addressee)
    steps = db.list_process_steps_for_session_and_addressee(session_id, norm_addressee)
    return processes, case_groups, steps


def _list_business_information_step_ids(session_id: int, norm_addressee: str) -> set[int]:
    business_regulation_ids = {
        int(row["regulation_id"])
        for row in db.list_regulations_for_session_and_addressee(session_id, norm_addressee)
        if bool(row.get("is_business_information_obligation"))
    }
    if not business_regulation_ids:
        return set()
    regulation_ids_by_step = db.get_process_step_regulation_ids_by_step(
        session_id,
        norm_addressee,
    )
    process_regulation_ids: dict[int, set[int]] = {}
    for row in db.list_regulations_for_session_and_addressee(session_id, norm_addressee):
        process_id = row.get("process_id")
        regulation_id = row.get("regulation_id")
        if process_id is None or regulation_id is None:
            continue
        process_regulation_ids.setdefault(int(process_id), set()).add(int(regulation_id))
    process_id_by_case_group = {
        int(row["case_group_id"]): int(row["process_id"])
        for row in db.list_case_groups_for_session_and_addressee(session_id, norm_addressee)
    }
    step_rows = db.list_process_steps_for_session_and_addressee(session_id, norm_addressee)
    matched_step_ids: set[int] = set()
    for step in step_rows:
        step_id = int(step["step_id"])
        case_group_id = int(step["case_group_id"])
        regulation_ids = regulation_ids_by_step.get(step_id)
        if not regulation_ids:
            process_id = process_id_by_case_group.get(case_group_id)
            regulation_ids = sorted(process_regulation_ids.get(process_id, set()))
        if regulation_ids and any(
            regulation_id in business_regulation_ids for regulation_id in regulation_ids
        ):
            matched_step_ids.add(step_id)
    return matched_step_ids


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


def _ensure_structure_or_skip(
    *,
    session_id: int,
    norm_addressee: str,
    processes: list[dict],
    case_groups: list[dict],
    steps: list[dict],
) -> dict | None:
    session_has_any_regulations = bool(db.list_regulations_for_session(session_id))
    if not processes:
        if (
            session_has_any_regulations
            and not db.has_applicable_regulations_for_addressee(session_id, norm_addressee)
        ):
            return _skipped_cost_response(norm_addressee)
        raise HTTPException(
            status_code=400,
            detail=(
                "No processes for session"
                if norm_addressee == ADMINISTRATION
                else "No processes for selected norm addressee"
            ),
        )
    if not case_groups:
        if (
            session_has_any_regulations
            and not db.has_applicable_regulations_for_addressee(session_id, norm_addressee)
        ):
            return _skipped_cost_response(norm_addressee)
        raise HTTPException(
            status_code=400,
            detail=(
                "No case groups for session"
                if norm_addressee == ADMINISTRATION
                else "No case groups for selected norm addressee"
            ),
        )
    if not steps:
        if (
            session_has_any_regulations
            and not db.has_applicable_regulations_for_addressee(session_id, norm_addressee)
        ):
            return _skipped_cost_response(norm_addressee)
        raise HTTPException(
            status_code=400,
            detail=(
                "No process steps for session"
                if norm_addressee == ADMINISTRATION
                else "No process steps for selected norm addressee"
            ),
        )
    return None


def _compute_step_metrics(
    *,
    steps: list[dict],
    case_groups: list[dict],
    norm_addressee: str,
    active_rates: dict[str, float],
    business_information_step_ids: set[int],
) -> tuple[
    dict[int, float],
    dict[int, float],
    dict[int, float],
    dict[int, float],
    dict[int, float],
    dict[int, float],
    dict[int, bool],
]:
    step_costs_current: dict[int, float] = {}
    step_costs_proposed: dict[int, float] = {}
    step_time_current: dict[int, float] = {}
    step_time_proposed: dict[int, float] = {}
    step_bureaucracy_current: dict[int, float] = {}
    step_bureaucracy_proposed: dict[int, float] = {}
    per_case_flags: dict[int, bool] = {}

    for step in steps:
        step_id = int(step["step_id"])
        if norm_addressee == CITIZENS:
            cost_current = _safe_number(step.get("expenses_current_effective"))
            cost_proposed = _safe_number(step.get("expenses_proposed_effective"))
        else:
            cost_current = _compute_step_cost(step, "current", norm_addressee, active_rates)
            cost_proposed = _compute_step_cost(step, "proposed", norm_addressee, active_rates)
        time_current = _compute_step_time_minutes(step, "current")
        time_proposed = _compute_step_time_minutes(step, "proposed")
        is_bureaucracy = (
            norm_addressee == BUSINESS
            and step_id in business_information_step_ids
        )
        step_costs_current[step_id] = cost_current
        step_costs_proposed[step_id] = cost_proposed
        step_time_current[step_id] = time_current
        step_time_proposed[step_id] = time_proposed
        step_bureaucracy_current[step_id] = cost_current if is_bureaucracy else 0.0
        step_bureaucracy_proposed[step_id] = cost_proposed if is_bureaucracy else 0.0
        per_case_flags[step_id] = bool(step.get("execution_per_case")) if step.get("execution_per_case") is not None else True
        step["cost_current"] = cost_current
        step["cost_proposed"] = cost_proposed

    return (
        step_costs_current,
        step_costs_proposed,
        step_time_current,
        step_time_proposed,
        step_bureaucracy_current,
        step_bureaucracy_proposed,
        per_case_flags,
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
            step_bureaucracy_current[step_id],
            step_bureaucracy_proposed[step_id],
            cost_current - step_bureaucracy_current[step_id],
            cost_proposed - step_bureaucracy_proposed[step_id],
        )


def _build_steps_by_group(steps: list[dict]) -> dict[int, list[int]]:
    steps_by_group: dict[int, list[int]] = {}
    for step in steps:
        steps_by_group.setdefault(int(step["case_group_id"]), []).append(
            int(step["step_id"])
        )
    return steps_by_group


def _aggregate_case_group_costs(
    *,
    session_id: int,
    effective_case_groups: list[dict],
    case_groups: list[dict],
    effective_steps_by_id: dict[int, dict],
    steps_by_group: dict[int, list[int]],
    step_costs_current: dict[int, float],
    step_costs_proposed: dict[int, float],
    step_time_current: dict[int, float],
    step_time_proposed: dict[int, float],
    step_bureaucracy_current: dict[int, float],
    step_bureaucracy_proposed: dict[int, float],
    per_case_flags: dict[int, bool],
    norm_addressee: str,
) -> tuple[dict[int, float], dict[int, float], dict[int, float], dict[int, float]]:
    case_group_costs: dict[int, float] = {}
    case_group_bureaucracy_costs: dict[int, float] = {}
    case_group_time_deltas: dict[int, float] = {}
    case_group_expense_deltas: dict[int, float] = {}
    for idx, group in enumerate(effective_case_groups):
        case_group_id = int(group["case_group_id"])
        case_steps = steps_by_group.get(case_group_id, [])
        cases_current = _compute_cases(group, "current")
        cases_proposed = _compute_cases(group, "proposed")
        cost_current = 0.0
        cost_proposed = 0.0
        bureaucracy_current = 0.0
        bureaucracy_proposed = 0.0
        time_total_current = 0.0
        time_total_proposed = 0.0
        expenses_total_current = 0.0
        expenses_total_proposed = 0.0
        for step_id in case_steps:
            step_effective = effective_steps_by_id.get(step_id, {})
            step_multiplier_current = cases_current if per_case_flags.get(step_id, True) else 1.0
            step_multiplier_proposed = cases_proposed if per_case_flags.get(step_id, True) else 1.0
            cost_current += step_costs_current.get(step_id, 0.0) * step_multiplier_current
            cost_proposed += step_costs_proposed.get(step_id, 0.0) * step_multiplier_proposed
            bureaucracy_current += (
                step_bureaucracy_current.get(step_id, 0.0) * step_multiplier_current
            )
            bureaucracy_proposed += (
                step_bureaucracy_proposed.get(step_id, 0.0) * step_multiplier_proposed
            )
            time_total_current += step_time_current.get(step_id, 0.0) * step_multiplier_current
            time_total_proposed += step_time_proposed.get(step_id, 0.0) * step_multiplier_proposed
            expenses_total_current += _safe_number(
                step_effective.get("expenses_current_effective")
            ) * step_multiplier_current
            expenses_total_proposed += _safe_number(
                step_effective.get("expenses_proposed_effective")
            ) * step_multiplier_proposed
        cost_delta = cost_proposed - cost_current
        group["cases_current"] = cases_current
        group["cases_proposed"] = cases_proposed
        group["cost"] = cost_delta
        case_groups[idx]["cost"] = cost_delta
        case_group_costs[case_group_id] = cost_delta
        case_group_bureaucracy_costs[case_group_id] = bureaucracy_proposed - bureaucracy_current
        case_group_time_deltas[case_group_id] = time_total_proposed - time_total_current
        case_group_expense_deltas[case_group_id] = expenses_total_proposed - expenses_total_current
        db.upsert_case_group_cost_by_addressee(
            session_id,
            case_group_id,
            norm_addressee,
            cost_delta,
        )
    return (
        case_group_costs,
        case_group_bureaucracy_costs,
        case_group_time_deltas,
        case_group_expense_deltas,
    )


def _aggregate_process_costs(
    *,
    session_id: int,
    processes: list[dict],
    case_groups: list[dict],
    case_group_costs: dict[int, float],
    case_group_bureaucracy_costs: dict[int, float],
    case_group_time_deltas: dict[int, float],
    case_group_expense_deltas: dict[int, float],
) -> tuple[dict[int, float], dict[int, float], dict[int, float], dict[int, float]]:
    groups_by_process: dict[int, list[int]] = {}
    for group in case_groups:
        groups_by_process.setdefault(int(group["process_id"]), []).append(
            int(group["case_group_id"])
        )

    process_costs: dict[int, float] = {}
    process_bureaucracy_costs: dict[int, float] = {}
    process_time_deltas: dict[int, float] = {}
    process_expense_deltas: dict[int, float] = {}
    for process in processes:
        process_id = int(process["process_id"])
        group_ids = groups_by_process.get(process_id, [])
        total = sum(case_group_costs.get(group_id, 0.0) for group_id in group_ids)
        bureaucracy_total = sum(
            case_group_bureaucracy_costs.get(group_id, 0.0) for group_id in group_ids
        )
        time_total = sum(case_group_time_deltas.get(group_id, 0.0) for group_id in group_ids)
        expense_total = sum(
            case_group_expense_deltas.get(group_id, 0.0) for group_id in group_ids
        )
        process_costs[process_id] = total
        process_bureaucracy_costs[process_id] = bureaucracy_total
        process_time_deltas[process_id] = time_total
        process_expense_deltas[process_id] = expense_total
        db.update_process_cost(session_id, process_id, total)
    return (
        process_costs,
        process_bureaucracy_costs,
        process_time_deltas,
        process_expense_deltas,
    )


@router.post("/compute")
async def compute_costs(payload: CostComputationRequest) -> dict:
    session = db.get_session_by_app_id(payload.app_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session_id = int(session["session_id"])
    norm_addressee = normalize_norm_addressee_or_422(payload.norm_addressee)

    processes, case_groups, steps = _load_structure_rows(session_id, norm_addressee)
    pay_rates = db.get_session_pay_rates_for_addressee(session_id, norm_addressee)
    if not pay_rates:
        raise HTTPException(status_code=404, detail="Session pay rates not found")
    active_rates = pay_rates["active"]
    effective_case_groups = [
        db.resolve_effective_case_group_metrics(group) for group in case_groups
    ]
    effective_steps = [db.resolve_effective_process_step_metrics(step) for step in steps]
    skipped_response = _ensure_structure_or_skip(
        session_id=session_id,
        norm_addressee=norm_addressee,
        processes=processes,
        case_groups=case_groups,
        steps=steps,
    )
    if skipped_response is not None:
        return skipped_response

    missing_case_groups = [
        str(group["case_group_id"])
        for group in effective_case_groups
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
        for step in effective_steps
        if not (
            _has_step_cost_inputs(step, "current", norm_addressee)
            or _has_step_cost_inputs(step, "proposed", norm_addressee)
        )
    ]
    if missing_steps:
        raise HTTPException(
            status_code=422,
            detail="Missing step cost metrics for step_id: " + ", ".join(missing_steps),
        )

    with db.transaction():
        business_information_step_ids = (
            _list_business_information_step_ids(session_id, norm_addressee)
            if norm_addressee == BUSINESS
            else set()
        )
        (
            step_costs_current,
            step_costs_proposed,
            step_time_current,
            step_time_proposed,
            step_bureaucracy_current,
            step_bureaucracy_proposed,
            per_case_flags,
        ) = _compute_step_metrics(
            steps=effective_steps,
            case_groups=effective_case_groups,
            norm_addressee=norm_addressee,
            active_rates=active_rates,
            business_information_step_ids=business_information_step_ids,
        )
        _persist_step_costs(
            session_id=session_id,
            steps=steps,
            norm_addressee=norm_addressee,
            step_costs_current=step_costs_current,
            step_costs_proposed=step_costs_proposed,
            step_bureaucracy_current=step_bureaucracy_current,
            step_bureaucracy_proposed=step_bureaucracy_proposed,
        )

        steps_by_group = _build_steps_by_group(effective_steps)
        effective_steps_by_id = {int(step["step_id"]): step for step in effective_steps}
        (
            case_group_costs,
            case_group_bureaucracy_costs,
            case_group_time_deltas,
            case_group_expense_deltas,
        ) = _aggregate_case_group_costs(
            session_id=session_id,
            effective_case_groups=effective_case_groups,
            case_groups=case_groups,
            effective_steps_by_id=effective_steps_by_id,
            steps_by_group=steps_by_group,
            step_costs_current=step_costs_current,
            step_costs_proposed=step_costs_proposed,
            step_time_current=step_time_current,
            step_time_proposed=step_time_proposed,
            step_bureaucracy_current=step_bureaucracy_current,
            step_bureaucracy_proposed=step_bureaucracy_proposed,
            per_case_flags=per_case_flags,
            norm_addressee=norm_addressee,
        )

        (
            process_costs,
            process_bureaucracy_costs,
            process_time_deltas,
            process_expense_deltas,
        ) = _aggregate_process_costs(
            session_id=session_id,
            processes=processes,
            case_groups=case_groups,
            case_group_costs=case_group_costs,
            case_group_bureaucracy_costs=case_group_bureaucracy_costs,
            case_group_time_deltas=case_group_time_deltas,
            case_group_expense_deltas=case_group_expense_deltas,
        )

        total_cost = sum(process_costs.values())
        bureaucracy_cost = sum(process_bureaucracy_costs.values()) if norm_addressee == BUSINESS else None
        total_time_minutes = (
            sum(process_time_deltas.values()) if norm_addressee == CITIZENS else None
        )
        total_expenses = (
            sum(process_expense_deltas.values()) if norm_addressee == CITIZENS else None
        )
        if norm_addressee == CITIZENS:
            total_cost = None
        db.upsert_session_total_costs_by_addressee(
            session_id=session_id,
            norm_addressee=norm_addressee,
            total_cost=total_cost,
            bureaucracy_cost=bureaucracy_cost,
            total_time_minutes=total_time_minutes,
            total_expenses=total_expenses,
        )
        if norm_addressee == ADMINISTRATION:
            db.update_session_cost(session_id, total_cost or 0.0)
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
                app_session_id=payload.app_session_id,
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
