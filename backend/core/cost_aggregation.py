from __future__ import annotations

from fastapi import HTTPException

from backend.core import db
from backend.core.norm_addressees import (
    ADMINISTRATION,
    BUSINESS,
    CITIZENS,
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
    default_rates: dict[str, float],
    edited_rates: dict[str, float | None],
) -> float:
    if norm_addressee == CITIZENS:
        return 0.0
    # Manual session override beats the per-step model rate (same semantics as
    # _effective_value(base, edited); inlined to avoid importing a private helper).
    edited = edited_rates.get(key)
    if edited is not None:
        return float(edited)
    value = step.get(f"hourly_rate_{key}_{suffix}")
    if value is not None:
        return float(value)
    if norm_addressee in {ADMINISTRATION, BUSINESS}:
        return _safe_number(default_rates.get(key))
    return 0.0


def _compute_step_cost(
    step: dict,
    suffix: str,
    norm_addressee: str,
    default_rates: dict[str, float],
    edited_rates: dict[str, float | None],
) -> float:
    total = 0.0
    for key in ["a", "b", "c", "d"]:
        rate = _resolve_hourly_rate(
            step, suffix, key, norm_addressee, default_rates, edited_rates
        )
        minutes = _safe_number(step.get(f"time_required_in_min_{key}_{suffix}_effective"))
        total += rate * (minutes / 60.0)
    total += _safe_number(step.get(f"expenses_{suffix}_effective"))
    return total


def _resolve_personnel_rate(row: dict, wage_overrides: dict) -> float:
    """Row rate: a session wage override (by source+qualification) wins over the
    model rate stored on the row."""
    key = (row["wage_source_kind"], row["wage_source_value"], row["qualification"])
    override = wage_overrides.get(key)
    if override is not None:
        return float(override)
    return _safe_number(row.get("model_hourly_rate"))


def _compute_step_personnel_cost_from_rows(
    period_rows: list[dict], wage_overrides: dict
) -> float:
    """Personnel cost for one period from the row-based model (excl. expenses)."""
    total = 0.0
    for row in period_rows:
        edited = row.get("time_required_in_min_edited")
        minutes = edited if edited is not None else row.get("time_required_in_min")
        total += _resolve_personnel_rate(row, wage_overrides) * (_safe_number(minutes) / 60.0)
    return total


_ADMIN_LEVEL_BUCKET: dict[str, str] = {
    "bund": "bund",
    "laender": "land",
    "kommunen": "land",
}


def _personnel_cost_by_level(
    period_rows: list[dict], wage_overrides: dict
) -> dict[str, float]:
    by_level: dict[str, float] = {}
    for row in period_rows:
        bucket = _ADMIN_LEVEL_BUCKET.get(row["wage_source_value"])
        if bucket is None:
            continue
        edited = row.get("time_required_in_min_edited")
        minutes = edited if edited is not None else row.get("time_required_in_min")
        cost = _resolve_personnel_rate(row, wage_overrides) * (_safe_number(minutes) / 60.0)
        by_level[bucket] = by_level.get(bucket, 0.0) + cost
    return by_level


def _step_cost_by_level(
    period_rows: list[dict], wage_overrides: dict, expenses: float
) -> dict[str, float]:
    by_level = _personnel_cost_by_level(period_rows, wage_overrides)
    if not expenses or not by_level:
        return by_level
    personnel_total = sum(by_level.values())
    if personnel_total > 0:
        for bucket in by_level:
            by_level[bucket] += expenses * (by_level[bucket] / personnel_total)
    else:
        share = expenses / len(by_level)
        for bucket in by_level:
            by_level[bucket] += share
    return by_level


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


def _load_structure_rows(session_id: int, norm_addressee: str) -> tuple[list[dict], list[dict], list[dict]]:
    processes = db.list_processes_for_session_and_addressee(session_id, norm_addressee)
    case_groups = db.list_case_groups_for_session_and_addressee(session_id, norm_addressee)
    steps = db.list_process_steps_for_session_and_addressee(session_id, norm_addressee)
    return processes, case_groups, steps


def _compute_step_bureaucracy_fractions(
    session_id: int, norm_addressee: str
) -> dict[int, float]:
    """Pro Schritt den Anteil der Informationspflicht-Vorgaben ermitteln.

    Leitfaden-konform: Buerokratiekosten muessen fuer Wirtschaft gesondert
    ausgewiesen werden - auch innerhalb groesserer Prozesse. Wenn ein Schritt
    an mehrere Vorgaben gekoppelt ist, von denen nur ein Teil Informations-
    pflichten sind, darf nicht der gesamte Schrittkosten-Anteil als Buerokratie
    verbucht werden. Stattdessen wird eine proportionale Aufteilung nach Anzahl
    der gekoppelten Informationspflicht-Vorgaben an der Gesamtzahl der
    gekoppelten Vorgaben vorgenommen. Gibt 0.0 zurueck, wenn keine
    Informationspflicht beteiligt ist.
    """
    business_regulation_ids = {
        int(row["regulation_id"])
        for row in db.list_regulations_for_session_and_addressee(session_id, norm_addressee)
        if bool(row.get("is_business_information_obligation"))
    }
    if not business_regulation_ids:
        return {}
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
    fractions: dict[int, float] = {}
    for step in step_rows:
        step_id = int(step["step_id"])
        case_group_id = int(step["case_group_id"])
        regulation_ids = regulation_ids_by_step.get(step_id)
        if not regulation_ids:
            process_id = process_id_by_case_group.get(case_group_id)
            regulation_ids = sorted(process_regulation_ids.get(process_id, set()))
        if not regulation_ids:
            continue
        total = len(regulation_ids)
        info_count = sum(
            1 for rid in regulation_ids if rid in business_regulation_ids
        )
        if info_count == 0:
            continue
        fractions[step_id] = info_count / total
    return fractions


def should_skip_addressee_costs(session_id: int, norm_addressee: str) -> bool:
    session_has_any_regulations = bool(db.list_regulations_for_session(session_id))
    return (
        session_has_any_regulations
        and not db.has_applicable_regulations_for_addressee(session_id, norm_addressee)
    ) or db.has_no_process_path_for_addressee(session_id, norm_addressee)


def _ensure_structure_or_skip(
    *,
    session_id: int,
    norm_addressee: str,
    processes: list[dict],
    case_groups: list[dict],
    steps: list[dict],
) -> bool:
    """Return ``True`` when cost computation should be skipped for this addressee.

    Skipping applies when the session has regulations but none are applicable to
    this norm addressee (so there is simply nothing to cost). Genuinely missing
    structure (no processes/case groups/steps despite applicable regulations)
    raises a 400 instead. The router turns a ``True`` here into the skipped cost
    response shape, keeping HTTP shaping out of the pure aggregation.
    """
    addressee_is_skippable = should_skip_addressee_costs(session_id, norm_addressee)
    if not processes:
        if addressee_is_skippable:
            return True
        raise HTTPException(
            status_code=400,
            detail=(
                "No processes for session"
                if norm_addressee == ADMINISTRATION
                else "No processes for selected norm addressee"
            ),
        )
    if not case_groups:
        if addressee_is_skippable:
            return True
        raise HTTPException(
            status_code=400,
            detail=(
                "No case groups for session"
                if norm_addressee == ADMINISTRATION
                else "No case groups for selected norm addressee"
            ),
        )
    if not steps:
        if addressee_is_skippable:
            return True
        raise HTTPException(
            status_code=400,
            detail=(
                "No process steps for session"
                if norm_addressee == ADMINISTRATION
                else "No process steps for selected norm addressee"
            ),
        )
    return False


def _compute_step_metrics(
    *,
    steps: list[dict],
    case_groups: list[dict],
    norm_addressee: str,
    default_rates: dict[str, float],
    edited_rates: dict[str, float | None],
    personnel_rows_by_step: dict[int, list[dict]],
    wage_overrides: dict,
    business_information_fractions: dict[int, float],
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
        level_current: dict[str, float] | None = None
        level_proposed: dict[str, float] | None = None
        if norm_addressee == CITIZENS:
            cost_current = _safe_number(step.get("expenses_current_effective"))
            cost_proposed = _safe_number(step.get("expenses_proposed_effective"))
        else:
            step_rows = personnel_rows_by_step.get(step_id, [])
            if step_rows:
                # Row-based model: authoritative once the step has child rows.
                current_rows = [r for r in step_rows if r["period"] == "current"]
                proposed_rows = [r for r in step_rows if r["period"] == "proposed"]
                cost_current = _compute_step_personnel_cost_from_rows(
                    current_rows, wage_overrides
                ) + _safe_number(step.get("expenses_current_effective"))
                cost_proposed = _compute_step_personnel_cost_from_rows(
                    proposed_rows, wage_overrides
                ) + _safe_number(step.get("expenses_proposed_effective"))
                if norm_addressee == ADMINISTRATION:
                    level_current = _step_cost_by_level(
                        current_rows, wage_overrides,
                        _safe_number(step.get("expenses_current_effective")),
                    )
                    level_proposed = _step_cost_by_level(
                        proposed_rows, wage_overrides,
                        _safe_number(step.get("expenses_proposed_effective")),
                    )
            else:
                # Legacy fallback (old sessions without child rows / migration).
                cost_current = _compute_step_cost(
                    step, "current", norm_addressee, default_rates, edited_rates
                )
                cost_proposed = _compute_step_cost(
                    step, "proposed", norm_addressee, default_rates, edited_rates
                )
        time_current = _compute_step_time_minutes(step, "current")
        time_proposed = _compute_step_time_minutes(step, "proposed")
        bureaucracy_fraction = (
            business_information_fractions.get(step_id, 0.0)
            if norm_addressee == BUSINESS
            else 0.0
        )
        step_costs_current[step_id] = cost_current
        step_costs_proposed[step_id] = cost_proposed
        step_time_current[step_id] = time_current
        step_time_proposed[step_id] = time_proposed
        step_bureaucracy_current[step_id] = cost_current * bureaucracy_fraction
        step_bureaucracy_proposed[step_id] = cost_proposed * bureaucracy_fraction
        per_case_flags[step_id] = bool(step.get("execution_per_case")) if step.get("execution_per_case") is not None else True
        step["cost_current"] = cost_current
        step["cost_proposed"] = cost_proposed
        step["level_cost_current"] = level_current
        step["level_cost_proposed"] = level_proposed

    return (
        step_costs_current,
        step_costs_proposed,
        step_time_current,
        step_time_proposed,
        step_bureaucracy_current,
        step_bureaucracy_proposed,
        per_case_flags,
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
        level_current_totals: dict[str, float] = {}
        level_proposed_totals: dict[str, float] = {}
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
            step_level_current = step_effective.get("level_cost_current")
            if step_level_current:
                for bucket, value in step_level_current.items():
                    level_current_totals[bucket] = (
                        level_current_totals.get(bucket, 0.0)
                        + value * step_multiplier_current
                    )
            step_level_proposed = step_effective.get("level_cost_proposed")
            if step_level_proposed:
                for bucket, value in step_level_proposed.items():
                    level_proposed_totals[bucket] = (
                        level_proposed_totals.get(bucket, 0.0)
                        + value * step_multiplier_proposed
                    )
        cost_delta = cost_proposed - cost_current
        level_buckets = set(level_current_totals) | set(level_proposed_totals)
        group["level_cost_delta"] = {
            bucket: level_proposed_totals.get(bucket, 0.0)
            - level_current_totals.get(bucket, 0.0)
            for bucket in level_buckets
        }
        group["cases_current"] = cases_current
        group["cases_proposed"] = cases_proposed
        group["cost"] = cost_delta
        case_groups[idx]["cost"] = cost_delta
        case_group_costs[case_group_id] = cost_delta
        case_group_bureaucracy_costs[case_group_id] = bureaucracy_proposed - bureaucracy_current
        case_group_time_deltas[case_group_id] = time_total_proposed - time_total_current
        case_group_expense_deltas[case_group_id] = expenses_total_proposed - expenses_total_current
    return (
        case_group_costs,
        case_group_bureaucracy_costs,
        case_group_time_deltas,
        case_group_expense_deltas,
    )


def _aggregate_process_costs(
    *,
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
    return (
        process_costs,
        process_bureaucracy_costs,
        process_time_deltas,
        process_expense_deltas,
    )


def _without_edits(row: dict) -> dict:
    """Return a copy of ``row`` with every ``*_edited`` overlay nulled.

    Used to derive the model-only (pre user-edit) view of steps, case groups and
    personnel rows for the compliance export's "reject user edits" policy.
    """
    return {
        key: (None if isinstance(key, str) and key.endswith("_edited") else value)
        for key, value in row.items()
    }


def aggregate_addressee_costs(
    session_id: int,
    norm_addressee: str,
    *,
    apply_user_edits: bool = True,
) -> dict:
    """Read-only cost aggregation for one norm addressee (no persistence).

    With ``apply_user_edits=True`` (default) this is the exact computation the
    live recompute uses; ``compute_total_cost_for_session`` wraps it and persists.
    With ``apply_user_edits=False`` all user edits are stripped first (row wage
    overrides ignored, ``*_edited`` overlays nulled), so the result is the pure
    model cost the compliance export needs for ``reject_if_user_edits``. Returning
    both the totals and the per-step cost maps keeps the export and the app on one
    cost source, so they can never drift. On skip the result is ``{"skipped": True}``
    and the caller builds the skipped response shape.
    """
    processes, case_groups, steps = _load_structure_rows(session_id, norm_addressee)
    pay_rates = db.get_session_pay_rates_for_addressee(session_id, norm_addressee)
    if not pay_rates:
        raise HTTPException(status_code=404, detail="Session pay rates not found")
    default_rates = pay_rates["defaults"]
    edited_rates = pay_rates["edited"] if apply_user_edits else {}
    personnel_rows_by_step: dict[int, list[dict]] = {}
    for row in db.list_process_step_personnel_effort(session_id, norm_addressee):
        if not apply_user_edits:
            row = _without_edits(row)
        personnel_rows_by_step.setdefault(int(row["step_id"]), []).append(row)
    wage_overrides = (
        db.get_session_wage_rate_overrides(session_id, norm_addressee)
        if apply_user_edits
        else {}
    )
    metric_case_groups = (
        case_groups if apply_user_edits else [_without_edits(g) for g in case_groups]
    )
    metric_steps = steps if apply_user_edits else [_without_edits(s) for s in steps]
    effective_case_groups = [
        db.resolve_effective_case_group_metrics(group) for group in metric_case_groups
    ]
    effective_steps = [
        db.resolve_effective_process_step_metrics(step) for step in metric_steps
    ]
    if _ensure_structure_or_skip(
        session_id=session_id,
        norm_addressee=norm_addressee,
        processes=processes,
        case_groups=case_groups,
        steps=steps,
    ):
        return {"skipped": True}

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

    business_information_fractions = (
        _compute_step_bureaucracy_fractions(session_id, norm_addressee)
        if norm_addressee == BUSINESS
        else {}
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
        default_rates=default_rates,
        edited_rates=edited_rates,
        personnel_rows_by_step=personnel_rows_by_step,
        wage_overrides=wage_overrides,
        business_information_fractions=business_information_fractions,
    )
    steps_by_group = _build_steps_by_group(effective_steps)
    effective_steps_by_id = {int(step["step_id"]): step for step in effective_steps}
    (
        case_group_costs,
        case_group_bureaucracy_costs,
        case_group_time_deltas,
        case_group_expense_deltas,
    ) = _aggregate_case_group_costs(
        effective_case_groups=effective_case_groups,
        case_groups=metric_case_groups,
        effective_steps_by_id=effective_steps_by_id,
        steps_by_group=steps_by_group,
        step_costs_current=step_costs_current,
        step_costs_proposed=step_costs_proposed,
        step_time_current=step_time_current,
        step_time_proposed=step_time_proposed,
        step_bureaucracy_current=step_bureaucracy_current,
        step_bureaucracy_proposed=step_bureaucracy_proposed,
        per_case_flags=per_case_flags,
    )
    (
        process_costs,
        process_bureaucracy_costs,
        process_time_deltas,
        process_expense_deltas,
    ) = _aggregate_process_costs(
        processes=processes,
        case_groups=metric_case_groups,
        case_group_costs=case_group_costs,
        case_group_bureaucracy_costs=case_group_bureaucracy_costs,
        case_group_time_deltas=case_group_time_deltas,
        case_group_expense_deltas=case_group_expense_deltas,
    )

    total_cost = sum(process_costs.values())
    bureaucracy_cost = (
        sum(process_bureaucracy_costs.values()) if norm_addressee == BUSINESS else None
    )
    verwaltung_bundesebene: float | None = None
    verwaltung_landesebene: float | None = None
    if norm_addressee == ADMINISTRATION and any(
        step.get("level_cost_current") is not None for step in effective_steps
    ):
        level_totals: dict[str, float] = {}
        for group in effective_case_groups:
            for bucket, value in (group.get("level_cost_delta") or {}).items():
                level_totals[bucket] = level_totals.get(bucket, 0.0) + value
        verwaltung_bundesebene = level_totals.get("bund", 0.0)
        verwaltung_landesebene = level_totals.get("land", 0.0)
    total_time_minutes = (
        sum(process_time_deltas.values()) if norm_addressee == CITIZENS else None
    )
    total_expenses = (
        sum(process_expense_deltas.values()) if norm_addressee == CITIZENS else None
    )
    if norm_addressee == CITIZENS:
        total_cost = None
    return {
        "skipped": None,
        "processes": processes,
        "case_groups": case_groups,
        "steps": steps,
        "step_costs_current": step_costs_current,
        "step_costs_proposed": step_costs_proposed,
        "step_bureaucracy_current": step_bureaucracy_current,
        "step_bureaucracy_proposed": step_bureaucracy_proposed,
        "case_group_costs": case_group_costs,
        "process_costs": process_costs,
        "total_cost": total_cost,
        "bureaucracy_cost": bureaucracy_cost,
        "verwaltung_bundesebene": verwaltung_bundesebene,
        "verwaltung_landesebene": verwaltung_landesebene,
        "total_time_minutes": total_time_minutes,
        "total_expenses": total_expenses,
    }
