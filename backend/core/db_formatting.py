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


def build_case_group_tile_text(
    description: str,
    addressees_current: float | None = None,
    annual_frequency_current: float | None = None,
    addressees_proposed: float | None = None,
    annual_frequency_proposed: float | None = None,
    cases_current: float | None = None,
    cases_proposed: float | None = None,
) -> str:
    lines = []
    base = (description or "").strip()
    if base:
        lines.append(base)

    if (
        addressees_current is not None
        or annual_frequency_current is not None
        or cases_current is not None
    ):
        lines.append("Gültig:")
        if addressees_current is not None:
            lines.append(f"Betroffene: {format_number(addressees_current)}")
        if annual_frequency_current is not None:
            lines.append(f"Häufigkeit/Jahr: {format_number(annual_frequency_current)}")
        if cases_current is not None:
            lines.append(f"Fälle/Jahr: {format_number(cases_current)}")

    if (
        addressees_proposed is not None
        or annual_frequency_proposed is not None
        or cases_proposed is not None
    ):
        lines.append("Vorschlag:")
        if addressees_proposed is not None:
            lines.append(f"Betroffene: {format_number(addressees_proposed)}")
        if annual_frequency_proposed is not None:
            lines.append(f"Häufigkeit/Jahr: {format_number(annual_frequency_proposed)}")
        if cases_proposed is not None:
            lines.append(f"Fälle/Jahr: {format_number(cases_proposed)}")
    return "\n".join(lines).strip()


def build_process_step_tile_text(
    description: str,
    hourly_rates_current: dict[str, float | None] | None = None,
    time_required_current: dict[str, float | None] | None = None,
    expenses_current: float | None = None,
    cost_current: float | None = None,
    hourly_rates_proposed: dict[str, float | None] | None = None,
    time_required_proposed: dict[str, float | None] | None = None,
    expenses_proposed: float | None = None,
    cost_proposed: float | None = None,
) -> str:
    hourly_rates_current = hourly_rates_current or {}
    time_required_current = time_required_current or {}
    hourly_rates_proposed = hourly_rates_proposed or {}
    time_required_proposed = time_required_proposed or {}

    lines = []
    base = (description or "").strip()
    if base:
        lines.append(base)

    def append_effort_section(
        label: str,
        hourly_rates_value: dict[str, float | None],
        time_required_value: dict[str, float | None],
        expenses_value: float | None,
        cost_value: float | None,
    ) -> None:
        has_effort = any(hourly_rates_value.get(key) is not None for key in ["a", "b", "c", "d"]) or any(
            time_required_value.get(key) is not None for key in ["a", "b", "c", "d"]
        )
        if not has_effort and expenses_value is None and cost_value is None:
            return
        lines.append(f"{label}:")
        for key in ["a", "b", "c", "d"]:
            rate = hourly_rates_value.get(key)
            if rate is not None:
                lines.append(f"Lohnsatz {key.upper()}: {format_number(rate)}")
        for key in ["a", "b", "c", "d"]:
            duration = time_required_value.get(key)
            if duration is not None:
                lines.append(f"Zeitaufwand {key.upper()}: {format_number(duration)}")
        if expenses_value is not None:
            try:
                expense_num = float(expenses_value)
            except (TypeError, ValueError):
                expense_num = None
            if expense_num is not None and abs(expense_num) > 0:
                lines.append(f"Sachaufwand: {format_number(expense_num)}")

    append_effort_section(
        "Gültig",
        hourly_rates_current,
        time_required_current,
        expenses_current,
        cost_current,
    )
    append_effort_section(
        "Vorschlag",
        hourly_rates_proposed,
        time_required_proposed,
        expenses_proposed,
        cost_proposed,
    )

    return "\n".join(lines).strip()


def build_process_tile_text(description: str, cost: float | None) -> str:
    lines = []
    base = (description or "").strip()
    if base:
        lines.append(base)
    return "\n".join(lines).strip()
