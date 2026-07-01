from backend.core import db
from backend.core.session_activity import EA_EDIT_LEASE_SECONDS, begin_session_activity


def ea_activity_id_for_session(session_id: int) -> str:
    active = db.get_session_activity(session_id)
    if active is not None:
        return active["activity_id"]
    return begin_session_activity(
        session_id=session_id,
        activity_type="ea_edit",
        label="EA bearbeiten",
        ttl_seconds=EA_EDIT_LEASE_SECONDS,
    ).activity_id


def ea_payload_for_session(session_id: int, payload: dict) -> dict:
    return {**payload, "ea_activity_id": ea_activity_id_for_session(session_id)}
