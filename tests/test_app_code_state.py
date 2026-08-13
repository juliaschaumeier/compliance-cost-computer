import json
import sqlite3

import pytest

from backend.core import db
from backend.core.runtime_info import app_code_state, format_app_code_state
from scripts.backfill_app_code_state import (
    backfill_db,
    backfill_run_log,
    collect_app_session_ids,
)


@pytest.fixture(autouse=True)
def clear_app_code_state_cache():
    app_code_state.cache_clear()
    yield
    app_code_state.cache_clear()


def test_format_app_code_state_includes_dirty_marker():
    assert format_app_code_state(branch="develop", sha="9b93524") == "develop@9b93524"
    assert (
        format_app_code_state(branch="feature", sha="abc1234", dirty=True)
        == "feature@abc1234-dirty"
    )


def test_app_code_state_prefers_explicit_env(monkeypatch):
    monkeypatch.setenv("CCC_APP_CODE_STATE", "release@abc1234")
    monkeypatch.setenv("CCC_APP_GIT_BRANCH", "develop")
    monkeypatch.setenv("CCC_APP_GIT_SHA", "ignored")

    assert app_code_state() == "release@abc1234"


def test_app_code_state_uses_env_branch_sha(monkeypatch):
    monkeypatch.delenv("CCC_APP_CODE_STATE", raising=False)
    monkeypatch.setenv("CCC_APP_GIT_BRANCH", "develop")
    monkeypatch.setenv("CCC_APP_GIT_SHA", "9b93524")
    monkeypatch.setenv("CCC_APP_GIT_DIRTY", "true")

    assert app_code_state() == "develop@9b93524-dirty"


def test_session_and_generated_artifacts_record_app_code_state(monkeypatch):
    monkeypatch.setattr(db, "app_code_state", lambda: "develop@9b93524")
    session_id, created = db.upsert_session("CODESTATE", "test-model")
    assert created is True

    session = db.get_session_by_id(session_id)
    assert session["app_code_state"] == "develop@9b93524"

    answer_id = db.insert_llm_answer(
        session_id,
        "law_summary",
        "test-model",
        "{}",
        metadata={"prompt_sha256": "abc"},
    )
    answer = db.get_llm_answer_by_id(answer_id)
    answer_metadata = answer["metadata"]
    assert answer_metadata["prompt_sha256"] == "abc"
    assert answer_metadata["app_code_state"] == "develop@9b93524"

    research_run_id = db.create_deep_research_run(
        session_id=session_id,
        purpose="case_group_metrics",
        agent="test-agent",
        status="running",
    )
    research_run = db.get_deep_research_run(research_run_id)
    assert research_run["app_code_state"] == "develop@9b93524"

    export_id = db.insert_compliance_text_export(
        session_id=session_id,
        llm_answer_id=answer_id,
        status="succeeded",
        model="test-model",
        provider="test",
        prompt_text="prompt",
        generated_markdown="# Export",
        source_snapshot_json={"session": "snapshot"},
        source_snapshot_sha256="snapshot-sha",
        used_deep_research=False,
        deep_research_run_id=None,
        used_user_edits=False,
        user_edit_policy="reject_if_user_edits",
        metadata_json={"app_session_id": "CODESTATE"},
    )
    export = db.get_latest_compliance_text_export(
        session_id,
        "snapshot-sha",
        "reject_if_user_edits",
    )
    assert export["export_id"] == export_id
    assert export["app_code_state"] == "develop@9b93524"
    export_metadata = json.loads(export["metadata_json"])
    assert export_metadata["app_code_state"] == "develop@9b93524"


def test_backfill_app_code_state_updates_only_batch_sessions(tmp_path):
    db_path = tmp_path / "backfill.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE sessions (
            session_id INTEGER PRIMARY KEY,
            app_session_id TEXT NOT NULL,
            app_code_state TEXT
        );
        CREATE TABLE llm_answers (
            answer_id INTEGER PRIMARY KEY,
            session_id INTEGER NOT NULL,
            metadata JSON
        );
        CREATE TABLE deep_research_runs (
            research_run_id INTEGER PRIMARY KEY,
            session_id INTEGER NOT NULL,
            app_code_state TEXT
        );
        CREATE TABLE compliance_text_exports (
            export_id INTEGER PRIMARY KEY,
            session_id INTEGER NOT NULL,
            app_code_state TEXT,
            metadata_json JSON
        );
        INSERT INTO sessions (session_id, app_session_id) VALUES (1, 'BATCH01'), (2, 'OTHER01');
        INSERT INTO llm_answers (answer_id, session_id, metadata) VALUES (10, 1, '{"x": 1}'), (20, 2, '{}');
        INSERT INTO deep_research_runs (research_run_id, session_id) VALUES (30, 1), (40, 2);
        INSERT INTO compliance_text_exports (export_id, session_id, metadata_json) VALUES (50, 1, '{}'), (60, 2, '{}');
        """
    )
    conn.commit()
    conn.close()
    run_log = tmp_path / "runs.jsonl"
    run_log.write_text(
        json.dumps({"scenario_id": "s1", "app_session_id": "BATCH01"}) + "\n",
        encoding="utf-8",
    )

    app_session_ids = collect_app_session_ids([run_log])
    stats = backfill_db(db_path, app_session_ids, "develop@9b93524")
    changed_rows = backfill_run_log(run_log, "develop@9b93524")

    assert stats == {
        "sessions": 1,
        "llm_answers": 1,
        "deep_research_runs": 1,
        "exports": 1,
    }
    assert changed_rows == 1
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT app_session_id, app_code_state FROM sessions ORDER BY session_id"
        ).fetchall()
        assert [tuple(row) for row in rows] == [
            ("BATCH01", "develop@9b93524"),
            ("OTHER01", None),
        ]
        metadata = conn.execute(
            "SELECT metadata FROM llm_answers WHERE answer_id = 10"
        ).fetchone()["metadata"]
        assert json.loads(metadata)["app_code_state"] == "develop@9b93524"
    finally:
        conn.close()
    row = json.loads(run_log.read_text(encoding="utf-8"))
    assert row["app_code_state"] == "develop@9b93524"
