from __future__ import annotations

import asyncio
import csv
import json
import os
import py_compile
from pathlib import Path

import httpx
import pytest

from scripts.batch_full_run import (
    BatchConfig,
    BatchLogger,
    BatchResult,
    LawPair,
    ModelSpec,
    ScenarioResult,
    build_scenarios,
    discover_law_pairs,
    failed_existing_sessions,
    load_config_from_env,
    load_dotenv_if_available,
    load_batch_result,
    preview_scenarios,
    quality_output_dir_for_batch,
    redacted_config,
    resume_existing_sessions,
    run_batch,
    run_workflow_with_retries,
    select_scenarios,
    validate_config,
)
from scripts import batch_full_run


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_discover_law_pairs(tmp_path: Path):
    (tmp_path / "alpha_gueltig.txt").write_text("A", encoding="utf-8")
    (tmp_path / "alpha_vorschlag.txt").write_text("B", encoding="utf-8")
    (tmp_path / "orphan_gueltig.txt").write_text("C", encoding="utf-8")

    assert discover_law_pairs(tmp_path) == [
        LawPair(
            name="alpha",
            current_filename="alpha_gueltig.txt",
            proposed_filename="alpha_vorschlag.txt",
        )
    ]


def test_batch_notebook_is_valid_and_has_batch_helpers():
    notebook_path = REPO_ROOT / "notebooks" / "batch_full_run.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    sources = ["".join(cell.get("source", [])) for cell in notebook.get("cells", [])]

    assert any("load_batch_result" in source for source in sources)
    assert any("preview_scenarios" in source for source in sources)
    assert any("quality_output_dir_for_batch" in source for source in sources)
    assert any("failed_existing_sessions" in source for source in sources)
    assert any("await resume_existing_sessions" in source for source in sources)
    assert any('batch_id=""' in source for source in sources)
    assert all(
        not cell.get("outputs")
        for cell in notebook.get("cells", [])
        if cell.get("cell_type") == "code"
    )
    assert all(
        cell.get("execution_count") is None
        for cell in notebook.get("cells", [])
        if cell.get("cell_type") == "code"
    )

    py_compile.compile(
        str(REPO_ROOT / "scripts" / "batch_full_run.py"),
        doraise=True,
    )


def test_build_scenarios_keeps_expected_matrix_order():
    scenarios = build_scenarios(
        [LawPair("alpha", "alpha_gueltig.txt", "alpha_vorschlag.txt")],
        [
            ModelSpec("gemini", "gemini-3.1-pro-preview"),
            ModelSpec("gemini", "gemini-3.5-flash"),
        ],
        [True, False],
        2,
    )

    assert [scenario.scenario_id for scenario in scenarios] == [
        "alpha__gemini-3.1-pro-preview__dr__01",
        "alpha__gemini-3.1-pro-preview__dr__02",
        "alpha__gemini-3.1-pro-preview__no-dr__01",
        "alpha__gemini-3.1-pro-preview__no-dr__02",
        "alpha__gemini-3.5-flash__dr__01",
        "alpha__gemini-3.5-flash__dr__02",
        "alpha__gemini-3.5-flash__no-dr__01",
        "alpha__gemini-3.5-flash__no-dr__02",
    ]


def test_batch_result_rows_include_app_code_state(monkeypatch):
    monkeypatch.setattr(
        batch_full_run, "current_app_code_state", lambda: "develop@9b93524"
    )
    result = ScenarioResult(
        status="success",
        law_pair="alpha",
        model="gemini-3.5-flash",
        deep_research=False,
        repetition=1,
        app_code_state=batch_full_run.current_app_code_state(),
    )

    row = result.to_row(include_diagnostics=True)

    assert row["app_code_state"] == "develop@9b93524"


def test_build_scenarios_can_limit_matrix():
    scenarios = build_scenarios(
        [
            LawPair("alpha", "alpha_gueltig.txt", "alpha_vorschlag.txt"),
            LawPair("beta", "beta_gueltig.txt", "beta_vorschlag.txt"),
        ],
        [ModelSpec("gemini", "gemini-3.5-flash")],
        [False],
        3,
        limit=4,
    )

    assert len(scenarios) == 4
    assert scenarios[-1].scenario_id == "beta__gemini-3.5-flash__no-dr__01"


def test_select_scenarios_filters_exact_ids_after_building_full_matrix():
    scenarios = select_scenarios(
        [
            LawPair("alpha", "alpha_gueltig.txt", "alpha_vorschlag.txt"),
            LawPair("beta", "beta_gueltig.txt", "beta_vorschlag.txt"),
        ],
        [
            ModelSpec("gemini", "gemini-3.1-pro-preview"),
            ModelSpec("gemini", "gemini-3.5-flash"),
        ],
        [True, False],
        2,
        scenario_ids=("beta__gemini-3.5-flash__no-dr__02",),
    )

    assert [scenario.scenario_id for scenario in scenarios] == [
        "beta__gemini-3.5-flash__no-dr__02"
    ]


def test_preview_scenarios_returns_configured_matrix(tmp_path: Path):
    laws_dir = tmp_path / "laws"
    laws_dir.mkdir()
    (laws_dir / "alpha_gueltig.txt").write_text("A", encoding="utf-8")
    (laws_dir / "alpha_vorschlag.txt").write_text("B", encoding="utf-8")
    config = BatchConfig(
        law_pairs=("alpha",),
        models=(ModelSpec("gemini", "gemini-3.5-flash"),),
        deep_research_modes=(True, False),
        repetitions=1,
        built_in_laws_dir=laws_dir,
    )

    rows = preview_scenarios(config).to_dict("records")

    assert rows == [
        {
            "scenario_index": 1,
            "scenario_id": "alpha__gemini-3.5-flash__dr__01",
            "law_pair": "alpha",
            "model": "gemini-3.5-flash",
            "deep_research": True,
            "repetition": 1,
        },
        {
            "scenario_index": 2,
            "scenario_id": "alpha__gemini-3.5-flash__no-dr__01",
            "law_pair": "alpha",
            "model": "gemini-3.5-flash",
            "deep_research": False,
            "repetition": 1,
        },
    ]


def test_select_scenarios_rejects_unknown_ids():
    with pytest.raises(RuntimeError, match="No matching scenario"):
        select_scenarios(
            [LawPair("alpha", "alpha_gueltig.txt", "alpha_vorschlag.txt")],
            [ModelSpec("gemini", "gemini-3.5-flash")],
            [False],
            1,
            scenario_ids=("missing__gemini-3.5-flash__no-dr__01",),
        )


def test_validate_config_rejects_non_positive_concurrency():
    config = BatchConfig(concurrency=0, max_run_attempts=1)

    try:
        validate_config(config)
    except ValueError as exc:
        assert str(exc) == "concurrency must be at least 1"
    else:
        raise AssertionError("validate_config should reject concurrency=0")


def test_validate_config_rejects_non_positive_deep_research_attempts():
    config = BatchConfig(max_deep_research_attempts=0)

    try:
        validate_config(config)
    except ValueError as exc:
        assert str(exc) == "max_deep_research_attempts must be at least 1"
    else:
        raise AssertionError("validate_config should reject max_deep_research_attempts=0")


def test_validate_config_rejects_non_positive_export_attempts():
    config = BatchConfig(max_export_attempts=0)

    try:
        validate_config(config)
    except ValueError as exc:
        assert str(exc) == "max_export_attempts must be at least 1"
    else:
        raise AssertionError("validate_config should reject max_export_attempts=0")


def test_validate_config_accepts_zero_stuck_minutes_as_disabled():
    validate_config(BatchConfig(max_stuck_minutes=0))


def test_validate_config_rejects_negative_stuck_minutes():
    config = BatchConfig(max_stuck_minutes=-1)

    try:
        validate_config(config)
    except ValueError as exc:
        assert str(exc) == "max_stuck_minutes must not be negative"
    else:
        raise AssertionError("validate_config should reject negative max_stuck_minutes")


def test_load_dotenv_if_available_reads_file_without_overriding_shell_env(
    tmp_path: Path,
    monkeypatch,
):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "CCC_BATCH_EMAIL=batch@example.test",
                "CCC_BATCH_PASSWORD='from-file'",
                "EXISTING_VALUE=from-file",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("CCC_BATCH_EMAIL", raising=False)
    monkeypatch.delenv("CCC_BATCH_PASSWORD", raising=False)
    monkeypatch.setenv("EXISTING_VALUE", "from-shell")

    assert load_dotenv_if_available(env_path) is True

    assert load_config_from_env().email == "batch@example.test"
    assert load_config_from_env().password == "from-file"
    assert os.environ["EXISTING_VALUE"] == "from-shell"


def test_redacted_config_does_not_include_secrets(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret-gemini-key")
    config = BatchConfig(
        email="batch@example.test",
        password="secret-password",
        gemini_api_key="",
    )

    payload = redacted_config(config)

    assert payload["email"] == "batch@example.test"
    assert payload["password"] == "<redacted>"
    assert payload["gemini_api_key_present"] is True
    assert "secret-password" not in json.dumps(payload)
    assert "secret-gemini-key" not in json.dumps(payload)


def test_deep_research_failure_uses_separate_retry_cap():
    requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.method == "POST" and request.url.path == "/sessions/run-all/start":
            return httpx.Response(
                200,
                json={
                    "app_session_id": "ABC123",
                    "run_id": "run-1",
                    "started": True,
                    "status": "running",
                },
            )
        if request.method == "GET" and request.url.path == "/sessions/run-all/run-1":
            return httpx.Response(
                200,
                json={
                    "app_session_id": "ABC123",
                    "run_id": "run-1",
                    "status": "failed",
                    "ok": False,
                    "steps": [
                        {
                            "key": "effort",
                            "label": "Aufwand quantifizieren",
                            "status": "failed",
                            "message": "Deep Research failed",
                        }
                    ],
                    "final_status": {
                        "case_group_research_status": "failed",
                        "last_failed_message": "Deep Research failed",
                    },
                    "current_step": None,
                    "current_label": None,
                    "current_norm_addressee": None,
                    "last_error": "Deep Research failed",
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    config = BatchConfig(
        max_run_attempts=5,
        max_deep_research_attempts=1,
        poll_seconds=0,
    )
    scenario = build_scenarios(
        [LawPair("alpha", "alpha_gueltig.txt", "alpha_vorschlag.txt")],
        [ModelSpec("gemini", "gemini-3.5-flash")],
        [True],
        1,
    )[0]

    async def run_test():
        async with httpx.AsyncClient(
            base_url="http://testserver",
            transport=httpx.MockTransport(handler),
        ) as client:
            return await run_workflow_with_retries(
                client,
                scenario,
                "ABC123",
                config,
                {},
            )

    _status, attempts, retry_reasons = asyncio.run(run_test())

    assert attempts == 1
    assert retry_reasons[-1] == "Deep Research retry cap reached (1)"
    assert requests.count(("POST", "/sessions/run-all/start")) == 1


def test_run_batch_smoke_with_mocked_api(tmp_path: Path):
    laws_dir = tmp_path / "laws"
    laws_dir.mkdir()
    (laws_dir / "alpha_gueltig.txt").write_text("A", encoding="utf-8")
    (laws_dir / "alpha_vorschlag.txt").write_text("B", encoding="utf-8")
    requests: list[tuple[str, str, dict | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8") or "{}") if request.content else None
        requests.append((request.method, request.url.path, body))
        if request.method == "POST" and request.url.path == "/auth/login":
            return httpx.Response(
                200,
                json={
                    "user_id": 1,
                    "email": "batch@example.test",
                    "is_admin": False,
                },
            )
        if request.method == "GET" and request.url.path == "/regulations":
            return httpx.Response(
                200,
                json={"files": ["alpha_gueltig.txt", "alpha_vorschlag.txt"]},
            )
        if request.method == "POST" and request.url.path == "/sessions":
            return httpx.Response(
                200,
                json={
                    "app_session_id": "ABC123",
                    "created": True,
                    "case_group_research_enabled": True,
                },
            )
        if request.method == "POST" and request.url.path == "/sessions/case-group-research":
            return httpx.Response(
                200,
                json={
                    "app_session_id": "ABC123",
                    "enabled": body["enabled"],
                    "status": "idle",
                    "locked": False,
                    "elapsed_seconds": None,
                    "gemini_key_available": True,
                },
            )
        if request.method == "POST" and request.url.path == "/sessions/run-all/start":
            return httpx.Response(
                200,
                json={
                    "app_session_id": "ABC123",
                    "run_id": "run-1",
                    "started": True,
                    "status": "running",
                },
            )
        if request.method == "GET" and request.url.path == "/sessions/run-all/run-1":
            return httpx.Response(
                200,
                json={
                    "app_session_id": "ABC123",
                    "run_id": "run-1",
                    "status": "completed",
                    "ok": True,
                    "steps": [
                        {
                            "key": "total_cost",
                            "label": "Gesamtkosten berechnen",
                            "status": "completed",
                        }
                    ],
                    "final_status": None,
                    "current_step": None,
                    "current_label": None,
                    "current_norm_addressee": None,
                    "last_error": None,
                },
            )
        if request.method == "POST" and request.url.path == "/sessions/compliance-text-export":
            return httpx.Response(200, content=b"%PDF")
        if request.method == "GET" and request.url.path == "/sessions/llm-monitor":
            return httpx.Response(
                200,
                json={
                    "app_session_id": "ABC123",
                    "pending": [],
                    "recent": [
                        {
                            "prompt_id": "law_summary",
                            "answer_state": "active",
                            "estimated_cost_usd": 0.1,
                        },
                        {
                            "prompt_id": "deep_research_case_group_metrics",
                            "answer_state": "active",
                            "estimated_cost_usd": 0.2,
                        },
                        {
                            "prompt_id": "regulations_identification",
                            "answer_state": "invalid",
                            "estimated_cost_usd": None,
                        },
                    ],
                    "events": [],
                    "stream_attempts": [],
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    config = BatchConfig(
        base_url="http://testserver",
        email="batch@example.test",
        password="password",
        law_pairs=("alpha",),
        models=(ModelSpec("gemini", "gemini-3.5-flash"),),
        deep_research_modes=(True,),
        repetitions=1,
        concurrency=1,
        output_dir=tmp_path / "out",
        batch_id="batch-test",
        built_in_laws_dir=laws_dir,
        poll_seconds=0,
    )

    result = asyncio.run(run_batch(config, transport=httpx.MockTransport(handler)))

    assert result.results[0].status == "success"
    assert result.results[0].app_session_id == "ABC123"
    assert result.results[0].estimated_llm_cost_usd == 0.1
    assert result.results[0].estimated_dr_cost_usd == 0.2
    assert result.results[0].estimated_total_cost_usd == pytest.approx(0.3)
    assert result.results[0].missing_cost_estimates == 1
    assert result.output_dir == tmp_path / "out" / "batch-test"
    assert (result.output_dir / "runs.jsonl").exists()
    assert (result.output_dir / "summary.csv").exists()
    assert (result.output_dir / "config.json").exists()
    config_snapshot = json.loads((result.output_dir / "config.json").read_text(encoding="utf-8"))
    assert config_snapshot["batch_id"] == "batch-test"
    assert config_snapshot["effective_output_dir"] == str(result.output_dir)
    assert "<redacted>" in json.dumps(config_snapshot)
    diagnostic_row = json.loads((result.output_dir / "runs.jsonl").read_text(encoding="utf-8"))
    assert diagnostic_row["batch_id"] == "batch-test"
    assert diagnostic_row["scenario_index"] == 1
    assert diagnostic_row["scenario_total"] == 1
    assert list((result.output_dir / "pdf").glob("*.pdf"))
    assert (
        "POST",
        "/sessions/case-group-research",
        {"app_session_id": "ABC123", "enabled": True},
    ) in requests


def test_run_batch_auto_batch_id_keeps_root_output_dir_clean(tmp_path: Path):
    laws_dir = tmp_path / "laws"
    laws_dir.mkdir()
    (laws_dir / "alpha_gueltig.txt").write_text("A", encoding="utf-8")
    (laws_dir / "alpha_vorschlag.txt").write_text("B", encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/auth/login":
            return httpx.Response(200, json={"user_id": 1, "email": "batch@example.test"})
        if request.method == "GET" and request.url.path == "/regulations":
            return httpx.Response(
                200,
                json={"files": ["alpha_gueltig.txt", "alpha_vorschlag.txt"]},
            )
        if request.method == "POST" and request.url.path == "/sessions":
            return httpx.Response(200, json={"app_session_id": "ABC123", "created": True})
        if request.method == "POST" and request.url.path == "/sessions/case-group-research":
            return httpx.Response(200, json={"app_session_id": "ABC123", "enabled": False})
        if request.method == "POST" and request.url.path == "/sessions/run-all/start":
            return httpx.Response(200, json={"run_id": "run-1", "status": "running"})
        if request.method == "GET" and request.url.path == "/sessions/run-all/run-1":
            return httpx.Response(200, json={"status": "completed", "ok": True, "steps": []})
        if request.method == "POST" and request.url.path == "/sessions/compliance-text-export":
            return httpx.Response(200, content=b"%PDF")
        if request.method == "GET" and request.url.path == "/sessions/llm-monitor":
            return httpx.Response(200, json={"recent": []})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    config = BatchConfig(
        base_url="http://testserver",
        email="batch@example.test",
        password="password",
        law_pairs=("alpha",),
        models=(ModelSpec("gemini", "gemini-3.5-flash"),),
        deep_research_modes=(False,),
        repetitions=1,
        concurrency=1,
        output_dir=tmp_path / "out",
        built_in_laws_dir=laws_dir,
        poll_seconds=0,
    )

    result = asyncio.run(run_batch(config, transport=httpx.MockTransport(handler)))

    assert result.output_dir.parent == tmp_path / "out"
    assert result.output_dir.name.startswith("batch_")
    assert not (tmp_path / "out" / "runs.jsonl").exists()
    assert (result.output_dir / "runs.jsonl").exists()


def test_quality_output_dir_uses_batch_name(tmp_path: Path):
    batch_dir = tmp_path / "batch_runs" / "full_matrix_once_20260804"

    assert quality_output_dir_for_batch(
        batch_dir,
        output_root=tmp_path / "code_analysis" / "output",
    ) == tmp_path / "code_analysis" / "output" / "full_matrix_once_20260804"


def test_result_dataframe_default_columns(tmp_path: Path):
    result = build_scenarios(
        [LawPair("alpha", "alpha_gueltig.txt", "alpha_vorschlag.txt")],
        [ModelSpec("gemini", "gemini-3.5-flash")],
        [False],
        1,
    )[0]

    batch_result = BatchResult(
        results=[
            ScenarioResult(
                status="success",
                law_pair=result.law_pair.name,
                model=result.model_spec.model,
                deep_research=False,
                repetition=1,
            )
        ],
        output_dir=tmp_path,
    )

    assert list(batch_result.to_dataframe().columns) == [
        "status",
        "scenario_id",
        "law_pair",
        "model",
        "deep_research",
        "repetition",
        "app_session_id",
        "duration_min",
        "run_attempts",
        "export_status",
        "export_attempts",
        "estimated_llm_cost_usd",
        "estimated_dr_cost_usd",
        "estimated_total_cost_usd",
        "missing_cost_estimates",
        "error",
    ]


def test_run_batch_resumes_by_skipping_successful_scenarios(tmp_path: Path):
    laws_dir = tmp_path / "laws"
    laws_dir.mkdir()
    (laws_dir / "alpha_gueltig.txt").write_text("A", encoding="utf-8")
    (laws_dir / "alpha_vorschlag.txt").write_text("B", encoding="utf-8")
    output_dir = tmp_path / "out"
    batch_dir = output_dir / "resume-test"
    batch_dir.mkdir(parents=True)
    (batch_dir / "runs.jsonl").write_text(
        json.dumps(
            {
                "status": "success",
                "scenario_id": "alpha__gemini-3.5-flash__no-dr__01",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.method == "POST" and request.url.path == "/auth/login":
            return httpx.Response(200, json={"user_id": 1, "email": "batch@example.test"})
        if request.method == "GET" and request.url.path == "/regulations":
            return httpx.Response(
                200,
                json={"files": ["alpha_gueltig.txt", "alpha_vorschlag.txt"]},
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    config = BatchConfig(
        base_url="http://testserver",
        email="batch@example.test",
        password="password",
        law_pairs=("alpha",),
        models=(ModelSpec("gemini", "gemini-3.5-flash"),),
        deep_research_modes=(False,),
        repetitions=1,
        concurrency=1,
        output_dir=output_dir,
        batch_id="resume-test",
        built_in_laws_dir=laws_dir,
    )

    result = asyncio.run(run_batch(config, transport=httpx.MockTransport(handler)))

    assert result.results == []
    assert ("POST", "/sessions") not in requests


def test_run_batch_scenario_ids_force_single_rerun_when_resume_is_disabled(tmp_path: Path):
    laws_dir = tmp_path / "laws"
    laws_dir.mkdir()
    (laws_dir / "alpha_gueltig.txt").write_text("A", encoding="utf-8")
    (laws_dir / "alpha_vorschlag.txt").write_text("B", encoding="utf-8")
    output_dir = tmp_path / "out"
    batch_dir = output_dir / "rerun-test"
    batch_dir.mkdir(parents=True)
    scenario_id = "alpha__gemini-3.5-flash__no-dr__02"
    (batch_dir / "runs.jsonl").write_text(
        json.dumps({"status": "success", "scenario_id": scenario_id}) + "\n",
        encoding="utf-8",
    )
    run_all_payloads: list[dict | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8") or "{}") if request.content else None
        if request.method == "POST" and request.url.path == "/auth/login":
            return httpx.Response(200, json={"user_id": 1, "email": "batch@example.test"})
        if request.method == "GET" and request.url.path == "/regulations":
            return httpx.Response(
                200,
                json={"files": ["alpha_gueltig.txt", "alpha_vorschlag.txt"]},
            )
        if request.method == "POST" and request.url.path == "/sessions":
            return httpx.Response(200, json={"app_session_id": "RERUN1", "created": True})
        if request.method == "POST" and request.url.path == "/sessions/case-group-research":
            return httpx.Response(200, json={"app_session_id": "RERUN1", "enabled": False})
        if request.method == "POST" and request.url.path == "/sessions/run-all/start":
            run_all_payloads.append(body)
            return httpx.Response(200, json={"run_id": "run-1", "status": "running"})
        if request.method == "GET" and request.url.path == "/sessions/run-all/run-1":
            return httpx.Response(200, json={"status": "completed", "ok": True, "steps": []})
        if request.method == "POST" and request.url.path == "/sessions/compliance-text-export":
            return httpx.Response(200, content=b"%PDF")
        if request.method == "GET" and request.url.path == "/sessions/llm-monitor":
            return httpx.Response(200, json={"recent": []})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    config = BatchConfig(
        base_url="http://testserver",
        email="batch@example.test",
        password="password",
        law_pairs=("alpha",),
        models=(ModelSpec("gemini", "gemini-3.5-flash"),),
        deep_research_modes=(False,),
        repetitions=2,
        concurrency=1,
        resume_completed=False,
        output_dir=output_dir,
        batch_id="rerun-test",
        built_in_laws_dir=laws_dir,
        scenario_ids=(scenario_id,),
        poll_seconds=0,
    )

    result = asyncio.run(run_batch(config, transport=httpx.MockTransport(handler)))

    assert len(result.results) == 1
    assert result.results[0].scenario_id == scenario_id
    assert run_all_payloads == [
        {
            "app_session_id": "RERUN1",
            "model": "gemini-3.5-flash",
            "provider": "gemini",
            "current_filename": "alpha_gueltig.txt",
            "proposed_filename": "alpha_vorschlag.txt",
        }
    ]


def test_resume_existing_sessions_reuses_session_and_appends_log(tmp_path: Path):
    laws_dir = tmp_path / "laws"
    laws_dir.mkdir()
    (laws_dir / "alpha_gueltig.txt").write_text("A", encoding="utf-8")
    (laws_dir / "alpha_vorschlag.txt").write_text("B", encoding="utf-8")
    output_dir = tmp_path / "out"
    requests: list[tuple[str, str, dict | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8") or "{}") if request.content else None
        requests.append((request.method, request.url.path, body))
        if request.method == "POST" and request.url.path == "/auth/login":
            return httpx.Response(200, json={"user_id": 1, "email": "batch@example.test"})
        if request.method == "GET" and request.url.path == "/regulations":
            return httpx.Response(
                200,
                json={"files": ["alpha_gueltig.txt", "alpha_vorschlag.txt"]},
            )
        if request.method == "GET" and request.url.path == "/sessions/status":
            return httpx.Response(200, json={"total_cost_ready": False})
        if request.method == "POST" and request.url.path == "/sessions/run-all/start":
            return httpx.Response(200, json={"run_id": "run-1", "status": "running"})
        if request.method == "GET" and request.url.path == "/sessions/run-all/run-1":
            return httpx.Response(200, json={"status": "completed", "ok": True, "steps": []})
        if request.method == "POST" and request.url.path == "/sessions/compliance-text-export":
            return httpx.Response(200, content=b"%PDF")
        if request.method == "GET" and request.url.path == "/sessions/llm-monitor":
            return httpx.Response(200, json={"recent": []})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    config = BatchConfig(
        base_url="http://testserver",
        email="batch@example.test",
        password="password",
        law_pairs=("alpha",),
        models=(ModelSpec("gemini", "gemini-3.5-flash"),),
        deep_research_modes=(True,),
        repetitions=1,
        concurrency=1,
        output_dir=output_dir,
        batch_id="resume-existing-test",
        built_in_laws_dir=laws_dir,
        poll_seconds=0,
    )

    result = asyncio.run(
        resume_existing_sessions(
            config,
            {"alpha__gemini-3.5-flash__dr__01": "EXIST1"},
            transport=httpx.MockTransport(handler),
            max_deep_research_attempts=3,
        )
    )

    assert result.results[0].status == "success"
    assert result.results[0].app_session_id == "EXIST1"
    assert result.results[0].retry_reasons[0] == "Resumed existing session EXIST1"
    assert ("POST", "/sessions", None) not in requests
    assert (
        "POST",
        "/sessions/case-group-research",
        {"app_session_id": "EXIST1", "enabled": True},
    ) not in requests
    assert (
        "POST",
        "/sessions/run-all/start",
        {
            "app_session_id": "EXIST1",
            "model": "gemini-3.5-flash",
            "provider": "gemini",
            "current_filename": "alpha_gueltig.txt",
            "proposed_filename": "alpha_vorschlag.txt",
        },
    ) in requests
    row = json.loads((result.output_dir / "runs.jsonl").read_text(encoding="utf-8"))
    assert row["app_session_id"] == "EXIST1"
    assert row["retry_reasons"].startswith("Resumed existing session EXIST1")


def test_resume_existing_session_with_total_cost_ready_retries_export_only(tmp_path: Path):
    laws_dir = tmp_path / "laws"
    laws_dir.mkdir()
    (laws_dir / "alpha_gueltig.txt").write_text("A", encoding="utf-8")
    (laws_dir / "alpha_vorschlag.txt").write_text("B", encoding="utf-8")
    output_dir = tmp_path / "out"
    requests: list[tuple[str, str]] = []
    export_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal export_calls
        requests.append((request.method, request.url.path))
        if request.method == "POST" and request.url.path == "/auth/login":
            return httpx.Response(200, json={"user_id": 1, "email": "batch@example.test"})
        if request.method == "GET" and request.url.path == "/regulations":
            return httpx.Response(
                200,
                json={"files": ["alpha_gueltig.txt", "alpha_vorschlag.txt"]},
            )
        if request.method == "GET" and request.url.path == "/sessions/status":
            return httpx.Response(200, json={"total_cost_ready": True})
        if request.method == "POST" and request.url.path == "/sessions/compliance-text-export":
            export_calls += 1
            if export_calls == 1:
                return httpx.Response(500, text="temporary export failure")
            return httpx.Response(200, content=b"%PDF")
        if request.method == "GET" and request.url.path == "/sessions/llm-monitor":
            return httpx.Response(200, json={"recent": []})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    config = BatchConfig(
        base_url="http://testserver",
        email="batch@example.test",
        password="password",
        law_pairs=("alpha",),
        models=(ModelSpec("gemini", "gemini-3.5-flash"),),
        deep_research_modes=(True,),
        repetitions=1,
        concurrency=1,
        max_export_attempts=2,
        output_dir=output_dir,
        batch_id="resume-export-test",
        built_in_laws_dir=laws_dir,
    )

    result = asyncio.run(
        resume_existing_sessions(
            config,
            {"alpha__gemini-3.5-flash__dr__01": "EXIST1"},
            transport=httpx.MockTransport(handler),
        )
    )

    assert result.results[0].status == "success"
    assert result.results[0].run_attempts == 0
    assert result.results[0].export_attempts == 2
    assert ("POST", "/sessions/run-all/start") not in requests
    assert export_calls == 2


def test_export_retry_handles_transient_request_errors(tmp_path: Path):
    laws_dir = tmp_path / "laws"
    laws_dir.mkdir()
    (laws_dir / "alpha_gueltig.txt").write_text("A", encoding="utf-8")
    (laws_dir / "alpha_vorschlag.txt").write_text("B", encoding="utf-8")
    output_dir = tmp_path / "out"
    export_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal export_calls
        if request.method == "POST" and request.url.path == "/auth/login":
            return httpx.Response(200, json={"user_id": 1, "email": "batch@example.test"})
        if request.method == "GET" and request.url.path == "/regulations":
            return httpx.Response(
                200,
                json={"files": ["alpha_gueltig.txt", "alpha_vorschlag.txt"]},
            )
        if request.method == "POST" and request.url.path == "/sessions":
            return httpx.Response(200, json={"app_session_id": "FRESH1", "created": True})
        if request.method == "POST" and request.url.path == "/sessions/case-group-research":
            return httpx.Response(200, json={"app_session_id": "FRESH1", "enabled": False})
        if request.method == "POST" and request.url.path == "/sessions/run-all/start":
            return httpx.Response(200, json={"run_id": "run-1", "status": "running"})
        if request.method == "GET" and request.url.path == "/sessions/run-all/run-1":
            return httpx.Response(200, json={"status": "completed", "ok": True, "steps": []})
        if request.method == "POST" and request.url.path == "/sessions/compliance-text-export":
            export_calls += 1
            if export_calls == 1:
                raise httpx.ReadError("temporary read failure", request=request)
            return httpx.Response(200, content=b"%PDF")
        if request.method == "GET" and request.url.path == "/sessions/llm-monitor":
            return httpx.Response(200, json={"recent": []})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    config = BatchConfig(
        base_url="http://testserver",
        email="batch@example.test",
        password="password",
        law_pairs=("alpha",),
        models=(ModelSpec("gemini", "gemini-3.5-flash"),),
        deep_research_modes=(False,),
        repetitions=1,
        concurrency=1,
        max_export_attempts=2,
        output_dir=output_dir,
        batch_id="export-retry-test",
        built_in_laws_dir=laws_dir,
        poll_seconds=0,
    )

    result = asyncio.run(run_batch(config, transport=httpx.MockTransport(handler)))

    assert result.results[0].status == "success"
    assert result.results[0].export_attempts == 2
    assert export_calls == 2
    assert "temporary read failure" in result.results[0].export_retry_reasons[0]


def test_summary_dataframe_aggregates_costs_duration_and_status(tmp_path: Path):
    batch_result = BatchResult(
        results=[
            ScenarioResult(
                status="success",
                law_pair="alpha",
                model="gemini-3.5-flash",
                deep_research=False,
                repetition=1,
                duration_min=2.0,
                run_attempts=1,
                estimated_llm_cost_usd=0.1,
                estimated_dr_cost_usd=0.0,
                estimated_total_cost_usd=0.1,
                missing_cost_estimates=0,
            ),
            ScenarioResult(
                status="success",
                law_pair="alpha",
                model="gemini-3.5-flash",
                deep_research=True,
                repetition=1,
                duration_min=6.0,
                run_attempts=2,
                estimated_llm_cost_usd=0.2,
                estimated_dr_cost_usd=0.3,
                estimated_total_cost_usd=0.5,
                missing_cost_estimates=1,
            ),
            ScenarioResult(
                status="failed",
                law_pair="alpha",
                model="gemini-3.1-pro-preview",
                deep_research=True,
                repetition=1,
                duration_min=4.0,
                run_attempts=2,
                estimated_llm_cost_usd=0.4,
                estimated_dr_cost_usd=0.6,
                estimated_total_cost_usd=1.0,
                missing_cost_estimates=2,
            ),
        ],
        output_dir=tmp_path,
    )

    rows = batch_result.to_summary_dataframe().set_index("group").to_dict("index")

    assert rows["gesamt"]["runs"] == 3
    assert rows["gesamt"]["success"] == 2
    assert rows["gesamt"]["failed"] == 1
    assert rows["gesamt"]["total_run_attempts"] == 5
    assert rows["gesamt"]["total_cost_usd"] == 1.6
    assert rows["gesamt"]["avg_duration_min"] == 4.0
    assert rows["gesamt"]["std_duration_min"] == 1.63
    assert rows["gesamt"]["std_cost_usd"] == 0.3682
    assert rows["gesamt"]["missing_cost_estimates"] == 3
    assert rows["model=gemini-3.5-flash"]["avg_cost_usd"] == 0.3
    assert rows["model=gemini-3.5-flash"]["std_cost_usd"] == 0.2
    assert rows["deep_research=True"]["avg_dr_cost_usd"] == 0.45
    assert rows["deep_research=True"]["std_dr_cost_usd"] == 0.15
    assert rows["model=gemini-3.5-flash | deep_research=False"]["runs"] == 1
    assert rows["model=gemini-3.5-flash | deep_research=False"]["std_cost_usd"] == 0.0


def test_latest_dataframe_keeps_one_row_per_scenario_with_attempt_history(tmp_path: Path):
    batch_result = BatchResult(
        results=[
            ScenarioResult(
                status="failed",
                scenario_id="alpha__gemini-3.5-flash__dr__01",
                law_pair="alpha",
                model="gemini-3.5-flash",
                deep_research=True,
                repetition=1,
                app_session_id="EXIST1",
                run_attempts=1,
                retry_reasons=["first failure"],
            ),
            ScenarioResult(
                status="success",
                scenario_id="alpha__gemini-3.5-flash__dr__01",
                law_pair="alpha",
                model="gemini-3.5-flash",
                deep_research=True,
                repetition=1,
                app_session_id="EXIST1",
                run_attempts=2,
                retry_reasons=["resumed"],
                export_retry_reasons=["export retry"],
            ),
            ScenarioResult(
                status="success",
                scenario_id="beta__gemini-3.5-flash__dr__01",
                law_pair="beta",
                model="gemini-3.5-flash",
                deep_research=True,
                repetition=1,
                app_session_id="OTHER1",
                run_attempts=1,
            ),
        ],
        output_dir=tmp_path,
    )

    all_attempts = batch_result.to_dataframe(mode="all_attempts")
    latest = batch_result.to_dataframe(mode="latest", include_diagnostics=True)
    summary = batch_result.to_summary_dataframe()

    assert len(all_attempts) == 3
    assert len(latest) == 2
    alpha = latest.loc[
        latest["scenario_id"].eq("alpha__gemini-3.5-flash__dr__01")
    ].iloc[0]
    assert alpha["status"] == "success"
    assert alpha["batch_log_attempt_rows"] == 2
    assert alpha["batch_log_status_history"] == "failed -> success"
    assert alpha["batch_log_total_run_attempts"] == 3
    assert alpha["batch_log_retry_reasons"] == "first failure; resumed"
    assert alpha["batch_log_export_retry_reasons"] == "export retry"
    assert alpha["batch_log_app_session_ids"] == "EXIST1"
    assert summary.loc[summary["group"].eq("gesamt"), "runs"].iloc[0] == 2
    assert summary.loc[summary["group"].eq("gesamt"), "total_run_attempts"].iloc[0] == 4
    assert summary.loc[summary["group"].eq("gesamt"), "avg_attempts"].iloc[0] == 2.0


def test_failed_existing_sessions_uses_latest_status_per_scenario(tmp_path: Path):
    batch_result = BatchResult(
        results=[
            ScenarioResult(
                status="failed",
                scenario_id="alpha__gemini-3.5-flash__dr__01",
                law_pair="alpha",
                model="gemini-3.5-flash",
                deep_research=True,
                repetition=1,
                app_session_id="ALPHA1",
            ),
            ScenarioResult(
                status="success",
                scenario_id="alpha__gemini-3.5-flash__dr__01",
                law_pair="alpha",
                model="gemini-3.5-flash",
                deep_research=True,
                repetition=1,
                app_session_id="ALPHA1",
            ),
            ScenarioResult(
                status="export_failed",
                scenario_id="beta__gemini-3.5-flash__dr__01",
                law_pair="beta",
                model="gemini-3.5-flash",
                deep_research=True,
                repetition=1,
                app_session_id="BETA1",
            ),
        ],
        output_dir=tmp_path,
    )

    assert failed_existing_sessions(batch_result) == {
        "beta__gemini-3.5-flash__dr__01": "BETA1"
    }


def test_batch_logger_rewrites_stale_summary_csv_header(tmp_path: Path):
    logger = BatchLogger(tmp_path)
    (tmp_path / "summary.csv").write_text("status,scenario_id\nfailed,old\n", encoding="utf-8")
    (tmp_path / "runs.jsonl").write_text(
        json.dumps(
            {
                "status": "failed",
                "scenario_id": "old",
                "law_pair": "alpha",
                "model": "gemini-3.5-flash",
                "deep_research": False,
                "repetition": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    logger.write_result(
        ScenarioResult(
            status="success",
            scenario_id="new",
            law_pair="alpha",
            model="gemini-3.5-flash",
            deep_research=False,
            repetition=1,
            export_attempts=2,
        )
    )

    with (tmp_path / "summary.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 2
    assert "export_attempts" in rows[0]
    assert rows[1]["scenario_id"] == "new"
    assert rows[1]["export_attempts"] == "2"


def test_load_batch_result_reconstructs_results_from_jsonl(tmp_path: Path):
    (tmp_path / "runs.jsonl").write_text(
        json.dumps(
            {
                "status": "success",
                "scenario_id": "alpha__gemini-3.5-flash__no-dr__01",
                "law_pair": "alpha",
                "model": "gemini-3.5-flash",
                "deep_research": False,
                "repetition": 1,
                "app_session_id": "ABC123",
                "estimated_total_cost_usd": 0.42,
                "retry_reasons": ["first retry", "second retry"],
                "export_retry_reasons": "export retry one; export retry two",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = load_batch_result(tmp_path)

    assert result.output_dir == tmp_path
    assert len(result.results) == 1
    assert result.results[0].app_session_id == "ABC123"
    assert result.results[0].estimated_total_cost_usd == 0.42
    assert result.results[0].retry_reasons == ["first retry", "second retry"]
    assert result.results[0].export_retry_reasons == [
        "export retry one",
        "export retry two",
    ]
