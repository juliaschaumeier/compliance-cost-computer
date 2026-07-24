from __future__ import annotations

import json
import logging
import secrets
import sqlite3
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
import re
from typing import Iterable, List

from .config import settings
from . import db_edit_metrics
from .edit_audit import insert_edit_audit_row, value_changed
from .db_formatting import (
    build_process_tile_text,
    format_currency,
    format_number,
)
from .models import Tile
from .norm_addressees import (
    ADMINISTRATION,
    ALL_NORM_ADDRESSEES,
    BUSINESS,
    CITIZENS,
    SUPPORTED_NORM_ADDRESSEES,
    normalize_norm_addressee,
)

logger = logging.getLogger(__name__)

_TX_CONN: ContextVar[sqlite3.Connection | None] = ContextVar("tx_conn", default=None)

CROCKFORD_BASE32_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
APP_SESSION_ID_LENGTH = 6


LLM_ANSWER_STATE_PENDING = "pending"
LLM_ANSWER_STATE_ACTIVE = "active"
LLM_ANSWER_STATE_INVALID = "invalid"

PAY_RATE_LEVEL_BUND = "bund"
PAY_RATE_KEYS = ("a", "b", "c", "d")
PAY_RATE_BUND_DEFAULTS: dict[str, float] = {
    "a": 33.8,
    "b": 40.4,
    "c": 67.6,
    "d": 44.4,
}
# Hourly wage rates per administration level (handbook_tables.py, Anhang 8).
# Keys are administration_level values; columns eD/mD,gD,hD,avg map to a,b,c,d.
PAY_RATE_LEVEL_DEFAULTS: dict[str, dict[str, float]] = {
    "bund": PAY_RATE_BUND_DEFAULTS,
    "laender": {"a": 30.5, "b": 43.2, "c": 69.3, "d": 46.7},
    "kommunen": {"a": 25.5, "b": 42.2, "c": 70.4, "d": 40.7},
    "sozialversicherung": {"a": 30.3, "b": 46.3, "c": 73.2, "d": 48.1},
    "durchschnitt": {"a": 27.3, "b": 42.9, "c": 69.3, "d": 44.4},
}
PAY_RATE_BUSINESS_DEFAULTS: dict[str, float] = {
    "a": 26.1,
    "b": 37.1,
    "c": 62.4,
    "d": 38.6,
}
# Hourly wage rates per economic section (handbook_tables.py).
# Keys are WZ sections (A..S without O) plus "gesamtwirtschaft".
PAY_RATE_BUSINESS_SECTION_DEFAULTS: dict[str, dict[str, float]] = {
    "A": {"a": 22.7, "b": 25.6, "c": 45.8, "d": 25.0},
    "B": {"a": 32.6, "b": 41.8, "c": 85.6, "d": 45.0},
    "C": {"a": 31.6, "b": 44.2, "c": 76.2, "d": 46.2},
    "D": {"a": 33.6, "b": 54.9, "c": 80.7, "d": 57.8},
    "E": {"a": 28.5, "b": 37.0, "c": 64.7, "d": 37.4},
    "F": {"a": 26.1, "b": 33.7, "c": 59.5, "d": 33.7},
    "G": {"a": 23.6, "b": 32.4, "c": 62.4, "d": 33.4},
    "H": {"a": 25.9, "b": 32.2, "c": 62.8, "d": 32.1},
    "I": {"a": 21.7, "b": 24.4, "c": 39.7, "d": 23.6},
    "J": {"a": 25.1, "b": 49.9, "c": 63.7, "d": 52.8},
    "K": {"a": 29.0, "b": 54.4, "c": 93.1, "d": 57.9},
    "L": {"a": 24.1, "b": 34.7, "c": 56.2, "d": 35.0},
    "M": {"a": 25.5, "b": 40.9, "c": 64.2, "d": 46.7},
    "N": {"a": 23.3, "b": 30.2, "c": 55.0, "d": 28.0},
    "P": {"a": 26.3, "b": 36.4, "c": 53.1, "d": 43.2},
    "Q": {"a": 27.0, "b": 34.2, "c": 62.0, "d": 36.9},
    "R": {"a": 22.9, "b": 32.2, "c": 51.0, "d": 31.7},
    "S": {"a": 23.6, "b": 30.3, "c": 49.0, "d": 32.1},
    "gesamtwirtschaft": PAY_RATE_BUSINESS_DEFAULTS,
}
NORM_ADDRESSEE_CHECK_SQL = "CHECK (norm_addressee IN ({values}))".format(
    values=", ".join(f"'{na}'" for na in SUPPORTED_NORM_ADDRESSEES)
)

# Canonical machine names for the qualification dimension of the row-based
# personnel-effort model (process_step_personnel_effort). The four slots a/b/c/d
# of the legacy fixed-column model map 1:1 onto these names per norm addressee.
PERSONNEL_QUALIFICATION_BY_SLOT: dict[str, dict[str, str]] = {
    ADMINISTRATION: {
        "a": "einfacher_und_mittlerer_dienst",
        "b": "gehobener_dienst",
        "c": "hoeherer_dienst",
        "d": "durchschnitt",
    },
    BUSINESS: {
        "a": "niedrig",
        "b": "mittel",
        "c": "hoch",
        "d": "durchschnitt",
    },
}
PERSONNEL_SLOT_BY_QUALIFICATION: dict[str, dict[str, str]] = {
    addressee: {name: slot for slot, name in slots.items()}
    for addressee, slots in PERSONNEL_QUALIFICATION_BY_SLOT.items()
}
# Wage-source kind is derivable from the norm addressee.
WAGE_SOURCE_KIND_BY_ADDRESSEE: dict[str, str] = {
    ADMINISTRATION: "verwaltungsebene",
    BUSINESS: "wirtschaftsabschnitt",
}


def get_model_hourly_rate(
    norm_addressee: str,
    wage_source_value: str,
    qualification: str,
) -> float | None:
    """Resolve the model hourly wage rate from the reference constants.

    This is the single seam between the row-based model and the wage reference
    data. Today it reads the in-code constants (PAY_RATE_*_DEFAULTS); promoting
    them to a DB table later only changes this function. Returns None when the
    (addressee, source, qualification) combination is unknown so callers can
    decide how to react; citizens have no monetised personnel rate (0.0).
    """
    resolved = normalize_norm_addressee(norm_addressee)
    if resolved == CITIZENS:
        return 0.0
    slot = PERSONNEL_SLOT_BY_QUALIFICATION.get(resolved, {}).get(qualification)
    if slot is None:
        return None
    if resolved == ADMINISTRATION:
        table = PAY_RATE_LEVEL_DEFAULTS.get(wage_source_value)
    elif resolved == BUSINESS:
        table = PAY_RATE_BUSINESS_SECTION_DEFAULTS.get(wage_source_value)
    else:
        return None
    if table is None:
        return None
    return table.get(slot)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _open_connection() -> sqlite3.Connection:
    _ensure_parent(settings.db_path)
    # timeout/busy_timeout: wait (up to 30s) instead of failing immediately when
    # another writer holds the lock. Relevant once work runs off the event loop
    # (e.g. deep-research via asyncio.to_thread) so concurrent writers can overlap.
    conn = sqlite3.connect(settings.db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn


def _table_exists(cur: sqlite3.Cursor, table_name: str) -> bool:
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    return cur.fetchone() is not None


def _table_sql(cur: sqlite3.Cursor, table_name: str) -> str:
    cur.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    row = cur.fetchone()
    return str(row["sql"] or "") if row else ""


def _create_session_scoped_tile_tables(cur: sqlite3.Cursor) -> None:
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS tiles (
            session_id INTEGER NOT NULL,
            norm_addressee TEXT NOT NULL DEFAULT 'administration' {NORM_ADDRESSEE_CHECK_SQL},
            id TEXT NOT NULL,
            title TEXT NOT NULL,
            text TEXT NOT NULL,
            meta JSON,
            col INTEGER NOT NULL DEFAULT 0,
            row INTEGER NOT NULL DEFAULT 0,
            deletable INTEGER NOT NULL DEFAULT 1 CHECK (deletable IN (0, 1)),
            PRIMARY KEY (session_id, norm_addressee, id),
            FOREIGN KEY (session_id)
            REFERENCES sessions(session_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        );
        """
    )
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS links (
            session_id INTEGER NOT NULL,
            norm_addressee TEXT NOT NULL DEFAULT 'administration' {NORM_ADDRESSEE_CHECK_SQL},
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            PRIMARY KEY (session_id, norm_addressee, source, target),
            FOREIGN KEY (session_id, norm_addressee, source)
            REFERENCES tiles(session_id, norm_addressee, id)
                ON UPDATE CASCADE
                ON DELETE CASCADE,
            FOREIGN KEY (session_id, norm_addressee, target)
            REFERENCES tiles(session_id, norm_addressee, id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        );
        """
    )


def _migrate_tile_tables_to_norm_addressee(cur: sqlite3.Cursor) -> None:
    tiles_exists = _table_exists(cur, "tiles")
    links_exists = _table_exists(cur, "links")
    check_fragment = "check (norm_addressee in ('administration', 'business', 'citizens'))"
    tiles_has_norm_addressee = tiles_exists and _table_has_column(cur, "tiles", "norm_addressee")
    links_has_norm_addressee = links_exists and _table_has_column(cur, "links", "norm_addressee")
    tiles_needs_migration = tiles_exists and (
        not tiles_has_norm_addressee
        or check_fragment not in _table_sql(cur, "tiles").lower()
    )
    links_needs_migration = links_exists and (
        not links_has_norm_addressee
        or check_fragment not in _table_sql(cur, "links").lower()
    )
    if not tiles_needs_migration and not links_needs_migration:
        return

    cur.execute("PRAGMA foreign_keys = OFF")
    if links_needs_migration:
        cur.execute("ALTER TABLE links RENAME TO links_legacy")
    if tiles_needs_migration:
        cur.execute("ALTER TABLE tiles RENAME TO tiles_legacy")

    _create_session_scoped_tile_tables(cur)

    if tiles_needs_migration:
        norm_addressee_select = (
            "norm_addressee" if tiles_has_norm_addressee else "'administration'"
        )
        cur.execute(
            f"""
            INSERT INTO tiles (
                session_id,
                norm_addressee,
                id,
                title,
                text,
                meta,
                col,
                row,
                deletable
            )
            SELECT
                session_id,
                {norm_addressee_select},
                id,
                title,
                text,
                meta,
                col,
                row,
                deletable
            FROM tiles_legacy
            """
        )
        cur.execute("DROP TABLE tiles_legacy")

    if links_needs_migration:
        norm_addressee_select = (
            "norm_addressee" if links_has_norm_addressee else "'administration'"
        )
        cur.execute(
            f"""
            INSERT INTO links (
                session_id,
                norm_addressee,
                source,
                target
            )
            SELECT
                session_id,
                {norm_addressee_select},
                source,
                target
            FROM links_legacy
            """
        )
        cur.execute("DROP TABLE links_legacy")

    cur.execute("PRAGMA foreign_keys = ON")


# Canonical wage rates per norm addressee. These constants are the single source
# of truth; there is no pay_rate_defaults table. Per-session reproducibility lives
# in the sessions.pay_rate_default_* snapshots.
_PAY_RATE_DEFAULTS_BY_ADDRESSEE: dict[str, dict[str, dict[str, float]]] = {
    ADMINISTRATION: PAY_RATE_LEVEL_DEFAULTS,
    BUSINESS: PAY_RATE_BUSINESS_SECTION_DEFAULTS,
}
# Fallback key + constant per norm addressee when neither the requested label
# nor the default key is found in the constants dict.
_PAY_RATE_FALLBACK_KEY: dict[str, str] = {
    ADMINISTRATION: PAY_RATE_LEVEL_BUND,
    BUSINESS: "gesamtwirtschaft",
}
_PAY_RATE_FALLBACK_DEFAULTS: dict[str, dict[str, float]] = {
    ADMINISTRATION: PAY_RATE_BUND_DEFAULTS,
    BUSINESS: PAY_RATE_BUSINESS_DEFAULTS,
}


def _resolve_pay_rate_defaults(
    norm_addressee: str,
    source_value: str | None,
) -> dict[str, float]:
    """Resolve the canonical rate row (a..d) for a norm addressee + source.

    Constants-only, no DB access. Fallback chain: requested source_value ->
    addressee default key (administration -> "bund", business -> "gesamtwirtschaft")
    -> hardcoded constant.
    """
    resolved = normalize_norm_addressee(norm_addressee)
    table = _PAY_RATE_DEFAULTS_BY_ADDRESSEE.get(resolved, {})

    fallback_key = _PAY_RATE_FALLBACK_KEY.get(resolved, PAY_RATE_LEVEL_BUND)
    requested = str(source_value or "").strip()
    if resolved == ADMINISTRATION:
        requested = requested.lower()
    lookup_keys = [requested] if requested else []
    if fallback_key not in lookup_keys:
        lookup_keys.append(fallback_key)

    for key in lookup_keys:
        rates = table.get(key)
        if rates:
            return {
                "a": float(rates["a"]),
                "b": float(rates["b"]),
                "c": float(rates["c"]),
                "d": float(rates["d"]),
            }
    return dict(_PAY_RATE_FALLBACK_DEFAULTS.get(resolved, PAY_RATE_BUND_DEFAULTS))


def get_default_pay_rates_for_addressee(
    norm_addressee: str,
    source_value: str | None = None,
) -> dict[str, float]:
    resolved = normalize_norm_addressee(norm_addressee)
    if resolved not in (ADMINISTRATION, BUSINESS):
        raise ValueError(
            f"pay-rate defaults are only defined for {ADMINISTRATION} and {BUSINESS}, "
            f"got norm_addressee={norm_addressee!r}"
        )
    return _resolve_pay_rate_defaults(resolved, source_value)


def _empty_pay_rate_edits() -> dict[str, float | None]:
    return {key: None for key in PAY_RATE_KEYS}


def _zero_pay_rates() -> dict[str, float]:
    return {key: 0.0 for key in PAY_RATE_KEYS}


def _used_models_expr(session_id_sql: str) -> str:
    return f"""
        (
            SELECT GROUP_CONCAT(t.model, ', ')
            FROM (
                SELECT DISTINCT a.model AS model
                FROM llm_answers a
                WHERE a.session_id = {session_id_sql}
                ORDER BY a.model
            ) AS t
        )
    """


def _create_used_models_triggers(cur: sqlite3.Cursor) -> None:
    """Create permanent triggers that keep sessions.used_llm_models in sync.

    These triggers are runtime behavior (not a one-off migration) and should
    remain in production.
    """
    cur.execute(
        f"""
        CREATE TRIGGER IF NOT EXISTS trg_llm_answers_used_models_ai
        AFTER INSERT ON llm_answers
        BEGIN
            UPDATE sessions
            SET used_llm_models = {_used_models_expr('NEW.session_id')}
            WHERE session_id = NEW.session_id;
        END
        """
    )
    cur.execute(
        f"""
        CREATE TRIGGER IF NOT EXISTS trg_llm_answers_used_models_au
        AFTER UPDATE OF session_id, model ON llm_answers
        BEGIN
            UPDATE sessions
            SET used_llm_models = {_used_models_expr('OLD.session_id')}
            WHERE session_id = OLD.session_id;
            UPDATE sessions
            SET used_llm_models = {_used_models_expr('NEW.session_id')}
            WHERE session_id = NEW.session_id;
        END
        """
    )
    cur.execute(
        f"""
        CREATE TRIGGER IF NOT EXISTS trg_llm_answers_used_models_ad
        AFTER DELETE ON llm_answers
        BEGIN
            UPDATE sessions
            SET used_llm_models = {_used_models_expr('OLD.session_id')}
            WHERE session_id = OLD.session_id;
        END
        """
    )


def _create_session_cc_cost_triggers(cur: sqlite3.Cursor) -> None:
    """Keep sessions.cc_cost in sync with SUM(total_cost) across all norm
    addressees in session_total_costs_by_addressee. NULL total_cost entries
    (e.g. citizens, whose effort is measured in time) contribute nothing;
    cc_cost becomes NULL when no per-addressee row exists for the session.
    """
    recompute = """
        UPDATE sessions
        SET cc_cost = (
            SELECT SUM(total_cost)
            FROM session_total_costs_by_addressee
            WHERE session_id = {sid}
        )
        WHERE session_id = {sid};
    """
    cur.execute(
        f"""
        CREATE TRIGGER IF NOT EXISTS trg_session_total_costs_cc_cost_ai
        AFTER INSERT ON session_total_costs_by_addressee
        BEGIN
            {recompute.format(sid='NEW.session_id')}
        END
        """
    )
    cur.execute(
        f"""
        CREATE TRIGGER IF NOT EXISTS trg_session_total_costs_cc_cost_au
        AFTER UPDATE OF total_cost, session_id ON session_total_costs_by_addressee
        BEGIN
            {recompute.format(sid='OLD.session_id')}
            {recompute.format(sid='NEW.session_id')}
        END
        """
    )
    cur.execute(
        f"""
        CREATE TRIGGER IF NOT EXISTS trg_session_total_costs_cc_cost_ad
        AFTER DELETE ON session_total_costs_by_addressee
        BEGIN
            {recompute.format(sid='OLD.session_id')}
        END
        """
    )


def _create_session_activities_table(cur: sqlite3.Cursor) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS session_activities (
            session_id      INTEGER PRIMARY KEY,
            activity_id     TEXT NOT NULL UNIQUE,
            activity_type   TEXT NOT NULL CHECK (activity_type IN ('workflow', 'ea_edit')),
            label           TEXT NOT NULL,
            created_at      REAL NOT NULL,
            updated_at      REAL NOT NULL,
            expires_at      REAL,
            FOREIGN KEY (session_id)
            REFERENCES sessions(session_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_session_activities_expires_at
        ON session_activities(expires_at)
        """
    )


def _create_citizens_hourly_rate_triggers(cur: sqlite3.Cursor) -> None:
    """Prevent persisted hourly rates for citizens rows in process_steps."""
    citizen_rate_guard = """
        NEW.norm_addressee = 'citizens'
        AND (
            NEW.hourly_rate_a_current IS NOT NULL
            OR NEW.hourly_rate_b_current IS NOT NULL
            OR NEW.hourly_rate_c_current IS NOT NULL
            OR NEW.hourly_rate_d_current IS NOT NULL
            OR NEW.hourly_rate_a_proposed IS NOT NULL
            OR NEW.hourly_rate_b_proposed IS NOT NULL
            OR NEW.hourly_rate_c_proposed IS NOT NULL
            OR NEW.hourly_rate_d_proposed IS NOT NULL
        )
    """
    cur.execute(
        f"""
        CREATE TRIGGER IF NOT EXISTS trg_process_steps_citizens_no_hourly_rates_ai
        AFTER INSERT ON process_steps
        WHEN {citizen_rate_guard}
        BEGIN
            SELECT RAISE(ABORT, 'Citizens process steps must not persist hourly rates');
        END
        """
    )
    cur.execute(
        f"""
        CREATE TRIGGER IF NOT EXISTS trg_process_steps_citizens_no_hourly_rates_au
        AFTER UPDATE OF
            norm_addressee,
            hourly_rate_a_current,
            hourly_rate_b_current,
            hourly_rate_c_current,
            hourly_rate_d_current,
            hourly_rate_a_proposed,
            hourly_rate_b_proposed,
            hourly_rate_c_proposed,
            hourly_rate_d_proposed
        ON process_steps
        WHEN {citizen_rate_guard}
        BEGIN
            SELECT RAISE(ABORT, 'Citizens process steps must not persist hourly rates');
        END
        """
    )


def _refresh_all_session_used_models(cur: sqlite3.Cursor) -> None:
    """Migration helper: one-off backfill for existing sessions rows.

    This is only needed for in-place upgrades of non-empty dev/legacy DBs.
    Safe to remove once production starts from an empty DB with final schema
    and triggers in place from day one.
    """
    cur.execute(
        f"""
        UPDATE sessions
        SET used_llm_models = {_used_models_expr('sessions.session_id')}
        """
    )


def _table_has_column(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    for row in cur.fetchall():
        name = row["name"] if isinstance(row, sqlite3.Row) else row[1]
        if name == column:
            return True
    return False


def _ensure_column(
    cur: sqlite3.Cursor,
    table: str,
    column: str,
    column_ddl: str,
) -> None:
    """Migration helper: add a column if missing on legacy/dev databases.

    This is only needed for in-place schema upgrades. Safe to remove once
    production starts from an empty DB with the final CREATE TABLE definitions.
    """
    if _table_has_column(cur, table, column):
        return
    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_ddl}")


def _ensure_columns(
    cur: sqlite3.Cursor,
    table: str,
    columns: dict[str, str],
) -> None:
    for column, column_ddl in columns.items():
        _ensure_column(cur, table, column, column_ddl)


def _create_users_table(cur: sqlite3.Cursor) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id        INTEGER PRIMARY KEY,
            email          TEXT NOT NULL,
            password_hash  TEXT NOT NULL,
            is_admin       INTEGER NOT NULL DEFAULT 0,
            is_active      INTEGER NOT NULL DEFAULT 1,
            created_at     TEXT NOT NULL DEFAULT current_timestamp
        )
        """
    )
    # Case-insensitive unique email.
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower ON users(lower(email))"
    )


def _create_process_steps_table(cur: sqlite3.Cursor, table_name: str = "process_steps") -> None:
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            step_id                         INTEGER PRIMARY KEY,
            case_group_id                   INTEGER NOT NULL,
            session_id                      INTEGER NOT NULL,
            norm_addressee                  TEXT NOT NULL DEFAULT 'administration' {NORM_ADDRESSEE_CHECK_SQL},
            step                            TEXT NOT NULL,
            description                     TEXT NOT NULL,
            change_status                   TEXT NOT NULL,
            created_at                      TEXT NOT NULL DEFAULT current_timestamp,
            previous_id                     INTEGER,
            next_id                         INTEGER,
            hourly_rate_a_current           REAL,
            hourly_rate_b_current           REAL,
            hourly_rate_c_current           REAL,
            hourly_rate_d_current           REAL,
            time_required_in_min_a_current  REAL,
            time_required_in_min_b_current  REAL,
            time_required_in_min_c_current  REAL,
            time_required_in_min_d_current  REAL,
            time_required_in_min_a_current_edited  REAL,
            time_required_in_min_b_current_edited  REAL,
            time_required_in_min_c_current_edited  REAL,
            time_required_in_min_d_current_edited  REAL,
            expenses_current                REAL,
            expenses_current_edited         REAL,
            hourly_rate_a_proposed          REAL,
            hourly_rate_b_proposed          REAL,
            hourly_rate_c_proposed          REAL,
            hourly_rate_d_proposed          REAL,
            time_required_in_min_a_proposed REAL,
            time_required_in_min_b_proposed REAL,
            time_required_in_min_c_proposed REAL,
            time_required_in_min_d_proposed REAL,
            time_required_in_min_a_proposed_edited REAL,
            time_required_in_min_b_proposed_edited REAL,
            time_required_in_min_c_proposed_edited REAL,
            time_required_in_min_d_proposed_edited REAL,
            expenses_proposed               REAL,
            expenses_proposed_edited        REAL,
            execution_per_case              INTEGER,
            cost_current                    REAL,
            cost_proposed                   REAL,
            last_edited_at                  TEXT,
            role_sources_current_json       TEXT,
            role_sources_proposed_json      TEXT,
            FOREIGN KEY (case_group_id)
            REFERENCES case_groups
                ON UPDATE CASCADE
                ON DELETE CASCADE,
            FOREIGN KEY (session_id)
            REFERENCES sessions (session_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        """
    )


def _create_processes_table(cur: sqlite3.Cursor, table_name: str = "processes") -> None:
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            process_id      INTEGER PRIMARY KEY,
            session_id      INTEGER NOT NULL,
            norm_addressee  TEXT NOT NULL DEFAULT 'administration' {NORM_ADDRESSEE_CHECK_SQL},
            process         TEXT NOT NULL,
            description     TEXT NOT NULL,
            change_status   TEXT NOT NULL,
            created_at      TEXT NOT NULL DEFAULT current_timestamp,
            cost            REAL,
            FOREIGN KEY (session_id)
            REFERENCES sessions (session_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        """
    )


def _create_case_groups_table(cur: sqlite3.Cursor, table_name: str = "case_groups") -> None:
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            case_group_id               INTEGER PRIMARY KEY,
            process_id                  INTEGER NOT NULL,
            session_id                  INTEGER NOT NULL,
            norm_addressee              TEXT NOT NULL DEFAULT 'administration' {NORM_ADDRESSEE_CHECK_SQL},
            case_group                  TEXT NOT NULL,
            description                 TEXT NOT NULL,
            change_status               TEXT NOT NULL,
            created_at                  TEXT NOT NULL DEFAULT current_timestamp,
            addressees_current          REAL,
            annual_frequency_current    REAL,
            cases_current               REAL,
            addressees_current_edited   REAL,
            annual_frequency_current_edited REAL,
            cases_current_edited        REAL,
            addressees_proposed         REAL,
            annual_frequency_proposed   REAL,
            cases_proposed              REAL,
            addressees_proposed_edited  REAL,
            annual_frequency_proposed_edited REAL,
            cases_proposed_edited       REAL,
            cost                        REAL,
            last_edited_at              TEXT,
            case_metric_research_json   JSON,
            FOREIGN KEY (process_id)
            REFERENCES processes
                ON UPDATE CASCADE
                ON DELETE CASCADE,
            FOREIGN KEY (session_id)
            REFERENCES sessions (session_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        """
    )


def _create_deep_research_runs_table(
    cur: sqlite3.Cursor,
    table_name: str = "deep_research_runs",
) -> None:
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            research_run_id       INTEGER PRIMARY KEY,
            session_id            INTEGER NOT NULL,
            purpose               TEXT NOT NULL,
            provider              TEXT NOT NULL DEFAULT 'gemini',
            agent                 TEXT NOT NULL,
            status                TEXT NOT NULL,
            interaction_id        TEXT,
            prompt_text           TEXT,
            report_md             TEXT,
            result_json           JSON,
            response_json         JSON,
            error                 TEXT,
            input_tokens          INTEGER,
            output_tokens         INTEGER,
            thought_tokens        INTEGER,
            total_tokens          INTEGER,
            estimated_cost_usd    REAL,
            created_at            TEXT NOT NULL DEFAULT current_timestamp,
            started_at            TEXT,
            completed_at          TEXT,
            parsed_at             TEXT,
            FOREIGN KEY (session_id)
            REFERENCES sessions (session_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        """
    )
    cur.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_{table_name}_session_purpose
        ON {table_name}(session_id, purpose, research_run_id)
        """
    )


def _create_regulation_process_links_by_addressee_table(
    cur: sqlite3.Cursor,
    table_name: str = "regulation_process_links_by_addressee",
) -> None:
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            session_id       INTEGER NOT NULL,
            norm_addressee   TEXT NOT NULL {NORM_ADDRESSEE_CHECK_SQL},
            regulation_id    INTEGER NOT NULL,
            process_id       INTEGER NOT NULL,
            PRIMARY KEY (session_id, norm_addressee, regulation_id),
            FOREIGN KEY (session_id, regulation_id)
            REFERENCES regulations (session_id, regulation_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE,
            FOREIGN KEY (session_id, norm_addressee, process_id)
            REFERENCES processes (session_id, norm_addressee, process_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        """
    )


def _create_process_step_regulation_links_table(
    cur: sqlite3.Cursor,
    table_name: str = "process_step_regulation_links",
) -> None:
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            session_id       INTEGER NOT NULL,
            norm_addressee   TEXT NOT NULL {NORM_ADDRESSEE_CHECK_SQL},
            step_id          INTEGER NOT NULL,
            regulation_id    INTEGER NOT NULL,
            PRIMARY KEY (session_id, norm_addressee, step_id, regulation_id),
            FOREIGN KEY (session_id, norm_addressee, step_id)
            REFERENCES process_steps (session_id, norm_addressee, step_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE,
            FOREIGN KEY (session_id, regulation_id)
            REFERENCES regulations (session_id, regulation_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        """
    )


def _create_session_total_costs_by_addressee_table(
    cur: sqlite3.Cursor,
    table_name: str = "session_total_costs_by_addressee",
) -> None:
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            session_id           INTEGER NOT NULL,
            norm_addressee       TEXT NOT NULL {NORM_ADDRESSEE_CHECK_SQL},
            total_cost           REAL,
            bureaucracy_cost     REAL,
            total_time_minutes   REAL,
            total_expenses       REAL,
            PRIMARY KEY (session_id, norm_addressee),
            FOREIGN KEY (session_id)
            REFERENCES sessions (session_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        """
    )


def _create_compliance_text_examples_table(
    cur: sqlite3.Cursor,
    table_name: str = "compliance_text_examples",
) -> None:
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            example_id      INTEGER PRIMARY KEY,
            slug            TEXT NOT NULL UNIQUE,
            title           TEXT NOT NULL,
            body_md         TEXT NOT NULL,
            sort_order      INTEGER NOT NULL DEFAULT 0,
            source_path     TEXT,
            created_at      TEXT NOT NULL DEFAULT current_timestamp,
            updated_at      TEXT NOT NULL DEFAULT current_timestamp
        )
        """
    )


def _create_compliance_text_exports_table(
    cur: sqlite3.Cursor,
    table_name: str = "compliance_text_exports",
) -> None:
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            export_id              INTEGER PRIMARY KEY,
            session_id             INTEGER NOT NULL,
            llm_answer_id          INTEGER,
            status                 TEXT NOT NULL,
            model                  TEXT,
            provider               TEXT,
            prompt_text            TEXT,
            generated_markdown     TEXT NOT NULL,
            source_snapshot_json   JSON NOT NULL,
            source_snapshot_sha256 TEXT NOT NULL,
            used_deep_research     INTEGER NOT NULL DEFAULT 0,
            deep_research_run_id   INTEGER,
            used_user_edits        INTEGER NOT NULL DEFAULT 0,
            user_edit_policy       TEXT NOT NULL,
            metadata_json          JSON,
            input_tokens           INTEGER,
            output_tokens          INTEGER,
            hidden_thinking_tokens INTEGER,
            estimated_cost_usd     REAL,
            created_at             TEXT NOT NULL DEFAULT current_timestamp,
            FOREIGN KEY (session_id)
            REFERENCES sessions (session_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE,
            FOREIGN KEY (llm_answer_id)
            REFERENCES llm_answers (answer_id)
                ON UPDATE SET NULL
                ON DELETE SET NULL
        )
        """
    )
    cur.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_{table_name}_session_snapshot_policy
        ON {table_name}(session_id, source_snapshot_sha256, user_edit_policy, export_id)
        """
    )


def _slugify_compliance_example(filename: str) -> str:
    stem = Path(filename).stem.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
    return slug or "example"


def _seed_compliance_text_examples(cur: sqlite3.Cursor) -> None:
    cur.execute("SELECT COUNT(*) AS count FROM compliance_text_examples")
    if int(cur.fetchone()["count"]) > 0:
        return
    examples_dir = Path(__file__).resolve().parents[2] / "resources" / "compliance_text_examples"
    if not examples_dir.exists():
        return
    markdown_files = sorted(path for path in examples_dir.iterdir() if path.suffix.lower() == ".md")
    for index, path in enumerate(markdown_files[:3], start=1):
        body_md = path.read_text(encoding="utf-8")
        slug = _slugify_compliance_example(path.name)
        title = path.stem.replace("_", " ").replace("-", " ").strip() or f"Beispiel {index}"
        source_path = str(path.relative_to(Path(__file__).resolve().parents[2]))
        cur.execute(
            """
            INSERT INTO compliance_text_examples (
                slug,
                title,
                body_md,
                sort_order,
                source_path
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (slug, title, body_md, index, source_path),
        )


def _seed_builtin_laws(cur: sqlite3.Cursor) -> None:
    builtins_dir = Path(__file__).resolve().parents[2] / "resources" / "built_in_laws"
    if not builtins_dir.exists():
        return
    law_files = sorted(path for path in builtins_dir.iterdir() if path.suffix.lower() == ".txt")
    for path in law_files:
        law_text = path.read_text(encoding="utf-8").strip()
        if not law_text:
            continue
        file_name = path.name
        cur.execute(
            """
            SELECT document_id
            FROM laws
            WHERE file_name = ? AND owner_user_id IS NULL
            ORDER BY is_builtin DESC, document_id ASC
            LIMIT 1
            """,
            (file_name,),
        )
        row = cur.fetchone()
        if row:
            cur.execute(
                """
                UPDATE laws
                SET law_text = ?, text_length = ?, is_builtin = 1
                WHERE document_id = ?
                """,
                (law_text, len(law_text), int(row["document_id"])),
            )
        else:
            cur.execute(
                """
                INSERT INTO laws (file_name, law_text, text_length, owner_user_id, is_builtin)
                VALUES (?, ?, ?, NULL, 1)
                """,
                (file_name, law_text, len(law_text)),
            )


def _create_session_pay_rate_overrides_by_addressee_table(
    cur: sqlite3.Cursor,
    table_name: str = "session_pay_rate_overrides_by_addressee",
) -> None:
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            session_id           INTEGER NOT NULL,
            norm_addressee       TEXT NOT NULL {NORM_ADDRESSEE_CHECK_SQL},
            edited_a             REAL,
            edited_b             REAL,
            edited_c             REAL,
            edited_d             REAL,
            last_edited_at       TEXT,
            PRIMARY KEY (session_id, norm_addressee),
            FOREIGN KEY (session_id)
            REFERENCES sessions (session_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        """
    )


def _create_process_step_personnel_effort_table(
    cur: sqlite3.Cursor,
    table_name: str = "process_step_personnel_effort",
) -> None:
    """Row-based personnel effort (child of process_steps).

    One row per (step, period, qualification, wage source). Replaces the fixed
    a/b/c/d wage/time columns on process_steps so that mixed wage sources for the
    same qualification (e.g. Bund and Laender gehobener Dienst in one step) no
    longer overwrite each other.

    The per-row cost is recomputed on demand from rate * time and deliberately not
    cached here (no ``computed_cost`` column): it is cheap to derive and a cache
    would only risk drifting from the authoritative rate/time/override inputs.
    """
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            effort_id                    INTEGER PRIMARY KEY,
            session_id                   INTEGER NOT NULL,
            norm_addressee               TEXT NOT NULL {NORM_ADDRESSEE_CHECK_SQL},
            step_id                      INTEGER NOT NULL,
            period                       TEXT NOT NULL CHECK (period IN ('current', 'proposed')),
            qualification                TEXT NOT NULL,
            wage_source_kind             TEXT NOT NULL,
            wage_source_value            TEXT NOT NULL,
            time_required_in_min         REAL,
            time_required_in_min_edited  REAL,
            model_hourly_rate            REAL NOT NULL,
            last_edited_at               TEXT,
            UNIQUE (
                session_id,
                norm_addressee,
                step_id,
                period,
                qualification,
                wage_source_kind,
                wage_source_value
            ),
            FOREIGN KEY (session_id)
            REFERENCES sessions (session_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE,
            FOREIGN KEY (step_id)
            REFERENCES process_steps (step_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        """
    )


def _create_session_wage_rate_overrides_table(
    cur: sqlite3.Cursor,
    table_name: str = "session_wage_rate_overrides",
) -> None:
    """Row-keyed session wage overrides (created now, used from Phase B/C).

    Keyed by (source, qualification) so a manual rate edit applies precisely to
    matching personnel-effort rows, unlike the legacy slot-based overrides.
    """
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            session_id           INTEGER NOT NULL,
            norm_addressee       TEXT NOT NULL {NORM_ADDRESSEE_CHECK_SQL},
            wage_source_kind     TEXT NOT NULL,
            wage_source_value    TEXT NOT NULL,
            qualification        TEXT NOT NULL,
            hourly_rate_edited   REAL,
            last_edited_at       TEXT,
            PRIMARY KEY (
                session_id,
                norm_addressee,
                wage_source_kind,
                wage_source_value,
                qualification
            ),
            FOREIGN KEY (session_id)
            REFERENCES sessions (session_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        """
    )


def _decode_role_sources_by_slot(raw_json: str | None) -> dict[str, str]:
    """Decode role_sources_*_json into ``{slot: source_value}`` (best effort)."""
    if not raw_json:
        return {}
    try:
        entries = json.loads(raw_json)
    except (TypeError, ValueError):
        return {}
    result: dict[str, str] = {}
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and entry.get("slot") and entry.get("source_value"):
                result[str(entry["slot"])] = str(entry["source_value"])
    return result


def _recover_backfill_wage_source(
    norm_addressee: str,
    slot: str,
    stored_rate: float | None,
    recorded_source: str | None,
) -> str | None:
    """Resolve the wage source for a legacy slot cell during backfill.

    Priority: (1) the source the parser recorded in role_sources_*_json, else
    (2) reverse-lookup by the stored slot rate -> the table source carrying that
    rate, else (3) when several sources share that rate, the aggregate label
    (durchschnitt / gesamtwirtschaft) if it is among them, otherwise the first
    candidate alphabetically. Every equal-rate candidate yields the same cost, so
    only the source *label* of an ambiguous cell is a best-effort guess.
    """
    if recorded_source:
        return recorded_source
    if norm_addressee == ADMINISTRATION:
        table = PAY_RATE_LEVEL_DEFAULTS
        default = "durchschnitt"
    elif norm_addressee == BUSINESS:
        table = PAY_RATE_BUSINESS_SECTION_DEFAULTS
        default = "gesamtwirtschaft"
    else:
        return None
    if stored_rate is None:
        return default
    candidates = sorted(
        source
        for source, col in table.items()
        if slot in col and abs(col[slot] - float(stored_rate)) < 0.005
    )
    if not candidates:
        return default
    if default in candidates:
        return default
    return candidates[0]


def _backfill_process_step_personnel_effort(cur: sqlite3.Cursor) -> int:
    """One-time, idempotent migration of legacy slot effort into child rows.

    For every org step (administration/business) that still has slot-based time
    but no child rows yet, create the equivalent process_step_personnel_effort
    rows. The wage source is recovered from role_sources_*_json or, when missing,
    reverse-looked-up from the stored slot rate (see
    `_recover_backfill_wage_source`). The model_hourly_rate is taken from the wage
    table, which equals the stored slot rate for legacy data, so per-step costs
    are preserved. Citizens carry no monetised personnel rows and are skipped.

    Returns the number of child rows inserted (0 on an already-migrated or empty
    database).
    """
    existing = {
        row["step_id"]
        for row in cur.execute(
            "SELECT DISTINCT step_id FROM process_step_personnel_effort"
        ).fetchall()
    }
    steps = cur.execute(
        "SELECT * FROM process_steps WHERE norm_addressee IN (?, ?)",
        (ADMINISTRATION, BUSINESS),
    ).fetchall()
    inserted = 0
    for step in steps:
        step_id = step["step_id"]
        if step_id in existing:
            continue
        addr = step["norm_addressee"]
        kind = WAGE_SOURCE_KIND_BY_ADDRESSEE.get(addr)
        for period in ("current", "proposed"):
            recorded = _decode_role_sources_by_slot(step[f"role_sources_{period}_json"])
            for slot in PAY_RATE_KEYS:
                base = step[f"time_required_in_min_{slot}_{period}"]
                edited = step[f"time_required_in_min_{slot}_{period}_edited"]
                if base is None and edited is None:
                    continue
                qualification = PERSONNEL_QUALIFICATION_BY_SLOT[addr][slot]
                source_value = _recover_backfill_wage_source(
                    addr, slot, step[f"hourly_rate_{slot}_{period}"], recorded.get(slot)
                )
                if source_value is None:
                    continue
                model_rate = get_model_hourly_rate(addr, source_value, qualification)
                if model_rate is None:
                    continue
                cur.execute(
                    """
                    INSERT INTO process_step_personnel_effort (
                        session_id, norm_addressee, step_id, period,
                        qualification, wage_source_kind, wage_source_value,
                        time_required_in_min, time_required_in_min_edited,
                        model_hourly_rate
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        step["session_id"], addr, step_id, period,
                        qualification, kind, source_value,
                        base, edited, model_rate,
                    ),
                )
                inserted += 1
    return inserted


def _create_parent_composite_indexes(cur: sqlite3.Cursor) -> None:
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_processes_session_addressee_process_id ON processes(session_id, norm_addressee, process_id)"
    )
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_case_groups_session_addressee_case_group_id ON case_groups(session_id, norm_addressee, case_group_id)"
    )
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_process_steps_session_addressee_step_id ON process_steps(session_id, norm_addressee, step_id)"
    )
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_regulations_session_regulation_id ON regulations(session_id, regulation_id)"
    )


def _migrate_addressee_metrics_into_parent_tables(cur: sqlite3.Cursor) -> None:
    if _table_exists(cur, "case_group_metrics_by_addressee"):
        cur.execute(
            """
            UPDATE case_groups
            SET addressees_current = (
                    SELECT metrics.addressees_current
                    FROM case_group_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = case_groups.session_id
                      AND metrics.case_group_id = case_groups.case_group_id
                      AND metrics.norm_addressee = case_groups.norm_addressee
                ),
                annual_frequency_current = (
                    SELECT metrics.annual_frequency_current
                    FROM case_group_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = case_groups.session_id
                      AND metrics.case_group_id = case_groups.case_group_id
                      AND metrics.norm_addressee = case_groups.norm_addressee
                ),
                cases_current = (
                    SELECT metrics.cases_current
                    FROM case_group_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = case_groups.session_id
                      AND metrics.case_group_id = case_groups.case_group_id
                      AND metrics.norm_addressee = case_groups.norm_addressee
                ),
                addressees_proposed = (
                    SELECT metrics.addressees_proposed
                    FROM case_group_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = case_groups.session_id
                      AND metrics.case_group_id = case_groups.case_group_id
                      AND metrics.norm_addressee = case_groups.norm_addressee
                ),
                annual_frequency_proposed = (
                    SELECT metrics.annual_frequency_proposed
                    FROM case_group_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = case_groups.session_id
                      AND metrics.case_group_id = case_groups.case_group_id
                      AND metrics.norm_addressee = case_groups.norm_addressee
                ),
                cases_proposed = (
                    SELECT metrics.cases_proposed
                    FROM case_group_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = case_groups.session_id
                      AND metrics.case_group_id = case_groups.case_group_id
                      AND metrics.norm_addressee = case_groups.norm_addressee
                )
            WHERE EXISTS (
                SELECT 1
                FROM case_group_metrics_by_addressee AS metrics
                WHERE metrics.session_id = case_groups.session_id
                  AND metrics.case_group_id = case_groups.case_group_id
                  AND metrics.norm_addressee = case_groups.norm_addressee
            )
            """
        )
        cur.execute("DROP TABLE case_group_metrics_by_addressee")

    if _table_exists(cur, "process_step_effort_metrics_by_addressee"):
        cur.execute(
            """
            UPDATE process_steps
            SET hourly_rate_a_current = (
                    SELECT metrics.hourly_rate_a_current
                    FROM process_step_effort_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                hourly_rate_b_current = (
                    SELECT metrics.hourly_rate_b_current
                    FROM process_step_effort_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                hourly_rate_c_current = (
                    SELECT metrics.hourly_rate_c_current
                    FROM process_step_effort_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                hourly_rate_d_current = (
                    SELECT metrics.hourly_rate_d_current
                    FROM process_step_effort_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                time_required_in_min_a_current = (
                    SELECT metrics.time_required_in_min_a_current
                    FROM process_step_effort_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                time_required_in_min_b_current = (
                    SELECT metrics.time_required_in_min_b_current
                    FROM process_step_effort_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                time_required_in_min_c_current = (
                    SELECT metrics.time_required_in_min_c_current
                    FROM process_step_effort_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                time_required_in_min_d_current = (
                    SELECT metrics.time_required_in_min_d_current
                    FROM process_step_effort_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                expenses_current = (
                    SELECT metrics.expenses_current
                    FROM process_step_effort_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                hourly_rate_a_proposed = (
                    SELECT metrics.hourly_rate_a_proposed
                    FROM process_step_effort_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                hourly_rate_b_proposed = (
                    SELECT metrics.hourly_rate_b_proposed
                    FROM process_step_effort_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                hourly_rate_c_proposed = (
                    SELECT metrics.hourly_rate_c_proposed
                    FROM process_step_effort_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                hourly_rate_d_proposed = (
                    SELECT metrics.hourly_rate_d_proposed
                    FROM process_step_effort_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                time_required_in_min_a_proposed = (
                    SELECT metrics.time_required_in_min_a_proposed
                    FROM process_step_effort_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                time_required_in_min_b_proposed = (
                    SELECT metrics.time_required_in_min_b_proposed
                    FROM process_step_effort_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                time_required_in_min_c_proposed = (
                    SELECT metrics.time_required_in_min_c_proposed
                    FROM process_step_effort_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                time_required_in_min_d_proposed = (
                    SELECT metrics.time_required_in_min_d_proposed
                    FROM process_step_effort_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                expenses_proposed = (
                    SELECT metrics.expenses_proposed
                    FROM process_step_effort_metrics_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                execution_per_case = COALESCE(
                    (
                        SELECT metrics.execution_per_case
                        FROM process_step_effort_metrics_by_addressee AS metrics
                        WHERE metrics.session_id = process_steps.session_id
                          AND metrics.step_id = process_steps.step_id
                          AND metrics.norm_addressee = process_steps.norm_addressee
                    ),
                    execution_per_case
                )
            WHERE EXISTS (
                SELECT 1
                FROM process_step_effort_metrics_by_addressee AS metrics
                WHERE metrics.session_id = process_steps.session_id
                  AND metrics.step_id = process_steps.step_id
                  AND metrics.norm_addressee = process_steps.norm_addressee
            )
            """
        )
        cur.execute("DROP TABLE process_step_effort_metrics_by_addressee")

    if _table_exists(cur, "process_step_costs_by_addressee"):
        cur.execute(
            """
            UPDATE process_steps
            SET cost_current = (
                    SELECT metrics.cost_current
                    FROM process_step_costs_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                ),
                cost_proposed = (
                    SELECT metrics.cost_proposed
                    FROM process_step_costs_by_addressee AS metrics
                    WHERE metrics.session_id = process_steps.session_id
                      AND metrics.step_id = process_steps.step_id
                      AND metrics.norm_addressee = process_steps.norm_addressee
                )
            WHERE EXISTS (
                SELECT 1
                FROM process_step_costs_by_addressee AS metrics
                WHERE metrics.session_id = process_steps.session_id
                  AND metrics.step_id = process_steps.step_id
                  AND metrics.norm_addressee = process_steps.norm_addressee
            )
            """
        )
        cur.execute("DROP TABLE process_step_costs_by_addressee")


def _run_legacy_migrations(cur: sqlite3.Cursor) -> None:
    """Migration helper: run one-off in-place upgrades for legacy/dev DB files.

    This helper exists solely for non-empty databases created before the final
    schema. Safe to remove when production starts from an empty DB and no
    in-place upgrade path is required.
    """
    # Drop orphaned mirror_matches table from earlier feature branch.
    cur.execute("DROP TABLE IF EXISTS mirror_matches")
    cur.execute("DROP INDEX IF EXISTS idx_mirror_matches_session_anchor")

    needs_used_models_backfill = not _table_has_column(cur, "sessions", "used_llm_models")

    _ensure_column(cur, "sessions", "law_diff_title", "TEXT")
    _ensure_column(cur, "sessions", "law_diff_blurb", "TEXT")
    _ensure_column(cur, "sessions", "law_diff_summary", "TEXT")
    _ensure_column(cur, "sessions", "used_llm_models", "TEXT")
    _ensure_column(
        cur,
        "sessions",
        "case_group_research_enabled",
        "INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        cur,
        "sessions",
        "pay_rate_administration_level",
        f"TEXT NOT NULL DEFAULT '{PAY_RATE_LEVEL_BUND}'",
    )
    _ensure_column(cur, "sessions", "pay_rate_default_a", "REAL")
    _ensure_column(cur, "sessions", "pay_rate_default_b", "REAL")
    _ensure_column(cur, "sessions", "pay_rate_default_c", "REAL")
    _ensure_column(cur, "sessions", "pay_rate_default_d", "REAL")
    _ensure_column(cur, "sessions", "pay_rate_edited_a", "REAL")
    _ensure_column(cur, "sessions", "pay_rate_edited_b", "REAL")
    _ensure_column(cur, "sessions", "pay_rate_edited_c", "REAL")
    _ensure_column(cur, "sessions", "pay_rate_edited_d", "REAL")
    _ensure_column(cur, "sessions", "pay_rate_last_edited_at", "TEXT")
    if all(
        _table_has_column(cur, "sessions", f"pay_rate_override_{key}")
        for key in PAY_RATE_KEYS
    ):
        # Migration helper: preserve existing non-empty DB overrides in the new
        # *_edited columns. Safe to remove once production starts from empty DB.
        cur.execute(
            """
            UPDATE sessions
            SET pay_rate_edited_a = COALESCE(pay_rate_edited_a, pay_rate_override_a),
                pay_rate_edited_b = COALESCE(pay_rate_edited_b, pay_rate_override_b),
                pay_rate_edited_c = COALESCE(pay_rate_edited_c, pay_rate_override_c),
                pay_rate_edited_d = COALESCE(pay_rate_edited_d, pay_rate_override_d)
            """
        )

    _ensure_column(cur, "llm_answers", "input_tokens", "INTEGER")
    _ensure_column(cur, "llm_answers", "output_tokens", "INTEGER")
    _ensure_column(cur, "llm_answers", "hidden_thinking_tokens", "INTEGER")
    _ensure_column(cur, "llm_answers", "estimated_cost_usd", "REAL")
    _ensure_column(cur, "llm_answers", "provider_response_json", "JSON")
    _ensure_column(cur, "llm_answers", "prompt_text", "TEXT")
    _ensure_column(
        cur,
        "llm_answers",
        "answer_state",
        "TEXT NOT NULL DEFAULT 'active'",
    )
    _ensure_column(cur, "llm_answers", "state_reason", "TEXT")
    _ensure_column(cur, "llm_answers", "norm_addressee", "TEXT")
    cur.execute(
        """
        UPDATE llm_answers
        SET answer_state = 'active'
        WHERE answer_state IS NULL OR answer_state = ''
        """
    )

    # Migration helper: drop the orphaned pay_rate_defaults table. Wage rates are
    # now constants-only; session snapshots in sessions.pay_rate_default_* are kept.
    cur.execute("DROP TABLE IF EXISTS pay_rate_defaults")

    # Migration helper: add editable overrides for case group metrics.
    _ensure_column(cur, "case_groups", "addressees_current_edited", "REAL")
    _ensure_column(cur, "case_groups", "annual_frequency_current_edited", "REAL")
    _ensure_column(cur, "case_groups", "cases_current_edited", "REAL")
    _ensure_column(cur, "case_groups", "addressees_proposed_edited", "REAL")
    _ensure_column(cur, "case_groups", "annual_frequency_proposed_edited", "REAL")
    _ensure_column(cur, "case_groups", "cases_proposed_edited", "REAL")
    _ensure_column(cur, "case_groups", "last_edited_at", "TEXT")
    _ensure_column(cur, "case_groups", "case_metric_research_json", "JSON")

    # Migration helper: add editable overrides for process-step metrics.
    for suffix in ("current", "proposed"):
        _ensure_column(
            cur,
            "process_steps",
            f"time_required_in_min_a_{suffix}_edited",
            "REAL",
        )
        _ensure_column(
            cur,
            "process_steps",
            f"time_required_in_min_b_{suffix}_edited",
            "REAL",
        )
        _ensure_column(
            cur,
            "process_steps",
            f"time_required_in_min_c_{suffix}_edited",
            "REAL",
        )
        _ensure_column(
            cur,
            "process_steps",
            f"time_required_in_min_d_{suffix}_edited",
            "REAL",
        )
        _ensure_column(cur, "process_steps", f"expenses_{suffix}_edited", "REAL")
    _ensure_column(cur, "process_steps", "last_edited_at", "TEXT")
    _ensure_column(cur, "process_steps", "execution_per_case", "INTEGER")
    _ensure_column(cur, "process_steps", "role_sources_current_json", "TEXT")
    _ensure_column(cur, "process_steps", "role_sources_proposed_json", "TEXT")

    defaults = _resolve_pay_rate_defaults(ADMINISTRATION, PAY_RATE_LEVEL_BUND)
    cur.execute(
        """
        UPDATE sessions
        SET pay_rate_administration_level = COALESCE(pay_rate_administration_level, ?),
            pay_rate_default_a = COALESCE(pay_rate_default_a, ?),
            pay_rate_default_b = COALESCE(pay_rate_default_b, ?),
            pay_rate_default_c = COALESCE(pay_rate_default_c, ?),
            pay_rate_default_d = COALESCE(pay_rate_default_d, ?)
        """,
        (
            PAY_RATE_LEVEL_BUND,
            defaults["a"],
            defaults["b"],
            defaults["c"],
            defaults["d"],
        ),
    )

    if needs_used_models_backfill:
        _refresh_all_session_used_models(cur)

    # Backfill sessions.cc_cost auf Summe aller NA total_cost. Bis hierhin lag
    # cc_cost nur fuer ADMINISTRATION vor; bestehende DBs werden so an die
    # neue Semantik angeglichen. Idempotent.
    cur.execute(
        """
        UPDATE sessions
        SET cc_cost = (
            SELECT SUM(total_cost)
            FROM session_total_costs_by_addressee
            WHERE session_id = sessions.session_id
        )
        """
    )

    _create_parent_composite_indexes(cur)
    _migrate_addressee_metrics_into_parent_tables(cur)


def get_conn() -> sqlite3.Connection:
    existing = _TX_CONN.get()
    if existing is not None:
        return existing
    return _open_connection()


def _in_transaction() -> bool:
    return _TX_CONN.get() is not None


def _maybe_commit(conn: sqlite3.Connection) -> None:
    if not _in_transaction():
        conn.commit()


def _maybe_close(conn: sqlite3.Connection) -> None:
    if not _in_transaction():
        conn.close()


@contextmanager
def transaction() -> Iterable[sqlite3.Connection]:
    existing = _TX_CONN.get()
    if existing is not None:
        yield existing
        return
    conn = _open_connection()
    token = _TX_CONN.set(conn)
    try:
        conn.execute("BEGIN")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _TX_CONN.reset(token)
        conn.close()


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS laws (
            document_id     INTEGER PRIMARY KEY,
            file_name       TEXT NOT NULL,
            law_text        TEXT NOT NULL,
            text_length     INTEGER NOT NULL,
            uploaded_at     TEXT NOT NULL DEFAULT current_timestamp,
            owner_user_id   INTEGER REFERENCES users(user_id),
            is_builtin      INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    _create_deep_research_runs_table(cur)
    # TODO: Maybe add updated_at with trigger rule: https://www.sqlitetutorial.net/sqlite-date-functions/sqlite-current_timestamp/
    # TODO: Potentially add the change in cases? How meaningful is that number?
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id          INTEGER PRIMARY KEY,
            app_session_id      TEXT NOT NULL,
            created_at          TEXT NOT NULL DEFAULT current_timestamp,
            llm_model           TEXT NOT NULL,
            used_llm_models     TEXT,
            pay_rate_administration_level TEXT NOT NULL DEFAULT 'bund',
            pay_rate_default_a  REAL,
            pay_rate_default_b  REAL,
            pay_rate_default_c  REAL,
            pay_rate_default_d  REAL,
            pay_rate_edited_a REAL,
            pay_rate_edited_b REAL,
            pay_rate_edited_c REAL,
            pay_rate_edited_d REAL,
            pay_rate_last_edited_at TEXT,
            current_law_id      INTEGER,
            proposed_law_id     INTEGER,
            law_diff_title      TEXT,
            law_diff_blurb      TEXT,
            law_diff_summary    TEXT,
            case_group_research_enabled INTEGER NOT NULL DEFAULT 0,
            cc_cost             REAL,
            FOREIGN KEY (current_law_id) 
            REFERENCES laws(document_id) 
                ON UPDATE RESTRICT
                ON DELETE RESTRICT,
            FOREIGN KEY (proposed_law_id) 
            REFERENCES laws(document_id) 
                ON UPDATE RESTRICT
                ON DELETE RESTRICT
        );
        """
    )
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_app_session_id ON sessions(app_session_id)"
    )
    _create_users_table(cur)
    _ensure_column(cur, "laws", "owner_user_id", "INTEGER REFERENCES users(user_id)")
    _ensure_column(cur, "laws", "is_builtin", "INTEGER NOT NULL DEFAULT 0")
    cur.execute("UPDATE laws SET is_builtin = 0 WHERE owner_user_id IS NULL")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_laws_owner_file ON laws(owner_user_id, file_name)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_laws_builtin_file ON laws(is_builtin, file_name)"
    )
    # Migration-only: add the ownership column to legacy/dev session tables.
    _ensure_column(cur, "sessions", "owner_user_id", "INTEGER REFERENCES users(user_id)")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_sessions_owner ON sessions(owner_user_id)"
    )
    _create_session_activities_table(cur)
    _create_session_total_costs_by_addressee_table(cur)
    _create_session_pay_rate_overrides_by_addressee_table(cur)
    _create_compliance_text_examples_table(cur)
    _create_compliance_text_exports_table(cur)
    _seed_compliance_text_examples(cur)
    _seed_builtin_laws(cur)
    _create_deep_research_runs_table(cur)
    _create_session_scoped_tile_tables(cur)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS web_sources_sessions (
            source_id           INTEGER PRIMARY KEY,
            session_id             INTEGER NOT NULL,
            exact_url           TEXT NOT NULL,
            direct_quote        TEXT NOT NULL,
            accessed_at         TEXT NOT NULL,
            url_validation      TEXT,
            quote_validation    TEXT,
            validated_at        TEXT,
            FOREIGN KEY (session_id)
            REFERENCES sessions (session_id) 
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_answers (
            answer_id       INTEGER PRIMARY KEY,
            session_id      INTEGER NOT NULL,
            prompt_id       TEXT NOT NULL,
            model           TEXT NOT NULL,
            answer_text     TEXT NOT NULL,
            prompt_text     TEXT,
            metadata        JSON,
            input_tokens    INTEGER,
            output_tokens   INTEGER,
            hidden_thinking_tokens INTEGER,
            estimated_cost_usd REAL,
            provider_response_json JSON,
            answer_state    TEXT NOT NULL DEFAULT 'active',
            state_reason    TEXT,
            created_at      TEXT NOT NULL DEFAULT current_timestamp,
            FOREIGN KEY (session_id)
            REFERENCES sessions (session_id) 
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        """
    )
    # NOTE: edit_audit_log is persisted for now to support cross-restart debugging.
    # This can be switched to temporary/in-memory only if long-term audit history
    # is not required in production.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS edit_audit_log (
            audit_id     INTEGER PRIMARY KEY,
            session_id   INTEGER NOT NULL,
            entity_type  TEXT NOT NULL,
            entity_id    INTEGER,
            field_name   TEXT NOT NULL,
            old_value    TEXT,
            new_value    TEXT,
            edited_at    TEXT NOT NULL DEFAULT current_timestamp,
            FOREIGN KEY (session_id)
            REFERENCES sessions (session_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_edit_audit_log_session_time
        ON edit_audit_log (session_id, edited_at DESC, audit_id DESC)
        """
    )
    # TODO: Maybe add llm_generated, edited, deleted, legal_citation_original, description_original
    # TODO: How to handle deletion of regulation for processes?
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS regulations (
            regulation_id   INTEGER PRIMARY KEY,
            process_id      INTEGER,
            session_id      INTEGER NOT NULL,
            legal_citation  TEXT NOT NULL,
            description     TEXT NOT NULL,
            change_status   TEXT NOT NULL,
            created_at      TEXT NOT NULL DEFAULT current_timestamp,
            FOREIGN KEY (session_id)
            REFERENCES sessions (session_id) 
                ON UPDATE CASCADE
                ON DELETE CASCADE,
            FOREIGN KEY (process_id)
            REFERENCES processes
                ON UPDATE CASCADE
                ON DELETE SET NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS web_sources_regulations (
            source_id           INTEGER PRIMARY KEY,
            regulation_id       INTEGER NOT NULL,
            exact_url           TEXT NOT NULL,
            direct_quote        TEXT NOT NULL,
            accessed_at         TEXT NOT NULL,
            url_validation      TEXT,
            quote_validation    TEXT,
            validated_at        TEXT,
            FOREIGN KEY (regulation_id)
            REFERENCES regulations (regulation_id) 
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        """
    )
    # TODO: many-to-one relationship of regulations-to-processes: if a regulation
    #  is linked to two processes, an error is thrown. Implement re-answering by llm?
    _create_processes_table(cur)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS web_sources_processes (
            source_id           INTEGER PRIMARY KEY,
            process_id          INTEGER NOT NULL,
            exact_url           TEXT NOT NULL,
            direct_quote        TEXT NOT NULL,
            accessed_at         TEXT NOT NULL,
            url_validation      TEXT,
            quote_validation    TEXT,
            validated_at        TEXT,
            FOREIGN KEY (process_id)
            REFERENCES processes (process_id) 
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        """
    )
    _create_case_groups_table(cur)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS web_sources_case_groups (
            source_id           INTEGER PRIMARY KEY,
            case_group_id       INTEGER NOT NULL,
            exact_url           TEXT NOT NULL,
            direct_quote        TEXT NOT NULL,
            accessed_at         TEXT NOT NULL,
            url_validation      TEXT,
            quote_validation    TEXT,
            validated_at        TEXT,
            FOREIGN KEY (case_group_id)
            REFERENCES case_groups (case_group_id) 
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        """
    )
    # TODO: Handle list insertion, possibly change to position list instead of linked list? Does it need to be doubly linked? Single just seems easier.
    # TODO: Change prozessschritt mit tätigkeiten?
    _create_process_steps_table(cur)
    # Row-based personnel-effort child table + row-keyed session wage overrides.
    # Created after process_steps so the step_id foreign key resolves.
    _create_process_step_personnel_effort_table(cur)
    _create_session_wage_rate_overrides_table(cur)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS web_sources_process_steps (
            source_id           INTEGER PRIMARY KEY,
            step_id             INTEGER NOT NULL,
            exact_url           TEXT NOT NULL,
            direct_quote        TEXT NOT NULL,
            accessed_at         TEXT NOT NULL,
            url_validation      TEXT,
            quote_validation    TEXT,
            validated_at        TEXT,
            FOREIGN KEY (step_id)
            REFERENCES process_steps (step_id) 
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        """
    )
    _ensure_columns(
        cur,
        "regulations",
        {
            "applies_to_administration": "INTEGER NOT NULL DEFAULT 1 CHECK (applies_to_administration IN (0, 1))",
            "applies_to_business": "INTEGER NOT NULL DEFAULT 0 CHECK (applies_to_business IN (0, 1))",
            "applies_to_citizens": "INTEGER NOT NULL DEFAULT 0 CHECK (applies_to_citizens IN (0, 1))",
            "is_business_information_obligation": "INTEGER NOT NULL DEFAULT 0 CHECK (is_business_information_obligation IN (0, 1))",
        },
    )
    _ensure_columns(
        cur,
        "processes",
        {
            "norm_addressee": "TEXT NOT NULL DEFAULT 'administration'",
        },
    )
    _ensure_columns(
        cur,
        "case_groups",
        {
            "norm_addressee": "TEXT NOT NULL DEFAULT 'administration'",
        },
    )
    _ensure_columns(
        cur,
        "process_steps",
        {
            "norm_addressee": "TEXT NOT NULL DEFAULT 'administration'",
        },
    )
    _create_regulation_process_links_by_addressee_table(cur)
    _create_process_step_regulation_links_table(cur)
    _run_legacy_migrations(cur)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_current_law_id ON sessions(current_law_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_proposed_law_id ON sessions(proposed_law_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_regulations_session_id ON regulations(session_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_regulations_process_id ON regulations(process_id)")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_process_step_regulation_links_session_addressee_step ON process_step_regulation_links(session_id, norm_addressee, step_id)"
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_processes_session_id ON processes(session_id)")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_processes_session_addressee ON processes(session_id, norm_addressee)"
    )
    _create_parent_composite_indexes(cur)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_case_groups_process_id ON case_groups(process_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_case_groups_session_id ON case_groups(session_id)")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_case_groups_session_addressee ON case_groups(session_id, norm_addressee)"
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_process_steps_case_group_id ON process_steps(case_group_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_process_steps_session_id ON process_steps(session_id)")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_process_steps_session_addressee ON process_steps(session_id, norm_addressee)"
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ws_sessions_session_id ON web_sources_sessions(session_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_llm_answers_session_id ON llm_answers(session_id)")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_answers_session_prompt ON llm_answers(session_id, prompt_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_answers_state ON llm_answers(answer_state)"
    )
    # Keep at most one active answer per (session_id, prompt_id, norm_addressee).
    # Normadressaten-spezifische Prompts (z.B. cases_calculation, effort_calculation)
    # muessen pro Adressat einen eigenen aktiven Answer halten koennen - sonst
    # verdraengt ein spaeterer Business-Lauf den zuvor gespeicherten
    # Verwaltungs-Answer und die Fallzahlen/Effort-Werte der Verwaltung gehen
    # verloren. COALESCE(norm_addressee, '') sorgt dafuer, dass auch NULL-Werte
    # (z.B. law_summary) deterministisch verglichen werden.
    cur.execute("DROP INDEX IF EXISTS idx_llm_answers_one_active")
    cur.execute(
        """
        UPDATE llm_answers
        SET answer_state = 'invalid',
            state_reason = COALESCE(state_reason, 'superseded_by_new_attempt')
        WHERE answer_state = 'active'
          AND answer_id NOT IN (
            SELECT MAX(answer_id)
            FROM llm_answers
            WHERE answer_state = 'active'
            GROUP BY session_id, prompt_id, COALESCE(norm_addressee, '')
          )
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_llm_answers_one_active
        ON llm_answers(session_id, prompt_id, COALESCE(norm_addressee, ''))
        WHERE answer_state = 'active'
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ws_regulations_regulation_id ON web_sources_regulations(regulation_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ws_processes_process_id ON web_sources_processes(process_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ws_case_groups_case_group_id ON web_sources_case_groups(case_group_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ws_process_steps_step_id ON web_sources_process_steps(step_id)")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_regulation_process_links_addressee ON regulation_process_links_by_addressee(session_id, norm_addressee)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_tiles_session_addressee ON tiles(session_id, norm_addressee)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_links_session_addressee_target ON links(session_id, norm_addressee, target)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_links_session_addressee_source ON links(session_id, norm_addressee, source)"
    )
    _migrate_tile_tables_to_norm_addressee(cur)
    _create_used_models_triggers(cur)
    _create_citizens_hourly_rate_triggers(cur)
    _create_session_cc_cost_triggers(cur)
    # One-time, idempotent backfill of legacy slot effort into the row model so
    # the cost engine can stop reading slot columns (Phase D2). Runs after all
    # schema is ensured; a no-op on fresh/already-migrated databases.
    _backfill_process_step_personnel_effort(cur)
    _maybe_commit(conn)
    _maybe_close(conn)


def ensure_db() -> None:
    init_db()
    conn = get_conn()
    _maybe_close(conn)


def fetch_tiles(session_id: int, norm_addressee: str = ADMINISTRATION) -> List[Tile]:
    resolved_session_id = int(session_id)
    resolved_addressee = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM tiles
        WHERE session_id = ? AND norm_addressee = ?
        """,
        (resolved_session_id, resolved_addressee),
    )
    tiles: List[Tile] = []
    for row in cur.fetchall():
        tile_id = row["id"]
        cur_links = conn.execute(
            """
            SELECT source
            FROM links
            WHERE session_id = ? AND norm_addressee = ? AND target = ?
            """,
            (resolved_session_id, resolved_addressee, tile_id),
        ).fetchall()
        tiles.append(
            Tile(
                id=tile_id,
                title=row["title"],
                text=row["text"],
                meta_information=json.loads(row["meta"] or "{}"),
                column=row["col"],
                row=row["row"],
                deletable=bool(row["deletable"]),
                link_from_tile=[r["source"] for r in cur_links],
            )
        )
    _maybe_close(conn)
    return tiles


def list_law_file_names(owner_user_id: int | None = None) -> List[str]:
    conn = get_conn()
    cur = conn.cursor()
    if owner_user_id is None:
        cur.execute(
            """
            SELECT file_name, MAX(uploaded_at) AS uploaded_at, MAX(document_id) AS document_id
            FROM laws
            GROUP BY file_name
            ORDER BY uploaded_at DESC, document_id DESC
            """
        )
    else:
        cur.execute(
            """
            SELECT
                file_name,
                MAX(is_builtin) AS builtin_rank,
                MAX(uploaded_at) AS uploaded_at,
                MAX(document_id) AS document_id
            FROM laws
            WHERE is_builtin = 1 OR owner_user_id = ?
            GROUP BY file_name
            ORDER BY builtin_rank DESC, uploaded_at DESC, document_id DESC
            """,
            (int(owner_user_id),),
        )
    names = [row["file_name"] for row in cur.fetchall()]
    _maybe_close(conn)
    return names


def get_law_by_filename(
    file_name: str,
    owner_user_id: int | None = None,
) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    if owner_user_id is None:
        cur.execute(
            """
            SELECT document_id, file_name, law_text, text_length, uploaded_at,
                   owner_user_id, is_builtin
            FROM laws
            WHERE file_name = ?
            ORDER BY is_builtin DESC, uploaded_at DESC, document_id DESC
            LIMIT 1
            """,
            (file_name,),
        )
    else:
        cur.execute(
            """
            SELECT document_id, file_name, law_text, text_length, uploaded_at,
                   owner_user_id, is_builtin
            FROM laws
            WHERE file_name = ?
              AND (is_builtin = 1 OR owner_user_id = ?)
            ORDER BY is_builtin DESC, owner_user_id DESC, uploaded_at DESC, document_id DESC
            LIMIT 1
            """,
            (file_name, int(owner_user_id)),
        )
    row = cur.fetchone()
    _maybe_close(conn)
    if row is None:
        return None
    return dict(row)


def get_law_by_id(document_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT document_id, file_name, law_text, text_length, uploaded_at,
               owner_user_id, is_builtin
        FROM laws
        WHERE document_id = ?
        LIMIT 1
        """,
        (document_id,),
    )
    row = cur.fetchone()
    _maybe_close(conn)
    if row is None:
        return None
    return dict(row)


def insert_law(
    file_name: str,
    law_text: str,
    owner_user_id: int | None = None,
    is_builtin: bool = False,
) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO laws (file_name, law_text, text_length, owner_user_id, is_builtin)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            file_name,
            law_text,
            len(law_text),
            None if is_builtin else owner_user_id,
            int(bool(is_builtin)),
        ),
    )
    _maybe_commit(conn)
    document_id = int(cur.lastrowid)
    _maybe_close(conn)
    return document_id


def get_session_by_app_id(app_session_id: str) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM sessions
        WHERE app_session_id = ?
        """,
        (app_session_id,),
    )
    row = cur.fetchone()
    _maybe_close(conn)
    if row is None:
        return None
    return dict(row)


def get_session_by_id(session_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM sessions
        WHERE session_id = ?
        LIMIT 1
        """,
        (session_id,),
    )
    row = cur.fetchone()
    _maybe_close(conn)
    if row is None:
        return None
    return dict(row)


def _activity_row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def purge_expired_session_activity(session_id: int | None = None) -> int:
    conn = get_conn()
    cur = conn.cursor()
    now = time.time()
    if session_id is None:
        params = (now,)
        cur.execute(
            """
            SELECT session_id, activity_id, activity_type, label, created_at, updated_at, expires_at
            FROM session_activities
            WHERE expires_at IS NOT NULL AND expires_at <= ?
            """,
            params,
        )
        expired_rows = cur.fetchall()
        cur.execute(
            """
            DELETE FROM session_activities
            WHERE expires_at IS NOT NULL AND expires_at <= ?
            """,
            params,
        )
    else:
        params = (int(session_id), now)
        cur.execute(
            """
            SELECT session_id, activity_id, activity_type, label, created_at, updated_at, expires_at
            FROM session_activities
            WHERE session_id = ?
              AND expires_at IS NOT NULL
              AND expires_at <= ?
            """,
            params,
        )
        expired_rows = cur.fetchall()
        cur.execute(
            """
            DELETE FROM session_activities
            WHERE session_id = ?
              AND expires_at IS NOT NULL
              AND expires_at <= ?
            """,
            params,
        )
    deleted = len(expired_rows)
    for row in expired_rows:
        logger.warning(
            "Purged expired session activity | session=%s activity=%s type=%s label=%s "
            "created_at=%s updated_at=%s expires_at=%s",
            row["session_id"],
            row["activity_id"],
            row["activity_type"],
            row["label"],
            row["created_at"],
            row["updated_at"],
            row["expires_at"],
        )
    _maybe_commit(conn)
    _maybe_close(conn)
    return deleted


def get_session_activity(session_id: int) -> dict | None:
    purge_expired_session_activity(session_id)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT session_id, activity_id, activity_type, label, created_at, updated_at, expires_at
        FROM session_activities
        WHERE session_id = ?
        LIMIT 1
        """,
        (int(session_id),),
    )
    row = cur.fetchone()
    _maybe_close(conn)
    return _activity_row_to_dict(row)


def begin_session_activity(
    *,
    session_id: int,
    activity_id: str,
    activity_type: str,
    label: str,
    ttl_seconds: float | None = None,
) -> tuple[dict | None, dict | None]:
    purge_expired_session_activity(session_id)
    conn = get_conn()
    cur = conn.cursor()
    now = time.time()
    expires_at = None if ttl_seconds is None else now + float(ttl_seconds)
    try:
        cur.execute(
            """
            INSERT INTO session_activities (
                session_id, activity_id, activity_type, label,
                created_at, updated_at, expires_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (int(session_id), activity_id, activity_type, label, now, now, expires_at),
        )
        _maybe_commit(conn)
    except sqlite3.IntegrityError:
        _maybe_close(conn)
        return None, get_session_activity(session_id)
    activity = get_session_activity(session_id)
    _maybe_close(conn)
    return activity, None


def refresh_session_activity(
    *,
    session_id: int,
    activity_id: str,
    ttl_seconds: float,
) -> dict | None:
    purge_expired_session_activity(session_id)
    conn = get_conn()
    cur = conn.cursor()
    now = time.time()
    cur.execute(
        """
        UPDATE session_activities
        SET updated_at = ?, expires_at = ?
        WHERE session_id = ? AND activity_id = ?
        """,
        (now, now + float(ttl_seconds), int(session_id), activity_id),
    )
    updated = int(cur.rowcount or 0)
    _maybe_commit(conn)
    _maybe_close(conn)
    if updated == 0:
        return None
    return get_session_activity(session_id)


def clear_session_activity(session_id: int, activity_id: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM session_activities
        WHERE session_id = ? AND activity_id = ?
        """,
        (int(session_id), activity_id),
    )
    deleted = int(cur.rowcount or 0) > 0
    _maybe_commit(conn)
    _maybe_close(conn)
    return deleted


def clear_all_session_activities() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM session_activities")
    deleted = int(cur.rowcount or 0)
    _maybe_commit(conn)
    _maybe_close(conn)
    return deleted


def get_session_law_texts(session_id: int) -> tuple[str, str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT current_law_id, proposed_law_id
        FROM sessions
        WHERE session_id = ?
        LIMIT 1
        """,
        (session_id,),
    )
    row = cur.fetchone()
    _maybe_close(conn)
    if row is None:
        return "", ""

    current_text = ""
    proposed_text = ""

    current_law_id = row["current_law_id"]
    if current_law_id is not None:
        current_law = get_law_by_id(int(current_law_id))
        if current_law is not None:
            current_text = str(current_law.get("law_text", "")).strip()

    proposed_law_id = row["proposed_law_id"]
    if proposed_law_id is not None:
        proposed_law = get_law_by_id(int(proposed_law_id))
        if proposed_law is not None:
            proposed_text = str(proposed_law.get("law_text", "")).strip()

    return current_text, proposed_text


def get_latest_session() -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM sessions
        ORDER BY created_at DESC, session_id DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    _maybe_close(conn)
    if row is None:
        return None
    return dict(row)


def list_sessions(limit: int = 50, owner_user_id: int | None = None) -> List[dict]:
    conn = get_conn()
    cur = conn.cursor()
    where = ""
    params: list = []
    if owner_user_id is not None:
        where = "WHERE s.owner_user_id = ?"
        params.append(int(owner_user_id))
    params.append(limit)
    cur.execute(
        f"""
        SELECT
            s.app_session_id,
            s.created_at,
            s.llm_model,
            s.used_llm_models,
            s.case_group_research_enabled
        FROM sessions AS s
        {where}
        ORDER BY s.created_at DESC, s.session_id DESC
        LIMIT ?
        """,
        tuple(params),
    )
    rows = [dict(row) for row in cur.fetchall()]
    _maybe_close(conn)
    return rows


def _row_to_user_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    data = dict(row)
    data["is_admin"] = bool(data.get("is_admin"))
    data["is_active"] = bool(data.get("is_active"))
    return data


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ? LIMIT 1", (int(user_id),))
    row = cur.fetchone()
    _maybe_close(conn)
    return _row_to_user_dict(row)


def get_user_by_email(email: str) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM users WHERE lower(email) = lower(?) LIMIT 1",
        (str(email).strip(),),
    )
    row = cur.fetchone()
    _maybe_close(conn)
    return _row_to_user_dict(row)


def list_users() -> List[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY user_id ASC")
    rows = [_row_to_user_dict(row) for row in cur.fetchall()]
    _maybe_close(conn)
    return [row for row in rows if row is not None]


def count_admins() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM users WHERE is_admin = 1 AND is_active = 1")
    row = cur.fetchone()
    _maybe_close(conn)
    return int(row["n"]) if row else 0


def create_user(
    email: str,
    password_hash: str,
    *,
    is_admin: bool = False,
    is_active: bool = True,
) -> dict:
    normalized_email = str(email).strip()
    if not normalized_email:
        raise ValueError("Email is required")
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO users (email, password_hash, is_admin, is_active)
            VALUES (?, ?, ?, ?)
            """,
            (normalized_email, password_hash, int(is_admin), int(is_active)),
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError("A user with this email already exists") from exc
    user_id = int(cur.lastrowid)
    _maybe_commit(conn)
    created = get_user_by_id(user_id)
    assert created is not None
    return created


def update_user(
    user_id: int,
    *,
    password_hash: str | None = None,
    is_active: bool | None = None,
    is_admin: bool | None = None,
) -> dict | None:
    fields: list[str] = []
    params: list = []
    if password_hash is not None:
        fields.append("password_hash = ?")
        params.append(password_hash)
    if is_active is not None:
        fields.append("is_active = ?")
        params.append(int(is_active))
    if is_admin is not None:
        fields.append("is_admin = ?")
        params.append(int(is_admin))
    if not fields:
        return get_user_by_id(user_id)
    params.append(int(user_id))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?", tuple(params))
    _maybe_commit(conn)
    return get_user_by_id(user_id)


def create_owned_session(owner_user_id: int, llm_model: str) -> tuple[str, int]:
    """Create a new session owned by the given user with a server-generated id."""
    if not str(llm_model or "").strip():
        raise ValueError("Model is required for new session")
    for _ in range(5):
        app_session_id = "".join(
            secrets.choice(CROCKFORD_BASE32_ALPHABET)
            for _ in range(APP_SESSION_ID_LENGTH)
        )
        if get_session_by_app_id(app_session_id) is not None:
            continue
        session_id, _created = upsert_session(
            app_session_id, llm_model, owner_user_id=int(owner_user_id)
        )
        return app_session_id, session_id
    raise RuntimeError("Could not allocate a unique app_session_id")


def get_case_group_research_enabled(session_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT case_group_research_enabled
        FROM sessions
        WHERE session_id = ?
        LIMIT 1
        """,
        (session_id,),
    )
    row = cur.fetchone()
    _maybe_close(conn)
    return bool(row and row["case_group_research_enabled"])


def update_case_group_research_enabled(session_id: int, enabled: bool) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE sessions
        SET case_group_research_enabled = ?
        WHERE session_id = ?
          AND COALESCE(case_group_research_enabled, 0) != ?
        """,
        (1 if enabled else 0, session_id, 1 if enabled else 0),
    )
    changed = cur.rowcount > 0
    _maybe_commit(conn)
    _maybe_close(conn)
    return changed


def create_deep_research_run(
    *,
    session_id: int,
    purpose: str,
    agent: str,
    provider: str = "gemini",
    prompt_text: str | None = None,
    status: str = "idle",
) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO deep_research_runs (
            session_id,
            purpose,
            provider,
            agent,
            status,
            prompt_text,
            started_at
        )
        VALUES (?, ?, ?, ?, ?, ?, CASE WHEN ? = 'running' THEN current_timestamp ELSE NULL END)
        """,
        (session_id, purpose, provider, agent, status, prompt_text, status),
    )
    _maybe_commit(conn)
    research_run_id = int(cur.lastrowid)
    _maybe_close(conn)
    return research_run_id


def update_deep_research_run(
    research_run_id: int,
    *,
    status: str | None = None,
    agent: str | None = None,
    interaction_id: str | None = None,
    report_md: str | None = None,
    result_json: dict | list | None = None,
    response_json: dict | list | None = None,
    error: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    thought_tokens: int | None = None,
    total_tokens: int | None = None,
    estimated_cost_usd: float | None = None,
) -> None:
    assignments: list[str] = []
    values: list[object] = []
    if status is not None:
        assignments.append("status = ?")
        values.append(status)
        if status == "running":
            assignments.append("started_at = COALESCE(started_at, current_timestamp)")
        if status in {"completed", "failed", "cancelled", "cancelled_harvested"}:
            assignments.append("completed_at = COALESCE(completed_at, current_timestamp)")
        if status == "parsed":
            assignments.append("parsed_at = COALESCE(parsed_at, current_timestamp)")
            assignments.append("completed_at = COALESCE(completed_at, current_timestamp)")
    for column, value in (
        ("agent", agent),
        ("interaction_id", interaction_id),
        ("report_md", report_md),
        ("error", error),
        ("input_tokens", input_tokens),
        ("output_tokens", output_tokens),
        ("thought_tokens", thought_tokens),
        ("total_tokens", total_tokens),
        ("estimated_cost_usd", estimated_cost_usd),
    ):
        if value is not None:
            assignments.append(f"{column} = ?")
            values.append(value)
    if result_json is not None:
        assignments.append("result_json = ?")
        values.append(json.dumps(result_json, ensure_ascii=False))
    if response_json is not None:
        assignments.append("response_json = ?")
        values.append(json.dumps(response_json, ensure_ascii=False))
    if not assignments:
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f"""
        UPDATE deep_research_runs
        SET {", ".join(assignments)}
        WHERE research_run_id = ?
        """,
        (*values, research_run_id),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def get_latest_deep_research_run(
    session_id: int,
    purpose: str,
) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM deep_research_runs
        WHERE session_id = ? AND purpose = ?
        ORDER BY research_run_id DESC
        LIMIT 1
        """,
        (session_id, purpose),
    )
    row = cur.fetchone()
    _maybe_close(conn)
    if row is None:
        return None
    return dict(row)


def get_deep_research_run(research_run_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM deep_research_runs
        WHERE research_run_id = ?
        """,
        (research_run_id,),
    )
    row = cur.fetchone()
    _maybe_close(conn)
    return dict(row) if row else None


def get_latest_deep_research_run_status(session_id: int, purpose: str) -> str:
    run = get_latest_deep_research_run(session_id, purpose)
    return str(run.get("status") or "idle") if run else "idle"


def list_compliance_text_examples(limit: int = 3) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    _create_compliance_text_examples_table(cur)
    cur.execute(
        """
        SELECT example_id, slug, title, body_md, sort_order, source_path, updated_at
        FROM compliance_text_examples
        ORDER BY sort_order, example_id
        LIMIT ?
        """,
        (max(1, min(limit, 20)),),
    )
    rows = [dict(row) for row in cur.fetchall()]
    _maybe_close(conn)
    return rows


def get_latest_compliance_text_export(
    session_id: int,
    source_snapshot_sha256: str,
    user_edit_policy: str,
) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    _create_compliance_text_exports_table(cur)
    cur.execute(
        """
        SELECT *
        FROM compliance_text_exports
        WHERE session_id = ?
          AND source_snapshot_sha256 = ?
          AND user_edit_policy = ?
          AND status = 'succeeded'
        ORDER BY export_id DESC
        LIMIT 1
        """,
        (session_id, source_snapshot_sha256, user_edit_policy),
    )
    row = cur.fetchone()
    _maybe_close(conn)
    return dict(row) if row else None


def insert_compliance_text_export(
    *,
    session_id: int,
    llm_answer_id: int | None,
    status: str,
    model: str | None,
    provider: str | None,
    prompt_text: str | None,
    generated_markdown: str,
    source_snapshot_json: dict | list,
    source_snapshot_sha256: str,
    used_deep_research: bool,
    deep_research_run_id: int | None,
    used_user_edits: bool,
    user_edit_policy: str,
    metadata_json: dict | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    hidden_thinking_tokens: int | None = None,
    estimated_cost_usd: float | None = None,
) -> int:
    conn = get_conn()
    cur = conn.cursor()
    _create_compliance_text_exports_table(cur)
    cur.execute(
        """
        INSERT INTO compliance_text_exports (
            session_id,
            llm_answer_id,
            status,
            model,
            provider,
            prompt_text,
            generated_markdown,
            source_snapshot_json,
            source_snapshot_sha256,
            used_deep_research,
            deep_research_run_id,
            used_user_edits,
            user_edit_policy,
            metadata_json,
            input_tokens,
            output_tokens,
            hidden_thinking_tokens,
            estimated_cost_usd
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            llm_answer_id,
            status,
            model,
            provider,
            prompt_text,
            generated_markdown,
            json.dumps(source_snapshot_json, ensure_ascii=False),
            source_snapshot_sha256,
            int(bool(used_deep_research)),
            deep_research_run_id,
            int(bool(used_user_edits)),
            user_edit_policy,
            json.dumps(metadata_json, ensure_ascii=False) if metadata_json is not None else None,
            input_tokens,
            output_tokens,
            hidden_thinking_tokens,
            estimated_cost_usd,
        ),
    )
    export_id = int(cur.lastrowid)
    _maybe_commit(conn)
    _maybe_close(conn)
    return export_id


def get_latest_deep_research_run_elapsed_seconds(
    session_id: int,
    purpose: str,
) -> int | None:
    run = get_latest_deep_research_run(session_id, purpose)
    if not run or not run.get("started_at"):
        return None
    completed_at = run.get("completed_at")
    try:
        started = datetime.fromisoformat(str(run["started_at"]).replace(" ", "T"))
        completed = (
            datetime.fromisoformat(str(completed_at).replace(" ", "T"))
            if completed_at
            else datetime.utcnow()
        )
    except ValueError:
        return None
    return max(0, int((completed - started).total_seconds()))


def _elapsed_ms_between(started_at: object, completed_at: object) -> int | None:
    if not started_at or not completed_at:
        return None
    try:
        started = datetime.fromisoformat(str(started_at).replace(" ", "T"))
        completed = datetime.fromisoformat(str(completed_at).replace(" ", "T"))
    except ValueError:
        return None
    elapsed = int((completed - started).total_seconds() * 1000)
    return max(elapsed, 0)


def list_recent_deep_research_monitor_rows_for_session(
    session_id: int,
    limit: int = 80,
) -> list[dict]:
    safe_limit = max(1, min(limit, 500))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            research_run_id,
            purpose,
            provider,
            agent,
            status,
            error,
            input_tokens,
            output_tokens,
            thought_tokens,
            estimated_cost_usd,
            created_at,
            started_at,
            completed_at,
            parsed_at
        FROM deep_research_runs
        WHERE session_id = ? AND purpose = 'case_group_metrics'
        ORDER BY research_run_id DESC
        LIMIT ?
        """,
        (session_id, safe_limit),
    )
    rows = [dict(row) for row in cur.fetchall()]
    _maybe_close(conn)

    normalized: list[dict] = []
    for row in rows:
        status = str(row.get("status") or "")
        if status == "running":
            answer_state = LLM_ANSWER_STATE_PENDING
            state_reason = "querying"
        elif status == "parsed":
            answer_state = LLM_ANSWER_STATE_ACTIVE
            state_reason = "session_updated"
        elif status == "completed":
            answer_state = LLM_ANSWER_STATE_PENDING
            state_reason = "waiting_for_session_update"
        else:
            answer_state = LLM_ANSWER_STATE_INVALID
            state_reason = status or "deep_research_failed"
        completed_at = row.get("parsed_at") or row.get("completed_at")
        elapsed_ms = (
            _elapsed_ms_between(row.get("started_at"), completed_at)
            if completed_at
            else None
        )
        normalized.append(
            {
                "answer_id": None,
                "prompt_id": "deep_research_case_group_metrics",
                "model": str(row.get("agent") or ""),
                "provider": str(row.get("provider") or "gemini"),
                "attempt_id": f"deep_research:{row.get('research_run_id')}",
                "request_id": None,
                "route_method": None,
                "route_path": None,
                "elapsed_ms": elapsed_ms,
                "answer_state": answer_state,
                "state_reason": state_reason,
                "input_tokens": row.get("input_tokens"),
                "output_tokens": row.get("output_tokens"),
                "hidden_thinking_tokens": row.get("thought_tokens"),
                "estimated_cost_usd": row.get("estimated_cost_usd"),
                "error_kind": (
                    status if status in {"failed", "cancelled", "cancelled_harvested"} else None
                ),
                "error_status_code": None,
                "error": row.get("error"),
                "created_at": completed_at or row.get("created_at"),
            }
        )
    return normalized


def clear_case_group_research(session_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM deep_research_runs
        WHERE session_id = ? AND purpose = 'case_group_metrics'
        """,
        (session_id,),
    )
    cur.execute(
        """
        UPDATE case_groups
        SET addressees_current = NULL,
            annual_frequency_current = NULL,
            cases_current = NULL,
            addressees_proposed = NULL,
            annual_frequency_proposed = NULL,
            cases_proposed = NULL,
            case_metric_research_json = NULL
        WHERE session_id = ?
        """,
        (session_id,),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def list_edit_audit_for_session(session_id: int, limit: int = 200) -> List[dict]:
    # NOTE: Reads persisted edit_audit_log rows. If audit logging is later made
    # temporary/dev-only, this function is one primary integration point to adapt.
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            audit_id,
            session_id,
            entity_type,
            entity_id,
            field_name,
            old_value,
            new_value,
            edited_at
        FROM edit_audit_log
        WHERE session_id = ?
        ORDER BY audit_id DESC
        LIMIT ?
        """,
        (session_id, limit),
    )
    rows = [dict(row) for row in cur.fetchall()]
    _maybe_close(conn)
    return rows


def get_session_status(app_session_id: str) -> dict | None:
    session = get_session_by_app_id(app_session_id)
    if not session:
        return None
    session_id = int(session["session_id"])
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS count FROM regulations WHERE session_id = ?", (session_id,))
    regulations_count = int(cur.fetchone()["count"])
    regulations_present_by_addressee = {
        addressee: has_applicable_regulations_for_addressee(session_id, addressee)
        for addressee in ALL_NORM_ADDRESSEES
    }
    no_process_path_by_addressee = {
        addressee: has_no_process_path_for_addressee(session_id, addressee)
        for addressee in ALL_NORM_ADDRESSEES
    }
    processes_ready_by_addressee: dict[str, bool] = {}
    case_groups_ready_by_addressee: dict[str, bool] = {}
    process_steps_ready_by_addressee: dict[str, bool] = {}
    for addressee in ALL_NORM_ADDRESSEES:
        addressee_is_skippable = (
            regulations_count > 0 and not regulations_present_by_addressee[addressee]
        ) or no_process_path_by_addressee[addressee]
        cur.execute(
            "SELECT COUNT(*) AS count FROM processes WHERE session_id = ? AND norm_addressee = ?",
            (session_id, addressee),
        )
        processes_ready_by_addressee[addressee] = (
            int(cur.fetchone()["count"]) > 0 or addressee_is_skippable
        )
        cur.execute(
            "SELECT COUNT(*) AS count FROM case_groups WHERE session_id = ? AND norm_addressee = ?",
            (session_id, addressee),
        )
        case_groups_ready_by_addressee[addressee] = (
            int(cur.fetchone()["count"]) > 0 or addressee_is_skippable
        )
        cur.execute(
            "SELECT COUNT(*) AS count FROM process_steps WHERE session_id = ? AND norm_addressee = ?",
            (session_id, addressee),
        )
        process_steps_ready_by_addressee[addressee] = (
            int(cur.fetchone()["count"]) > 0 or addressee_is_skippable
        )
    _maybe_close(conn)
    summary_ready = bool(
        session.get("law_diff_title")
        or session.get("law_diff_blurb")
        or session.get("law_diff_summary")
        or session.get("current_law_id")
        or session.get("proposed_law_id")
    )
    case_group_research_enabled = bool(session.get("case_group_research_enabled"))
    case_group_research_status = get_latest_deep_research_run_status(
        session_id,
        "case_group_metrics",
    )
    case_group_research_ready = (
        not case_group_research_enabled or case_group_research_status == "parsed"
    )
    effort_ready_by_addressee = {}
    for addressee in ALL_NORM_ADDRESSEES:
        addressee_is_skippable = (
            regulations_count > 0 and not regulations_present_by_addressee[addressee]
        ) or no_process_path_by_addressee[addressee]
        effort_ready_by_addressee[addressee] = addressee_is_skippable or (
            has_effort_metrics(session_id, addressee) and case_group_research_ready
        )
    total_cost_ready_by_addressee = {
        addressee: (
            has_total_cost_for_addressee(session_id, addressee)
            or (regulations_count > 0 and not regulations_present_by_addressee[addressee])
            or no_process_path_by_addressee[addressee]
        )
        for addressee in ALL_NORM_ADDRESSEES
    }
    return {
        "summary_ready": summary_ready,
        "regulations_ready": regulations_count > 0,
        "regulations_present_by_addressee": regulations_present_by_addressee,
        "processes_ready": all(
            processes_ready_by_addressee[addressee]
            for addressee in SUPPORTED_NORM_ADDRESSEES
        ),
        "case_groups_ready": all(
            case_groups_ready_by_addressee[addressee]
            for addressee in SUPPORTED_NORM_ADDRESSEES
        ),
        "process_steps_ready": all(
            process_steps_ready_by_addressee[addressee]
            for addressee in SUPPORTED_NORM_ADDRESSEES
        ),
        "processes_ready_by_addressee": processes_ready_by_addressee,
        "case_groups_ready_by_addressee": case_groups_ready_by_addressee,
        "process_steps_ready_by_addressee": process_steps_ready_by_addressee,
        "effort_ready": all(
            effort_ready_by_addressee[addressee]
            for addressee in SUPPORTED_NORM_ADDRESSEES
        ),
        "total_cost_ready": all(
            total_cost_ready_by_addressee[addressee]
            for addressee in SUPPORTED_NORM_ADDRESSEES
        ),
        "effort_ready_by_addressee": effort_ready_by_addressee,
        "total_cost_ready_by_addressee": total_cost_ready_by_addressee,
        "case_group_research_enabled": case_group_research_enabled,
        "case_group_research_status": case_group_research_status,
        "case_group_research_elapsed_seconds": get_latest_deep_research_run_elapsed_seconds(
            session_id,
            "case_group_metrics",
        ),
    }


def _count_process_steps_with_cost_inputs(
    cur: sqlite3.Cursor,
    session_id: int,
    norm_addressee: str,
) -> tuple[int, int]:
    cur.execute(
        """
        SELECT COUNT(*) AS total_count
        FROM process_steps
        WHERE session_id = ? AND norm_addressee = ?
        """,
        (session_id, norm_addressee),
    )
    total_steps = int(cur.fetchone()["total_count"] or 0)
    if total_steps == 0:
        return 0, 0

    # Ready-Check MUSS auf dieselben Felder schauen, die _has_step_cost_inputs
    # in costs.py fordert, sonst meldet die Pipeline faelschlich "fertig",
    # effort.py skippt die Neuberechnung, und compute_costs wirft 422.
    # hourly_rate ist allein nicht kostenrelevant; die Rate kommt ggf. aus active_rates.
    cur.execute(
        """
        SELECT COUNT(*) AS count
        FROM process_steps
        WHERE session_id = ? AND norm_addressee = ?
          AND (
            time_required_in_min_a_current IS NOT NULL
            OR time_required_in_min_b_current IS NOT NULL
            OR time_required_in_min_c_current IS NOT NULL
            OR time_required_in_min_d_current IS NOT NULL
            OR time_required_in_min_a_proposed IS NOT NULL
            OR time_required_in_min_b_proposed IS NOT NULL
            OR time_required_in_min_c_proposed IS NOT NULL
            OR time_required_in_min_d_proposed IS NOT NULL
            OR expenses_current IS NOT NULL
            OR expenses_proposed IS NOT NULL
          )
        """,
        (session_id, norm_addressee),
    )
    return total_steps, int(cur.fetchone()["count"])


def has_effort_metrics(session_id: int, norm_addressee: str = ADMINISTRATION) -> bool:
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS total_count
        FROM case_groups
        WHERE session_id = ? AND norm_addressee = ?
        """,
        (session_id, resolved),
    )
    total_case_groups = int(cur.fetchone()["total_count"] or 0)
    if total_case_groups == 0:
        _maybe_close(conn)
        return False

    cur.execute(
        """
        SELECT COUNT(*) AS count
        FROM case_groups
        WHERE session_id = ? AND norm_addressee = ?
          AND (
            addressees_current IS NOT NULL OR annual_frequency_current IS NOT NULL
            OR addressees_proposed IS NOT NULL OR annual_frequency_proposed IS NOT NULL
          )
        """,
        (session_id, resolved),
    )
    groups_with_metrics = int(cur.fetchone()["count"])
    total_steps, steps_with_metrics = _count_process_steps_with_cost_inputs(
        cur,
        session_id,
        resolved,
    )
    _maybe_close(conn)
    return (
        total_case_groups > 0
        and total_steps > 0
        and groups_with_metrics == total_case_groups
        and steps_with_metrics == total_steps
    )


def has_process_step_effort_metrics(
    session_id: int,
    norm_addressee: str = ADMINISTRATION,
) -> bool:
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    total_steps, steps_with_metrics = _count_process_steps_with_cost_inputs(
        cur,
        session_id,
        resolved,
    )
    _maybe_close(conn)
    return total_steps > 0 and steps_with_metrics == total_steps


def has_total_cost_for_addressee(session_id: int, norm_addressee: str = ADMINISTRATION) -> bool:
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT total_cost, bureaucracy_cost, total_time_minutes, total_expenses
        FROM session_total_costs_by_addressee
        WHERE session_id = ? AND norm_addressee = ?
        """,
        (session_id, resolved),
    )
    row = cur.fetchone()
    if row and any(
        row[key] is not None
        for key in (
            "total_cost",
            "bureaucracy_cost",
            "total_time_minutes",
            "total_expenses",
        )
    ):
        _maybe_close(conn)
        return True
    _maybe_close(conn)
    return False


def get_session_id_by_app_id(app_session_id: str) -> int | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT session_id FROM sessions WHERE app_session_id = ?",
        (app_session_id,),
    )
    row = cur.fetchone()
    _maybe_close(conn)
    if not row:
        return None
    return int(row["session_id"])


def ensure_session(
    app_session_id: str,
    llm_model: str | None = None,
    owner_user_id: int | None = None,
) -> tuple[int, bool, str]:
    requested_model = str(llm_model or "").strip()
    existing = get_session_by_app_id(app_session_id)
    if existing:
        if owner_user_id is not None and existing.get("owner_user_id") != owner_user_id:
            raise PermissionError("Session is owned by another user")
        session_id = int(existing["session_id"])
        existing_model = str(existing.get("llm_model") or "").strip()
        if not existing_model:
            raise ValueError("Session exists without llm_model; please select a model")
        if requested_model and requested_model != existing_model:
            upsert_session(app_session_id, requested_model)
            return session_id, False, requested_model
        return session_id, False, existing_model

    if not requested_model:
        raise ValueError("Model is required for new session")
    model = requested_model
    session_id, created = upsert_session(app_session_id, model, owner_user_id=owner_user_id)
    return session_id, created, model


def upsert_session(
    app_session_id: str,
    llm_model: str,
    owner_user_id: int | None = None,
) -> tuple[int, bool]:
    conn = get_conn()
    cur = conn.cursor()
    defaults = _resolve_pay_rate_defaults(ADMINISTRATION, PAY_RATE_LEVEL_BUND)
    cur.execute(
        "SELECT session_id FROM sessions WHERE app_session_id = ?",
        (app_session_id,),
    )
    row = cur.fetchone()
    if row:
        cur.execute(
            "UPDATE sessions SET llm_model = ? WHERE app_session_id = ?",
            (llm_model, app_session_id),
        )
        cur.execute(
            """
            UPDATE sessions
            SET pay_rate_administration_level = COALESCE(pay_rate_administration_level, ?),
                pay_rate_default_a = COALESCE(pay_rate_default_a, ?),
                pay_rate_default_b = COALESCE(pay_rate_default_b, ?),
                pay_rate_default_c = COALESCE(pay_rate_default_c, ?),
                pay_rate_default_d = COALESCE(pay_rate_default_d, ?)
            WHERE app_session_id = ?
            """,
            (
                PAY_RATE_LEVEL_BUND,
                defaults["a"],
                defaults["b"],
                defaults["c"],
                defaults["d"],
                app_session_id,
            ),
        )
        session_id = int(row["session_id"])
        created = False
    else:
        cur.execute(
            """
            INSERT INTO sessions (
                app_session_id,
                llm_model,
                owner_user_id,
                case_group_research_enabled,
                pay_rate_administration_level,
                pay_rate_default_a,
                pay_rate_default_b,
                pay_rate_default_c,
                pay_rate_default_d
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                app_session_id,
                llm_model,
                owner_user_id,
                0,
                PAY_RATE_LEVEL_BUND,
                defaults["a"],
                defaults["b"],
                defaults["c"],
                defaults["d"],
            ),
        )
        session_id = int(cur.lastrowid)
        created = True
    _maybe_commit(conn)
    _maybe_close(conn)
    return session_id, created


def insert_llm_answer(
    session_id: int,
    prompt_id: str,
    model: str,
    answer_text: str,
    metadata: dict | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    hidden_thinking_tokens: int | None = None,
    estimated_cost_usd: float | None = None,
    provider_response_json: dict | list | None = None,
    answer_state: str = LLM_ANSWER_STATE_ACTIVE,
    state_reason: str | None = None,
    norm_addressee: str | None = None,
    prompt_text: str | None = None,
) -> int:
    if answer_state not in {
        LLM_ANSWER_STATE_PENDING,
        LLM_ANSWER_STATE_ACTIVE,
        LLM_ANSWER_STATE_INVALID,
    }:
        raise ValueError(f"Invalid llm answer state: {answer_state}")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO llm_answers (
            session_id,
            prompt_id,
            model,
            answer_text,
            prompt_text,
            metadata,
            input_tokens,
            output_tokens,
            hidden_thinking_tokens,
            estimated_cost_usd,
            provider_response_json,
            answer_state,
            state_reason,
            norm_addressee
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            prompt_id,
            model,
            answer_text,
            prompt_text,
            json.dumps(metadata, ensure_ascii=False) if metadata else None,
            input_tokens,
            output_tokens,
            hidden_thinking_tokens,
            estimated_cost_usd,
            (
                json.dumps(provider_response_json, ensure_ascii=False)
                if provider_response_json is not None
                else None
            ),
            answer_state,
            state_reason,
            norm_addressee,
        ),
    )
    answer_id = int(cur.lastrowid)
    _maybe_commit(conn)
    _maybe_close(conn)
    return answer_id


def create_pending_llm_answer(
    session_id: int,
    prompt_id: str,
    model: str,
    answer_text: str,
    metadata: dict | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    hidden_thinking_tokens: int | None = None,
    estimated_cost_usd: float | None = None,
    provider_response_json: dict | list | None = None,
    norm_addressee: str | None = None,
    prompt_text: str | None = None,
) -> int:
    invalidate_llm_answers(
        session_id=session_id,
        prompt_ids=[prompt_id],
        states=[LLM_ANSWER_STATE_PENDING],
        reason="superseded_by_new_attempt",
        norm_addressee=norm_addressee,
        match_norm_addressee=True,
    )
    return insert_llm_answer(
        session_id=session_id,
        prompt_id=prompt_id,
        model=model,
        answer_text=answer_text,
        metadata=metadata,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        hidden_thinking_tokens=hidden_thinking_tokens,
        estimated_cost_usd=estimated_cost_usd,
        provider_response_json=provider_response_json,
        answer_state=LLM_ANSWER_STATE_PENDING,
        state_reason="waiting_for_session_update",
        norm_addressee=norm_addressee,
        prompt_text=prompt_text,
    )


def invalidate_llm_answer(
    answer_id: int,
    reason: str,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE llm_answers
        SET answer_state = ?, state_reason = ?
        WHERE answer_id = ?
        """,
        (LLM_ANSWER_STATE_INVALID, reason, answer_id),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def invalidate_llm_answers(
    session_id: int,
    prompt_ids: Iterable[str],
    states: Iterable[str] | None = None,
    reason: str = "invalidated",
    exclude_answer_id: int | None = None,
    norm_addressee: str | None = None,
    match_norm_addressee: bool = False,
) -> int:
    ids = [pid for pid in prompt_ids if pid]
    if not ids:
        return 0
    target_states = list(states or [LLM_ANSWER_STATE_ACTIVE, LLM_ANSWER_STATE_PENDING])
    if not target_states:
        return 0
    placeholders_ids = ", ".join(["?"] * len(ids))
    placeholders_states = ", ".join(["?"] * len(target_states))
    params: list = [LLM_ANSWER_STATE_INVALID, reason, session_id, *ids, *target_states]
    sql = f"""
        UPDATE llm_answers
        SET answer_state = ?, state_reason = ?
        WHERE session_id = ?
          AND prompt_id IN ({placeholders_ids})
          AND answer_state IN ({placeholders_states})
    """
    if match_norm_addressee:
        sql += " AND COALESCE(norm_addressee, '') = COALESCE(?, '')"
        params.append(norm_addressee)
    if exclude_answer_id is not None:
        sql += " AND answer_id <> ?"
        params.append(exclude_answer_id)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    updated = int(cur.rowcount or 0)
    _maybe_commit(conn)
    _maybe_close(conn)
    return updated


def get_reusable_pending_llm_answer(
    *,
    session_id: int,
    prompt_id: str,
    model: str,
    provider: str | None,
    prompt_sha256: str,
    norm_addressee: str | None = None,
) -> dict | None:
    # Nur Zeilen wiederverwenden, die der Paired-Retry-Pfad bewusst auf
    # "waiting_for_paired_retry" promotet hat. Zombie-Pendings in
    # "waiting_for_session_update" stammen aus abgebrochenen Requests und
    # duerfen NICHT reused werden (sie werden beim naechsten Staging via
    # create_pending_llm_answer ohnehin superseded).
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT answer_id, answer_text, metadata, state_reason
        FROM llm_answers
        WHERE session_id = ?
          AND prompt_id = ?
          AND model = ?
          AND answer_state = ?
          AND state_reason = 'waiting_for_paired_retry'
          AND COALESCE(norm_addressee, '') = COALESCE(?, '')
        ORDER BY answer_id DESC
        """,
        (session_id, prompt_id, model, LLM_ANSWER_STATE_PENDING, norm_addressee),
    )
    rows = cur.fetchall()
    _maybe_close(conn)
    for row in rows:
        metadata = json.loads(row["metadata"] or "{}")
        if not isinstance(metadata, dict):
            continue
        if metadata.get("provider") != provider:
            continue
        if metadata.get("prompt_sha256") != prompt_sha256:
            continue
        return {
            "answer_id": int(row["answer_id"]),
            "answer_text": str(row["answer_text"]),
            "state_reason": row["state_reason"],
            "metadata": metadata,
        }
    return None


def promote_waiting_session_update_llm_answers_to_paired_retry(
    *,
    session_id: int,
    prompts: list[tuple[str, str | None, str, str, str | None]],
) -> list[int]:
    """Promote fully staged but unapplied pending answers so an atomic retry can reuse them.

    Each prompt tuple is `(prompt_id, norm_addressee, prompt_sha256, model, provider)`.
    """
    promoted: list[int] = []
    conn = get_conn()
    cur = conn.cursor()
    for prompt_id, norm_addressee, prompt_hash, model, provider in prompts:
        cur.execute(
            """
            SELECT answer_id, metadata, answer_text
            FROM llm_answers
            WHERE session_id = ?
              AND prompt_id = ?
              AND model = ?
              AND answer_state = ?
              AND state_reason = 'waiting_for_session_update'
              AND COALESCE(norm_addressee, '') = COALESCE(?, '')
            ORDER BY answer_id DESC
            """,
            (session_id, prompt_id, model, LLM_ANSWER_STATE_PENDING, norm_addressee),
        )
        for row in cur.fetchall():
            if not str(row["answer_text"] or "").strip():
                continue
            metadata = json.loads(row["metadata"] or "{}")
            if not isinstance(metadata, dict):
                continue
            if metadata.get("provider") != provider:
                continue
            if metadata.get("prompt_sha256") != prompt_hash:
                continue
            answer_id = int(row["answer_id"])
            cur.execute(
                """
                UPDATE llm_answers
                SET state_reason = 'waiting_for_paired_retry'
                WHERE answer_id = ?
                """,
                (answer_id,),
            )
            promoted.append(answer_id)
            break
    _maybe_commit(conn)
    _maybe_close(conn)
    return promoted


def promote_waiting_session_update_answers_by_prompt(
    session_id: int,
    prompt_ids: list[str],
) -> list[int]:
    safe_prompt_ids = [prompt_id for prompt_id in prompt_ids if str(prompt_id or "").strip()]
    if not safe_prompt_ids:
        return []
    placeholders = ", ".join("?" for _ in safe_prompt_ids)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT answer_id
        FROM llm_answers
        WHERE session_id = ?
          AND prompt_id IN ({placeholders})
          AND answer_state = ?
          AND state_reason = 'waiting_for_session_update'
          AND TRIM(answer_text) != ''
        """,
        (session_id, *safe_prompt_ids, LLM_ANSWER_STATE_PENDING),
    )
    answer_ids = [int(row["answer_id"]) for row in cur.fetchall()]
    if answer_ids:
        id_placeholders = ", ".join("?" for _ in answer_ids)
        cur.execute(
            f"""
            UPDATE llm_answers
            SET state_reason = 'waiting_for_paired_retry'
            WHERE answer_id IN ({id_placeholders})
            """,
            answer_ids,
        )
    _maybe_commit(conn)
    _maybe_close(conn)
    return answer_ids


def update_llm_answer_state_reason(
    answer_id: int,
    reason: str,
    *,
    state: str | None = None,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    if state:
        cur.execute(
            """
            UPDATE llm_answers
            SET state_reason = ?
            WHERE answer_id = ? AND answer_state = ?
            """,
            (reason, answer_id, state),
        )
    else:
        cur.execute(
            """
            UPDATE llm_answers
            SET state_reason = ?
            WHERE answer_id = ?
            """,
            (reason, answer_id),
        )
    _maybe_commit(conn)
    _maybe_close(conn)


def activate_llm_answer(
    answer_id: int,
    session_id: int,
    prompt_id: str,
    reason: str = "session_updated",
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    # Sibling-Answers zum selben (session, prompt, norm_addressee) verdraengen.
    # Answers mit abweichendem norm_addressee bleiben unberuehrt, damit z.B.
    # ein Verwaltungs-Answer nicht vom spaeter laufenden Business-Lauf
    # invalidiert wird.
    cur.execute(
        """
        UPDATE llm_answers
        SET answer_state = ?, state_reason = ?
        WHERE session_id = ?
          AND prompt_id = ?
          AND answer_state IN (?, ?)
          AND answer_id <> ?
          AND COALESCE(norm_addressee, '') = COALESCE(
              (SELECT norm_addressee FROM llm_answers WHERE answer_id = ?), ''
          )
        """,
        (
            LLM_ANSWER_STATE_INVALID,
            "superseded_by_new_attempt",
            session_id,
            prompt_id,
            LLM_ANSWER_STATE_ACTIVE,
            LLM_ANSWER_STATE_PENDING,
            answer_id,
            answer_id,
        ),
    )
    cur.execute(
        """
        UPDATE llm_answers
        SET answer_state = ?, state_reason = ?
        WHERE answer_id = ? AND session_id = ? AND prompt_id = ?
        """,
        (
            LLM_ANSWER_STATE_ACTIVE,
            reason,
            answer_id,
            session_id,
            prompt_id,
        ),
    )
    if cur.rowcount == 0:
        raise ValueError(
            f"Could not activate llm answer {answer_id} for session {session_id} and prompt {prompt_id}"
        )
    _maybe_commit(conn)
    _maybe_close(conn)


def get_llm_answer_by_id(answer_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            answer_id,
            session_id,
            prompt_id,
            model,
            metadata,
            answer_state,
            state_reason,
            input_tokens,
            output_tokens,
            hidden_thinking_tokens,
            estimated_cost_usd,
            norm_addressee,
            prompt_text,
            created_at
        FROM llm_answers
        WHERE answer_id = ?
        LIMIT 1
        """,
        (answer_id,),
    )
    row = cur.fetchone()
    _maybe_close(conn)
    if row is None:
        return None
    parsed = dict(row)
    metadata_raw = parsed.get("metadata")
    try:
        metadata = json.loads(metadata_raw) if metadata_raw else {}
    except (TypeError, json.JSONDecodeError):
        metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}
    parsed["metadata"] = metadata
    return parsed


def has_active_empty_process_compilation_answer(
    session_id: int,
    norm_addressee: str,
) -> bool:
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT answer_text
        FROM llm_answers
        WHERE session_id = ?
          AND prompt_id = 'process_compilation'
          AND answer_state = ?
          AND norm_addressee = ?
        ORDER BY answer_id DESC
        LIMIT 1
        """,
        (session_id, LLM_ANSWER_STATE_ACTIVE, resolved),
    )
    row = cur.fetchone()
    _maybe_close(conn)
    if row is None:
        return False
    try:
        data = json.loads(str(row["answer_text"] or ""))
    except json.JSONDecodeError:
        return False
    return isinstance(data, dict) and data.get("prozesse") == []


def has_no_process_path_for_addressee(
    session_id: int,
    norm_addressee: str,
) -> bool:
    return has_active_empty_process_compilation_answer(session_id, norm_addressee)


def list_recent_llm_answers_for_session(session_id: int, limit: int = 80) -> list[dict]:
    safe_limit = max(1, min(limit, 500))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            answer_id,
            prompt_id,
            model,
            answer_state,
            state_reason,
            input_tokens,
            output_tokens,
            hidden_thinking_tokens,
            estimated_cost_usd,
            norm_addressee,
            created_at,
            metadata
        FROM llm_answers
        WHERE session_id = ?
        ORDER BY answer_id DESC
        LIMIT ?
        """,
        (session_id, safe_limit),
    )
    rows = [dict(row) for row in cur.fetchall()]
    _maybe_close(conn)

    normalized: list[dict] = []
    for row in rows:
        metadata_raw = row.get("metadata")
        try:
            metadata = json.loads(metadata_raw) if metadata_raw else {}
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}
        normalized.append(
            {
                "answer_id": int(row["answer_id"]),
                "prompt_id": str(row.get("prompt_id") or ""),
                "model": str(row.get("model") or ""),
                "provider": metadata.get("provider"),
                "attempt_id": metadata.get("attempt_id"),
                "request_id": metadata.get("request_id"),
                "route_method": metadata.get("route_method"),
                "route_path": metadata.get("route_path"),
                "elapsed_ms": metadata.get("elapsed_ms"),
                "answer_state": str(row.get("answer_state") or ""),
                "state_reason": row.get("state_reason"),
                "input_tokens": row.get("input_tokens"),
                "output_tokens": row.get("output_tokens"),
                "hidden_thinking_tokens": row.get("hidden_thinking_tokens"),
                "estimated_cost_usd": row.get("estimated_cost_usd"),
                "norm_addressee": row.get("norm_addressee"),
                "error_kind": metadata.get("error_kind"),
                "error_status_code": metadata.get("error_status_code"),
                "error": metadata.get("error"),
                "created_at": row.get("created_at"),
            }
        )
    return normalized


def list_regulations_for_session(session_id: int) -> List[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            regulation_id,
            legal_citation,
            description,
            process_id,
            change_status,
            applies_to_administration,
            applies_to_business,
            applies_to_citizens,
            is_business_information_obligation
        FROM regulations
        WHERE session_id = ?
        ORDER BY regulation_id
        """,
        (session_id,),
    )
    rows = [dict(row) for row in cur.fetchall()]
    _maybe_close(conn)
    return rows


def list_regulations_for_session_and_addressee(
    session_id: int,
    norm_addressee: str,
) -> List[dict]:
    resolved = normalize_norm_addressee(norm_addressee)
    regulations = [
        row for row in list_regulations_for_session(session_id)
        if (
            resolved == ADMINISTRATION
            and bool(row.get("applies_to_administration"))
        )
        or (resolved == BUSINESS and bool(row.get("applies_to_business")))
        or (resolved == CITIZENS and bool(row.get("applies_to_citizens")))
    ]
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT regulation_id, process_id
        FROM regulation_process_links_by_addressee
        WHERE session_id = ? AND norm_addressee = ?
        """,
        (session_id, resolved),
    )
    links = {int(row["regulation_id"]): int(row["process_id"]) for row in cur.fetchall()}
    _maybe_close(conn)
    for row in regulations:
        if resolved != ADMINISTRATION:
            row["process_id"] = links.get(int(row["regulation_id"]))
    return regulations


def has_applicable_regulations_for_addressee(session_id: int, norm_addressee: str) -> bool:
    return len(list_regulations_for_session_and_addressee(session_id, norm_addressee)) > 0


def get_regulation_by_id(regulation_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            regulation_id,
            session_id,
            legal_citation,
            description,
            process_id,
            change_status,
            applies_to_administration,
            applies_to_business,
            applies_to_citizens,
            is_business_information_obligation
        FROM regulations
        WHERE regulation_id = ?
        """,
        (regulation_id,),
    )
    row = cur.fetchone()
    _maybe_close(conn)
    if not row:
        return None
    return dict(row)


def list_processes_for_session(session_id: int) -> List[dict]:
    return list_processes_for_session_and_addressee(session_id, ADMINISTRATION)


def list_processes_for_session_and_addressee(
    session_id: int,
    norm_addressee: str,
) -> List[dict]:
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT process_id, process, description, change_status, cost, norm_addressee
        FROM processes
        WHERE session_id = ?
          AND norm_addressee = ?
        ORDER BY process_id
        """,
        (session_id, resolved),
    )
    rows = [dict(row) for row in cur.fetchall()]
    _maybe_close(conn)
    return rows


def list_case_groups_for_session(session_id: int) -> List[dict]:
    rows: List[dict] = []
    for addressee in ALL_NORM_ADDRESSEES:
        rows.extend(list_case_groups_for_session_and_addressee(session_id, addressee))
    return rows


def list_case_groups_for_session_and_addressee(
    session_id: int,
    norm_addressee: str,
) -> List[dict]:
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            case_group_id,
            process_id,
            norm_addressee,
            case_group,
            description,
            change_status,
            addressees_current,
            annual_frequency_current,
            cases_current,
            addressees_current_edited,
            annual_frequency_current_edited,
            cases_current_edited,
            addressees_proposed,
            annual_frequency_proposed,
            cases_proposed,
            addressees_proposed_edited,
            annual_frequency_proposed_edited,
            cases_proposed_edited,
            last_edited_at,
            case_metric_research_json,
            cost
        FROM case_groups
        WHERE session_id = ?
          AND norm_addressee = ?
        ORDER BY case_group_id
        """,
        (session_id, resolved),
    )
    rows = [dict(row) for row in cur.fetchall()]
    _maybe_close(conn)
    return rows


def list_process_steps_for_session(session_id: int) -> List[dict]:
    rows: List[dict] = []
    for addressee in ALL_NORM_ADDRESSEES:
        rows.extend(list_process_steps_for_session_and_addressee(session_id, addressee))
    return rows


def list_process_steps_for_session_and_addressee(
    session_id: int,
    norm_addressee: str,
) -> List[dict]:
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    # Migration compatibility helper (dev/legacy DBs only):
    # Build the SELECT list defensively so older local DB files with partial
    # schema drift don't fail hard if deprecated columns differ.
    # Safe to remove when production runs from a clean DB at final schema.
    columns = [
        "step_id",
        "case_group_id",
        "norm_addressee",
        "step",
        "description",
        "previous_id",
        "next_id",
        "change_status",
        "hourly_rate_a_current",
        "hourly_rate_b_current",
        "hourly_rate_c_current",
        "hourly_rate_d_current",
        "time_required_in_min_a_current",
        "time_required_in_min_b_current",
        "time_required_in_min_c_current",
        "time_required_in_min_d_current",
        "expenses_current",
        "hourly_rate_a_proposed",
        "hourly_rate_b_proposed",
        "hourly_rate_c_proposed",
        "hourly_rate_d_proposed",
        "time_required_in_min_a_proposed",
        "time_required_in_min_b_proposed",
        "time_required_in_min_c_proposed",
        "time_required_in_min_d_proposed",
        "expenses_proposed",
        "cost_current",
        "cost_proposed",
    ]
    optional_columns = [
        "time_required_in_min_a_current_edited",
        "time_required_in_min_b_current_edited",
        "time_required_in_min_c_current_edited",
        "time_required_in_min_d_current_edited",
        "expenses_current_edited",
        "time_required_in_min_a_proposed_edited",
        "time_required_in_min_b_proposed_edited",
        "time_required_in_min_c_proposed_edited",
        "time_required_in_min_d_proposed_edited",
        "expenses_proposed_edited",
        "last_edited_at",
        "role_sources_current_json",
        "role_sources_proposed_json",
    ]
    for optional_column in optional_columns:
        if _table_has_column(cur, "process_steps", optional_column):
            columns.append(optional_column)
    columns.append("execution_per_case")
    select_columns = ", ".join(columns)
    cur.execute(
        f"""
        SELECT {select_columns}
        FROM process_steps
        WHERE session_id = ?
          AND norm_addressee = ?
        ORDER BY step_id
        """,
        (session_id, resolved),
    )
    rows = [dict(row) for row in cur.fetchall()]
    _maybe_close(conn)
    regulation_ids_by_step = get_process_step_regulation_ids_by_step(session_id, resolved)
    for row in rows:
        row["regulation_ids"] = regulation_ids_by_step.get(int(row["step_id"]), [])
    return rows


def _effective_value(base: float | int | None, edited: float | int | None) -> float | None:
    if edited is not None:
        return float(edited)
    if base is not None:
        return float(base)
    return None


def resolve_effective_case_group_metrics(group: dict) -> dict:
    addressees_current = _effective_value(
        group.get("addressees_current"),
        group.get("addressees_current_edited"),
    )
    annual_frequency_current = _effective_value(
        group.get("annual_frequency_current"),
        group.get("annual_frequency_current_edited"),
    )
    addressees_proposed = _effective_value(
        group.get("addressees_proposed"),
        group.get("addressees_proposed_edited"),
    )
    annual_frequency_proposed = _effective_value(
        group.get("annual_frequency_proposed"),
        group.get("annual_frequency_proposed_edited"),
    )
    cases_current = (
        addressees_current * annual_frequency_current
        if addressees_current is not None and annual_frequency_current is not None
        else _effective_value(group.get("cases_current"), group.get("cases_current_edited"))
    )
    cases_proposed = (
        addressees_proposed * annual_frequency_proposed
        if addressees_proposed is not None and annual_frequency_proposed is not None
        else _effective_value(group.get("cases_proposed"), group.get("cases_proposed_edited"))
    )
    resolved = dict(group)
    resolved["addressees_current_effective"] = addressees_current
    resolved["annual_frequency_current_effective"] = annual_frequency_current
    resolved["cases_current_effective"] = cases_current
    resolved["addressees_proposed_effective"] = addressees_proposed
    resolved["annual_frequency_proposed_effective"] = annual_frequency_proposed
    resolved["cases_proposed_effective"] = cases_proposed
    return resolved


def resolve_effective_process_step_metrics(step: dict) -> dict:
    resolved = dict(step)
    for suffix in ("current", "proposed"):
        for key in PAY_RATE_KEYS:
            base_key = f"time_required_in_min_{key}_{suffix}"
            edited_key = f"time_required_in_min_{key}_{suffix}_edited"
            resolved[f"{base_key}_effective"] = _effective_value(
                step.get(base_key),
                step.get(edited_key),
            )
        resolved[f"expenses_{suffix}_effective"] = _effective_value(
            step.get(f"expenses_{suffix}"),
            step.get(f"expenses_{suffix}_edited"),
        )
        raw_json = step.get(f"role_sources_{suffix}_json")
        resolved[f"role_sources_{suffix}"] = json.loads(raw_json) if raw_json else None
    return resolved


def list_pay_rate_defaults(norm_addressee: str = ADMINISTRATION) -> list[dict]:
    """List the canonical rate rows for a norm addressee.

    Defaults to administration so the validation/render path does not accidentally
    accept business source_values (WZ sections) as valid administration_level. For
    administration, source_value is exposed as administration_level to keep the
    existing router/test contract stable.
    """
    resolved = normalize_norm_addressee(norm_addressee)
    table = _PAY_RATE_DEFAULTS_BY_ADDRESSEE.get(resolved, {})
    return [
        {
            "administration_level": source_value,
            "hourly_rate_a": float(rates["a"]),
            "hourly_rate_b": float(rates["b"]),
            "hourly_rate_c": float(rates["c"]),
            "hourly_rate_d": float(rates["d"]),
        }
        for source_value, rates in sorted(table.items())
    ]


def get_used_wage_baseline(session_id: int, norm_addressee: str) -> str | None:
    """Return the dominant wage-row label from role_sources (read-only).

    Reads role_sources_current_json + role_sources_proposed_json across all steps of
    the session+addressee and returns the most frequent source_value (e.g. "laender"
    for admin, "K" for business), or None when no valid role_sources exist (callers
    then fall back to the constant defaults). current and proposed are intentionally
    collapsed into one dominant label per addressee.
    """
    resolved = normalize_norm_addressee(norm_addressee)
    if resolved not in (ADMINISTRATION, BUSINESS):
        return None
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            role_sources_current_json,
            role_sources_proposed_json
        FROM process_steps
        WHERE session_id = ? AND norm_addressee = ?
        """,
        (session_id, resolved),
    )
    rows = cur.fetchall()
    _maybe_close(conn)

    # Count occurrences per source_value to pick the dominant one.
    counts: dict[str, int] = {}
    for row in rows:
        for suffix in ("current", "proposed"):
            raw = row[f"role_sources_{suffix}_json"]
            if not raw:
                continue
            try:
                entries = json.loads(raw)
            except (TypeError, ValueError):
                continue
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                source_value = entry.get("source_value")
                slot = entry.get("slot")
                if not source_value or slot not in PAY_RATE_KEYS:
                    continue
                counts[source_value] = counts.get(source_value, 0) + 1

    if not counts:
        return None
    # Pick the dominant row. Deterministic tie-break: on equal counts the
    # alphabetically first source_value wins, independent of dict iteration order.
    max_count = max(counts.values())
    return min(value for value, count in counts.items() if count == max_count)


def get_session_administration_pay_rates(session_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            pay_rate_administration_level,
            pay_rate_default_a,
            pay_rate_default_b,
            pay_rate_default_c,
            pay_rate_default_d,
            pay_rate_edited_a,
            pay_rate_edited_b,
            pay_rate_edited_c,
            pay_rate_edited_d
        FROM sessions
        WHERE session_id = ?
        """,
        (session_id,),
    )
    row = cur.fetchone()
    _maybe_close(conn)
    if row is None:
        return None
    level = str(row["pay_rate_administration_level"] or PAY_RATE_LEVEL_BUND).strip().lower()
    defaults = {
        "a": float(row["pay_rate_default_a"]) if row["pay_rate_default_a"] is not None else PAY_RATE_BUND_DEFAULTS["a"],
        "b": float(row["pay_rate_default_b"]) if row["pay_rate_default_b"] is not None else PAY_RATE_BUND_DEFAULTS["b"],
        "c": float(row["pay_rate_default_c"]) if row["pay_rate_default_c"] is not None else PAY_RATE_BUND_DEFAULTS["c"],
        "d": float(row["pay_rate_default_d"]) if row["pay_rate_default_d"] is not None else PAY_RATE_BUND_DEFAULTS["d"],
    }
    edited = {
        "a": float(row["pay_rate_edited_a"]) if row["pay_rate_edited_a"] is not None else None,
        "b": float(row["pay_rate_edited_b"]) if row["pay_rate_edited_b"] is not None else None,
        "c": float(row["pay_rate_edited_c"]) if row["pay_rate_edited_c"] is not None else None,
        "d": float(row["pay_rate_edited_d"]) if row["pay_rate_edited_d"] is not None else None,
    }
    active = {
        key: (edited[key] if edited[key] is not None else defaults[key])
        for key in PAY_RATE_KEYS
    }
    return {
        "administration_level": level,
        "defaults": defaults,
        "edited": edited,
        "active": active,
    }


def get_session_pay_rates_for_addressee(
    session_id: int,
    norm_addressee: str,
) -> dict | None:
    resolved = normalize_norm_addressee(norm_addressee)
    if resolved == ADMINISTRATION:
        administration_rates = get_session_administration_pay_rates(session_id)
        if administration_rates is None:
            return None
        level = administration_rates["administration_level"]
        defaults = administration_rates["defaults"]
        baseline = get_used_wage_baseline(session_id, ADMINISTRATION)
        if baseline is not None:
            # administration_level carries the used level label; it is a valid level
            # and thus save-compatible, so no separate wage_source_label is needed.
            level = baseline
            defaults = get_default_pay_rates_for_addressee(
                ADMINISTRATION, source_value=baseline
            )
        edited = administration_rates["edited"]
        active = {
            key: (edited[key] if edited[key] is not None else defaults[key])
            for key in PAY_RATE_KEYS
        }
        return {
            "norm_addressee": resolved,
            "editable": True,
            "administration_level": level,
            "wage_source_label": None,
            "defaults": defaults,
            "edited": edited,
            "active": active,
        }
    if resolved == BUSINESS:
        baseline = get_used_wage_baseline(session_id, BUSINESS)
        # Used WZ section: full rate row + label for the badge. Without a label the
        # resolve falls back to gesamtwirtschaft.
        defaults = get_default_pay_rates_for_addressee(BUSINESS, source_value=baseline)
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT edited_a, edited_b, edited_c, edited_d
            FROM session_pay_rate_overrides_by_addressee
            WHERE session_id = ? AND norm_addressee = ?
            """,
            (session_id, resolved),
        )
        row = cur.fetchone()
        _maybe_close(conn)
        edited = {
            "a": float(row["edited_a"]) if row and row["edited_a"] is not None else None,
            "b": float(row["edited_b"]) if row and row["edited_b"] is not None else None,
            "c": float(row["edited_c"]) if row and row["edited_c"] is not None else None,
            "d": float(row["edited_d"]) if row and row["edited_d"] is not None else None,
        }
        active = {
            key: (edited[key] if edited[key] is not None else defaults[key])
            for key in PAY_RATE_KEYS
        }
        return {
            "norm_addressee": resolved,
            "editable": True,
            "administration_level": None,
            "wage_source_label": baseline,
            "defaults": defaults,
            "edited": edited,
            "active": active,
        }
    defaults = _zero_pay_rates()
    return {
        "norm_addressee": resolved,
        "editable": False,
        "administration_level": None,
        "wage_source_label": None,
        "defaults": defaults,
        "edited": _empty_pay_rate_edits(),
        "active": defaults,
    }


def get_session_pay_rates(session_id: int) -> dict | None:
    """Compatibility wrapper for the existing administration pay-rate UI."""
    pay_rates = get_session_pay_rates_for_addressee(session_id, ADMINISTRATION)
    if pay_rates is None:
        return None
    return {
        "administration_level": pay_rates["administration_level"],
        "defaults": pay_rates["defaults"],
        "edited": pay_rates["edited"],
        "active": pay_rates["active"],
    }


def update_session_pay_rate_edits(
    session_id: int,
    administration_level: str | None,
    edited: dict[str, float | None],
) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            pay_rate_administration_level,
            pay_rate_default_a,
            pay_rate_default_b,
            pay_rate_default_c,
            pay_rate_default_d,
            pay_rate_edited_a,
            pay_rate_edited_b,
            pay_rate_edited_c,
            pay_rate_edited_d
        FROM sessions
        WHERE session_id = ?
        """,
        (session_id,),
    )
    previous_row = cur.fetchone()
    if previous_row is None:
        _maybe_close(conn)
        return False
    previous = dict(previous_row)
    level = str(administration_level or PAY_RATE_LEVEL_BUND).strip().lower()
    # Constants-only validation: only real administration levels are valid; a WZ
    # section (e.g. "K") is not a valid administration_level.
    rates = PAY_RATE_LEVEL_DEFAULTS.get(level)
    if rates is None:
        _maybe_close(conn)
        raise ValueError(f"Unknown administration_level: {level}")
    defaults = {
        "a": float(rates["a"]),
        "b": float(rates["b"]),
        "c": float(rates["c"]),
        "d": float(rates["d"]),
    }
    changed = value_changed(previous.get("pay_rate_administration_level"), level)
    for key in PAY_RATE_KEYS:
        changed = changed or value_changed(
            previous.get(f"pay_rate_default_{key}"),
            defaults[key],
        )
        changed = changed or value_changed(
            previous.get(f"pay_rate_edited_{key}"),
            edited.get(key),
        )
    if not changed:
        _maybe_close(conn)
        return False

    cur.execute(
        """
        UPDATE sessions
        SET pay_rate_administration_level = ?,
            pay_rate_default_a = ?,
            pay_rate_default_b = ?,
            pay_rate_default_c = ?,
            pay_rate_default_d = ?,
            pay_rate_edited_a = ?,
            pay_rate_edited_b = ?,
            pay_rate_edited_c = ?,
            pay_rate_edited_d = ?,
            pay_rate_last_edited_at = current_timestamp
        WHERE session_id = ?
        """,
        (
            level,
            defaults["a"],
            defaults["b"],
            defaults["c"],
            defaults["d"],
            edited.get("a"),
            edited.get("b"),
            edited.get("c"),
            edited.get("d"),
            session_id,
        ),
    )
    insert_edit_audit_row(
        cur,
        session_id=session_id,
        entity_type="pay_rate",
        entity_id=None,
        field_name="administration_level",
        old_value=previous.get("pay_rate_administration_level"),
        new_value=level,
    )
    for key in PAY_RATE_KEYS:
        insert_edit_audit_row(
            cur,
            session_id=session_id,
            entity_type="pay_rate",
            entity_id=None,
            field_name=f"default_{key}",
            old_value=previous.get(f"pay_rate_default_{key}"),
            new_value=defaults[key],
        )
        insert_edit_audit_row(
            cur,
            session_id=session_id,
            entity_type="pay_rate",
            entity_id=None,
            field_name=f"edited_{key}",
            old_value=previous.get(f"pay_rate_edited_{key}"),
            new_value=edited.get(key),
    )
    _maybe_commit(conn)
    _maybe_close(conn)
    return True


def update_session_pay_rate_edits_for_addressee(
    session_id: int,
    norm_addressee: str,
    administration_level: str | None,
    edited: dict[str, float | None],
) -> bool:
    resolved = normalize_norm_addressee(norm_addressee)
    if resolved == ADMINISTRATION:
        return update_session_pay_rate_edits(
            session_id=session_id,
            administration_level=administration_level,
            edited=edited,
        )
    if resolved == CITIZENS:
        raise ValueError("Citizens pay rates are not editable")
    if administration_level is not None:
        raise ValueError("administration_level is only supported for administration")

    # resolved is always BUSINESS here (admin/citizens handled above), and
    # get_session_pay_rates_for_addressee always returns a dict for BUSINESS,
    # so no None guard is needed.
    previous = get_session_pay_rates_for_addressee(session_id, resolved)
    changed = False
    for key in PAY_RATE_KEYS:
        changed = changed or value_changed(previous["edited"].get(key), edited.get(key))
    if not changed:
        return False

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO session_pay_rate_overrides_by_addressee (
            session_id,
            norm_addressee,
            edited_a,
            edited_b,
            edited_c,
            edited_d,
            last_edited_at
        )
        VALUES (?, ?, ?, ?, ?, ?, current_timestamp)
        ON CONFLICT(session_id, norm_addressee) DO UPDATE SET
            edited_a = excluded.edited_a,
            edited_b = excluded.edited_b,
            edited_c = excluded.edited_c,
            edited_d = excluded.edited_d,
            last_edited_at = current_timestamp
        """,
        (
            session_id,
            resolved,
            edited.get("a"),
            edited.get("b"),
            edited.get("c"),
            edited.get("d"),
        ),
    )
    for key in PAY_RATE_KEYS:
        if value_changed(previous["edited"].get(key), edited.get(key)):
            insert_edit_audit_row(
                session_id=session_id,
                entity_type="pay_rate",
                entity_id=None,
                field_name=f"{resolved}_edited_{key}",
                old_value=previous["edited"].get(key),
                new_value=edited.get(key),
                cur=cur,
            )
    _maybe_commit(conn)
    _maybe_close(conn)
    return True


def reset_all_ea_edit_overrides(session_id: int) -> dict[str, int]:
    """Clear user EA overrides without deleting generated model values."""
    with transaction():
        case_rows = [
            {
                "case_group_id": row["case_group_id"],
                "addressees_current": None,
                "annual_frequency_current": None,
                "addressees_proposed": None,
                "annual_frequency_proposed": None,
            }
            for row in list_editable_case_groups(session_id)
        ]
        process_step_rows = [
            {
                "step_id": row["step_id"],
                "time_required_in_min_a_current": None,
                "time_required_in_min_b_current": None,
                "time_required_in_min_c_current": None,
                "time_required_in_min_d_current": None,
                "expenses_current": None,
                "time_required_in_min_a_proposed": None,
                "time_required_in_min_b_proposed": None,
                "time_required_in_min_c_proposed": None,
                "time_required_in_min_d_proposed": None,
                "expenses_proposed": None,
            }
            for row in list_editable_process_steps(session_id)
        ]

        updated_case_groups, _missing_case_groups = bulk_update_case_group_edits(
            session_id,
            case_rows,
        )
        updated_process_steps, _missing_process_steps = bulk_update_process_step_edits(
            session_id,
            process_step_rows,
        )

        updated_pay_rates = 0
        for norm_addressee in (ADMINISTRATION, BUSINESS):
            pay_rates = get_session_pay_rates_for_addressee(session_id, norm_addressee)
            if not pay_rates or not any(
                pay_rates["edited"].get(key) is not None for key in PAY_RATE_KEYS
            ):
                continue
            if update_session_pay_rate_edits_for_addressee(
                session_id=session_id,
                norm_addressee=norm_addressee,
                administration_level=pay_rates.get("administration_level"),
                edited=_empty_pay_rate_edits(),
            ):
                updated_pay_rates += 1

        # NEU stores (Dual-Write phase): clear the row-based wage overrides and the
        # effort-time edit overlay session-wide so a global reset yields pure model
        # costs. ALT pay_rates reset above is left untouched (Phase-4 teardown).
        cleared_wage_overrides = clear_session_wage_rate_overrides(session_id)
        cleared_effort_time_edits = clear_personnel_effort_time_edits(session_id)

        return {
            "pay_rates": updated_pay_rates,
            "case_groups": updated_case_groups,
            "process_steps": updated_process_steps,
            "wage_overrides": cleared_wage_overrides,
            "effort_time_edits": cleared_effort_time_edits,
        }


# --- Edit Metrics (delegated to backend.core.db_edit_metrics) ---
def list_editable_case_groups(session_id: int) -> list[dict]:
    rows = list_case_groups_for_session(session_id)
    return db_edit_metrics.list_editable_case_groups(
        rows=rows,
        resolve_effective_case_group_metrics=resolve_effective_case_group_metrics,
    )


def bulk_update_case_group_edits(session_id: int, rows: list[dict]) -> tuple[int, list[int]]:
    conn = get_conn()
    cur = conn.cursor()
    updated, missing_ids = db_edit_metrics.bulk_update_case_group_edits(
        cur=cur,
        session_id=session_id,
        rows=rows,
    )
    if missing_ids:
        _maybe_close(conn)
        return 0, missing_ids
    _maybe_commit(conn)
    _maybe_close(conn)
    return updated, []


def list_editable_process_steps(
    session_id: int,
    case_group_id: int | None = None,
) -> list[dict]:
    rows = list_process_steps_for_session(session_id)
    return db_edit_metrics.list_editable_process_steps(
        rows=rows,
        resolve_effective_process_step_metrics=resolve_effective_process_step_metrics,
        case_group_id=case_group_id,
    )


def bulk_update_process_step_edits(session_id: int, rows: list[dict]) -> tuple[int, list[int]]:
    conn = get_conn()
    cur = conn.cursor()
    updated, missing_ids = db_edit_metrics.bulk_update_process_step_edits(
        cur=cur,
        session_id=session_id,
        rows=rows,
    )
    if missing_ids:
        _maybe_close(conn)
        return 0, missing_ids
    _maybe_commit(conn)
    _maybe_close(conn)
    return updated, []


def insert_regulation(
    session_id: int,
    legal_citation: str,
    description: str,
    change_status: str = "geaendert",
    process_id: int | None = None,
    applies_to_administration: bool = True,
    applies_to_business: bool = False,
    applies_to_citizens: bool = False,
    is_business_information_obligation: bool = False,
) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO regulations (
            session_id,
            process_id,
            legal_citation,
            description,
            change_status,
            applies_to_administration,
            applies_to_business,
            applies_to_citizens,
            is_business_information_obligation
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            process_id,
            legal_citation,
            description,
            change_status,
            int(bool(applies_to_administration)),
            int(bool(applies_to_business)),
            int(bool(applies_to_citizens)),
            int(bool(is_business_information_obligation)),
        ),
    )
    _maybe_commit(conn)
    regulation_id = int(cur.lastrowid)
    _maybe_close(conn)
    return regulation_id


def insert_process(
    session_id: int,
    process: str,
    description: str,
    change_status: str = "geaendert",
    cost: float | None = None,
    norm_addressee: str = ADMINISTRATION,
) -> int:
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO processes (session_id, norm_addressee, process, description, change_status, cost)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (session_id, resolved, process, description, change_status, cost),
    )
    _maybe_commit(conn)
    process_id = int(cur.lastrowid)
    _maybe_close(conn)
    return process_id


def insert_case_group(
    session_id: int,
    process_id: int,
    case_group: str,
    description: str,
    change_status: str = "geaendert",
    norm_addressee: str = ADMINISTRATION,
) -> int:
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO case_groups (session_id, process_id, norm_addressee, case_group, description, change_status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (session_id, process_id, resolved, case_group, description, change_status),
    )
    _maybe_commit(conn)
    case_group_id = int(cur.lastrowid)
    _maybe_close(conn)
    return case_group_id


def insert_process_step(
    session_id: int,
    case_group_id: int,
    step: str,
    description: str,
    change_status: str = "geaendert",
    previous_id: int | None = None,
    next_id: int | None = None,
    norm_addressee: str = ADMINISTRATION,
) -> int:
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO process_steps (
            session_id,
            case_group_id,
            norm_addressee,
            step,
            description,
            change_status,
            previous_id,
            next_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            case_group_id,
            resolved,
            step,
            description,
            change_status,
            previous_id,
            next_id,
        ),
    )
    _maybe_commit(conn)
    step_id = int(cur.lastrowid)
    _maybe_close(conn)
    return step_id


def update_case_group_metrics(
    session_id: int,
    case_group_id: int,
    addressees_current: float | None = None,
    annual_frequency_current: float | None = None,
    addressees_proposed: float | None = None,
    annual_frequency_proposed: float | None = None,
    cases_current: float | None = None,
    cases_proposed: float | None = None,
) -> None:
    if (
        cases_current is None
        and addressees_current is not None
        and annual_frequency_current is not None
    ):
        cases_current = addressees_current * annual_frequency_current
    if (
        cases_proposed is None
        and addressees_proposed is not None
        and annual_frequency_proposed is not None
    ):
        cases_proposed = addressees_proposed * annual_frequency_proposed

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE case_groups
        SET addressees_current = ?,
            annual_frequency_current = ?,
            addressees_proposed = ?,
            annual_frequency_proposed = ?,
            cases_current = ?,
            cases_proposed = ?
        WHERE case_group_id = ? AND session_id = ? AND norm_addressee = ?
        """,
        (
            addressees_current,
            annual_frequency_current,
            addressees_proposed,
            annual_frequency_proposed,
            cases_current,
            cases_proposed,
            case_group_id,
            session_id,
            ADMINISTRATION,
        ),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def update_case_group_edited_metrics(
    session_id: int,
    norm_addressee: str,
    case_group_id: int,
    addressees_current_edited: float | None = None,
    annual_frequency_current_edited: float | None = None,
    addressees_proposed_edited: float | None = None,
    annual_frequency_proposed_edited: float | None = None,
) -> None:
    """Setze die Edited-Overrides einer Fallgruppe fuer einen bestimmten
    Normadressaten."""
    resolved = normalize_norm_addressee(norm_addressee)
    cases_current_edited: float | None = None
    cases_proposed_edited: float | None = None
    if (
        addressees_current_edited is not None
        and annual_frequency_current_edited is not None
    ):
        cases_current_edited = float(addressees_current_edited) * float(
            annual_frequency_current_edited
        )
    if (
        addressees_proposed_edited is not None
        and annual_frequency_proposed_edited is not None
    ):
        cases_proposed_edited = float(addressees_proposed_edited) * float(
            annual_frequency_proposed_edited
        )
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE case_groups
        SET addressees_current_edited = ?,
            annual_frequency_current_edited = ?,
            cases_current_edited = ?,
            addressees_proposed_edited = ?,
            annual_frequency_proposed_edited = ?,
            cases_proposed_edited = ?,
            last_edited_at = current_timestamp
        WHERE case_group_id = ? AND session_id = ? AND norm_addressee = ?
        """,
        (
            addressees_current_edited,
            annual_frequency_current_edited,
            cases_current_edited,
            addressees_proposed_edited,
            annual_frequency_proposed_edited,
            cases_proposed_edited,
            case_group_id,
            session_id,
            resolved,
        ),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def upsert_case_group_metrics_by_addressee(
    session_id: int,
    case_group_id: int,
    norm_addressee: str,
    addressees_current: float | None = None,
    annual_frequency_current: float | None = None,
    addressees_proposed: float | None = None,
    annual_frequency_proposed: float | None = None,
    cases_current: float | None = None,
    cases_proposed: float | None = None,
    case_metric_research_json: dict | list | None = None,
) -> None:
    resolved = normalize_norm_addressee(norm_addressee)
    if cases_current is None and addressees_current is not None and annual_frequency_current is not None:
        cases_current = addressees_current * annual_frequency_current
    if cases_proposed is None and addressees_proposed is not None and annual_frequency_proposed is not None:
        cases_proposed = addressees_proposed * annual_frequency_proposed
    conn = get_conn()
    cur = conn.cursor()
    assignments = [
        "addressees_current = ?",
        "annual_frequency_current = ?",
        "addressees_proposed = ?",
        "annual_frequency_proposed = ?",
        "cases_current = ?",
        "cases_proposed = ?",
    ]
    values: list[object] = [
        addressees_current,
        annual_frequency_current,
        addressees_proposed,
        annual_frequency_proposed,
        cases_current,
        cases_proposed,
    ]
    if case_metric_research_json is not None:
        assignments.append("case_metric_research_json = ?")
        values.append(json.dumps(case_metric_research_json, ensure_ascii=False))
    cur.execute(
        f"""
        UPDATE case_groups
        SET {", ".join(assignments)}
        WHERE case_group_id = ? AND session_id = ? AND norm_addressee = ?
        """,
        (*values, case_group_id, session_id, resolved),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def update_process_step_effort_split(
    session_id: int,
    step_id: int,
    hourly_rates_current: dict[str, float | None],
    time_required_current: dict[str, float | None],
    expenses_current: float | None,
    hourly_rates_proposed: dict[str, float | None],
    time_required_proposed: dict[str, float | None],
    expenses_proposed: float | None,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT execution_per_case FROM process_steps WHERE step_id = ? AND session_id = ? AND norm_addressee = ?",
        (step_id, session_id, ADMINISTRATION),
    )
    row = cur.fetchone()
    execution_per_case = row["execution_per_case"] if row is not None else None
    cur.execute(
        """
        UPDATE process_steps
        SET hourly_rate_a_current = ?, hourly_rate_b_current = ?, hourly_rate_c_current = ?, hourly_rate_d_current = ?,
            time_required_in_min_a_current = ?, time_required_in_min_b_current = ?, time_required_in_min_c_current = ?, time_required_in_min_d_current = ?,
            expenses_current = ?,
            hourly_rate_a_proposed = ?, hourly_rate_b_proposed = ?, hourly_rate_c_proposed = ?, hourly_rate_d_proposed = ?,
            time_required_in_min_a_proposed = ?, time_required_in_min_b_proposed = ?, time_required_in_min_c_proposed = ?, time_required_in_min_d_proposed = ?,
            expenses_proposed = ?,
            execution_per_case = ?
        WHERE step_id = ? AND session_id = ? AND norm_addressee = ?
        """,
        (
            hourly_rates_current.get("a"),
            hourly_rates_current.get("b"),
            hourly_rates_current.get("c"),
            hourly_rates_current.get("d"),
            time_required_current.get("a"),
            time_required_current.get("b"),
            time_required_current.get("c"),
            time_required_current.get("d"),
            expenses_current,
            hourly_rates_proposed.get("a"),
            hourly_rates_proposed.get("b"),
            hourly_rates_proposed.get("c"),
            hourly_rates_proposed.get("d"),
            time_required_proposed.get("a"),
            time_required_proposed.get("b"),
            time_required_proposed.get("c"),
            time_required_proposed.get("d"),
            expenses_proposed,
            execution_per_case,
            step_id,
            session_id,
            ADMINISTRATION,
        ),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def upsert_process_step_effort_split_by_addressee(
    session_id: int,
    step_id: int,
    norm_addressee: str,
    hourly_rates_current: dict[str, float | None],
    time_required_current: dict[str, float | None],
    expenses_current: float | None,
    hourly_rates_proposed: dict[str, float | None],
    time_required_proposed: dict[str, float | None],
    expenses_proposed: float | None,
    execution_per_case: bool | None = None,
    role_sources_current: list[dict] | None = None,
    role_sources_proposed: list[dict] | None = None,
) -> None:
    resolved = normalize_norm_addressee(norm_addressee)
    if resolved == CITIZENS:
        citizen_rates = (
            hourly_rates_current.get("a"),
            hourly_rates_current.get("b"),
            hourly_rates_current.get("c"),
            hourly_rates_current.get("d"),
            hourly_rates_proposed.get("a"),
            hourly_rates_proposed.get("b"),
            hourly_rates_proposed.get("c"),
            hourly_rates_proposed.get("d"),
        )
        if any(rate is not None for rate in citizen_rates):
            raise ValueError("Citizens effort must not persist hourly rates")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE process_steps
        SET hourly_rate_a_current = ?,
            hourly_rate_b_current = ?,
            hourly_rate_c_current = ?,
            hourly_rate_d_current = ?,
            time_required_in_min_a_current = ?,
            time_required_in_min_b_current = ?,
            time_required_in_min_c_current = ?,
            time_required_in_min_d_current = ?,
            expenses_current = ?,
            hourly_rate_a_proposed = ?,
            hourly_rate_b_proposed = ?,
            hourly_rate_c_proposed = ?,
            hourly_rate_d_proposed = ?,
            time_required_in_min_a_proposed = ?,
            time_required_in_min_b_proposed = ?,
            time_required_in_min_c_proposed = ?,
            time_required_in_min_d_proposed = ?,
            expenses_proposed = ?,
            execution_per_case = COALESCE(?, execution_per_case),
            role_sources_current_json = ?,
            role_sources_proposed_json = ?
        WHERE step_id = ? AND session_id = ? AND norm_addressee = ?
        """,
        (
            hourly_rates_current.get("a"),
            hourly_rates_current.get("b"),
            hourly_rates_current.get("c"),
            hourly_rates_current.get("d"),
            time_required_current.get("a"),
            time_required_current.get("b"),
            time_required_current.get("c"),
            time_required_current.get("d"),
            expenses_current,
            hourly_rates_proposed.get("a"),
            hourly_rates_proposed.get("b"),
            hourly_rates_proposed.get("c"),
            hourly_rates_proposed.get("d"),
            time_required_proposed.get("a"),
            time_required_proposed.get("b"),
            time_required_proposed.get("c"),
            time_required_proposed.get("d"),
            expenses_proposed,
            (int(bool(execution_per_case)) if execution_per_case is not None else None),
            json.dumps(role_sources_current) if role_sources_current else None,
            json.dumps(role_sources_proposed) if role_sources_proposed else None,
            step_id,
            session_id,
            resolved,
        ),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def update_process_step_cost(
    session_id: int,
    step_id: int,
    cost_current: float | None,
    cost_proposed: float | None,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE process_steps
        SET cost_current = ?, cost_proposed = ?
        WHERE step_id = ? AND session_id = ?
        """,
        (cost_current, cost_proposed, step_id, session_id),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def upsert_process_step_cost_by_addressee(
    session_id: int,
    step_id: int,
    norm_addressee: str,
    cost_current: float | None,
    cost_proposed: float | None,
) -> None:
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE process_steps
        SET cost_current = ?,
            cost_proposed = ?
        WHERE step_id = ? AND session_id = ? AND norm_addressee = ?
        """,
        (
            cost_current,
            cost_proposed,
            step_id,
            session_id,
            resolved,
        ),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def update_case_group_cost(
    session_id: int,
    case_group_id: int,
    cost: float | None,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE case_groups
        SET cost = ?
        WHERE case_group_id = ? AND session_id = ?
        """,
        (cost, case_group_id, session_id),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def upsert_case_group_cost_by_addressee(
    session_id: int,
    case_group_id: int,
    norm_addressee: str,
    cost: float | None,
) -> None:
    resolved = normalize_norm_addressee(norm_addressee)
    if resolved == ADMINISTRATION:
        update_case_group_cost(session_id, case_group_id, cost)
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE case_groups
        SET cost = ?
        WHERE case_group_id = ? AND session_id = ? AND norm_addressee = ?
        """,
        (cost, case_group_id, session_id, resolved),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def update_process_cost(
    session_id: int,
    process_id: int,
    cost: float | None,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE processes
        SET cost = ?
        WHERE process_id = ? AND session_id = ?
        """,
        (cost, process_id, session_id),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def update_process_step_next(step_id: int, next_id: int | None) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE process_steps SET next_id = ? WHERE step_id = ?",
        (next_id, step_id),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def update_regulation_process(
    regulation_id: int,
    process_id: int,
    norm_addressee: str = ADMINISTRATION,
) -> bool:
    resolved = normalize_norm_addressee(norm_addressee)
    if resolved == ADMINISTRATION:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE regulations
            SET process_id = ?
            WHERE regulation_id = ?
              AND process_id IS NULL
            """,
            (process_id, regulation_id),
        )
        _maybe_commit(conn)
        updated = cur.rowcount > 0
        _maybe_close(conn)
        return updated

    regulation = get_regulation_by_id(regulation_id)
    if not regulation:
        return False
    session_id = int(regulation["session_id"])
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO regulation_process_links_by_addressee (
            session_id, norm_addressee, regulation_id, process_id
        )
        SELECT ?, ?, ?, ?
        WHERE NOT EXISTS (
            SELECT 1
            FROM regulation_process_links_by_addressee
            WHERE session_id = ?
              AND norm_addressee = ?
              AND regulation_id = ?
        )
        """,
        (session_id, resolved, regulation_id, process_id, session_id, resolved, regulation_id),
    )
    _maybe_commit(conn)
    updated = cur.rowcount > 0
    _maybe_close(conn)
    return updated


def replace_process_step_regulation_links(
    session_id: int,
    step_id: int,
    norm_addressee: str,
    regulation_ids: list[int],
) -> None:
    resolved = normalize_norm_addressee(norm_addressee)
    unique_ids = sorted({int(regulation_id) for regulation_id in regulation_ids})
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM process_step_regulation_links
        WHERE session_id = ? AND norm_addressee = ? AND step_id = ?
        """,
        (session_id, resolved, step_id),
    )
    for regulation_id in unique_ids:
        cur.execute(
            """
            INSERT INTO process_step_regulation_links (
                session_id, norm_addressee, step_id, regulation_id
            )
            VALUES (?, ?, ?, ?)
            """,
            (session_id, resolved, step_id, regulation_id),
        )
    _maybe_commit(conn)
    _maybe_close(conn)


def get_process_step_regulation_ids_by_step(
    session_id: int,
    norm_addressee: str,
) -> dict[int, list[int]]:
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT step_id, regulation_id
        FROM process_step_regulation_links
        WHERE session_id = ? AND norm_addressee = ?
        ORDER BY step_id, regulation_id
        """,
        (session_id, resolved),
    )
    rows = cur.fetchall()
    _maybe_close(conn)
    links: dict[int, list[int]] = {}
    for row in rows:
        links.setdefault(int(row["step_id"]), []).append(int(row["regulation_id"]))
    return links


def update_session_documents(
    app_session_id: str,
    current_filename: str | None,
    proposed_filename: str | None,
    owner_user_id: int | None = None,
) -> None:
    current_id = None
    proposed_id = None
    if current_filename:
        current = get_law_by_filename(current_filename, owner_user_id=owner_user_id)
        if current is None:
            raise ValueError("Current law not found")
        current_id = current["document_id"]
    if proposed_filename:
        proposed = get_law_by_filename(proposed_filename, owner_user_id=owner_user_id)
        if proposed is None:
            raise ValueError("Proposed law not found")
        proposed_id = proposed["document_id"]

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE sessions
        SET current_law_id = ?, proposed_law_id = ?
        WHERE app_session_id = ?
        """,
        (current_id, proposed_id, app_session_id),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def update_session_summary(
    app_session_id: str,
    law_diff_title: str,
    law_diff_summary: str,
    law_diff_blurb: str | None = None,
) -> None:
    blurb = law_diff_blurb if law_diff_blurb is not None else law_diff_summary
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE sessions
        SET law_diff_title = ?, law_diff_blurb = ?, law_diff_summary = ?
        WHERE app_session_id = ?
        """,
        (law_diff_title, blurb, law_diff_summary, app_session_id),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def upsert_session_total_costs_by_addressee(
    session_id: int,
    norm_addressee: str,
    total_cost: float | None,
    bureaucracy_cost: float | None,
    total_time_minutes: float | None,
    total_expenses: float | None,
) -> None:
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO session_total_costs_by_addressee (
            session_id,
            norm_addressee,
            total_cost,
            bureaucracy_cost,
            total_time_minutes,
            total_expenses
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id, norm_addressee) DO UPDATE SET
            total_cost = excluded.total_cost,
            bureaucracy_cost = excluded.bureaucracy_cost,
            total_time_minutes = excluded.total_time_minutes,
            total_expenses = excluded.total_expenses
        """,
        (
            session_id,
            resolved,
            total_cost,
            bureaucracy_cost,
            total_time_minutes,
            total_expenses,
        ),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def get_session_total_costs_by_addressee(
    session_id: int,
    norm_addressee: str,
) -> dict | None:
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            session_id,
            norm_addressee,
            total_cost,
            bureaucracy_cost,
            total_time_minutes,
            total_expenses
        FROM session_total_costs_by_addressee
        WHERE session_id = ? AND norm_addressee = ?
        """,
        (session_id, resolved),
    )
    row = cur.fetchone()
    _maybe_close(conn)
    return dict(row) if row else None


def clear_session_summary(session_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE sessions
        SET law_diff_title = NULL,
            law_diff_blurb = NULL,
            law_diff_summary = NULL,
            current_law_id = NULL,
            proposed_law_id = NULL
        WHERE session_id = ?
        """,
        (session_id,),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def replace_process_step_personnel_effort(
    session_id: int,
    norm_addressee: str,
    step_id: int,
    rows: list[dict],
) -> None:
    """Replace all personnel-effort rows for one step (fresh effort calc).

    `rows` items carry: period ('current'|'proposed'), qualification,
    wage_source_kind, wage_source_value, time_required_in_min (optional) and
    model_hourly_rate. Replace semantics keep re-runs idempotent.
    """
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    # Integrity guard at the DB layer: the two foreign keys (session_id, step_id)
    # are independent, so enforce that the step actually belongs to this
    # session+addressee instead of relying on every caller to pass a matching
    # combination.
    belongs = cur.execute(
        """
        SELECT 1 FROM process_steps
        WHERE step_id = ? AND session_id = ? AND norm_addressee = ?
        """,
        (step_id, session_id, resolved),
    ).fetchone()
    if belongs is None:
        _maybe_close(conn)
        raise ValueError(
            f"process_step {step_id} does not belong to session {session_id} "
            f"/ norm_addressee {resolved!r}"
        )
    cur.execute(
        """
        DELETE FROM process_step_personnel_effort
        WHERE session_id = ? AND norm_addressee = ? AND step_id = ?
        """,
        (session_id, resolved, step_id),
    )
    for row in rows:
        cur.execute(
            """
            INSERT INTO process_step_personnel_effort (
                session_id,
                norm_addressee,
                step_id,
                period,
                qualification,
                wage_source_kind,
                wage_source_value,
                time_required_in_min,
                model_hourly_rate
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                resolved,
                step_id,
                row["period"],
                row["qualification"],
                row["wage_source_kind"],
                row["wage_source_value"],
                row.get("time_required_in_min"),
                row["model_hourly_rate"],
            ),
        )
    _maybe_commit(conn)
    _maybe_close(conn)


def list_process_step_personnel_effort(
    session_id: int,
    norm_addressee: str,
    step_id: int | None = None,
) -> list[dict]:
    """Read personnel-effort rows for a session+addressee (optionally one step)."""
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    if step_id is None:
        cur.execute(
            """
            SELECT * FROM process_step_personnel_effort
            WHERE session_id = ? AND norm_addressee = ?
            ORDER BY step_id, period, qualification, wage_source_value
            """,
            (session_id, resolved),
        )
    else:
        cur.execute(
            """
            SELECT * FROM process_step_personnel_effort
            WHERE session_id = ? AND norm_addressee = ? AND step_id = ?
            ORDER BY period, qualification, wage_source_value
            """,
            (session_id, resolved, step_id),
        )
    rows = [dict(row) for row in cur.fetchall()]
    _maybe_close(conn)
    return rows


def list_session_personnel_effort(session_id: int) -> list[dict]:
    """All personnel-effort rows of a session across norm addressees (step_id is a
    global PK, so callers can group by step_id)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM process_step_personnel_effort
        WHERE session_id = ?
        ORDER BY step_id, period, qualification, wage_source_value
        """,
        (session_id,),
    )
    rows = [dict(row) for row in cur.fetchall()]
    _maybe_close(conn)
    return rows


def upsert_personnel_effort_time_edit(
    session_id: int,
    norm_addressee: str,
    step_id: int,
    period: str,
    qualification: str,
    wage_source_kind: str,
    wage_source_value: str,
    time_required_in_min_edited: float | None,
) -> int:
    """Set or clear the edited time of one personnel-effort row.

    Creates the row when the user adds time for a (qualification, source) the LLM
    did not assign (model_hourly_rate from the wage table, model time NULL); and
    removes a user-created row when its edit is cleared (an LLM row keeps its model
    time and only clears the edit). Returns 1 when something changed, else 0.
    Raises ValueError on an unknown combination or a step not owned by the session.
    """
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    existing = cur.execute(
        """
        SELECT effort_id, time_required_in_min, time_required_in_min_edited
        FROM process_step_personnel_effort
        WHERE session_id = ? AND norm_addressee = ? AND step_id = ? AND period = ?
            AND qualification = ? AND wage_source_kind = ? AND wage_source_value = ?
        """,
        (session_id, resolved, step_id, period, qualification, wage_source_kind, wage_source_value),
    ).fetchone()

    # Row effort edits join the same no-op/audit contract as the other EA edits:
    # only a real change to the edited time persists, bumps last_edited_at and writes
    # an audit row; an unchanged payload is a no-op (returns 0, rejected as 422).
    audit_field = f"time_required_in_min_edited[{period}/{qualification}/{wage_source_value}]"

    def _audit(old_value: float | None, new_value: float | None) -> None:
        insert_edit_audit_row(
            cur,
            session_id=session_id,
            entity_type="personnel_effort",
            entity_id=step_id,
            field_name=audit_field,
            old_value=old_value,
            new_value=new_value,
        )

    if time_required_in_min_edited is None:
        if existing is None:
            _maybe_close(conn)
            return 0
        old_edited = existing["time_required_in_min_edited"]
        if existing["time_required_in_min"] is None:
            # User-created row (no model time): clearing removes it entirely.
            cur.execute(
                "DELETE FROM process_step_personnel_effort WHERE effort_id = ?",
                (existing["effort_id"],),
            )
        elif old_edited is None:
            # LLM row whose edit is already cleared: nothing changes.
            _maybe_close(conn)
            return 0
        else:
            cur.execute(
                """
                UPDATE process_step_personnel_effort
                SET time_required_in_min_edited = NULL, last_edited_at = current_timestamp
                WHERE effort_id = ?
                """,
                (existing["effort_id"],),
            )
        _audit(old_edited, None)
        _maybe_commit(conn)
        _maybe_close(conn)
        return 1

    new_edited = float(time_required_in_min_edited)
    if existing is not None:
        old_edited = existing["time_required_in_min_edited"]
        if not value_changed(old_edited, new_edited):
            _maybe_close(conn)
            return 0
        cur.execute(
            """
            UPDATE process_step_personnel_effort
            SET time_required_in_min_edited = ?, last_edited_at = current_timestamp
            WHERE effort_id = ?
            """,
            (new_edited, existing["effort_id"]),
        )
        _audit(old_edited, new_edited)
        _maybe_commit(conn)
        _maybe_close(conn)
        return 1

    # No row yet: create one for the LLM-unassigned (qualification, source).
    model_rate = get_model_hourly_rate(resolved, wage_source_value, qualification)
    if model_rate is None:
        _maybe_close(conn)
        raise ValueError(
            f"Unknown wage combination: {wage_source_value!r} / {qualification!r} "
            f"for {resolved!r}"
        )
    belongs = cur.execute(
        "SELECT 1 FROM process_steps WHERE step_id = ? AND session_id = ? AND norm_addressee = ?",
        (step_id, session_id, resolved),
    ).fetchone()
    if belongs is None:
        _maybe_close(conn)
        raise ValueError(
            f"process_step {step_id} does not belong to session {session_id} / {resolved!r}"
        )
    cur.execute(
        """
        INSERT INTO process_step_personnel_effort (
            session_id, norm_addressee, step_id, period, qualification,
            wage_source_kind, wage_source_value, time_required_in_min,
            time_required_in_min_edited, model_hourly_rate, last_edited_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, current_timestamp)
        """,
        (
            session_id, resolved, step_id, period, qualification,
            wage_source_kind, wage_source_value,
            new_edited, model_rate,
        ),
    )
    _audit(None, new_edited)
    _maybe_commit(conn)
    _maybe_close(conn)
    return 1


def clear_personnel_effort_time_edits(session_id: int) -> int:
    """Reset all personnel-effort time edits of a session to their model state.

    Mirrors the per-row clear in `upsert_personnel_effort_time_edit(..., None)` so a
    global reset yields the exact same DB state as N per-row resets:
    - user-created rows (no model time, `time_required_in_min IS NULL`) are DELETED,
      because there is no model value to fall back to; this also clears any leftover
      NULL/NULL zombie rows.
    - model (LLM) rows keep their `time_required_in_min` and only have their
      `time_required_in_min_edited` overlay nulled.

    Invariant after reset: every surviving row is a model row; user-created rows
    without a model time are removed (analogous to the per-row clear path). DELETE
    runs before UPDATE. Returns the total number of affected rows. Transaction-safe:
    inside an open transaction() block _maybe_commit / _maybe_close are no-ops.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM process_step_personnel_effort
        WHERE session_id = ? AND time_required_in_min IS NULL
        """,
        (session_id,),
    )
    deleted = cur.rowcount
    cur.execute(
        """
        UPDATE process_step_personnel_effort
        SET time_required_in_min_edited = NULL, last_edited_at = current_timestamp
        WHERE session_id = ? AND time_required_in_min_edited IS NOT NULL
        """,
        (session_id,),
    )
    updated = cur.rowcount
    _maybe_commit(conn)
    _maybe_close(conn)
    return deleted + updated


def get_session_wage_rate_overrides(
    session_id: int,
    norm_addressee: str,
) -> dict[tuple[str, str, str], float]:
    """Row-keyed session wage overrides as {(kind, value, qualification): rate}.

    Only rows with a non-null hourly_rate_edited are returned. Empty until the
    Phase C editing UI writes to session_wage_rate_overrides; the cost engine
    already reads it so no further cost change is needed when that UI lands.
    """
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT wage_source_kind, wage_source_value, qualification, hourly_rate_edited
        FROM session_wage_rate_overrides
        WHERE session_id = ? AND norm_addressee = ? AND hourly_rate_edited IS NOT NULL
        """,
        (session_id, resolved),
    )
    overrides = {
        (row["wage_source_kind"], row["wage_source_value"], row["qualification"]):
            float(row["hourly_rate_edited"])
        for row in cur.fetchall()
    }
    _maybe_close(conn)
    return overrides


def list_session_wage_rate_rows(
    session_id: int,
    norm_addressee: str,
) -> list[dict]:
    """Editable wage rows for the session: for each wage source actually used in
    the session, every qualification of the addressee with its model rate and the
    current override (if any). Drives the row-based "Globale Loehnsaetze" tab.
    """
    resolved = normalize_norm_addressee(norm_addressee)
    if resolved == CITIZENS:
        return []
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT wage_source_kind, wage_source_value
        FROM process_step_personnel_effort
        WHERE session_id = ? AND norm_addressee = ?
        ORDER BY wage_source_kind, wage_source_value
        """,
        (session_id, resolved),
    )
    used_sources = [(r["wage_source_kind"], r["wage_source_value"]) for r in cur.fetchall()]
    cur.execute(
        """
        SELECT wage_source_kind, wage_source_value, qualification, hourly_rate_edited
        FROM session_wage_rate_overrides
        WHERE session_id = ? AND norm_addressee = ? AND hourly_rate_edited IS NOT NULL
        """,
        (session_id, resolved),
    )
    overrides = {
        (r["wage_source_kind"], r["wage_source_value"], r["qualification"]):
            float(r["hourly_rate_edited"])
        for r in cur.fetchall()
    }
    _maybe_close(conn)

    qualifications = PERSONNEL_QUALIFICATION_BY_SLOT.get(resolved, {})
    rows: list[dict] = []
    for kind, value in used_sources:
        for slot in PAY_RATE_KEYS:
            qualification = qualifications.get(slot)
            if qualification is None:
                continue
            model = get_model_hourly_rate(resolved, value, qualification)
            if model is None:
                continue
            rows.append(
                {
                    "wage_source_kind": kind,
                    "wage_source_value": value,
                    "qualification": qualification,
                    "model_hourly_rate": model,
                    "hourly_rate_edited": overrides.get((kind, value, qualification)),
                }
            )
    return rows


def upsert_session_wage_rate_override(
    session_id: int,
    norm_addressee: str,
    wage_source_kind: str,
    wage_source_value: str,
    qualification: str,
    hourly_rate_edited: float | None,
) -> int:
    """Set (or clear, when hourly_rate_edited is None) one row-keyed wage override.

    Row wage overrides join the same no-op/audit contract as the other EA edits:
    only a real change to the override persists, bumps last_edited_at and writes an
    audit row; an unchanged payload is a no-op (returns 0, rejected as 422). Returns
    1 when something changed, else 0.
    """
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    previous = cur.execute(
        """
        SELECT hourly_rate_edited FROM session_wage_rate_overrides
        WHERE session_id = ? AND norm_addressee = ? AND wage_source_kind = ?
            AND wage_source_value = ? AND qualification = ?
        """,
        (session_id, resolved, wage_source_kind, wage_source_value, qualification),
    ).fetchone()
    old_value = previous["hourly_rate_edited"] if previous is not None else None
    new_value = float(hourly_rate_edited) if hourly_rate_edited is not None else None
    if not value_changed(old_value, new_value):
        _maybe_close(conn)
        return 0

    if new_value is None:
        cur.execute(
            """
            DELETE FROM session_wage_rate_overrides
            WHERE session_id = ? AND norm_addressee = ? AND wage_source_kind = ?
                AND wage_source_value = ? AND qualification = ?
            """,
            (session_id, resolved, wage_source_kind, wage_source_value, qualification),
        )
    else:
        cur.execute(
            """
            INSERT INTO session_wage_rate_overrides (
                session_id, norm_addressee, wage_source_kind, wage_source_value,
                qualification, hourly_rate_edited, last_edited_at
            )
            VALUES (?, ?, ?, ?, ?, ?, current_timestamp)
            ON CONFLICT(session_id, norm_addressee, wage_source_kind,
                        wage_source_value, qualification)
            DO UPDATE SET
                hourly_rate_edited = excluded.hourly_rate_edited,
                last_edited_at = current_timestamp
            """,
            (
                session_id,
                resolved,
                wage_source_kind,
                wage_source_value,
                qualification,
                new_value,
            ),
        )
    insert_edit_audit_row(
        cur,
        session_id=session_id,
        entity_type="wage_rate",
        entity_id=None,
        field_name=f"hourly_rate_edited[{wage_source_value}/{qualification}]",
        old_value=old_value,
        new_value=new_value,
    )
    _maybe_commit(conn)
    _maybe_close(conn)
    return 1


def clear_session_wage_rate_overrides(session_id: int) -> int:
    """Delete all row-keyed wage overrides of a session (all norm addressees).

    Mirrors upsert_session_wage_rate_override(..., hourly_rate_edited=None), which
    deletes a single override row; model rates are constants from the wage table, so
    deleting the override rows loses no model value. Returns the number of deleted
    rows. Transaction-safe: inside an open transaction() block _maybe_commit /
    _maybe_close are no-ops, so this runs in the caller's transaction.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM session_wage_rate_overrides WHERE session_id = ?",
        (session_id,),
    )
    deleted = cur.rowcount
    _maybe_commit(conn)
    _maybe_close(conn)
    return deleted


def clear_effort_metrics(session_id: int, norm_addressee: str = ADMINISTRATION) -> None:
    # Effort undo clears the step `_edited` times and role_sources, but intentionally
    # NOT the manual pay-rate overrides (sessions.pay_rate_edited_* /
    # session_pay_rate_overrides_by_addressee). The override is a standalone
    # session-level user setting, not an effort result, so it survives a re-run.
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE case_groups
        SET addressees_current = NULL,
            annual_frequency_current = NULL,
            cases_current = NULL,
            addressees_current_edited = NULL,
            annual_frequency_current_edited = NULL,
            cases_current_edited = NULL,
            addressees_proposed = NULL,
            annual_frequency_proposed = NULL,
            cases_proposed = NULL,
            addressees_proposed_edited = NULL,
            annual_frequency_proposed_edited = NULL,
            cases_proposed_edited = NULL,
            case_metric_research_json = NULL,
            last_edited_at = NULL
        WHERE session_id = ? AND norm_addressee = ?
        """,
        (session_id, resolved),
    )
    cur.execute(
        """
        UPDATE process_steps
        SET hourly_rate_a_current = NULL,
            hourly_rate_b_current = NULL,
            hourly_rate_c_current = NULL,
            hourly_rate_d_current = NULL,
            time_required_in_min_a_current = NULL,
            time_required_in_min_b_current = NULL,
            time_required_in_min_c_current = NULL,
            time_required_in_min_d_current = NULL,
            time_required_in_min_a_current_edited = NULL,
            time_required_in_min_b_current_edited = NULL,
            time_required_in_min_c_current_edited = NULL,
            time_required_in_min_d_current_edited = NULL,
            expenses_current = NULL,
            expenses_current_edited = NULL,
            hourly_rate_a_proposed = NULL,
            hourly_rate_b_proposed = NULL,
            hourly_rate_c_proposed = NULL,
            hourly_rate_d_proposed = NULL,
            time_required_in_min_a_proposed = NULL,
            time_required_in_min_b_proposed = NULL,
            time_required_in_min_c_proposed = NULL,
            time_required_in_min_d_proposed = NULL,
            time_required_in_min_a_proposed_edited = NULL,
            time_required_in_min_b_proposed_edited = NULL,
            time_required_in_min_c_proposed_edited = NULL,
            time_required_in_min_d_proposed_edited = NULL,
            expenses_proposed = NULL,
            expenses_proposed_edited = NULL,
            last_edited_at = NULL,
            role_sources_current_json = NULL,
            role_sources_proposed_json = NULL
        WHERE session_id = ? AND norm_addressee = ?
        """,
        (session_id, resolved),
    )
    # Row-based effort rows are an effort result, so undo clears them too
    # (mirrors the slot columns above). Session wage overrides are a standalone
    # user setting and intentionally survive, like the legacy pay-rate edits.
    cur.execute(
        """
        DELETE FROM process_step_personnel_effort
        WHERE session_id = ? AND norm_addressee = ?
        """,
        (session_id, resolved),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def clear_costs(session_id: int, norm_addressee: str = ADMINISTRATION) -> None:
    resolved = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE process_steps
        SET cost_current = NULL,
            cost_proposed = NULL
        WHERE session_id = ? AND norm_addressee = ?
        """,
        (session_id, resolved),
    )
    cur.execute(
        """
        UPDATE case_groups
        SET cost = NULL
        WHERE session_id = ? AND norm_addressee = ?
        """,
        (session_id, resolved),
    )
    cur.execute(
        """
        UPDATE processes
        SET cost = NULL
        WHERE session_id = ? AND norm_addressee = ?
        """,
        (session_id, resolved),
    )
    cur.execute(
        """
        DELETE FROM session_total_costs_by_addressee
        WHERE session_id = ? AND norm_addressee = ?
        """,
        (session_id, resolved),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def delete_process_steps_for_session(
    session_id: int,
    norm_addressee: str | None = None,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    if norm_addressee is None:
        cur.execute(
            "DELETE FROM process_steps WHERE session_id = ?",
            (session_id,),
        )
    else:
        cur.execute(
            "DELETE FROM process_steps WHERE session_id = ? AND norm_addressee = ?",
            (session_id, normalize_norm_addressee(norm_addressee)),
        )
    _maybe_commit(conn)
    _maybe_close(conn)


def delete_case_groups_for_session(
    session_id: int,
    norm_addressee: str | None = None,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    if norm_addressee is None:
        cur.execute(
            "DELETE FROM case_groups WHERE session_id = ?",
            (session_id,),
        )
    else:
        resolved = normalize_norm_addressee(norm_addressee)
        cur.execute(
            "DELETE FROM case_groups WHERE session_id = ? AND norm_addressee = ?",
            (session_id, resolved),
        )
    _maybe_commit(conn)
    _maybe_close(conn)


def delete_processes_for_session(
    session_id: int,
    norm_addressee: str | None = None,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    if norm_addressee is None:
        cur.execute(
            "DELETE FROM processes WHERE session_id = ?",
            (session_id,),
        )
    else:
        resolved = normalize_norm_addressee(norm_addressee)
        cur.execute(
            "DELETE FROM processes WHERE session_id = ? AND norm_addressee = ?",
            (session_id, resolved),
        )
    _maybe_commit(conn)
    _maybe_close(conn)


def delete_regulations_for_session(session_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM regulations WHERE session_id = ?",
        (session_id,),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def delete_llm_answers(session_id: int, prompt_ids: Iterable[str]) -> None:
    ids = [pid for pid in prompt_ids if pid]
    if not ids:
        return
    conn = get_conn()
    cur = conn.cursor()
    placeholders = ", ".join(["?"] * len(ids))
    cur.execute(
        f"DELETE FROM llm_answers WHERE session_id = ? AND prompt_id IN ({placeholders})",
        (session_id, *ids),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def upsert_tile(
    tile: Tile,
    session_id: int,
    norm_addressee: str = ADMINISTRATION,
) -> None:
    resolved_session_id = int(session_id)
    resolved_addressee = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO tiles (session_id, norm_addressee, id, title, text, meta, col, row, deletable)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id, norm_addressee, id) DO UPDATE SET
            title = excluded.title,
            text = excluded.text,
            meta = excluded.meta,
            col = excluded.col,
            row = excluded.row,
            deletable = excluded.deletable
        """,
        (
            resolved_session_id,
            resolved_addressee,
            tile.id,
            tile.title,
            tile.text,
            json.dumps(tile.meta_information or {}, ensure_ascii=False),
            tile.column,
            tile.row,
            1 if tile.deletable else 0,
        ),
    )
    _maybe_commit(conn)
    _maybe_close(conn)
    if tile.link_from_tile is not None:
        set_links(
            tile.id,
            tile.link_from_tile,
            session_id=resolved_session_id,
            norm_addressee=resolved_addressee,
        )


def delete_tile(tile_id: str, session_id: int, norm_addressee: str = ADMINISTRATION) -> None:
    resolved_session_id = int(session_id)
    resolved_addressee = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM links
        WHERE session_id = ? AND norm_addressee = ? AND (target = ? OR source = ?)
        """,
        (resolved_session_id, resolved_addressee, tile_id, tile_id),
    )
    cur.execute(
        "DELETE FROM tiles WHERE session_id = ? AND norm_addressee = ? AND id = ?",
        (resolved_session_id, resolved_addressee, tile_id),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def clear_tiles(session_id: int, norm_addressee: str = ADMINISTRATION) -> None:
    conn = get_conn()
    cur = conn.cursor()
    resolved_session_id = int(session_id)
    resolved_addressee = normalize_norm_addressee(norm_addressee)
    cur.execute(
        "DELETE FROM links WHERE session_id = ? AND norm_addressee = ?",
        (resolved_session_id, resolved_addressee),
    )
    cur.execute(
        "DELETE FROM tiles WHERE session_id = ? AND norm_addressee = ?",
        (resolved_session_id, resolved_addressee),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def set_links(
    target_id: str,
    sources: Iterable[str],
    session_id: int,
    norm_addressee: str = ADMINISTRATION,
) -> None:
    resolved_session_id = int(session_id)
    resolved_addressee = normalize_norm_addressee(norm_addressee)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM links WHERE session_id = ? AND norm_addressee = ? AND target = ?",
        (resolved_session_id, resolved_addressee, target_id),
    )
    for src in sources:
        cur.execute(
            """
            INSERT OR REPLACE INTO links (session_id, norm_addressee, source, target)
            VALUES (?, ?, ?, ?)
            """,
            (resolved_session_id, resolved_addressee, src, target_id),
        )
    _maybe_commit(conn)
    _maybe_close(conn)
