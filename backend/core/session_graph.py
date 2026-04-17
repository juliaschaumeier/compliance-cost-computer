from __future__ import annotations

from backend.core import db
from backend.core.db_formatting import (
    build_case_group_tile_text,
    build_process_step_tile_text,
)
from backend.core.models import Tile
from backend.core.norm_addressees import (
    ADMINISTRATION,
    ALL_NORM_ADDRESSEES,
    DISPLAY_LABELS,
    EFFORT_GROUP_LABELS,
    normalize_norm_addressee,
)


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


def build_session_tiles_snapshot(
    session: dict,
    norm_addressee: str = ADMINISTRATION,
) -> list[Tile]:
    session_id = int(session["session_id"])
    resolved = normalize_norm_addressee(norm_addressee)

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

    regulations = db.list_regulations_for_session_and_addressee(session_id, resolved)
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
                    "normadressaten": [
                        name
                        for name, enabled in (
                            ("administration", regulation.get("applies_to_administration")),
                            ("business", regulation.get("applies_to_business")),
                            ("citizens", regulation.get("applies_to_citizens")),
                        )
                        if enabled
                    ],
                },
                column=1,
                row=idx,
                deletable=True,
                link_from_tile=["law_tile"],
            )
        )

    processes = db.list_processes_for_session_and_addressee(session_id, resolved)
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
                "cost": process.get("cost"),
            },
            column=process_col,
            row=idx,
            deletable=True,
            link_from_tile=regs_by_process.get(process_id, []),
        )
        process_tiles[process_id] = tile
        tiles.append(tile)

    case_groups = db.list_case_groups_for_session_and_addressee(session_id, resolved)
    groups_by_process: dict[int, list[dict]] = {}
    for group in case_groups:
        groups_by_process.setdefault(int(group["process_id"]), []).append(group)

    case_group_tiles: dict[int, Tile] = {}
    case_group_col = process_col + 1
    for process in processes:
        process_id = int(process["process_id"])
        base_row = process_tiles.get(process_id).row if process_id in process_tiles else 0
        for idx, group in enumerate(groups_by_process.get(process_id, [])):
            effective_group = db.resolve_effective_case_group_metrics(group)
            case_group_id = int(group["case_group_id"])
            tile = Tile(
                id=f"case_group_{case_group_id}",
                title=group["case_group"],
                text=build_case_group_tile_text(
                    description=effective_group.get("description") or "",
                    addressees_current=effective_group.get("addressees_current_effective"),
                    annual_frequency_current=effective_group.get(
                        "annual_frequency_current_effective"
                    ),
                    addressees_proposed=effective_group.get("addressees_proposed_effective"),
                    annual_frequency_proposed=effective_group.get(
                        "annual_frequency_proposed_effective"
                    ),
                    cases_current=effective_group.get("cases_current_effective"),
                    cases_proposed=effective_group.get("cases_proposed_effective"),
                ),
                meta_information={
                    "case_group_id": case_group_id,
                    "process_id": process_id,
                    "description": effective_group.get("description"),
                    "change_status": group.get("change_status"),
                    "addressees_current": effective_group.get("addressees_current_effective"),
                    "annual_frequency_current": effective_group.get(
                        "annual_frequency_current_effective"
                    ),
                    "cases_current": effective_group.get("cases_current_effective"),
                    "addressees_proposed": effective_group.get("addressees_proposed_effective"),
                    "annual_frequency_proposed": effective_group.get(
                        "annual_frequency_proposed_effective"
                    ),
                    "cases_proposed": effective_group.get("cases_proposed_effective"),
                    "cost": group.get("cost"),
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

    steps = db.list_process_steps_for_session_and_addressee(session_id, resolved)
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
            effective_step = db.resolve_effective_process_step_metrics(step)
            time_required_current = {
                "a": effective_step.get("time_required_in_min_a_current_effective"),
                "b": effective_step.get("time_required_in_min_b_current_effective"),
                "c": effective_step.get("time_required_in_min_c_current_effective"),
                "d": effective_step.get("time_required_in_min_d_current_effective"),
            }
            time_required_proposed = {
                "a": effective_step.get("time_required_in_min_a_proposed_effective"),
                "b": effective_step.get("time_required_in_min_b_proposed_effective"),
                "c": effective_step.get("time_required_in_min_c_proposed_effective"),
                "d": effective_step.get("time_required_in_min_d_proposed_effective"),
            }
            tiles.append(
                Tile(
                    id=f"step_{step_id}",
                    title=step["step"],
                    text=build_process_step_tile_text(
                        description=effective_step.get("description") or "",
                        hourly_rates_current={
                            "a": effective_step.get("hourly_rate_a_current"),
                            "b": effective_step.get("hourly_rate_b_current"),
                            "c": effective_step.get("hourly_rate_c_current"),
                            "d": effective_step.get("hourly_rate_d_current"),
                        },
                        time_required_current=time_required_current,
                        expenses_current=effective_step.get("expenses_current_effective"),
                        cost_current=step.get("cost_current"),
                        hourly_rates_proposed={
                            "a": effective_step.get("hourly_rate_a_proposed"),
                            "b": effective_step.get("hourly_rate_b_proposed"),
                            "c": effective_step.get("hourly_rate_c_proposed"),
                            "d": effective_step.get("hourly_rate_d_proposed"),
                        },
                        time_required_proposed=time_required_proposed,
                        expenses_proposed=effective_step.get("expenses_proposed_effective"),
                        cost_proposed=step.get("cost_proposed"),
                        execution_per_case=step.get("execution_per_case"),
                        group_labels=EFFORT_GROUP_LABELS.get(resolved),
                    ),
                    meta_information={
                        "step_id": step_id,
                        "case_group_id": case_group_id,
                        "process_id": case_group_tile.meta_information.get("process_id"),
                        "description": effective_step.get("description"),
                        "change_status": step.get("change_status"),
                        "time_required_current": time_required_current,
                        "time_required_proposed": time_required_proposed,
                        "expenses_current": effective_step.get("expenses_current_effective"),
                        "expenses_proposed": effective_step.get("expenses_proposed_effective"),
                        "cost_current": step.get("cost_current"),
                        "cost_proposed": step.get("cost_proposed"),
                        "execution_per_case": step.get("execution_per_case"),
                    },
                    column=case_group_tile.column + 1 + idx,
                    row=case_group_tile.row,
                    deletable=True,
                    link_from_tile=[f"step_{ordered[idx - 1]}"]
                    if idx > 0
                    else [case_group_tile.id],
                )
            )

    if (
        not regulations
        and not processes
        and not case_groups
        and not steps
    ):
        label = DISPLAY_LABELS.get(resolved, resolved)
        tiles.append(
            Tile(
                id="empty_addressee",
                title=f"Kein Aufwand fuer {label}",
                text=(
                    f"Fuer {label} wurden in diesem Regelungsvorhaben keine "
                    "relevanten Vorgaben und keine kostenrelevanten Folgeprozesse "
                    "identifiziert."
                ),
                meta_information={
                    "norm_addressee": resolved,
                    "empty_state": True,
                },
                column=1,
                row=0,
                deletable=False,
                link_from_tile=["law_tile"],
            )
        )

    if processes and all(process.get("cost") is not None for process in processes):
        step_tiles = [tile for tile in tiles if tile.id.startswith("step_")]
        max_step_col = max((tile.column for tile in step_tiles), default=None)
        max_col = max((tile.column for tile in tiles), default=case_group_col)
        total_col = (max_step_col if max_step_col is not None else max_col) + 1

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

        total_cost = sum(float(process.get("cost") or 0.0) for process in processes)
        tiles.append(
            Tile(
                id="total_cost",
                title="Jährliche Kosten",
                text=db.format_currency(total_cost),
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


def persist_session_tiles_snapshot(
    session: dict,
    norm_addressee: str = ADMINISTRATION,
) -> list[Tile]:
    session_id = int(session["session_id"])
    resolved = normalize_norm_addressee(norm_addressee)
    tiles = build_session_tiles_snapshot(session, resolved)
    with db.transaction():
        db.clear_tiles(session_id=session_id, norm_addressee=resolved)
        for tile in tiles:
            db.upsert_tile(tile, session_id=session_id, norm_addressee=resolved)
    return tiles


def sync_all_norm_addressee_tile_snapshots(session: dict) -> None:
    for norm_addressee in ALL_NORM_ADDRESSEES:
        persist_session_tiles_snapshot(session, norm_addressee)
