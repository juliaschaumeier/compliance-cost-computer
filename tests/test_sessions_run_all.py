import json
import time
import asyncio

from backend.core import db
from backend.routers import (
    case_groups as case_groups_router,
    effort as effort_router,
    process_steps as process_steps_router,
    processes as processes_router,
    regulations as regulations_router,
)


def _patch_run_all_llms(monkeypatch, app_session_id: str) -> None:
    async def fake_regulations_llm(prompt, *_args, **_kwargs):
        if "vorgaben" in prompt.lower():
            return json.dumps(
                {
                    "vorgaben": [
                        {"normzitat": "§ 1", "beschreibung": "Vorgabe A"},
                        {"normzitat": "§ 2", "beschreibung": "Vorgabe B"},
                    ]
                }
            )
        return json.dumps({"title": "Kurz", "blurb": "Ein Satz."})

    async def fake_processes_llm(*_args, **_kwargs):
        session_id = db.get_session_id_by_app_id(app_session_id)
        assert session_id is not None
        regulations = db.list_regulations_for_session(session_id)
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_bezeichnung": "Prozess A",
                        "prozess_beschreibung": "Beschreibung Prozess A",
                        "vorgaben": [
                            {
                                "vorgaben_id": str(regulations[0]["regulation_id"]),
                                "normzitat": regulations[0]["legal_citation"],
                                "beschreibung": regulations[0]["description"],
                            }
                        ],
                    },
                    {
                        "prozess_bezeichnung": "Prozess B",
                        "prozess_beschreibung": "Beschreibung Prozess B",
                        "vorgaben": [
                            {
                                "vorgaben_id": str(regulations[1]["regulation_id"]),
                                "normzitat": regulations[1]["legal_citation"],
                                "beschreibung": regulations[1]["description"],
                            }
                        ],
                    },
                ]
            }
        )

    async def fake_case_groups_llm(*_args, **_kwargs):
        session_id = db.get_session_id_by_app_id(app_session_id)
        assert session_id is not None
        processes = db.list_processes_for_session(session_id)
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_id": str(processes[0]["process_id"]),
                        "prozess_bezeichnung": processes[0]["process"],
                        "prozess_beschreibung": processes[0]["description"],
                        "fallgruppen": [
                            {
                                "fallgruppe_bezeichnung": "Fallgruppe A",
                                "fallgruppe_beschreibung": "Beschreibung A",
                            }
                        ],
                    },
                    {
                        "prozess_id": str(processes[1]["process_id"]),
                        "prozess_bezeichnung": processes[1]["process"],
                        "prozess_beschreibung": processes[1]["description"],
                        "fallgruppen": [
                            {
                                "fallgruppe_bezeichnung": "Fallgruppe B",
                                "fallgruppe_beschreibung": "Beschreibung B",
                            }
                        ],
                    },
                ]
            }
        )

    async def fake_steps_llm(*_args, **_kwargs):
        session_id = db.get_session_id_by_app_id(app_session_id)
        assert session_id is not None
        processes = db.list_processes_for_session(session_id)
        case_groups = db.list_case_groups_for_session(session_id)
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_id": str(processes[0]["process_id"]),
                        "fallgruppen": [
                            {
                                "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                                "taetigkeiten": [
                                    {
                                        "taetigkeit": "Schritt A1",
                                        "beschreibung": "Beschreibung A1",
                                    },
                                    {
                                        "taetigkeit": "Schritt A2",
                                        "beschreibung": "Beschreibung A2",
                                    },
                                ],
                            }
                        ],
                    },
                    {
                        "prozess_id": str(processes[1]["process_id"]),
                        "fallgruppen": [
                            {
                                "fallgruppen_id": str(case_groups[1]["case_group_id"]),
                                "taetigkeiten": [
                                    {
                                        "taetigkeit": "Schritt B1",
                                        "beschreibung": "Beschreibung B1",
                                    }
                                ],
                            }
                        ],
                    },
                ]
            }
        )

    async def fake_effort_llm(prompt, *_args, **_kwargs):
        session_id = db.get_session_id_by_app_id(app_session_id)
        assert session_id is not None
        processes = db.list_processes_for_session(session_id)
        case_groups = db.list_case_groups_for_session(session_id)
        steps = db.list_process_steps_for_session(session_id)
        steps_by_group: dict[int, list[dict]] = {}
        for step in steps:
            steps_by_group.setdefault(int(step["case_group_id"]), []).append(step)
        if "fallzahl" in prompt.lower():
            return json.dumps(
                {
                    "prozesse": [
                        {
                            "prozess_id": str(processes[0]["process_id"]),
                            "fallgruppen": [
                                {
                                    "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                                    "anzahl_betroffene": "10",
                                    "haeufigkeit_pro_jahr": "2",
                                }
                            ],
                        },
                        {
                            "prozess_id": str(processes[1]["process_id"]),
                            "fallgruppen": [
                                {
                                    "fallgruppen_id": str(case_groups[1]["case_group_id"]),
                                    "anzahl_betroffene": "5",
                                    "haeufigkeit_pro_jahr": "1",
                                }
                            ],
                        },
                    ]
                }
            )
        effort_fallgruppen = []
        for group in case_groups:
            group_id = int(group["case_group_id"])
            taetigkeiten = [
                {
                    "taetigkeiten_id": str(step["step_id"]),
                    "taetigkeit": step["step"],
                    "beschreibung": step["description"],
                    "stundenlohn_satz_a": "50",
                    "zeitaufwand_in_min_a": "10",
                    "sachaufwand": "5",
                }
                for step in steps_by_group.get(group_id, [])
            ]
            effort_fallgruppen.append(
                {
                    "fallgruppen_id": str(group_id),
                    "fallgruppe_bezeichnung": group["case_group"],
                    "fallgruppe_beschreibung": group["description"],
                    "taetigkeiten": taetigkeiten,
                }
            )
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_id": str(processes[0]["process_id"]),
                        "fallgruppen": [effort_fallgruppen[0]],
                    },
                    {
                        "prozess_id": str(processes[1]["process_id"]),
                        "fallgruppen": [effort_fallgruppen[1]],
                    },
                ]
            }
        )

    monkeypatch.setattr(regulations_router, "query_llm", fake_regulations_llm)
    monkeypatch.setattr(processes_router, "query_llm", fake_processes_llm)
    monkeypatch.setattr(case_groups_router, "query_llm", fake_case_groups_llm)
    monkeypatch.setattr(process_steps_router, "query_llm", fake_steps_llm)
    monkeypatch.setattr(effort_router, "query_llm", fake_effort_llm)


def test_run_all_executes_workflow_end_to_end(test_client, monkeypatch):
    app_session_id = "RUNALL-E2E"
    db.insert_law("current.txt", "aktuelles gesetz")
    db.insert_law("proposed.txt", "neuer entwurf")
    _patch_run_all_llms(monkeypatch, app_session_id)

    start_response = test_client.post(
        "/sessions/run-all/start",
        json={
            "app_session_id": app_session_id,
            "current_filename": "current.txt",
            "proposed_filename": "proposed.txt",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    run_id = start_response.json()["run_id"]
    payload = _wait_for_run_completion(test_client, run_id)
    assert payload["status"] == "completed"
    assert payload["ok"] is True
    assert [step["key"] for step in payload["steps"]] == [
        "summary",
        "regulations",
        "processes",
        "case_groups",
        "process_steps",
        "effort",
        "total_cost",
    ]
    assert all(step["status"] == "completed" for step in payload["steps"])
    assert payload["final_status"]["total_cost_ready"] is True
    assert payload["final_status"]["last_completed_step"] == "total_cost"


def test_run_all_reports_step_failure(test_client):
    start_response = test_client.post(
        "/sessions/run-all/start",
        json={"app_session_id": "RUNALL-FAIL", "model": "test-model"},
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(test_client, start_response.json()["run_id"])
    assert payload["status"] == "failed"
    assert payload["ok"] is False
    assert payload["steps"][0]["key"] == "summary"
    assert payload["steps"][0]["status"] == "failed"
    assert "proposed_filename" in (payload["steps"][0]["message"] or "")
    assert payload["final_status"]["summary_ready"] is False


def test_run_all_skips_summary_when_already_done(test_client, monkeypatch):
    app_session_id = "RUNALL-SKIP"
    db.insert_law("current_skip.txt", "aktuelles gesetz")
    db.insert_law("proposed_skip.txt", "neuer entwurf")
    _patch_run_all_llms(monkeypatch, app_session_id)

    summary_response = test_client.post(
        "/regulations/summary",
        json={
            "filename": "proposed_skip.txt",
            "current_filename": "current_skip.txt",
            "app_session_id": app_session_id,
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert summary_response.status_code == 200

    start_response = test_client.post(
        "/sessions/run-all/start",
        json={"app_session_id": app_session_id, "model": "test-model", "provider": "openai"},
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(test_client, start_response.json()["run_id"])
    assert payload["status"] == "completed"
    assert payload["ok"] is True
    assert payload["steps"][0]["key"] == "summary"
    assert payload["steps"][0]["status"] == "skipped"
    assert payload["final_status"]["total_cost_ready"] is True


def _wait_for_run_completion(test_client, run_id: str, timeout_s: float = 5.0) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        response = test_client.get(f"/sessions/run-all/{run_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] != "running":
            return payload
        time.sleep(0.05)
    raise AssertionError("Run did not finish before timeout")


def test_run_all_start_returns_run_id_and_completes(test_client, monkeypatch):
    app_session_id = "RUNALL-START"
    db.insert_law("current_start.txt", "aktuelles gesetz")
    db.insert_law("proposed_start.txt", "neuer entwurf")
    _patch_run_all_llms(monkeypatch, app_session_id)

    start_response = test_client.post(
        "/sessions/run-all/start",
        json={
            "app_session_id": app_session_id,
            "current_filename": "current_start.txt",
            "proposed_filename": "proposed_start.txt",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    start_payload = start_response.json()
    assert start_payload["started"] is True
    assert start_payload["status"] == "running"
    run_id = start_payload["run_id"]
    assert isinstance(run_id, str)
    assert run_id

    done = _wait_for_run_completion(test_client, run_id)
    assert done["status"] == "completed"
    assert done["ok"] is True
    assert done["final_status"]["total_cost_ready"] is True


def test_run_all_events_stream_emits_terminal_event(test_client, monkeypatch):
    app_session_id = "RUNALL-SSE"
    db.insert_law("current_sse.txt", "aktuelles gesetz")
    db.insert_law("proposed_sse.txt", "neuer entwurf")
    _patch_run_all_llms(monkeypatch, app_session_id)

    start_response = test_client.post(
        "/sessions/run-all/start",
        json={
            "app_session_id": app_session_id,
            "current_filename": "current_sse.txt",
            "proposed_filename": "proposed_sse.txt",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    run_id = start_response.json()["run_id"]

    seen_events: list[str] = []
    with test_client.stream("GET", f"/sessions/run-all/{run_id}/events") as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if not line or not line.startswith("event: "):
                continue
            event_name = line.split("event: ", 1)[1]
            seen_events.append(event_name)
            if event_name in {"run_completed", "run_failed", "run_cancelled"}:
                break

    assert "snapshot" in seen_events
    assert "run_completed" in seen_events


def test_run_all_cancel_reverts_to_baseline_and_allows_restart(test_client, monkeypatch):
    app_session_id = "RUNALL-CANCEL"
    current_name = "current_cancel.txt"
    proposed_name = "proposed_cancel.txt"
    db.insert_law(current_name, "aktuelles gesetz")
    db.insert_law(proposed_name, "neuer entwurf")
    db.upsert_session(app_session_id, "test-model")
    db.update_session_documents(app_session_id, current_name, proposed_name)
    db.update_session_summary(app_session_id, "Titel", "Zusammenfassung")

    async def slow_identify(*_args, **_kwargs):
        await asyncio.sleep(5.0)
        return {"vorgaben": []}

    monkeypatch.setattr(regulations_router, "identify_regulations", slow_identify)

    start_response = test_client.post(
        "/sessions/run-all/start",
        json={
            "app_session_id": app_session_id,
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    run_id = start_response.json()["run_id"]

    cancel_response = test_client.post(f"/sessions/run-all/{run_id}/cancel")
    assert cancel_response.status_code == 200
    cancel_payload = cancel_response.json()
    assert cancel_payload["accepted"] is True
    assert cancel_payload["status"] == "cancelling"

    done = _wait_for_run_completion(test_client, run_id, timeout_s=10.0)
    assert done["status"] == "cancelled"
    assert done["ok"] is False
    assert done["final_status"]["summary_ready"] is True
    assert done["final_status"]["regulations_ready"] is False
    assert done["final_status"]["last_completed_step"] == "summary"

    restart_response = test_client.post(
        "/sessions/run-all/start",
        json={
            "app_session_id": app_session_id,
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert restart_response.status_code == 200
    restart_payload = restart_response.json()
    assert restart_payload["started"] is True
    assert restart_payload["status"] == "running"
    restart_run_id = restart_payload["run_id"]
    second_cancel = test_client.post(f"/sessions/run-all/{restart_run_id}/cancel")
    assert second_cancel.status_code == 200
