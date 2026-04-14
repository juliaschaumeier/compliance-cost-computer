from __future__ import annotations

from fastapi import HTTPException

from backend.core.norm_addressees import normalize_norm_addressee


def normalize_norm_addressee_or_422(value: str | None) -> str:
    try:
        return normalize_norm_addressee(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
