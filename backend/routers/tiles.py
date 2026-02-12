from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core import db
from backend.core.models import Tile, TilesResponse


router = APIRouter(prefix="/tiles", tags=["tiles"])


@router.get("", response_model=TilesResponse)
async def list_tiles() -> TilesResponse:
    tiles = db.fetch_tiles()
    return TilesResponse(tiles=tiles)


@router.post("", response_model=Tile)
async def create_tile(tile: Tile) -> Tile:
    db.upsert_tile(tile)
    return tile


@router.delete("/{tile_id}")
async def remove_tile(tile_id: str) -> dict:
    db.delete_tile(tile_id)
    return {"ok": True}


@router.post("/seed")
async def seed_tiles() -> dict:
    db.seed_from_json()
    return {"ok": True}


class RebuildTilesRequest(BaseModel):
    app_session_id: str | None = None


@router.post("/rebuild")
async def rebuild_tiles(payload: RebuildTilesRequest) -> dict:
    if payload.app_session_id:
        session = db.get_session_by_app_id(payload.app_session_id)
    else:
        session = db.get_latest_session()
    if not session:
        raise HTTPException(status_code=404, detail="No session available")

    session_id = int(session["session_id"])
    db.clear_tiles()

    current_law = None
    proposed_law = None
    if session.get("current_law_id") is not None:
        current_law = db.get_law_by_id(int(session["current_law_id"]))
    if session.get("proposed_law_id") is not None:
        proposed_law = db.get_law_by_id(int(session["proposed_law_id"]))

    title = (session.get("law_diff_title") or "").strip()
    summary = (session.get("law_diff_summary") or "").strip()
    if not title:
        title = (
            (proposed_law or {}).get("file_name")
            or (current_law or {}).get("file_name")
            or "Gesetz"
        )
    law_tile = Tile(
        id="law_tile",
        title=title,
        text=summary,
        meta_information={
            "source_file": (proposed_law or {}).get("file_name"),
            "source_current_file": (current_law or {}).get("file_name"),
        },
        column=0,
        row=0,
        deletable=False,
        link_from_tile=[],
    )
    db.upsert_tile(law_tile)

    regulations = db.list_regulations_for_session(session_id)
    regulation_tiles: dict[int, Tile] = {}
    for idx, regulation in enumerate(regulations):
        regulation_id = int(regulation["regulation_id"])
        tile = Tile(
            id=f"regulation_{regulation_id}",
            title=regulation["legal_citation"],
            text=regulation["description"],
            meta_information={"regulation_id": regulation_id},
            column=1,
            row=idx,
            deletable=True,
            link_from_tile=["law_tile"],
        )
        db.upsert_tile(tile)
        regulation_tiles[regulation_id] = tile

    processes = db.list_processes_for_session(session_id)
    process_col = 2 if regulations else 2
    process_tiles: dict[int, Tile] = {}
    regs_by_process: dict[int, list[str]] = {}
    for regulation in regulations:
        process_id = regulation.get("process_id")
        if process_id is None:
            continue
        regs_by_process.setdefault(int(process_id), []).append(
            f"regulation_{regulation['regulation_id']}"
        )

    for idx, process in enumerate(processes):
        process_id = int(process["process_id"])
        process_text = db.build_process_tile_text(
            description=process.get("description") or "",
            cost=process.get("cost"),
        )
        tile = Tile(
            id=f"process_{process_id}",
            title=process["process"],
            text=process_text,
            meta_information={"process_id": process_id},
            column=process_col,
            row=idx,
            deletable=True,
            link_from_tile=regs_by_process.get(process_id, []),
        )
        db.upsert_tile(tile)
        process_tiles[process_id] = tile

    case_groups = db.list_case_groups_for_session(session_id)
    case_group_col = process_col + 1
    groups_by_process: dict[int, list[dict]] = {}
    for group in case_groups:
        groups_by_process.setdefault(int(group["process_id"]), []).append(group)

    case_group_tiles: dict[int, Tile] = {}
    for process in processes:
        process_id = int(process["process_id"])
        base_row = process_tiles.get(process_id).row if process_id in process_tiles else 0
        for idx, group in enumerate(groups_by_process.get(process_id, [])):
            case_group_id = int(group["case_group_id"])
            case_group_text = db.build_case_group_tile_text(
                description=group["description"],
                addressees=group.get("addressees"),
                annual_frequency=group.get("annual_frequency"),
            )
            tile = Tile(
                id=f"case_group_{case_group_id}",
                title=group["case_group"],
                text=case_group_text,
                meta_information={
                    "case_group_id": case_group_id,
                    "process_id": process_id,
                },
                column=case_group_col,
                row=base_row + idx,
                deletable=True,
                link_from_tile=[f"process_{process_id}"]
                if process_id in process_tiles
                else [],
            )
            db.upsert_tile(tile)
            case_group_tiles[case_group_id] = tile

    steps = db.list_process_steps_for_session(session_id)
    steps_by_group: dict[int, dict[int, dict]] = {}
    for step in steps:
        steps_by_group.setdefault(int(step["case_group_id"]), {})[
            int(step["step_id"])
        ] = step

    for case_group_id, step_map in steps_by_group.items():
        case_group_tile = case_group_tiles.get(case_group_id)
        if not case_group_tile:
            continue
        steps_by_prev: dict[int | None, list[int]] = {}
        for step_id, step in step_map.items():
            steps_by_prev.setdefault(step.get("previous_id"), []).append(step_id)
        ordered: list[int] = []
        start_ids = steps_by_prev.get(None, [])
        if start_ids:
            current_id = start_ids[0]
            seen = set()
            while current_id and current_id not in seen:
                seen.add(current_id)
                ordered.append(current_id)
                next_id = step_map[current_id].get("next_id")
                current_id = int(next_id) if next_id is not None else None
        if not ordered:
            ordered = sorted(step_map.keys())

        for idx, step_id in enumerate(ordered):
            step = step_map[step_id]
            hourly_rates = {
                "a": step.get("hourly_rate_a"),
                "b": step.get("hourly_rate_b"),
                "c": step.get("hourly_rate_c"),
                "d": step.get("hourly_rate_d"),
                "e": step.get("hourly_rate_e"),
            }
            time_required = {
                "a": step.get("time_required_in_min_a"),
                "b": step.get("time_required_in_min_b"),
                "c": step.get("time_required_in_min_c"),
                "d": step.get("time_required_in_min_d"),
                "e": step.get("time_required_in_min_e"),
            }
            step_text = db.build_process_step_tile_text(
                description=step["description"],
                hourly_rates=hourly_rates,
                time_required=time_required,
                expenses=step.get("expenses"),
                cost=step.get("cost"),
                execution_per_case=step.get("execution_per_case"),
            )
            link_from = (
                [f"step_{ordered[idx - 1]}"]
                if idx > 0
                else [case_group_tile.id]
            )
            tile = Tile(
                id=f"step_{step_id}",
                title=step["step"],
                text=step_text,
                meta_information={
                    "step_id": step_id,
                    "case_group_id": case_group_id,
                    "process_id": case_group_tile.meta_information.get("process_id"),
                },
                column=case_group_tile.column + 1 + idx,
                row=case_group_tile.row,
                deletable=True,
                link_from_tile=link_from,
            )
            db.upsert_tile(tile)

    if session.get("cc_cost") is not None:
        tiles = db.fetch_tiles()
        step_tiles = [tile for tile in tiles if tile.id.startswith("step_")]
        max_step_col = max((tile.column for tile in step_tiles), default=None)
        max_col = max((tile.column for tile in tiles), default=case_group_col)
        total_col = (max_step_col if max_step_col is not None else max_col) + 1
        total_cases = 0.0
        for group in case_groups:
            addressees = group.get("addressees") or 0
            frequency = group.get("annual_frequency") or 0
            try:
                total_cases += float(addressees) * float(frequency)
            except (TypeError, ValueError):
                continue
        last_steps = []
        for step_map in steps_by_group.values():
            candidates = [
                step_id
                for step_id, step in step_map.items()
                if step.get("next_id") is None
            ]
            if candidates:
                last_steps.extend(candidates)
            elif step_map:
                last_steps.append(max(step_map.keys()))
        total_tile = Tile(
            id="total_cost",
            title="Jährliche Kosten",
            text="\n".join(
                [
                    db.format_currency(float(session["cc_cost"])),
                    f"Fälle pro Jahr: {db.format_number(total_cases)}",
                ]
            ),
            meta_information={"session_id": session_id},
            column=total_col,
            row=0,
            deletable=True,
            link_from_tile=[f"step_{step_id}" for step_id in last_steps],
        )
        db.upsert_tile(total_tile)

    return {"ok": True, "session_id": session_id}
