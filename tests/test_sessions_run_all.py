import json
import time
import asyncio

import pytest

from backend.core import db
from backend.core.deep_research_service import DeepResearchResult
from backend.routers import (
    case_groups as case_groups_router,
    effort as effort_router,
    process_steps as process_steps_router,
    processes as processes_router,
    regulations as regulations_router,
    sessions as sessions_router,
)
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS


def _is_effort_prompt(prompt: str) -> bool:
    return "prozessschritte differenziert werden" in prompt.lower()


def _detect_addressee_from_prompt(prompt: str) -> str:
    lowered = prompt.lower()
    if (
        '"normadressat": "citizens"' in lowered
        or "normadressat `citizens`" in lowered
        or "normadressaten `citizens`" in lowered
        or "normadressat citizens" in lowered
        or "normadressaten citizens" in lowered
        or "normadressaten bürgerinnen und bürger" in lowered
        or "normadressaten buergerinnen und buerger" in lowered
        or "normadressat buergerinnen und buerger" in lowered
        or "normadressat bürgerinnen und bürger" in lowered
    ):
        return CITIZENS
    if (
        '"normadressat": "business"' in lowered
        or "normadressat `business`" in lowered
        or "normadressaten `business`" in lowered
        or "normadressat business" in lowered
        or "normadressaten business" in lowered
        or "normadressaten wirtschaft" in lowered
        or "normadressat wirtschaft" in lowered
    ):
        return BUSINESS
    if (
        '"normadressat": "administration"' in lowered
        or "normadressat `administration`" in lowered
        or "normadressaten `administration`" in lowered
        or "normadressat administration" in lowered
        or "normadressaten administration" in lowered
        or "normadressaten verwaltung" in lowered
        or "normadressat verwaltung" in lowered
    ):
        return ADMINISTRATION
    return ADMINISTRATION


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
        if not _is_effort_prompt(prompt):
            return json.dumps(
                {
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
            )
        effort_fallgruppen = []
        for group in case_groups:
            group_id = int(group["case_group_id"])
            taetigkeiten = [
                {
                    "taetigkeiten_id": str(step["step_id"]),
                    "taetigkeit": step["step"],
                    "beschreibung": step["description"],
                    "stundenlohn_satz_a_vorschlag": "50",
                    "zeitaufwand_in_min_a_vorschlag": "10",
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


def _patch_run_all_llms_for_all_addressees(monkeypatch, app_session_id: str) -> None:
    async def fake_regulations_llm(prompt, *_args, **_kwargs):
        if "vorgaben" in prompt.lower():
            return json.dumps(
                {
                    "vorgaben": [
                        {
                            "normzitat": "§ A",
                            "beschreibung": "Vorgabe Verwaltung",
                            "normadressaten": [ADMINISTRATION],
                        },
                        {
                            "normzitat": "§ B",
                            "beschreibung": "Vorgabe Wirtschaft",
                            "normadressaten": [BUSINESS],
                            "ist_informationspflicht_wirtschaft": 1,
                        },
                        {
                            "normzitat": "§ C",
                            "beschreibung": "Vorgabe Bürger",
                            "normadressaten": [CITIZENS],
                        },
                    ]
                }
            )
        return json.dumps({"title": "Kurz", "blurb": "Ein Satz."})

    async def fake_processes_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        session_id = db.get_session_id_by_app_id(app_session_id)
        assert session_id is not None
        regulations = db.list_regulations_for_session_and_addressee(session_id, addressee)
        assert len(regulations) == 1
        regulation = regulations[0]
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_bezeichnung": f"Prozess {addressee}",
                        "prozess_beschreibung": f"Beschreibung Prozess {addressee}",
                        "vorgaben": [
                            {
                                "vorgaben_id": str(regulation["regulation_id"]),
                                "normzitat": regulation["legal_citation"],
                                "beschreibung": regulation["description"],
                            }
                        ],
                    }
                ]
            }
        )

    async def fake_case_groups_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        session_id = db.get_session_id_by_app_id(app_session_id)
        assert session_id is not None
        processes = db.list_processes_for_session_and_addressee(session_id, addressee)
        assert len(processes) == 1
        process = processes[0]
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_id": str(process["process_id"]),
                        "prozess_bezeichnung": process["process"],
                        "prozess_beschreibung": process["description"],
                        "fallgruppen": [
                            {
                                "fallgruppe_bezeichnung": f"Fallgruppe {addressee}",
                                "fallgruppe_beschreibung": f"Beschreibung Fallgruppe {addressee}",
                            }
                        ],
                    }
                ]
            }
        )

    async def fake_steps_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        session_id = db.get_session_id_by_app_id(app_session_id)
        assert session_id is not None
        processes = db.list_processes_for_session_and_addressee(session_id, addressee)
        case_groups = db.list_case_groups_for_session_and_addressee(session_id, addressee)
        assert len(processes) == 1
        assert len(case_groups) == 1
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
                                        "taetigkeit": f"Schritt {addressee}",
                                        "beschreibung": f"Beschreibung Schritt {addressee}",
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        )

    async def fake_effort_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        session_id = db.get_session_id_by_app_id(app_session_id)
        assert session_id is not None
        processes = db.list_processes_for_session_and_addressee(session_id, addressee)
        case_groups = db.list_case_groups_for_session_and_addressee(session_id, addressee)
        steps = db.list_process_steps_for_session_and_addressee(session_id, addressee)
        assert len(processes) == 1
        assert len(case_groups) == 1
        assert len(steps) == 1
        if not _is_effort_prompt(prompt):
            return json.dumps(
                {
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
                        }
                    ]
                }
            )
        if addressee == CITIZENS:
            effort_entry = {
                "taetigkeiten_id": str(steps[0]["step_id"]),
                "taetigkeit": steps[0]["step"],
                "beschreibung": steps[0]["description"],
                "zeitaufwand_in_min_vorschlag": "30",
                "sachaufwand_vorschlag": "10",
            }
        else:
            effort_entry = {
                "taetigkeiten_id": str(steps[0]["step_id"]),
                "taetigkeit": steps[0]["step"],
                "beschreibung": steps[0]["description"],
                "stundenlohn_satz_a_vorschlag": "60",
                "zeitaufwand_in_min_a_vorschlag": "30",
                "sachaufwand_vorschlag": "10",
            }
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_id": str(processes[0]["process_id"]),
                        "fallgruppen": [
                            {
                                "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                                "taetigkeiten": [effort_entry],
                            }
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr(regulations_router, "query_llm", fake_regulations_llm)
    monkeypatch.setattr(processes_router, "query_llm", fake_processes_llm)
    monkeypatch.setattr(case_groups_router, "query_llm", fake_case_groups_llm)
    monkeypatch.setattr(process_steps_router, "query_llm", fake_steps_llm)
    monkeypatch.setattr(effort_router, "query_llm", fake_effort_llm)


def _patch_run_all_llms_for_business_only(monkeypatch, app_session_id: str) -> None:
    async def fake_regulations_llm(prompt, *_args, **_kwargs):
        if "vorgaben" in prompt.lower():
            return json.dumps(
                {
                    "vorgaben": [
                        {
                            "normzitat": "§ B",
                            "beschreibung": "Vorgabe Wirtschaft",
                            "normadressaten": [BUSINESS],
                            "ist_informationspflicht_wirtschaft": 1,
                        }
                    ]
                }
            )
        return json.dumps({"title": "Kurz", "blurb": "Ein Satz."})

    async def fake_processes_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        session_id = db.get_session_id_by_app_id(app_session_id)
        assert session_id is not None
        regulations = db.list_regulations_for_session_and_addressee(session_id, addressee)
        assert len(regulations) == 1
        regulation = regulations[0]
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_bezeichnung": f"Prozess {addressee}",
                        "prozess_beschreibung": f"Beschreibung Prozess {addressee}",
                        "vorgaben": [
                            {
                                "vorgaben_id": str(regulation["regulation_id"]),
                                "normzitat": regulation["legal_citation"],
                                "beschreibung": regulation["description"],
                            }
                        ],
                    }
                ]
            }
        )

    async def fake_case_groups_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        session_id = db.get_session_id_by_app_id(app_session_id)
        assert session_id is not None
        processes = db.list_processes_for_session_and_addressee(session_id, addressee)
        assert len(processes) == 1
        process = processes[0]
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_id": str(process["process_id"]),
                        "prozess_bezeichnung": process["process"],
                        "prozess_beschreibung": process["description"],
                        "fallgruppen": [
                            {
                                "fallgruppe_bezeichnung": f"Fallgruppe {addressee}",
                                "fallgruppe_beschreibung": f"Beschreibung Fallgruppe {addressee}",
                            }
                        ],
                    }
                ]
            }
        )

    async def fake_steps_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        session_id = db.get_session_id_by_app_id(app_session_id)
        assert session_id is not None
        processes = db.list_processes_for_session_and_addressee(session_id, addressee)
        case_groups = db.list_case_groups_for_session_and_addressee(session_id, addressee)
        assert len(processes) == 1
        assert len(case_groups) == 1
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
                                        "taetigkeit": f"Schritt {addressee}",
                                        "beschreibung": f"Beschreibung Schritt {addressee}",
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        )

    async def fake_effort_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        session_id = db.get_session_id_by_app_id(app_session_id)
        assert session_id is not None
        processes = db.list_processes_for_session_and_addressee(session_id, addressee)
        case_groups = db.list_case_groups_for_session_and_addressee(session_id, addressee)
        steps = db.list_process_steps_for_session_and_addressee(session_id, addressee)
        assert len(processes) == 1
        assert len(case_groups) == 1
        assert len(steps) == 1
        if not _is_effort_prompt(prompt):
            return json.dumps(
                {
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
                        }
                    ]
                }
            )
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
                                        "taetigkeiten_id": str(steps[0]["step_id"]),
                                        "taetigkeit": steps[0]["step"],
                                        "beschreibung": steps[0]["description"],
                                        "stundenlohn_satz_a_vorschlag": "60",
                                        "zeitaufwand_in_min_a_vorschlag": "30",
                                        "sachaufwand_vorschlag": "10",
                                    }
                                ],
                            }
                        ],
                    }
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


def test_run_all_executes_workflow_end_to_end_for_new_law_session(
    test_client, monkeypatch
):
    app_session_id = "RUNALL-NEW-LAW"
    db.insert_law("proposed_new_law.txt", "neuer entwurf")
    _patch_run_all_llms(monkeypatch, app_session_id)

    start_response = test_client.post(
        "/sessions/run-all/start",
        json={
            "app_session_id": app_session_id,
            "proposed_filename": "proposed_new_law.txt",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(test_client, start_response.json()["run_id"])
    assert payload["status"] == "completed"
    assert payload["ok"] is True
    assert payload["final_status"]["total_cost_ready"] is True

    session = db.get_session_by_app_id(app_session_id)
    assert session is not None
    assert session["current_law_id"] is None
    assert session["proposed_law_id"] is not None


def test_run_all_executes_all_addressees_end_to_end(test_client, monkeypatch):
    app_session_id = "RUNALL-ALL-ADDRESSEES"
    db.insert_law("current_all_addr.txt", "aktuelles gesetz")
    db.insert_law("proposed_all_addr.txt", "neuer entwurf")
    _patch_run_all_llms_for_all_addressees(monkeypatch, app_session_id)

    start_response = test_client.post(
        "/sessions/run-all/start",
        json={
            "app_session_id": app_session_id,
            "current_filename": "current_all_addr.txt",
            "proposed_filename": "proposed_all_addr.txt",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(test_client, start_response.json()["run_id"])
    assert payload["status"] == "completed"
    assert payload["ok"] is True
    assert payload["final_status"]["processes_ready_by_addressee"] == {
        ADMINISTRATION: True,
        BUSINESS: True,
        CITIZENS: True,
    }
    assert payload["final_status"]["case_groups_ready_by_addressee"] == {
        ADMINISTRATION: True,
        BUSINESS: True,
        CITIZENS: True,
    }
    assert payload["final_status"]["process_steps_ready_by_addressee"] == {
        ADMINISTRATION: True,
        BUSINESS: True,
        CITIZENS: True,
    }
    assert payload["final_status"]["effort_ready_by_addressee"] == {
        ADMINISTRATION: True,
        BUSINESS: True,
        CITIZENS: True,
    }
    assert payload["final_status"]["total_cost_ready_by_addressee"] == {
        ADMINISTRATION: True,
        BUSINESS: True,
        CITIZENS: True,
    }


def test_run_all_uses_deep_research_for_case_group_metrics(test_client, monkeypatch):
    app_session_id = "RUNALL-DEEP-RESEARCH"
    db.insert_law("current_deep.txt", "aktuelles gesetz")
    db.insert_law("proposed_deep.txt", "neuer entwurf")
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    db.update_case_group_research_enabled(session_id, True)
    _patch_run_all_llms_for_all_addressees(monkeypatch, app_session_id)

    async def fake_effort_llm(prompt, *_args, **_kwargs):
        if not _is_effort_prompt(prompt):
            raise AssertionError("cases_calculation should be replaced by Deep Research")
        addressee = _detect_addressee_from_prompt(prompt)
        sid = db.get_session_id_by_app_id(app_session_id)
        assert sid is not None
        processes = db.list_processes_for_session_and_addressee(sid, addressee)
        case_groups = db.list_case_groups_for_session_and_addressee(sid, addressee)
        steps = db.list_process_steps_for_session_and_addressee(sid, addressee)
        assert len(processes) == 1
        assert len(case_groups) == 1
        assert len(steps) == 1
        if addressee == CITIZENS:
            effort_entry = {
                "taetigkeiten_id": str(steps[0]["step_id"]),
                "zeitaufwand_in_min_vorschlag": "30",
                "sachaufwand_vorschlag": "10",
            }
        else:
            effort_entry = {
                "taetigkeiten_id": str(steps[0]["step_id"]),
                "stundenlohn_satz_a_vorschlag": "60",
                "zeitaufwand_in_min_a_vorschlag": "30",
                "sachaufwand_vorschlag": "10",
            }
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_id": str(processes[0]["process_id"]),
                        "normadressat": addressee,
                        "fallgruppen": [
                            {
                                "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                                "taetigkeiten": [effort_entry],
                            }
                        ],
                    }
                ]
            }
        )

    async def fake_run_deep_research(*_args, **_kwargs):
        sid = db.get_session_id_by_app_id(app_session_id)
        assert sid is not None
        processes = []
        for group in db.list_case_groups_for_session(sid):
            processes.append(
                {
                    "prozess_id": str(group["process_id"]),
                    "normadressat": group["norm_addressee"],
                    "fallgruppen": [
                        {
                            "fallgruppen_id": str(group["case_group_id"]),
                            "anzahl_betroffene_gueltig": "10",
                            "haeufigkeit_pro_jahr_gueltig": "1",
                            "anzahl_betroffene_vorschlag": "10",
                            "haeufigkeit_pro_jahr_vorschlag": "2",
                            "confidence": {
                                "anzahl_betroffene_gueltig": "high",
                                "haeufigkeit_pro_jahr_gueltig": "medium",
                                "anzahl_betroffene_vorschlag": "high",
                                "haeufigkeit_pro_jahr_vorschlag": "medium",
                            },
                            "erklaerungen": {
                                "anzahl_betroffene_gueltig": "Deep Research Begründung",
                                "haeufigkeit_pro_jahr_gueltig": "Deep Research Begründung",
                                "anzahl_betroffene_vorschlag": "Deep Research Begründung",
                                "haeufigkeit_pro_jahr_vorschlag": "Deep Research Begründung",
                            },
                        }
                    ],
                }
            )
        report_text = json.dumps({"prozesse": processes})
        return DeepResearchResult(
            agent="test-agent",
            interaction_id="dr-test",
            report_text=report_text,
            response_json={"status": "completed"},
            estimated_cost_usd=0.032,
        )

    monkeypatch.setattr(effort_router, "query_llm", fake_effort_llm)
    monkeypatch.setattr(sessions_router, "run_deep_research", fake_run_deep_research)

    start_response = test_client.post(
        "/sessions/run-all/start",
        json={
            "app_session_id": app_session_id,
            "current_filename": "current_deep.txt",
            "proposed_filename": "proposed_deep.txt",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(test_client, start_response.json()["run_id"])

    assert payload["status"] == "completed"
    assert payload["ok"] is True
    assert payload["final_status"]["total_cost_ready"] is True
    run = db.get_latest_deep_research_run(session_id, "case_group_metrics")
    assert run is not None
    assert run["status"] == "parsed"
    assert run["estimated_cost_usd"] == pytest.approx(0.032)
    assert all(
        group["case_metric_research_json"]
        for group in db.list_case_groups_for_session(session_id)
    )


def test_run_all_skips_administration_when_only_business_regulations_exist(
    test_client, monkeypatch
):
    app_session_id = "RUNALL-BUSINESS-ONLY"
    db.insert_law("current_business_only.txt", "aktuelles gesetz")
    db.insert_law("proposed_business_only.txt", "neuer entwurf")
    _patch_run_all_llms_for_business_only(monkeypatch, app_session_id)

    start_response = test_client.post(
        "/sessions/run-all/start",
        json={
            "app_session_id": app_session_id,
            "current_filename": "current_business_only.txt",
            "proposed_filename": "proposed_business_only.txt",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(test_client, start_response.json()["run_id"])

    assert payload["status"] == "completed"
    assert payload["ok"] is True
    assert payload["final_status"]["processes_ready_by_addressee"] == {
        ADMINISTRATION: True,
        BUSINESS: True,
        CITIZENS: True,
    }
    assert payload["final_status"]["case_groups_ready_by_addressee"] == {
        ADMINISTRATION: True,
        BUSINESS: True,
        CITIZENS: True,
    }
    assert payload["final_status"]["process_steps_ready_by_addressee"] == {
        ADMINISTRATION: True,
        BUSINESS: True,
        CITIZENS: True,
    }
    assert payload["final_status"]["effort_ready_by_addressee"] == {
        ADMINISTRATION: True,
        BUSINESS: True,
        CITIZENS: True,
    }


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


def test_run_all_reports_step_failure_when_only_current_law_is_selected(test_client):
    db.insert_law("current_only.txt", "aktuelles gesetz")

    start_response = test_client.post(
        "/sessions/run-all/start",
        json={
            "app_session_id": "RUNALL-CURRENT-ONLY",
            "current_filename": "current_only.txt",
            "model": "test-model",
        },
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(test_client, start_response.json()["run_id"])
    assert payload["status"] == "failed"
    assert payload["ok"] is False
    assert payload["steps"][0]["key"] == "summary"
    assert payload["steps"][0]["status"] == "failed"
    assert payload["steps"][0]["message"] == "Missing proposed_filename for summary step"
    assert payload["final_status"]["summary_ready"] is False


def test_run_all_reports_failing_addressee_in_step_message(test_client, monkeypatch):
    app_session_id = "RUNALL-ADDRESSEE-FAIL"
    db.upsert_session(app_session_id, "test-model")
    db.update_session_summary(app_session_id, "Titel", "Zusammenfassung")
    session_id = db.get_session_id_by_app_id(app_session_id)
    assert session_id is not None
    db.insert_regulation(
        session_id,
        "§ B",
        "Vorgabe Wirtschaft",
        applies_to_administration=False,
        applies_to_business=True,
        applies_to_citizens=False,
    )

    async def fake_compile_processes(payload, *_args, **_kwargs):
        if payload.norm_addressee == BUSINESS:
            raise RuntimeError("No regulations mapped to process cluster")
        return {"status": "skipped"}

    monkeypatch.setattr(processes_router, "compile_processes", fake_compile_processes)

    start_response = test_client.post(
        "/sessions/run-all/start",
        json={"app_session_id": app_session_id, "model": "test-model"},
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(test_client, start_response.json()["run_id"])
    assert payload["status"] == "failed"
    assert payload["ok"] is False
    assert payload["steps"][0]["key"] == "summary"
    assert payload["steps"][0]["status"] == "skipped"
    assert payload["steps"][1]["key"] == "regulations"
    assert payload["steps"][1]["status"] == "skipped"
    assert payload["steps"][2]["key"] == "processes"
    assert payload["steps"][2]["status"] == "failed"
    assert (
        payload["steps"][2]["message"]
        == "business: No regulations mapped to process cluster"
    )
    assert payload["final_status"]["summary_ready"] is True
    assert payload["final_status"]["regulations_ready"] is True
    assert payload["final_status"]["processes_ready"] is False
    assert payload["last_error"] == "business: No regulations mapped to process cluster"


def test_run_all_start_requires_model_for_new_session(test_client):
    start_response = test_client.post(
        "/sessions/run-all/start",
        json={"app_session_id": "RUNALL-NO-MODEL"},
    )
    assert start_response.status_code == 400
    assert "Model is required for new session" in start_response.json()["detail"]


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


def test_run_all_start_keeps_existing_model_when_request_model_missing(
    test_client, monkeypatch
):
    app_session_id = "RUNALL-KEEP-MODEL"
    db.upsert_session(app_session_id, "gpt-5")

    async def fake_background(*_args, **_kwargs):
        return None

    monkeypatch.setattr(sessions_router, "_run_all_background", fake_background)

    start_response = test_client.post(
        "/sessions/run-all/start",
        json={"app_session_id": app_session_id},
    )
    assert start_response.status_code == 200

    session = db.get_session_by_app_id(app_session_id)
    assert session is not None
    assert session["llm_model"] == "gpt-5"


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


def test_run_all_status_reports_current_step_and_addressee_while_running(
    test_client, monkeypatch
):
    app_session_id = "RUNALL-CURRENT-STATUS"
    db.upsert_session(app_session_id, "test-model")
    db.update_session_summary(app_session_id, "Titel", "Zusammenfassung")
    session_id = db.get_session_id_by_app_id(app_session_id)
    assert session_id is not None
    db.insert_regulation(
        session_id,
        "§ A",
        "Vorgabe Verwaltung",
        applies_to_administration=True,
        applies_to_business=False,
        applies_to_citizens=False,
    )

    reached_processes = asyncio.Event()

    async def slow_compile_processes(payload, *_args, **_kwargs):
        reached_processes.set()
        await asyncio.sleep(0.3)
        return {"status": "existing"}

    monkeypatch.setattr(processes_router, "compile_processes", slow_compile_processes)

    start_response = test_client.post(
        "/sessions/run-all/start",
        json={"app_session_id": app_session_id, "model": "test-model"},
    )
    assert start_response.status_code == 200
    run_id = start_response.json()["run_id"]

    deadline = time.time() + 2.0
    seen_running_status = None
    while time.time() < deadline:
        response = test_client.get(f"/sessions/run-all/{run_id}")
        assert response.status_code == 200
        payload = response.json()
        if (
            payload["status"] == "running"
            and payload["current_step"] == "processes"
            and payload["current_norm_addressee"] == ADMINISTRATION
        ):
            seen_running_status = payload
            break
        time.sleep(0.05)

    assert reached_processes.is_set()
    assert seen_running_status is not None
    assert seen_running_status["current_label"] == "Prozesse bündeln"


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
    assert "addressee_started" in seen_events
    assert "run_completed" in seen_events


def test_run_all_cancel_preserves_completed_steps_and_allows_restart(
    test_client, monkeypatch
):
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


def test_run_all_successful_restart_clears_transient_status_fields(test_client, monkeypatch):
    app_session_id = "RUNALL-RESTART-CLEARS-STATUS"
    current_name = "current_restart_status.txt"
    proposed_name = "proposed_restart_status.txt"
    db.insert_law(current_name, "aktuelles gesetz")
    db.insert_law(proposed_name, "neuer entwurf")
    db.upsert_session(app_session_id, "test-model")
    db.update_session_documents(app_session_id, current_name, proposed_name)
    db.update_session_summary(app_session_id, "Titel", "Zusammenfassung")
    session_id = db.get_session_id_by_app_id(app_session_id)
    assert session_id is not None
    db.insert_regulation(
        session_id,
        "§ B",
        "Vorgabe Wirtschaft",
        applies_to_administration=False,
        applies_to_business=True,
        applies_to_citizens=False,
    )

    original_compile_processes = processes_router.compile_processes

    async def failing_compile_processes(payload, *_args, **_kwargs):
        if payload.norm_addressee == BUSINESS:
            raise RuntimeError("No regulations mapped to process cluster")
        return {"status": "skipped"}

    monkeypatch.setattr(processes_router, "compile_processes", failing_compile_processes)

    first_start = test_client.post(
        "/sessions/run-all/start",
        json={"app_session_id": app_session_id, "model": "test-model"},
    )
    assert first_start.status_code == 200
    first_done = _wait_for_run_completion(test_client, first_start.json()["run_id"])
    assert first_done["status"] == "failed"
    assert first_done["last_error"] == "business: No regulations mapped to process cluster"

    monkeypatch.setattr(processes_router, "compile_processes", original_compile_processes)
    _patch_run_all_llms_for_business_only(monkeypatch, app_session_id)

    restart_response = test_client.post(
        "/sessions/run-all/start",
        json={
            "app_session_id": app_session_id,
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert restart_response.status_code == 200
    restart_done = _wait_for_run_completion(test_client, restart_response.json()["run_id"])
    assert restart_done["status"] == "completed"
    assert restart_done["ok"] is True
    assert restart_done["last_error"] is None
    assert restart_done["current_step"] is None
    assert restart_done["current_label"] is None
    assert restart_done["current_norm_addressee"] is None
