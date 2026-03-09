from __future__ import annotations

from backend.core import db
from backend.core.models import Tile


def _ordered_step_ids(step_map: dict[int, dict]) -> list[int]:
    steps_by_prev: dict[int | None, list[int]] = {}
    for step_id, step in step_map.items():
        steps_by_prev.setdefault(step.get("previous_id"), []).append(step_id)
    ordered: list[int] = []
    start_ids = steps_by_prev.get(None, [])
    if start_ids:
        current_id = start_ids[0]
        seen: set[int] = set()
        while current_id and current_id not in seen:
            seen.add(current_id)
            ordered.append(current_id)
            next_id = step_map[current_id].get("next_id")
            current_id = int(next_id) if next_id is not None else None
    if not ordered:
        ordered = sorted(step_map.keys())
    return ordered


def build_session_tiles_snapshot(session: dict) -> list[Tile]:
    session_id = int(session["session_id"])

    current_law = None
    proposed_law = None
    if session.get("current_law_id") is not None:
        current_law = db.get_law_by_id(int(session["current_law_id"]))
    if session.get("proposed_law_id") is not None:
        proposed_law = db.get_law_by_id(int(session["proposed_law_id"]))

    title = (session.get("law_diff_title") or "").strip()
    blurb = (session.get("law_diff_blurb") or "").strip()
    summary = (session.get("law_diff_summary") or "").strip()
    law_tile_text = blurb or summary
    if not title:
        title = (
            (proposed_law or {}).get("file_name")
            or (current_law or {}).get("file_name")
            or "Gesetz"
        )

    tiles: list[Tile] = [
        Tile(
            id="law_tile",
            title=title,
            text=law_tile_text,
            meta_information={
                "source_file": (proposed_law or {}).get("file_name"),
                "source_current_file": (current_law or {}).get("file_name"),
            },
            column=0,
            row=0,
            deletable=False,
            link_from_tile=[],
        )
    ]

    regulations = db.list_regulations_for_session(session_id)
    for idx, regulation in enumerate(regulations):
        regulation_id = int(regulation["regulation_id"])
        tiles.append(
            Tile(
                id=f"regulation_{regulation_id}",
                title=regulation["legal_citation"],
                text=regulation["description"],
                meta_information={
                    "regulation_id": regulation_id,
                    "change_status": regulation.get("change_status"),
                },
                column=1,
                row=idx,
                deletable=True,
                link_from_tile=["law_tile"],
            )
        )

    processes = db.list_processes_for_session(session_id)
    regs_by_process: dict[int, list[str]] = {}
    for regulation in regulations:
        process_id = regulation.get("process_id")
        if process_id is None:
            continue
        regs_by_process.setdefault(int(process_id), []).append(
            f"regulation_{regulation['regulation_id']}"
        )

    process_tiles: dict[int, Tile] = {}
    process_col = 2
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
            meta_information={
                "process_id": process_id,
                "change_status": process.get("change_status"),
            },
            column=process_col,
            row=idx,
            deletable=True,
            link_from_tile=regs_by_process.get(process_id, []),
        )
        process_tiles[process_id] = tile
        tiles.append(tile)

    case_groups = db.list_case_groups_for_session(session_id)
    groups_by_process: dict[int, list[dict]] = {}
    for group in case_groups:
        groups_by_process.setdefault(int(group["process_id"]), []).append(group)

    case_group_tiles: dict[int, Tile] = {}
    case_group_col = process_col + 1
    for process in processes:
        process_id = int(process["process_id"])
        base_row = process_tiles.get(process_id).row if process_id in process_tiles else 0
        for idx, group in enumerate(groups_by_process.get(process_id, [])):
            case_group_id = int(group["case_group_id"])
            case_group_text = db.build_case_group_tile_text(
                description=group["description"],
                addressees_current=group.get("addressees_current"),
                annual_frequency_current=group.get("annual_frequency_current"),
                addressees_proposed=group.get("addressees_proposed"),
                annual_frequency_proposed=group.get("annual_frequency_proposed"),
                cases_current=group.get("cases_current"),
                cases_proposed=group.get("cases_proposed"),
            )
            tile = Tile(
                id=f"case_group_{case_group_id}",
                title=group["case_group"],
                text=case_group_text,
                meta_information={
                    "case_group_id": case_group_id,
                    "process_id": process_id,
                    "change_status": group.get("change_status"),
                },
                column=case_group_col,
                row=base_row + idx,
                deletable=True,
                link_from_tile=[f"process_{process_id}"]
                if process_id in process_tiles
                else [],
            )
            case_group_tiles[case_group_id] = tile
            tiles.append(tile)

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
        ordered = _ordered_step_ids(step_map)
        for idx, step_id in enumerate(ordered):
            step = step_map[step_id]
            hourly_rates_current = {
                "a": step.get("hourly_rate_a_current"),
                "b": step.get("hourly_rate_b_current"),
                "c": step.get("hourly_rate_c_current"),
                "d": step.get("hourly_rate_d_current"),
            }
            time_required_current = {
                "a": step.get("time_required_in_min_a_current"),
                "b": step.get("time_required_in_min_b_current"),
                "c": step.get("time_required_in_min_c_current"),
                "d": step.get("time_required_in_min_d_current"),
            }
            hourly_rates_proposed = {
                "a": step.get("hourly_rate_a_proposed"),
                "b": step.get("hourly_rate_b_proposed"),
                "c": step.get("hourly_rate_c_proposed"),
                "d": step.get("hourly_rate_d_proposed"),
            }
            time_required_proposed = {
                "a": step.get("time_required_in_min_a_proposed"),
                "b": step.get("time_required_in_min_b_proposed"),
                "c": step.get("time_required_in_min_c_proposed"),
                "d": step.get("time_required_in_min_d_proposed"),
            }
            step_text = db.build_process_step_tile_text(
                description=step["description"],
                hourly_rates_current=hourly_rates_current,
                time_required_current=time_required_current,
                expenses_current=step.get("expenses_current"),
                cost_current=step.get("cost_current"),
                hourly_rates_proposed=hourly_rates_proposed,
                time_required_proposed=time_required_proposed,
                expenses_proposed=step.get("expenses_proposed"),
                cost_proposed=step.get("cost_proposed"),
                execution_per_case=step.get("execution_per_case"),
            )
            tiles.append(
                Tile(
                    id=f"step_{step_id}",
                    title=step["step"],
                    text=step_text,
                    meta_information={
                        "step_id": step_id,
                        "case_group_id": case_group_id,
                        "process_id": case_group_tile.meta_information.get("process_id"),
                        "change_status": step.get("change_status"),
                    },
                    column=case_group_tile.column + 1 + idx,
                    row=case_group_tile.row,
                    deletable=True,
                    link_from_tile=[f"step_{ordered[idx - 1]}"]
                    if idx > 0
                    else [case_group_tile.id],
                )
            )

    if session.get("cc_cost") is not None:
        step_tiles = [tile for tile in tiles if tile.id.startswith("step_")]
        max_step_col = max((tile.column for tile in step_tiles), default=None)
        max_col = max((tile.column for tile in tiles), default=case_group_col)
        total_col = (max_step_col if max_step_col is not None else max_col) + 1

        total_cases_delta = 0.0
        for group in case_groups:
            try:
                proposed = float(group.get("cases_proposed") or 0)
                current = float(group.get("cases_current") or 0)
                total_cases_delta += proposed - current
            except (TypeError, ValueError):
                continue

        last_steps: list[int] = []
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

        tiles.append(
            Tile(
                id="total_cost",
                title="Jährliche Kosten",
                text="\n".join(
                    [
                        db.format_currency(float(session["cc_cost"])),
                        f"Fälle pro Jahr (Δ): {db.format_number(round(total_cases_delta))}",
                    ]
                ),
                meta_information=(
                    {"app_session_id": session["app_session_id"]}
                    if session.get("app_session_id")
                    else {}
                ),
                column=total_col,
                row=0,
                deletable=True,
                link_from_tile=[f"step_{step_id}" for step_id in last_steps],
            )
        )

    return tiles
