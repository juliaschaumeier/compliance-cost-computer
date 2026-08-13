from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable


DEFAULT_RUN_LOGS = (
    Path("batch_runs/full_matrix_once_20260804/runs.jsonl"),
    Path("batch_runs/full_matrix_4x_20260805/runs.jsonl"),
)


def collect_app_session_ids(run_logs: Iterable[Path]) -> set[str]:
    app_session_ids: set[str] = set()
    for path in run_logs:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            app_session_id = str(row.get("app_session_id") or "").strip()
            if app_session_id:
                app_session_ids.add(app_session_id)
    return app_session_ids


def backfill_db(
    db_path: Path,
    app_session_ids: set[str],
    app_code_state: str,
) -> dict[str, int]:
    if not db_path.exists():
        return {"sessions": 0, "llm_answers": 0, "deep_research_runs": 0, "exports": 0}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)
        session_ids = session_ids_for_app_ids(conn, app_session_ids)
        if not session_ids:
            return {"sessions": 0, "llm_answers": 0, "deep_research_runs": 0, "exports": 0}

        session_placeholders = ",".join("?" for _ in session_ids)
        before = conn.total_changes
        conn.execute(
            f"""
            UPDATE sessions
            SET app_code_state = ?
            WHERE session_id IN ({session_placeholders})
            """,
            (app_code_state, *session_ids),
        )
        sessions_changed = conn.total_changes - before

        llm_changed = backfill_llm_answers(conn, session_ids, app_code_state)
        deep_research_changed = update_table_code_state(
            conn,
            "deep_research_runs",
            "session_id",
            session_ids,
            app_code_state,
        )
        exports_changed = backfill_compliance_exports(conn, session_ids, app_code_state)
        conn.commit()
        return {
            "sessions": sessions_changed,
            "llm_answers": llm_changed,
            "deep_research_runs": deep_research_changed,
            "exports": exports_changed,
        }
    finally:
        conn.close()


def ensure_schema(conn: sqlite3.Connection) -> None:
    ensure_column(conn, "sessions", "app_code_state", "TEXT")
    ensure_column(conn, "deep_research_runs", "app_code_state", "TEXT")
    ensure_column(conn, "compliance_text_exports", "app_code_state", "TEXT")


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if not table_exists(conn, table):
        return
    columns = {
        str(row["name"])
        for row in conn.execute(f"PRAGMA table_info({quote_ident(table)})").fetchall()
    }
    if column not in columns:
        conn.execute(
            f"ALTER TABLE {quote_ident(table)} ADD COLUMN {quote_ident(column)} {definition}"
        )


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def session_ids_for_app_ids(
    conn: sqlite3.Connection,
    app_session_ids: set[str],
) -> list[int]:
    if not app_session_ids or not table_exists(conn, "sessions"):
        return []
    placeholders = ",".join("?" for _ in app_session_ids)
    rows = conn.execute(
        f"""
        SELECT session_id
        FROM sessions
        WHERE app_session_id IN ({placeholders})
        """,
        tuple(sorted(app_session_ids)),
    ).fetchall()
    return [int(row["session_id"]) for row in rows]


def backfill_llm_answers(
    conn: sqlite3.Connection,
    session_ids: list[int],
    app_code_state: str,
) -> int:
    if not session_ids or not table_exists(conn, "llm_answers"):
        return 0
    placeholders = ",".join("?" for _ in session_ids)
    rows = conn.execute(
        f"""
        SELECT answer_id, metadata
        FROM llm_answers
        WHERE session_id IN ({placeholders})
        """,
        tuple(session_ids),
    ).fetchall()
    changed = 0
    for row in rows:
        metadata = parse_json_object(row["metadata"])
        if metadata.get("app_code_state") == app_code_state:
            continue
        metadata["app_code_state"] = app_code_state
        conn.execute(
            "UPDATE llm_answers SET metadata = ? WHERE answer_id = ?",
            (json.dumps(metadata, ensure_ascii=False), int(row["answer_id"])),
        )
        changed += 1
    return changed


def backfill_compliance_exports(
    conn: sqlite3.Connection,
    session_ids: list[int],
    app_code_state: str,
) -> int:
    if not session_ids or not table_exists(conn, "compliance_text_exports"):
        return 0
    placeholders = ",".join("?" for _ in session_ids)
    rows = conn.execute(
        f"""
        SELECT export_id, metadata_json
        FROM compliance_text_exports
        WHERE session_id IN ({placeholders})
        """,
        tuple(session_ids),
    ).fetchall()
    changed = 0
    for row in rows:
        metadata = parse_json_object(row["metadata_json"])
        metadata["app_code_state"] = app_code_state
        conn.execute(
            """
            UPDATE compliance_text_exports
            SET app_code_state = ?, metadata_json = ?
            WHERE export_id = ?
            """,
            (
                app_code_state,
                json.dumps(metadata, ensure_ascii=False),
                int(row["export_id"]),
            ),
        )
        changed += 1
    return changed


def update_table_code_state(
    conn: sqlite3.Connection,
    table: str,
    id_column: str,
    session_ids: list[int],
    app_code_state: str,
) -> int:
    if not session_ids or not table_exists(conn, table):
        return 0
    placeholders = ",".join("?" for _ in session_ids)
    before = conn.total_changes
    conn.execute(
        f"""
        UPDATE {quote_ident(table)}
        SET app_code_state = ?
        WHERE {quote_ident(id_column)} IN ({placeholders})
        """,
        (app_code_state, *session_ids),
    )
    return conn.total_changes - before


def backfill_run_log(path: Path, app_code_state: str) -> int:
    if not path.exists():
        return 0
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    changed = 0
    for row in rows:
        if row.get("app_code_state") != app_code_state:
            row["app_code_state"] = app_code_state
            changed += 1
    if not changed:
        return 0
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    rewrite_summary_csv(path.with_name("summary.csv"), rows)
    return changed


def rewrite_summary_csv(csv_path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def parse_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill app_code_state for sessions referenced by batch runs."
    )
    parser.add_argument(
        "--db",
        action="append",
        type=Path,
        default=[],
        help="SQLite DB to update. Can be provided more than once.",
    )
    parser.add_argument(
        "--runs-jsonl",
        action="append",
        type=Path,
        default=[],
        help="Batch runs.jsonl file to use and update. Can be provided more than once.",
    )
    parser.add_argument(
        "--app-code-state",
        required=True,
        help="Code-state label to apply, e.g. develop@9b93524.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_paths = args.db or [Path("backend/ccc.db")]
    run_logs = args.runs_jsonl or list(DEFAULT_RUN_LOGS)
    app_session_ids = collect_app_session_ids(run_logs)
    print(f"Found {len(app_session_ids)} app sessions in batch logs.")
    for db_path in db_paths:
        stats = backfill_db(db_path, app_session_ids, args.app_code_state)
        print(f"{db_path}: {stats}")
    for run_log in run_logs:
        changed = backfill_run_log(run_log, args.app_code_state)
        print(f"{run_log}: updated {changed} row(s)")


if __name__ == "__main__":
    main()
