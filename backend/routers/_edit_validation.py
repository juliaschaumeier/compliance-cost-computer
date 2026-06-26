from __future__ import annotations

from fastapi import HTTPException
from pydantic import BaseModel

from backend.core import db


def validate_non_negative_fields(
    row: BaseModel,
    *,
    field_names: tuple[str, ...],
    id_field: str,
    entity_label: str,
) -> None:
    row_id = getattr(row, id_field)
    for field_name in field_names:
        value = getattr(row, field_name)
        if value is None:
            continue
        if value < 0:
            raise HTTPException(
                status_code=422,
                detail=f"{field_name} must be non-negative for {entity_label} {row_id}",
            )


def validate_unique_ids(
    rows: list[BaseModel],
    *,
    id_field: str,
    entity_label: str,
) -> None:
    seen: set[int] = set()
    duplicates: set[int] = set()
    for row in rows:
        row_id = int(getattr(row, id_field))
        if row_id in seen:
            duplicates.add(row_id)
        seen.add(row_id)
    if duplicates:
        dupes = ", ".join(str(value) for value in sorted(duplicates))
        raise HTTPException(
            status_code=422,
            detail=f"Duplicate {entity_label} values in payload: {dupes}",
        )


def validate_non_empty_rows(rows: list[BaseModel]) -> None:
    if rows:
        return
    raise HTTPException(
        status_code=422,
        detail="rows must not be empty",
    )


def validate_non_noop_update_count(updated: int) -> None:
    if updated > 0:
        return
    raise HTTPException(
        status_code=422,
        detail="No changes in payload",
    )


def validate_wage_source_kind(wage_source_kind: str, norm_addressee: str) -> None:
    """Reject a wage_source_kind that does not match the addressee's canonical kind.

    Single source of truth for the row-identity invariant shared by the row effort
    edit API and the wage override API (administration -> verwaltungsebene, business
    -> wirtschaftsabschnitt; citizens have no editable wage source).
    """
    expected = db.WAGE_SOURCE_KIND_BY_ADDRESSEE.get(norm_addressee)
    if wage_source_kind != expected:
        raise HTTPException(
            status_code=422,
            detail=f"wage_source_kind {wage_source_kind!r} does not match {norm_addressee!r}",
        )
