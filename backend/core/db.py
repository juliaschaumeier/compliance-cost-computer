from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable, List

from .config import settings
from .models import Tile


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    _ensure_parent(settings.db_path)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tiles (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            text TEXT NOT NULL,
            meta JSON,
            col INTEGER DEFAULT 0,
            row INTEGER DEFAULT 0,
            deletable INTEGER DEFAULT 1
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS links (
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            PRIMARY KEY (source, target),
            FOREIGN KEY (source) REFERENCES tiles(id) ON DELETE CASCADE,
            FOREIGN KEY (target) REFERENCES tiles(id) ON DELETE CASCADE
        );
        """
    )
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
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id          INTEGER PRIMARY KEY,
            app_session_id      TEXT NOT NULL,
            created_at          TEXT NOT NULL DEFAULT current_timestamp,
            llm_model           TEXT NOT NULL,
            current_law_id      INTEGER,
            proposed_law_id     INTEGER,
            law_diff_title      TEXT,
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
            case_group_id       INTEGER PRIMARY KEY,
            process_id          INTEGER NOT NULL,
            session_id          INTEGER NOT NULL,
            case_group          TEXT NOT NULL,
            description         TEXT NOT NULL,
            created_at          TEXT NOT NULL DEFAULT current_timestamp,
            addressees          REAL,
            annual_frequency    REAL,
            cost                REAL,
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
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS process_steps (
            step_id                 INTEGER PRIMARY KEY,
            case_group_id           INTEGER NOT NULL,
            session_id              INTEGER NOT NULL,
            step                    TEXT NOT NULL,
            description             TEXT NOT NULL,
            created_at              TEXT NOT NULL DEFAULT current_timestamp,
            previous_id             INTEGER,
            next_id                 INTEGER,
            hourly_rate_a           REAL,
            hourly_rate_b           REAL,
            hourly_rate_c           REAL,
            hourly_rate_d           REAL,
            hourly_rate_e           REAL,
            time_required_in_min_a  REAL,
            time_required_in_min_b  REAL,
            time_required_in_min_c  REAL,
            time_required_in_min_d  REAL,
            time_required_in_min_e  REAL,
            expenses                REAL,
            execution_per_case      BIT,
            cost                    REAL,
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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ws_regulations_regulation_id ON web_sources_regulations(regulation_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ws_processes_process_id ON web_sources_processes(process_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ws_case_groups_case_group_id ON web_sources_case_groups(case_group_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ws_process_steps_step_id ON web_sources_process_steps(step_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_links_target ON links(target)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_links_source ON links(source)")
    conn.commit()
    conn.close()


def seed_from_json() -> None:
    if not settings.seed_json.exists():
        return
    data = json.loads(settings.seed_json.read_text(encoding="utf-8"))
    tiles = data.get("tiles", [])
    links = []
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM links")
    cur.execute("DELETE FROM tiles")
    for tile in tiles:
        tile_id = tile["id"]
        cur.execute(
            """
            INSERT OR REPLACE INTO tiles (id, title, text, meta, col, row, deletable)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tile_id,
                tile.get("title", tile_id),
                tile.get("text", ""),
                json.dumps(tile.get("meta_information", {}), ensure_ascii=False),
                tile.get("column", 0),
                tile.get("row", 0),
                1 if tile.get("deletable", True) else 0,
            ),
        )
        for src in tile.get("link_from_tile", []):
            links.append((src, tile_id))
    for src, tgt in links:
        cur.execute(
            """
            INSERT OR REPLACE INTO links (source, target)
            VALUES (?, ?)
            """,
            (src, tgt),
        )
    conn.commit()
    conn.close()


def ensure_db() -> None:
    init_db()
    conn = get_conn()
    conn.close()


def fetch_tiles() -> List[Tile]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tiles")
    tiles: List[Tile] = []
    for row in cur.fetchall():
        tile_id = row["id"]
        cur_links = conn.execute("SELECT source FROM links WHERE target = ?", (tile_id,)).fetchall()
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
    conn.close()
    return tiles


def list_law_file_names() -> List[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT file_name FROM laws ORDER BY uploaded_at DESC, document_id DESC"
    )
    names = [row["file_name"] for row in cur.fetchall()]
    conn.close()
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
    conn.close()
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
    conn.close()
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
    conn.commit()
    document_id = int(cur.lastrowid)
    conn.close()
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
    conn.close()
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
    conn.close()
    if row is None:
        return None
    return dict(row)


def list_sessions(limit: int = 50) -> List[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT app_session_id, created_at, llm_model
        FROM sessions
        ORDER BY created_at DESC, session_id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
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
    conn.close()
    summary_ready = bool(
        session.get("law_diff_title")
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
          AND (addressees IS NOT NULL OR annual_frequency IS NOT NULL)
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
            hourly_rate_a IS NOT NULL OR hourly_rate_b IS NOT NULL OR hourly_rate_c IS NOT NULL
            OR hourly_rate_d IS NOT NULL OR hourly_rate_e IS NOT NULL
            OR time_required_in_min_a IS NOT NULL OR time_required_in_min_b IS NOT NULL
            OR time_required_in_min_c IS NOT NULL OR time_required_in_min_d IS NOT NULL
            OR time_required_in_min_e IS NOT NULL
            OR expenses IS NOT NULL
          )
        """,
        (session_id,),
    )
    steps_with_metrics = int(cur.fetchone()["count"])
    conn.close()
    return groups_with_metrics > 0 or steps_with_metrics > 0


def get_session_id_by_app_id(app_session_id: str) -> int | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT session_id FROM sessions WHERE app_session_id = ?",
        (app_session_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return int(row["session_id"])


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
    conn.commit()
    conn.close()
    return session_id, created


def insert_llm_answer(
    session_id: int,
    prompt_id: str,
    model: str,
    answer_text: str,
    metadata: dict | None = None,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO llm_answers (session_id, prompt_id, model, answer_text, metadata)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            session_id,
            prompt_id,
            model,
            answer_text,
            json.dumps(metadata, ensure_ascii=False) if metadata else None,
        ),
    )
    conn.commit()
    conn.close()


def list_regulations_for_session(session_id: int) -> List[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT regulation_id, legal_citation, description, process_id
        FROM regulations
        WHERE session_id = ?
        ORDER BY regulation_id
        """,
        (session_id,),
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def get_regulation_by_id(regulation_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT regulation_id, legal_citation, description, process_id
        FROM regulations
        WHERE regulation_id = ?
        """,
        (regulation_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def list_processes_for_session(session_id: int) -> List[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT process_id, process, description, cost
        FROM processes
        WHERE session_id = ?
        ORDER BY process_id
        """,
        (session_id,),
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def list_case_groups_for_session(session_id: int) -> List[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT case_group_id, process_id, case_group, description, addressees, annual_frequency
        FROM case_groups
        WHERE session_id = ?
        ORDER BY case_group_id
        """,
        (session_id,),
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def list_process_steps_for_session(session_id: int) -> List[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT step_id, case_group_id, step, description, previous_id, next_id,
               hourly_rate_a, hourly_rate_b, hourly_rate_c, hourly_rate_d, hourly_rate_e,
               time_required_in_min_a, time_required_in_min_b, time_required_in_min_c, time_required_in_min_d, time_required_in_min_e,
               expenses, cost, execution_per_case
        FROM process_steps
        WHERE session_id = ?
        ORDER BY step_id
        """,
        (session_id,),
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def insert_regulation(
    session_id: int,
    legal_citation: str,
    description: str,
    process_id: int | None = None,
) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO regulations (session_id, process_id, legal_citation, description)
        VALUES (?, ?, ?, ?)
        """,
        (session_id, process_id, legal_citation, description),
    )
    conn.commit()
    regulation_id = int(cur.lastrowid)
    conn.close()
    return regulation_id


def insert_process(
    session_id: int,
    process: str,
    description: str,
    cost: float | None = None,
) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO processes (session_id, process, description, cost)
        VALUES (?, ?, ?, ?)
        """,
        (session_id, process, description, cost),
    )
    conn.commit()
    process_id = int(cur.lastrowid)
    conn.close()
    return process_id


def insert_case_group(
    session_id: int,
    process_id: int,
    case_group: str,
    description: str,
) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO case_groups (session_id, process_id, case_group, description)
        VALUES (?, ?, ?, ?)
        """,
        (session_id, process_id, case_group, description),
    )
    conn.commit()
    case_group_id = int(cur.lastrowid)
    conn.close()
    return case_group_id


def insert_process_step(
    session_id: int,
    case_group_id: int,
    step: str,
    description: str,
    previous_id: int | None = None,
    next_id: int | None = None,
    execution_per_case: bool | None = None,
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
            previous_id,
            next_id,
            execution_per_case
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            case_group_id,
            step,
            description,
            previous_id,
            next_id,
            execution_per_case,
        ),
    )
    conn.commit()
    step_id = int(cur.lastrowid)
    conn.close()
    return step_id


def update_case_group_metrics(
    session_id: int,
    case_group_id: int,
    addressees: float | None,
    annual_frequency: float | None,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE case_groups
        SET addressees = ?, annual_frequency = ?
        WHERE case_group_id = ? AND session_id = ?
        """,
        (addressees, annual_frequency, case_group_id, session_id),
    )
    conn.commit()
    conn.close()


def update_process_step_effort(
    session_id: int,
    step_id: int,
    hourly_rates: dict[str, float | None],
    time_required: dict[str, float | None],
    expenses: float | None,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE process_steps
        SET hourly_rate_a = ?, hourly_rate_b = ?, hourly_rate_c = ?, hourly_rate_d = ?, hourly_rate_e = ?,
            time_required_in_min_a = ?, time_required_in_min_b = ?, time_required_in_min_c = ?, time_required_in_min_d = ?, time_required_in_min_e = ?,
            expenses = ?
        WHERE step_id = ? AND session_id = ?
        """,
        (
            hourly_rates.get("a"),
            hourly_rates.get("b"),
            hourly_rates.get("c"),
            hourly_rates.get("d"),
            hourly_rates.get("e"),
            time_required.get("a"),
            time_required.get("b"),
            time_required.get("c"),
            time_required.get("d"),
            time_required.get("e"),
            expenses,
            step_id,
            session_id,
        ),
    )
    conn.commit()
    conn.close()


def update_process_step_cost(
    session_id: int,
    step_id: int,
    cost: float | None,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE process_steps
        SET cost = ?
        WHERE step_id = ? AND session_id = ?
        """,
        (cost, step_id, session_id),
    )
    conn.commit()
    conn.close()


def update_process_step_execution(
    session_id: int,
    step_id: int,
    execution_per_case: bool | None,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE process_steps
        SET execution_per_case = ?
        WHERE step_id = ? AND session_id = ?
        """,
        (execution_per_case, step_id, session_id),
    )
    conn.commit()
    conn.close()


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
    conn.commit()
    conn.close()


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
    conn.commit()
    conn.close()


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
    addressees: float | None,
    annual_frequency: float | None,
) -> str:
    lines = []
    base = (description or "").strip()
    if base:
        lines.append(base)
    if addressees is not None:
        lines.append(f"Betroffene: {format_number(addressees)}")
    if annual_frequency is not None:
        lines.append(f"Häufigkeit: {format_number(annual_frequency)}")
    return "\n".join(lines).strip()


def build_process_step_tile_text(
    description: str,
    hourly_rates: dict[str, float | None],
    time_required: dict[str, float | None],
    expenses: float | None,
    cost: float | None = None,
    execution_per_case: bool | None = None,
) -> str:
    lines = []
    base = (description or "").strip()
    if base:
        lines.append(base)
    for key in ["a", "b", "c", "d", "e"]:
        rate = hourly_rates.get(key)
        if rate is not None:
            lines.append(f"Lohnsatz {key.upper()}: {format_number(rate)}")
    for key in ["a", "b", "c", "d", "e"]:
        duration = time_required.get(key)
        if duration is not None:
            lines.append(f"Zeitaufwand {key.upper()}: {format_number(duration)}")
    if expenses is not None:
        try:
            expense_value = float(expenses)
        except (TypeError, ValueError):
            expense_value = None
        if expense_value is not None and abs(expense_value) > 0:
            lines.append(f"Sachaufwand: {format_number(expense_value)}")
    if cost is not None:
        try:
            cost_value = float(cost)
        except (TypeError, ValueError):
            cost_value = None
        if cost_value is not None:
            if execution_per_case is None:
                per_case = True
            elif isinstance(execution_per_case, str):
                normalized = execution_per_case.strip().lower()
                if normalized in {"0", "false", "nein", "no", "n"}:
                    per_case = False
                elif normalized in {"1", "true", "ja", "yes", "y"}:
                    per_case = True
                else:
                    per_case = True
            else:
                per_case = bool(execution_per_case)
            scope = "pro Einzelfall" if per_case else "pro Fallgruppe"
            lines.append(f"Kosten: {format_currency(cost_value)} ({scope})")
    return "\n".join(lines).strip()


def build_process_tile_text(description: str, cost: float | None) -> str:
    lines = []
    base = (description or "").strip()
    if base:
        lines.append(base)
    if cost is not None:
        try:
            cost_value = float(cost)
        except (TypeError, ValueError):
            cost_value = None
        if cost_value is not None:
            lines.append(f"Kosten: {format_currency(cost_value)}")
    return "\n".join(lines).strip()


def update_process_step_next(step_id: int, next_id: int | None) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE process_steps SET next_id = ? WHERE step_id = ?",
        (next_id, step_id),
    )
    conn.commit()
    conn.close()


def update_regulation_process(
    regulation_id: int,
    process_id: int,
    legal_citation: str,
    description: str,
) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE regulations
        SET process_id = ?
        WHERE regulation_id = ?
          AND process_id IS NULL
          AND legal_citation = ?
          AND description = ?
        """,
        (process_id, regulation_id, legal_citation, description),
    )
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
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
    conn.commit()
    conn.close()


def update_session_summary(
    app_session_id: str,
    law_diff_title: str,
    law_diff_summary: str,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE sessions
        SET law_diff_title = ?, law_diff_summary = ?
        WHERE app_session_id = ?
        """,
        (law_diff_title, law_diff_summary, app_session_id),
    )
    conn.commit()
    conn.close()


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
    conn.commit()
    conn.close()


def clear_session_summary(session_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE sessions
        SET law_diff_title = NULL,
            law_diff_summary = NULL,
            current_law_id = NULL,
            proposed_law_id = NULL
        WHERE session_id = ?
        """,
        (session_id,),
    )
    conn.commit()
    conn.close()


def clear_effort_metrics(session_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE case_groups
        SET addressees = NULL,
            annual_frequency = NULL
        WHERE session_id = ?
        """,
        (session_id,),
    )
    cur.execute(
        """
        UPDATE process_steps
        SET hourly_rate_a = NULL,
            hourly_rate_b = NULL,
            hourly_rate_c = NULL,
            hourly_rate_d = NULL,
            hourly_rate_e = NULL,
            time_required_in_min_a = NULL,
            time_required_in_min_b = NULL,
            time_required_in_min_c = NULL,
            time_required_in_min_d = NULL,
            time_required_in_min_e = NULL,
            expenses = NULL
        WHERE session_id = ?
        """,
        (session_id,),
    )
    conn.commit()
    conn.close()


def clear_costs(session_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE process_steps
        SET cost = NULL
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
    conn.commit()
    conn.close()


def delete_process_steps_for_session(session_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM process_steps WHERE session_id = ?",
        (session_id,),
    )
    conn.commit()
    conn.close()


def delete_case_groups_for_session(session_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM case_groups WHERE session_id = ?",
        (session_id,),
    )
    conn.commit()
    conn.close()


def delete_processes_for_session(session_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM processes WHERE session_id = ?",
        (session_id,),
    )
    conn.commit()
    conn.close()


def delete_regulations_for_session(session_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM regulations WHERE session_id = ?",
        (session_id,),
    )
    conn.commit()
    conn.close()


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
    conn.commit()
    conn.close()


def upsert_tile(tile: Tile) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO tiles (id, title, text, meta, col, row, deletable)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tile.id,
            tile.title,
            tile.text,
            json.dumps(tile.meta_information or {}, ensure_ascii=False),
            tile.column,
            tile.row,
            1 if tile.deletable else 0,
        ),
    )
    conn.commit()
    conn.close()
    if tile.link_from_tile is not None:
        set_links(tile.id, tile.link_from_tile)


def delete_tile(tile_id: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM links WHERE target = ? OR source = ?", (tile_id, tile_id))
    cur.execute("DELETE FROM tiles WHERE id = ?", (tile_id,))
    conn.commit()
    conn.close()


def clear_tiles() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM links")
    cur.execute("DELETE FROM tiles")
    conn.commit()
    conn.close()


def set_links(target_id: str, sources: Iterable[str]) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM links WHERE target = ?", (target_id,))
    for src in sources:
        cur.execute(
            "INSERT OR REPLACE INTO links (source, target) VALUES (?, ?)",
            (src, target_id),
        )
    conn.commit()
    conn.close()
