from __future__ import annotations

import json
import sqlite3


def value_changed(old_value: object, new_value: object) -> bool:
    if old_value is None and new_value is None:
        return False
    if old_value is None or new_value is None:
        return True
    if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
        return abs(float(old_value) - float(new_value)) > 1e-9
    return old_value != new_value


def _audit_value_to_text(value: object) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def insert_edit_audit_row(
    cur: sqlite3.Cursor,
    *,
    session_id: int,
    entity_type: str,
    entity_id: int | None,
    field_name: str,
    old_value: object,
    new_value: object,
) -> None:
    if not value_changed(old_value, new_value):
        return
    cur.execute(
        """
        INSERT INTO edit_audit_log (
            session_id,
            entity_type,
            entity_id,
            field_name,
            old_value,
            new_value
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            entity_type,
            entity_id,
            field_name,
            _audit_value_to_text(old_value),
            _audit_value_to_text(new_value),
        ),
    )
