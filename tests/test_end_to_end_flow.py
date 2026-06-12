import json

from backend.core import db
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS
from backend.routers import (
    regulations as regulations_router,
    processes as processes_router,
    case_groups as case_groups_router,
    process_steps as process_steps_router,
    effort as effort_router,
)


def _is_effort_prompt(prompt: str) -> bool:
    return "prozessschritte differenziert werden" in prompt.lower()


def _personalaufwand_row(addressee: str, minutes: str) -> dict:
    """Build a single row-based personnel-effort entry for org addressees.

    The LLM contract is row-only (`personalaufwand_*`); the backend resolves the
    wage from the wage table, so no `stundenlohn_satz_*` is emitted. Business and
    administration require addressee-appropriate qualifikation/lohnquelle, else
    the parser raises 422.
    """
    if addressee == BUSINESS:
        return {
            "qualifikation": "niedrig",
            "lohnquelle": "gesamtwirtschaft",
            "zeitaufwand_in_min": minutes,
        }
    return {
        "qualifikation": "einfacher_und_mittlerer_dienst",
        "lohnquelle": "bund",
        "zeitaufwand_in_min": minutes,
    }


def test_end_to_end_flow_and_undo(test_client, monkeypatch):
    """Runs steps 1-7 with mocked LLMs, then undoes steps in reverse order."""
    app_id = "E2E-UNDO"
    db.insert_law("current.txt", "aktuelles gesetz")
    db.insert_law("proposed.txt", "neuer entwurf")

    responses = iter(
        [
            json.dumps({"title": "Kurz", "blurb": "Ein Satz."}),
            json.dumps(
                {
                    "vorgaben": [
                        {"normzitat": "§ 1", "beschreibung": "Vorgabe A"},
                        {"normzitat": "§ 2", "beschreibung": "Vorgabe B"},
                    ]
                }
            ),
        ]
    )

    async def fake_regulations_llm(*_args, **_kwargs):
        return next(responses)

    monkeypatch.setattr(regulations_router, "query_llm", fake_regulations_llm)

    summary_resp = test_client.post(
        "/regulations/summary",
        json={
            "filename": "proposed.txt",
            "current_filename": "current.txt",
            "app_session_id": app_id,
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert summary_resp.status_code == 200

    identify_resp = test_client.post(
        "/regulations/identify",
        json={
            "app_session_id": app_id,
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert identify_resp.status_code == 200

    session_id = db.get_session_id_by_app_id(app_id)
    assert session_id is not None
    regulations = db.list_regulations_for_session(session_id)
    assert len(regulations) == 2

    processes_response = {
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

    async def fake_processes_llm(*_args, **_kwargs):
        return json.dumps(processes_response)

    monkeypatch.setattr(processes_router, "query_llm", fake_processes_llm)

    processes_resp = test_client.post(
        "/processes/compile",
        json={"app_session_id": app_id, "model": "test-model", "provider": "openai"},
    )
    assert processes_resp.status_code == 200

    processes = db.list_processes_for_session(session_id)
    assert len(processes) == 2

    case_groups_response = {
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

    async def fake_case_groups_llm(*_args, **_kwargs):
        return json.dumps(case_groups_response)

    monkeypatch.setattr(case_groups_router, "query_llm", fake_case_groups_llm)

    case_groups_resp = test_client.post(
        "/case-groups/develop",
        json={"app_session_id": app_id, "model": "test-model", "provider": "openai"},
    )
    assert case_groups_resp.status_code == 200

    case_groups = db.list_case_groups_for_session(session_id)
    assert len(case_groups) == 2

    step_analysis_response = {
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

    async def fake_steps_llm(*_args, **_kwargs):
        return json.dumps(step_analysis_response)

    monkeypatch.setattr(process_steps_router, "query_llm", fake_steps_llm)

    steps_resp = test_client.post(
        "/process-steps/analyze",
        json={"app_session_id": app_id, "model": "test-model", "provider": "openai"},
    )
    assert steps_resp.status_code == 200

    steps = db.list_process_steps_for_session(session_id)
    assert len(steps) == 3

    cases_response = {
        "prozesse": [
            {
                "prozess_id": str(processes[0]["process_id"]),
                "fallgruppen": [
                    {
                        "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                        "anzahl_betroffene_vorschlag": "10",
                        "haeufigkeit_pro_jahr_vorschlag": "2",
                    }
                ],
            },
            {
                "prozess_id": str(processes[1]["process_id"]),
                "fallgruppen": [
                    {
                        "fallgruppen_id": str(case_groups[1]["case_group_id"]),
                        "anzahl_betroffene_vorschlag": "5",
                        "haeufigkeit_pro_jahr_vorschlag": "1",
                    }
                ],
            },
        ]
    }

    steps_by_group: dict[int, list[dict]] = {}
    for step in steps:
        steps_by_group.setdefault(int(step["case_group_id"]), []).append(step)

    effort_fallgruppen = []
    for group in case_groups:
        group_id = int(group["case_group_id"])
        taetigkeiten = [
            {
                "taetigkeiten_id": str(step["step_id"]),
                "taetigkeit": step["step"],
                "beschreibung": step["description"],
                # Processes/steps here are seeded without an explicit addressee, so
                # `/effort/calculate` runs under the ADMINISTRATION default.
                "personalaufwand_vorschlag": [
                    _personalaufwand_row(ADMINISTRATION, "10")
                ],
                "sachaufwand_vorschlag": "5",
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

    effort_response = {
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

    async def fake_effort_llm(prompt, *_args, **_kwargs):
        if _is_effort_prompt(prompt):
            return json.dumps(effort_response)
        return json.dumps(cases_response)

    monkeypatch.setattr(effort_router, "query_llm", fake_effort_llm)

    effort_resp = test_client.post(
        "/effort/calculate",
        json={"app_session_id": app_id, "model": "test-model", "provider": "openai"},
    )
    assert effort_resp.status_code == 200

    cost_resp = test_client.post("/costs/compute", json={"app_session_id": app_id})
    assert cost_resp.status_code == 200

    status = test_client.get(
        "/sessions/status", params={"app_session_id": app_id}
    ).json()
    assert status["summary_ready"] is True
    assert status["regulations_ready"] is True
    assert status["processes_ready"] is True
    assert status["case_groups_ready"] is True
    assert status["process_steps_ready"] is True
    assert status["effort_ready"] is True
    assert status["total_cost_ready"] is True

    resp = test_client.post("/sessions/undo", json={"app_session_id": app_id})
    assert resp.json()["undone_step"] == "total_cost"
    status = test_client.get(
        "/sessions/status", params={"app_session_id": app_id}
    ).json()
    assert status["total_cost_ready"] is False
    assert status["effort_ready"] is True

    resp = test_client.post("/sessions/undo", json={"app_session_id": app_id})
    assert resp.json()["undone_step"] == "effort"
    status = test_client.get(
        "/sessions/status", params={"app_session_id": app_id}
    ).json()
    assert status["effort_ready"] is False
    assert status["process_steps_ready"] is True

    resp = test_client.post("/sessions/undo", json={"app_session_id": app_id})
    assert resp.json()["undone_step"] == "process_steps"
    status = test_client.get(
        "/sessions/status", params={"app_session_id": app_id}
    ).json()
    assert status["process_steps_ready"] is False

    resp = test_client.post("/sessions/undo", json={"app_session_id": app_id})
    assert resp.json()["undone_step"] == "case_groups"
    status = test_client.get(
        "/sessions/status", params={"app_session_id": app_id}
    ).json()
    assert status["case_groups_ready"] is False

    resp = test_client.post("/sessions/undo", json={"app_session_id": app_id})
    assert resp.json()["undone_step"] == "processes"
    status = test_client.get(
        "/sessions/status", params={"app_session_id": app_id}
    ).json()
    assert status["processes_ready"] is False
    assert status["regulations_ready"] is True

    resp = test_client.post("/sessions/undo", json={"app_session_id": app_id})
    assert resp.json()["undone_step"] == "regulations"
    status = test_client.get(
        "/sessions/status", params={"app_session_id": app_id}
    ).json()
    assert status["regulations_ready"] is False
    assert status["summary_ready"] is True

    resp = test_client.post("/sessions/undo", json={"app_session_id": app_id})
    assert resp.json()["undone_step"] == "summary"
    status = test_client.get(
        "/sessions/status", params={"app_session_id": app_id}
    ).json()
    assert status["summary_ready"] is False
