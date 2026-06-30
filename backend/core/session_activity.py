from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Literal

from backend.core import db


SessionActivityType = Literal["workflow", "ea_edit"]

EA_EDIT_LEASE_SECONDS = 120.0
WORKFLOW_LEASE_SECONDS = 12 * 60 * 60.0


@dataclass(frozen=True)
class SessionActivity:
    session_id: int
    activity_id: str
    activity_type: SessionActivityType
    label: str
    created_at: float
    updated_at: float
    expires_at: float | None


class SessionActivityConflict(Exception):
    def __init__(self, active: SessionActivity):
        self.active = active
        super().__init__(
            f"Active {active.activity_type} for session {active.session_id}: "
            f"{active.activity_id}"
        )


class SessionActivityUnavailable(Exception):
    def __init__(self, *, session_id: int, activity_type: SessionActivityType):
        self.session_id = session_id
        self.activity_type = activity_type
        super().__init__(f"No active {activity_type} for session {session_id}")


def _activity_from_row(row: dict | None) -> SessionActivity | None:
    if row is None:
        return None
    return SessionActivity(
        session_id=int(row["session_id"]),
        activity_id=str(row["activity_id"]),
        activity_type=str(row["activity_type"]),  # type: ignore[arg-type]
        label=str(row["label"]),
        created_at=float(row["created_at"]),
        updated_at=float(row["updated_at"]),
        expires_at=(
            None if row.get("expires_at") is None else float(row["expires_at"])
        ),
    )


def get_session_activity(session_id: int) -> SessionActivity | None:
    return _activity_from_row(db.get_session_activity(session_id))


def begin_session_activity(
    *,
    session_id: int,
    activity_type: SessionActivityType,
    label: str,
    ttl_seconds: float | None,
) -> SessionActivity:
    activity_id = f"{activity_type}:{uuid.uuid4().hex}"
    activity_row, conflict_row = db.begin_session_activity(
        session_id=session_id,
        activity_id=activity_id,
        activity_type=activity_type,
        label=label,
        ttl_seconds=ttl_seconds,
    )
    activity = _activity_from_row(activity_row)
    if activity is not None:
        return activity
    conflict = _activity_from_row(conflict_row)
    if conflict is not None:
        raise SessionActivityConflict(conflict)
    raise SessionActivityUnavailable(session_id=session_id, activity_type=activity_type)


def refresh_session_activity(
    *,
    session_id: int,
    activity_id: str,
    activity_type: SessionActivityType,
    ttl_seconds: float,
) -> SessionActivity:
    active = get_session_activity(session_id)
    if active is None:
        raise SessionActivityUnavailable(
            session_id=session_id,
            activity_type=activity_type,
        )
    if active.activity_id != activity_id or active.activity_type != activity_type:
        raise SessionActivityConflict(active)
    refreshed = _activity_from_row(
        db.refresh_session_activity(
            session_id=session_id,
            activity_id=activity_id,
            ttl_seconds=ttl_seconds,
        )
    )
    if refreshed is None:
        raise SessionActivityUnavailable(
            session_id=session_id,
            activity_type=activity_type,
        )
    return refreshed


def use_existing_session_activity(
    *,
    session_id: int,
    activity_id: str | None,
    activity_type: SessionActivityType,
) -> SessionActivity:
    if not activity_id:
        active = get_session_activity(session_id)
        if active is not None:
            raise SessionActivityConflict(active)
        raise SessionActivityUnavailable(
            session_id=session_id,
            activity_type=activity_type,
        )
    active = get_session_activity(session_id)
    if active is None:
        raise SessionActivityUnavailable(
            session_id=session_id,
            activity_type=activity_type,
        )
    if active.activity_id != activity_id or active.activity_type != activity_type:
        raise SessionActivityConflict(active)
    return active


def clear_session_activity(session_id: int, activity_id: str) -> None:
    db.clear_session_activity(session_id, activity_id)


def release_session_activity(
    *,
    session_id: int,
    activity_id: str,
    activity_type: SessionActivityType,
) -> bool:
    active = get_session_activity(session_id)
    if active is None:
        return False
    if active.activity_id != activity_id or active.activity_type != activity_type:
        return False
    return db.clear_session_activity(session_id, activity_id)


def clear_all_session_activities() -> None:
    db.clear_all_session_activities()


@asynccontextmanager
async def session_activity_scope(
    *,
    session_id: int,
    activity_type: SessionActivityType,
    label: str,
    owner_activity_id: str | None = None,
    ttl_seconds: float | None = None,
) -> AsyncIterator[SessionActivity]:
    if owner_activity_id:
        yield use_existing_session_activity(
            session_id=session_id,
            activity_id=owner_activity_id,
            activity_type=activity_type,
        )
        return
    activity = begin_session_activity(
        session_id=session_id,
        activity_type=activity_type,
        label=label,
        ttl_seconds=ttl_seconds,
    )
    try:
        yield activity
    finally:
        clear_session_activity(session_id, activity.activity_id)
