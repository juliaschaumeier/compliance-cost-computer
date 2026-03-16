from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Iterable, List

from .config import settings
from .db_formatting import (
    build_case_group_tile_text,
    build_process_step_tile_text,
    build_process_tile_text,
    format_currency,
    format_number,
)
from .models import Tile

_TX_CONN: ContextVar[sqlite3.Connection | None] = ContextVar("tx_conn", default=None)


LLM_ANSWER_STATE_PENDING = "pending"
LLM_ANSWER_STATE_ACTIVE = "active"
LLM_ANSWER_STATE_INVALID = "invalid"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _create_session_scoped_tile_tables(cur: sqlite3.Cursor) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tiles (
            session_id INTEGER NOT NULL,
            id TEXT NOT NULL,
            title TEXT NOT NULL,
            text TEXT NOT NULL,
            meta JSON,
            col INTEGER NOT NULL DEFAULT 0,
            row INTEGER NOT NULL DEFAULT 0,
            deletable INTEGER NOT NULL DEFAULT 1 CHECK (deletable IN (0, 1)),
            PRIMARY KEY (session_id, id),
            FOREIGN KEY (session_id)
            REFERENCES sessions(session_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS links (
            session_id INTEGER NOT NULL,
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            PRIMARY KEY (session_id, source, target),
            FOREIGN KEY (session_id, source)
            REFERENCES tiles(session_id, id)
                ON UPDATE CASCADE
                ON DELETE CASCADE,
            FOREIGN KEY (session_id, target)
            REFERENCES tiles(session_id, id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        );
        """
    )


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


def _create_process_steps_table(cur: sqlite3.Cursor, table_name: str = "process_steps") -> None:
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            step_id                         INTEGER PRIMARY KEY,
            case_group_id                   INTEGER NOT NULL,
            session_id                      INTEGER NOT NULL,
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
            expenses_current                REAL,
            hourly_rate_a_proposed          REAL,
            hourly_rate_b_proposed          REAL,
            hourly_rate_c_proposed          REAL,
            hourly_rate_d_proposed          REAL,
            time_required_in_min_a_proposed REAL,
            time_required_in_min_b_proposed REAL,
            time_required_in_min_c_proposed REAL,
            time_required_in_min_d_proposed REAL,
            expenses_proposed               REAL,
            cost_current                    REAL,
            cost_proposed                   REAL,
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


def _migrate_process_steps_drop_execution_per_case(cur: sqlite3.Cursor) -> None:
    """Migration helper: rebuild process_steps without execution_per_case.

    This is a one-off compatibility migration for legacy/dev DB files that
    still contain the deprecated column. Safe to remove once production starts
    from an empty DB with the final schema.
    """
    if not _table_has_column(cur, "process_steps", "execution_per_case"):
        return

    cur.execute("PRAGMA foreign_keys = OFF;")
    try:
        cur.execute("DROP TABLE IF EXISTS process_steps_new")
        _create_process_steps_table(cur, "process_steps_new")
        cur.execute(
            """
            INSERT INTO process_steps_new (
                step_id, case_group_id, session_id, step, description, change_status,
                created_at, previous_id, next_id,
                hourly_rate_a_current, hourly_rate_b_current, hourly_rate_c_current, hourly_rate_d_current,
                time_required_in_min_a_current, time_required_in_min_b_current, time_required_in_min_c_current, time_required_in_min_d_current,
                expenses_current,
                hourly_rate_a_proposed, hourly_rate_b_proposed, hourly_rate_c_proposed, hourly_rate_d_proposed,
                time_required_in_min_a_proposed, time_required_in_min_b_proposed, time_required_in_min_c_proposed, time_required_in_min_d_proposed,
                expenses_proposed,
                cost_current, cost_proposed
            )
            SELECT
                step_id, case_group_id, session_id, step, description, change_status,
                created_at, previous_id, next_id,
                hourly_rate_a_current, hourly_rate_b_current, hourly_rate_c_current, hourly_rate_d_current,
                time_required_in_min_a_current, time_required_in_min_b_current, time_required_in_min_c_current, time_required_in_min_d_current,
                expenses_current,
                hourly_rate_a_proposed, hourly_rate_b_proposed, hourly_rate_c_proposed, hourly_rate_d_proposed,
                time_required_in_min_a_proposed, time_required_in_min_b_proposed, time_required_in_min_c_proposed, time_required_in_min_d_proposed,
                expenses_proposed,
                cost_current, cost_proposed
            FROM process_steps
            """
        )
        cur.execute("DROP TABLE process_steps")
        cur.execute("ALTER TABLE process_steps_new RENAME TO process_steps")
    finally:
        cur.execute("PRAGMA foreign_keys = ON;")


def _run_legacy_migrations(cur: sqlite3.Cursor) -> None:
    """Migration helper: run one-off in-place upgrades for legacy/dev DB files.

    This helper exists solely for non-empty databases created before the final
    schema. Safe to remove when production starts from an empty DB and no
    in-place upgrade path is required.
    """
    needs_used_models_backfill = not _table_has_column(cur, "sessions", "used_llm_models")

    _ensure_column(cur, "sessions", "law_diff_title", "TEXT")
    _ensure_column(cur, "sessions", "law_diff_blurb", "TEXT")
    _ensure_column(cur, "sessions", "law_diff_summary", "TEXT")
    _ensure_column(cur, "sessions", "used_llm_models", "TEXT")

    _ensure_column(cur, "llm_answers", "input_tokens", "INTEGER")
    _ensure_column(cur, "llm_answers", "output_tokens", "INTEGER")
    _ensure_column(cur, "llm_answers", "hidden_thinking_tokens", "INTEGER")
    _ensure_column(cur, "llm_answers", "estimated_cost_usd", "REAL")
    _ensure_column(cur, "llm_answers", "provider_response_json", "JSON")
    _ensure_column(
        cur,
        "llm_answers",
        "answer_state",
        "TEXT NOT NULL DEFAULT 'active'",
    )
    _ensure_column(cur, "llm_answers", "state_reason", "TEXT")
    cur.execute(
        """
        UPDATE llm_answers
        SET answer_state = 'active'
        WHERE answer_state IS NULL OR answer_state = ''
        """
    )

    _migrate_process_steps_drop_execution_per_case(cur)

    if needs_used_models_backfill:
        _refresh_all_session_used_models(cur)


def get_conn() -> sqlite3.Connection:
    existing = _TX_CONN.get()
    if existing is not None:
        return existing
    _ensure_parent(settings.db_path)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


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
    _ensure_parent(settings.db_path)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
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
            uploaded_at     TEXT NOT NULL DEFAULT current_timestamp
        )
        """
    )
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
            current_law_id      INTEGER,
            proposed_law_id     INTEGER,
            law_diff_title      TEXT,
            law_diff_blurb      TEXT,
            law_diff_summary    TEXT,
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
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS processes (
            process_id      INTEGER PRIMARY KEY,
            session_id      INTEGER NOT NULL,
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
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS case_groups (
            case_group_id               INTEGER PRIMARY KEY,
            process_id                  INTEGER NOT NULL,
            session_id                  INTEGER NOT NULL,
            case_group                  TEXT NOT NULL,
            description                 TEXT NOT NULL,
            change_status               TEXT NOT NULL,
            created_at                  TEXT NOT NULL DEFAULT current_timestamp,
            addressees_current          REAL,
            annual_frequency_current    REAL,
            cases_current               REAL,
            addressees_proposed         REAL,
            annual_frequency_proposed   REAL,
            cases_proposed              REAL,
            cost                        REAL,
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
    _run_legacy_migrations(cur)
    _create_used_models_triggers(cur)
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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_current_law_id ON sessions(current_law_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_proposed_law_id ON sessions(proposed_law_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_regulations_session_id ON regulations(session_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_regulations_process_id ON regulations(process_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_processes_session_id ON processes(session_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_case_groups_process_id ON case_groups(process_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_case_groups_session_id ON case_groups(session_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_process_steps_case_group_id ON process_steps(case_group_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_process_steps_session_id ON process_steps(session_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ws_sessions_session_id ON web_sources_sessions(session_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_llm_answers_session_id ON llm_answers(session_id)")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_answers_session_prompt ON llm_answers(session_id, prompt_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_answers_state ON llm_answers(answer_state)"
    )
    # Keep at most one active answer per (session_id, prompt_id).
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
            GROUP BY session_id, prompt_id
          )
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_llm_answers_one_active
        ON llm_answers(session_id, prompt_id)
        WHERE answer_state = 'active'
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ws_regulations_regulation_id ON web_sources_regulations(regulation_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ws_processes_process_id ON web_sources_processes(process_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ws_case_groups_case_group_id ON web_sources_case_groups(case_group_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ws_process_steps_step_id ON web_sources_process_steps(step_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tiles_session_id ON tiles(session_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_links_session_target ON links(session_id, target)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_links_session_source ON links(session_id, source)")
    _maybe_commit(conn)
    _maybe_close(conn)


def ensure_db() -> None:
    init_db()
    conn = get_conn()
    _maybe_close(conn)


def fetch_tiles(session_id: int) -> List[Tile]:
    resolved_session_id = int(session_id)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM tiles
        WHERE session_id = ?
        """,
        (resolved_session_id,),
    )
    tiles: List[Tile] = []
    for row in cur.fetchall():
        tile_id = row["id"]
        cur_links = conn.execute(
            """
            SELECT source
            FROM links
            WHERE session_id = ? AND target = ?
            """,
            (resolved_session_id, tile_id),
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


def list_law_file_names() -> List[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT file_name FROM laws ORDER BY uploaded_at DESC, document_id DESC"
    )
    names = [row["file_name"] for row in cur.fetchall()]
    _maybe_close(conn)
    return names


def get_law_by_filename(file_name: str) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT document_id, file_name, law_text, text_length, uploaded_at
        FROM laws
        WHERE file_name = ?
        LIMIT 1
        """,
        (file_name,),
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
        SELECT document_id, file_name, law_text, text_length, uploaded_at
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


def insert_law(file_name: str, law_text: str) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO laws (file_name, law_text, text_length)
        VALUES (?, ?, ?)
        """,
        (file_name, law_text, len(law_text)),
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


def get_session_export_info(app_session_id: str) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            s.app_session_id,
            s.created_at,
            s.llm_model,
            current.file_name AS current_file_name,
            proposed.file_name AS proposed_file_name
        FROM sessions s
        LEFT JOIN laws AS current ON current.document_id = s.current_law_id
        LEFT JOIN laws AS proposed ON proposed.document_id = s.proposed_law_id
        WHERE s.app_session_id = ?
        """,
        (app_session_id,),
    )
    row = cur.fetchone()
    _maybe_close(conn)
    if row is None:
        return None
    return dict(row)


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


def list_sessions(limit: int = 50) -> List[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            s.app_session_id,
            s.created_at,
            s.llm_model,
            s.used_llm_models
        FROM sessions AS s
        ORDER BY s.created_at DESC, s.session_id DESC
        LIMIT ?
        """,
        (limit,),
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
    cur.execute("SELECT COUNT(*) AS count FROM processes WHERE session_id = ?", (session_id,))
    processes_count = int(cur.fetchone()["count"])
    cur.execute("SELECT COUNT(*) AS count FROM case_groups WHERE session_id = ?", (session_id,))
    case_groups_count = int(cur.fetchone()["count"])
    cur.execute("SELECT COUNT(*) AS count FROM process_steps WHERE session_id = ?", (session_id,))
    steps_count = int(cur.fetchone()["count"])
    _maybe_close(conn)
    summary_ready = bool(
        session.get("law_diff_title")
        or session.get("law_diff_blurb")
        or session.get("law_diff_summary")
        or session.get("current_law_id")
        or session.get("proposed_law_id")
    )
    total_cost_ready = session.get("cc_cost") is not None
    return {
        "summary_ready": summary_ready,
        "regulations_ready": regulations_count > 0,
        "processes_ready": processes_count > 0,
        "case_groups_ready": case_groups_count > 0,
        "process_steps_ready": steps_count > 0,
        "effort_ready": has_effort_metrics(session_id),
        "total_cost_ready": total_cost_ready,
    }


def has_effort_metrics(session_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS count
        FROM case_groups
        WHERE session_id = ?
          AND (
            addressees_current IS NOT NULL OR annual_frequency_current IS NOT NULL
            OR addressees_proposed IS NOT NULL OR annual_frequency_proposed IS NOT NULL
          )
        """,
        (session_id,),
    )
    groups_with_metrics = int(cur.fetchone()["count"])
    cur.execute(
        """
        SELECT COUNT(*) AS count
        FROM process_steps
        WHERE session_id = ?
          AND (
            hourly_rate_a_current IS NOT NULL OR hourly_rate_b_current IS NOT NULL
            OR hourly_rate_c_current IS NOT NULL OR hourly_rate_d_current IS NOT NULL
            OR time_required_in_min_a_current IS NOT NULL
            OR time_required_in_min_b_current IS NOT NULL
            OR time_required_in_min_c_current IS NOT NULL
            OR time_required_in_min_d_current IS NOT NULL
            OR expenses_current IS NOT NULL
            OR hourly_rate_a_proposed IS NOT NULL OR hourly_rate_b_proposed IS NOT NULL
            OR hourly_rate_c_proposed IS NOT NULL OR hourly_rate_d_proposed IS NOT NULL
            OR time_required_in_min_a_proposed IS NOT NULL
            OR time_required_in_min_b_proposed IS NOT NULL
            OR time_required_in_min_c_proposed IS NOT NULL
            OR time_required_in_min_d_proposed IS NOT NULL
            OR expenses_proposed IS NOT NULL
          )
        """,
        (session_id,),
    )
    steps_with_metrics = int(cur.fetchone()["count"])
    _maybe_close(conn)
    return groups_with_metrics > 0 or steps_with_metrics > 0


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
) -> tuple[int, bool, str]:
    requested_model = str(llm_model or "").strip()
    existing = get_session_by_app_id(app_session_id)
    if existing:
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
    session_id, created = upsert_session(app_session_id, model)
    return session_id, created, model


def upsert_session(app_session_id: str, llm_model: str) -> tuple[int, bool]:
    conn = get_conn()
    cur = conn.cursor()
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
        session_id = int(row["session_id"])
        created = False
    else:
        cur.execute(
            """
            INSERT INTO sessions (app_session_id, llm_model)
            VALUES (?, ?)
            """,
            (app_session_id, llm_model),
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
            metadata,
            input_tokens,
            output_tokens,
            hidden_thinking_tokens,
            estimated_cost_usd,
            provider_response_json,
            answer_state,
            state_reason
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            prompt_id,
            model,
            answer_text,
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
) -> int:
    invalidate_llm_answers(
        session_id=session_id,
        prompt_ids=[prompt_id],
        states=[LLM_ANSWER_STATE_PENDING],
        reason="superseded_by_new_attempt",
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
) -> dict | None:
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
        ORDER BY answer_id DESC
        """,
        (session_id, prompt_id, model, LLM_ANSWER_STATE_PENDING),
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
    cur.execute(
        """
        UPDATE llm_answers
        SET answer_state = ?, state_reason = ?
        WHERE session_id = ?
          AND prompt_id = ?
          AND answer_state IN (?, ?)
          AND answer_id <> ?
        """,
        (
            LLM_ANSWER_STATE_INVALID,
            "superseded_by_new_attempt",
            session_id,
            prompt_id,
            LLM_ANSWER_STATE_ACTIVE,
            LLM_ANSWER_STATE_PENDING,
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
        SELECT regulation_id, legal_citation, description, process_id, change_status
        FROM regulations
        WHERE session_id = ?
        ORDER BY regulation_id
        """,
        (session_id,),
    )
    rows = [dict(row) for row in cur.fetchall()]
    _maybe_close(conn)
    return rows


def get_regulation_by_id(regulation_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT regulation_id, legal_citation, description, process_id, change_status
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
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT process_id, process, description, change_status, cost
        FROM processes
        WHERE session_id = ?
        ORDER BY process_id
        """,
        (session_id,),
    )
    rows = [dict(row) for row in cur.fetchall()]
    _maybe_close(conn)
    return rows


def list_case_groups_for_session(session_id: int) -> List[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            case_group_id,
            process_id,
            case_group,
            description,
            change_status,
            addressees_current,
            annual_frequency_current,
            cases_current,
            addressees_proposed,
            annual_frequency_proposed,
            cases_proposed,
            cost
        FROM case_groups
        WHERE session_id = ?
        ORDER BY case_group_id
        """,
        (session_id,),
    )
    rows = [dict(row) for row in cur.fetchall()]
    _maybe_close(conn)
    return rows


def list_process_steps_for_session(session_id: int) -> List[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT step_id, case_group_id, step, description, previous_id, next_id,
               change_status,
               hourly_rate_a_current, hourly_rate_b_current, hourly_rate_c_current, hourly_rate_d_current,
               time_required_in_min_a_current, time_required_in_min_b_current, time_required_in_min_c_current, time_required_in_min_d_current,
               expenses_current,
               hourly_rate_a_proposed, hourly_rate_b_proposed, hourly_rate_c_proposed, hourly_rate_d_proposed,
               time_required_in_min_a_proposed, time_required_in_min_b_proposed, time_required_in_min_c_proposed, time_required_in_min_d_proposed,
               expenses_proposed,
               cost_current,
               cost_proposed
        FROM process_steps
        WHERE session_id = ?
        ORDER BY step_id
        """,
        (session_id,),
    )
    rows = [dict(row) for row in cur.fetchall()]
    _maybe_close(conn)
    return rows


def insert_regulation(
    session_id: int,
    legal_citation: str,
    description: str,
    change_status: str = "geaendert",
    process_id: int | None = None,
) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO regulations (session_id, process_id, legal_citation, description, change_status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, process_id, legal_citation, description, change_status),
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
) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO processes (session_id, process, description, change_status, cost)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, process, description, change_status, cost),
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
) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO case_groups (session_id, process_id, case_group, description, change_status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, process_id, case_group, description, change_status),
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
) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO process_steps (
            session_id,
            case_group_id,
            step,
            description,
            change_status,
            previous_id,
            next_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            case_group_id,
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
        WHERE case_group_id = ? AND session_id = ?
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
        ),
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
        """
        UPDATE process_steps
        SET hourly_rate_a_current = ?, hourly_rate_b_current = ?, hourly_rate_c_current = ?, hourly_rate_d_current = ?,
            time_required_in_min_a_current = ?, time_required_in_min_b_current = ?, time_required_in_min_c_current = ?, time_required_in_min_d_current = ?,
            expenses_current = ?,
            hourly_rate_a_proposed = ?, hourly_rate_b_proposed = ?, hourly_rate_c_proposed = ?, hourly_rate_d_proposed = ?,
            time_required_in_min_a_proposed = ?, time_required_in_min_b_proposed = ?, time_required_in_min_c_proposed = ?, time_required_in_min_d_proposed = ?,
            expenses_proposed = ?
        WHERE step_id = ? AND session_id = ?
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
            step_id,
            session_id,
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
) -> bool:
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


def update_session_documents(
    app_session_id: str,
    current_filename: str | None,
    proposed_filename: str | None,
) -> None:
    current_id = None
    proposed_id = None
    if current_filename:
        current = get_law_by_filename(current_filename)
        if current is None:
            raise ValueError("Current law not found")
        current_id = current["document_id"]
    if proposed_filename:
        proposed = get_law_by_filename(proposed_filename)
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


def update_session_cost(session_id: int, cost: float | None) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE sessions
        SET cc_cost = ?
        WHERE session_id = ?
        """,
        (cost, session_id),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


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


def clear_effort_metrics(session_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE case_groups
        SET addressees_current = NULL,
            annual_frequency_current = NULL,
            cases_current = NULL,
            addressees_proposed = NULL,
            annual_frequency_proposed = NULL,
            cases_proposed = NULL
        WHERE session_id = ?
        """,
        (session_id,),
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
            expenses_current = NULL,
            hourly_rate_a_proposed = NULL,
            hourly_rate_b_proposed = NULL,
            hourly_rate_c_proposed = NULL,
            hourly_rate_d_proposed = NULL,
            time_required_in_min_a_proposed = NULL,
            time_required_in_min_b_proposed = NULL,
            time_required_in_min_c_proposed = NULL,
            time_required_in_min_d_proposed = NULL,
            expenses_proposed = NULL
        WHERE session_id = ?
        """,
        (session_id,),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def clear_costs(session_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE process_steps
        SET cost_current = NULL,
            cost_proposed = NULL
        WHERE session_id = ?
        """,
        (session_id,),
    )
    cur.execute(
        """
        UPDATE case_groups
        SET cost = NULL
        WHERE session_id = ?
        """,
        (session_id,),
    )
    cur.execute(
        """
        UPDATE processes
        SET cost = NULL
        WHERE session_id = ?
        """,
        (session_id,),
    )
    cur.execute(
        """
        UPDATE sessions
        SET cc_cost = NULL
        WHERE session_id = ?
        """,
        (session_id,),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def delete_process_steps_for_session(session_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM process_steps WHERE session_id = ?",
        (session_id,),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def delete_case_groups_for_session(session_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM case_groups WHERE session_id = ?",
        (session_id,),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def delete_processes_for_session(session_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM processes WHERE session_id = ?",
        (session_id,),
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


def upsert_tile(tile: Tile, session_id: int) -> None:
    resolved_session_id = int(session_id)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO tiles (session_id, id, title, text, meta, col, row, deletable)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id, id) DO UPDATE SET
            title = excluded.title,
            text = excluded.text,
            meta = excluded.meta,
            col = excluded.col,
            row = excluded.row,
            deletable = excluded.deletable
        """,
        (
            resolved_session_id,
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
        set_links(tile.id, tile.link_from_tile, session_id=resolved_session_id)


def delete_tile(tile_id: str, session_id: int) -> None:
    resolved_session_id = int(session_id)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM links
        WHERE session_id = ? AND (target = ? OR source = ?)
        """,
        (resolved_session_id, tile_id, tile_id),
    )
    cur.execute(
        "DELETE FROM tiles WHERE session_id = ? AND id = ?",
        (resolved_session_id, tile_id),
    )
    _maybe_commit(conn)
    _maybe_close(conn)


def clear_tiles(session_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    resolved_session_id = int(session_id)
    cur.execute("DELETE FROM links WHERE session_id = ?", (resolved_session_id,))
    cur.execute("DELETE FROM tiles WHERE session_id = ?", (resolved_session_id,))
    _maybe_commit(conn)
    _maybe_close(conn)


def set_links(
    target_id: str,
    sources: Iterable[str],
    session_id: int,
) -> None:
    resolved_session_id = int(session_id)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM links WHERE session_id = ? AND target = ?",
        (resolved_session_id, target_id),
    )
    for src in sources:
        cur.execute(
            """
            INSERT OR REPLACE INTO links (session_id, source, target)
            VALUES (?, ?, ?)
            """,
            (resolved_session_id, src, target_id),
        )
    _maybe_commit(conn)
    _maybe_close(conn)
