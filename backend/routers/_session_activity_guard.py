from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import HTTPException

from backend.core.session_activity import (
    SessionActivity,
    SessionActivityConflict,
    SessionActivityType,
    SessionActivityUnavailable,
    use_existing_session_activity,
    session_activity_scope,
)


def raise_session_activity_conflict(exc: SessionActivityConflict) -> None:
    active = exc.active
    if active.activity_type == "workflow":
        message = (
            "Diese Aktion ist während einer laufenden Ausführung in derselben "
            "Session nicht möglich. Bitte den Lauf zuerst abbrechen oder "
            "abschließen."
        )
    else:
        message = (
            "Diese Aktion ist während einer laufenden EA-Bearbeitung in "
            "derselben Session nicht möglich. Bitte die Bearbeitung zuerst "
            "abschließen."
        )
    raise HTTPException(
        status_code=409,
        detail={
            "error": "session_activity_conflict",
            "active_type": active.activity_type,
            "message": message,
        },
    ) from exc


def raise_session_activity_unavailable(exc: SessionActivityUnavailable) -> None:
    if exc.activity_type == "ea_edit":
        message = (
            "EA-Bearbeitung ist nicht mehr aktiv. Bitte den Editor schließen "
            "und erneut öffnen."
        )
    else:
        message = "Die Ausführung ist nicht mehr aktiv. Bitte den Lauf erneut starten."
    raise HTTPException(
        status_code=409,
        detail={
            "error": "session_activity_unavailable",
            "activity_type": exc.activity_type,
            "message": message,
        },
    ) from exc


@asynccontextmanager
async def guarded_session_activity(
    *,
    session_id: int,
    activity_type: SessionActivityType,
    label: str,
    owner_activity_id: str | None = None,
    ttl_seconds: float | None = None,
) -> AsyncIterator[SessionActivity]:
    try:
        if activity_type == "ea_edit":
            yield use_existing_session_activity(
                session_id=session_id,
                activity_id=owner_activity_id,
                activity_type=activity_type,
            )
            return
        async with session_activity_scope(
            session_id=session_id,
            activity_type=activity_type,
            label=label,
            owner_activity_id=owner_activity_id,
            ttl_seconds=ttl_seconds,
        ) as activity:
            yield activity
    except SessionActivityConflict as exc:
        raise_session_activity_conflict(exc)
    except SessionActivityUnavailable as exc:
        raise_session_activity_unavailable(exc)
