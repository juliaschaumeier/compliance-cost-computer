from __future__ import annotations


def build_case_groups_payload(
    processes: list[dict],
    case_groups: list[dict],
    include_metrics: bool,
) -> list[dict]:
    groups_by_process: dict[int, list[dict]] = {}
    for group in case_groups:
        process_id = int(group["process_id"])
        group_payload = {
            "fallgruppen_id": group["case_group_id"],
            "fallgruppe_bezeichnung": group["case_group"],
            "fallgruppe_beschreibung": group["description"],
            "aenderungsstatus": group.get("change_status"),
        }
        if include_metrics:
            group_payload |= {
                "anzahl_betroffene_gueltig": group.get("addressees_current"),
                "haeufigkeit_pro_jahr_gueltig": group.get("annual_frequency_current"),
                "anzahl_betroffene_vorschlag": group.get("addressees_proposed"),
                "haeufigkeit_pro_jahr_vorschlag": group.get("annual_frequency_proposed"),
            }
        groups_by_process.setdefault(process_id, []).append(group_payload)

    payload: list[dict] = []
    for process in processes:
        process_id = int(process["process_id"])
        payload.append(
            {
                "prozess_id": process_id,
                "prozess_bezeichnung": process["process"],
                "prozess_beschreibung": process["description"],
                "aenderungsstatus": process.get("change_status"),
                "fallgruppen": groups_by_process.get(process_id, []),
            }
        )
    return payload


def build_processes_payload_with_regulations(
    processes: list[dict],
    regulations: list[dict],
) -> list[dict]:
    regs_by_process: dict[int, list[dict]] = {}
    for regulation in regulations:
        process_id = regulation.get("process_id")
        if process_id is None:
            continue
        regs_by_process.setdefault(int(process_id), []).append(regulation)

    payload: list[dict] = []
    for process in processes:
        process_id = int(process["process_id"])
        payload.append(
            {
                "prozess_id": process_id,
                "prozess_bezeichnung": process["process"],
                "prozess_beschreibung": process["description"],
                "aenderungsstatus": process["change_status"],
                "vorgaben": [
                    {
                        "vorgaben_id": row["regulation_id"],
                        "normzitat": row["legal_citation"],
                        "beschreibung": row["description"],
                        "aenderungsstatus": row["change_status"],
                    }
                    for row in regs_by_process.get(process_id, [])
                ],
            }
        )
    return payload


def _order_steps(steps: list[dict]) -> list[dict]:
    step_map = {int(step["step_id"]): step for step in steps}
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
    return [step_map[step_id] for step_id in ordered]


def build_step_analysis_payload(
    processes: list[dict],
    case_groups: list[dict],
    steps: list[dict],
) -> list[dict]:
    groups_by_process: dict[int, list[dict]] = {}
    for group in case_groups:
        process_id = int(group["process_id"])
        groups_by_process.setdefault(process_id, []).append(group)

    steps_by_group: dict[int, list[dict]] = {}
    for step in steps:
        steps_by_group.setdefault(int(step["case_group_id"]), []).append(step)

    payload: list[dict] = []
    for process in processes:
        process_id = int(process["process_id"])
        fallgruppen_payload: list[dict] = []
        for group in groups_by_process.get(process_id, []):
            case_group_id = int(group["case_group_id"])
            ordered_steps = _order_steps(steps_by_group.get(case_group_id, []))
            taetigkeiten = [
                {
                    "taetigkeiten_id": step["step_id"],
                    "taetigkeit": step["step"],
                    "beschreibung": step["description"],
                    "aenderungsstatus": step.get("change_status"),
                    "stundenlohn_satz_a_gueltig": step.get("hourly_rate_a_current"),
                    "stundenlohn_satz_b_gueltig": step.get("hourly_rate_b_current"),
                    "stundenlohn_satz_c_gueltig": step.get("hourly_rate_c_current"),
                    "stundenlohn_satz_d_gueltig": step.get("hourly_rate_d_current"),
                    "zeitaufwand_in_min_a_gueltig": step.get("time_required_in_min_a_current"),
                    "zeitaufwand_in_min_b_gueltig": step.get("time_required_in_min_b_current"),
                    "zeitaufwand_in_min_c_gueltig": step.get("time_required_in_min_c_current"),
                    "zeitaufwand_in_min_d_gueltig": step.get("time_required_in_min_d_current"),
                    "sachaufwand_gueltig": step.get("expenses_current"),
                    "stundenlohn_satz_a_vorschlag": step.get("hourly_rate_a_proposed"),
                    "stundenlohn_satz_b_vorschlag": step.get("hourly_rate_b_proposed"),
                    "stundenlohn_satz_c_vorschlag": step.get("hourly_rate_c_proposed"),
                    "stundenlohn_satz_d_vorschlag": step.get("hourly_rate_d_proposed"),
                    "zeitaufwand_in_min_a_vorschlag": step.get("time_required_in_min_a_proposed"),
                    "zeitaufwand_in_min_b_vorschlag": step.get("time_required_in_min_b_proposed"),
                    "zeitaufwand_in_min_c_vorschlag": step.get("time_required_in_min_c_proposed"),
                    "zeitaufwand_in_min_d_vorschlag": step.get("time_required_in_min_d_proposed"),
                    "sachaufwand_vorschlag": step.get("expenses_proposed"),
                    "ausfuehrung_pro_einzelfall": step.get("execution_per_case"),
                }
                for step in ordered_steps
            ]
            fallgruppen_payload.append(
                {
                    "fallgruppen_id": case_group_id,
                    "fallgruppe_bezeichnung": group["case_group"],
                    "fallgruppe_beschreibung": group["description"],
                    "aenderungsstatus": group.get("change_status"),
                    "taetigkeiten": taetigkeiten,
                }
            )
        payload.append(
            {
                "prozess_id": process_id,
                "prozess_bezeichnung": process["process"],
                "prozess_beschreibung": process["description"],
                "aenderungsstatus": process.get("change_status"),
                "fallgruppen": fallgruppen_payload,
            }
        )
    return payload
