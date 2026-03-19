from __future__ import annotations


def format_number(value: float | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, (int, float)):
        num = float(value)
        if num.is_integer():
            return str(int(num))
        formatted = f"{num:.4f}".rstrip("0").rstrip(".")
        return formatted
    return str(value)


def format_currency(value: float | int | None) -> str:
    if value is None:
        return ""
    amount = float(value)
    sign = "-" if amount < 0 else ""
    amount = abs(amount)

    def _format_compact(num: float) -> str:
        if num >= 100:
            decimals = 0
        elif num >= 10:
            decimals = 1
        else:
            decimals = 2
        formatted = f"{num:,.{decimals}f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")

    if amount >= 1_000_000_000:
        return f"{sign}{_format_compact(amount / 1_000_000_000)} Mrd. €"
    if amount >= 1_000_000:
        return f"{sign}{_format_compact(amount / 1_000_000)} Mio. €"
    if amount >= 1_000:
        return f"{sign}{_format_compact(amount / 1_000)} Tsd. €"

    if amount.is_integer():
        formatted = f"{amount:,.0f}".replace(",", ".")
    else:
        formatted = f"{amount:,.2f}".replace(",", ".")
    return f"{sign}{formatted} €"


def build_process_tile_text(description: str, cost: float | None) -> str:
    lines = []
    base = (description or "").strip()
    if base:
        lines.append(base)
    return "\n".join(lines).strip()


def build_case_group_tile_text(
    description: str,
    addressees_current: float | int | None,
    annual_frequency_current: float | int | None,
    addressees_proposed: float | int | None,
    annual_frequency_proposed: float | int | None,
    cases_current: float | int | None,
    cases_proposed: float | int | None,
) -> str:
    lines = []
    base = (description or "").strip()
    if base:
        lines.append(base)

    def _format_case_line(
        label: str,
        addressees: float | int | None,
        annual_frequency: float | int | None,
        cases: float | int | None,
    ) -> str | None:
        if addressees is None and annual_frequency is None and cases is None:
            return None
        parts = []
        if addressees is not None:
            parts.append(f"Betroffene: {format_number(addressees)}")
        if annual_frequency is not None:
            parts.append(f"Haeufigkeit/Jahr: {format_number(annual_frequency)}")
        if cases is not None:
            parts.append(f"Faelle: {format_number(cases)}")
        return f"{label}: " + " | ".join(parts)

    current_line = _format_case_line(
        "Gueltig",
        addressees_current,
        annual_frequency_current,
        cases_current,
    )
    proposed_line = _format_case_line(
        "Vorschlag",
        addressees_proposed,
        annual_frequency_proposed,
        cases_proposed,
    )
    if current_line:
        lines.append(current_line)
    if proposed_line:
        lines.append(proposed_line)
    return "\n".join(lines).strip()


def build_process_step_tile_text(
    description: str,
    hourly_rates_current: dict[str, float | int | None] | None,
    time_required_current: dict[str, float | int | None] | None,
    expenses_current: float | int | None,
    cost_current: float | int | None,
    hourly_rates_proposed: dict[str, float | int | None] | None,
    time_required_proposed: dict[str, float | int | None] | None,
    expenses_proposed: float | int | None,
    cost_proposed: float | int | None,
    execution_per_case: bool | int | None,
    group_labels: dict[str, str] | None = None,
) -> str:
    lines = []
    base = (description or "").strip()
    if base:
        lines.append(base)

    def _format_effort_values(
        label: str,
        hourly_rates: dict[str, float | int | None] | None,
        time_required: dict[str, float | int | None] | None,
        expenses: float | int | None,
        cost: float | int | None,
    ) -> str | None:
        parts = []
        for key in ("a", "b", "c", "d"):
            minutes = (time_required or {}).get(key)
            rate = (hourly_rates or {}).get(key)
            if minutes is None and rate is None:
                continue
            effort_label = (group_labels or {}).get(key, key.upper())
            detail = []
            if minutes is not None:
                detail.append(f"{format_number(minutes)} Min.")
            if rate is not None:
                detail.append(f"{format_currency(rate)}/Std.")
            parts.append(f"{effort_label}: " + ", ".join(detail))
        if expenses is not None:
            parts.append(f"Sachaufwand: {format_currency(expenses)}")
        if cost is not None:
            parts.append(f"Kosten: {format_currency(cost)}")
        if not parts:
            return None
        return f"{label}: " + " | ".join(parts)

    current_line = _format_effort_values(
        "Gueltig",
        hourly_rates_current,
        time_required_current,
        expenses_current,
        cost_current,
    )
    proposed_line = _format_effort_values(
        "Vorschlag",
        hourly_rates_proposed,
        time_required_proposed,
        expenses_proposed,
        cost_proposed,
    )
    if current_line:
        lines.append(current_line)
    if proposed_line:
        lines.append(proposed_line)
    if execution_per_case is not None:
        lines.append(
            "Ausfuehrung pro Einzelfall: "
            + ("ja" if bool(execution_per_case) else "nein")
        )
    return "\n".join(lines).strip()
