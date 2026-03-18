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
