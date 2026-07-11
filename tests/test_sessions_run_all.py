import json
import time
import asyncio

import pytest

from backend.core import db, llm_monitor
from backend.core.deep_research_service import DeepResearchError, DeepResearchResult
from backend.core.models import Tile
from backend.core.prompts import PromptId
from backend.routers import (
    case_groups as case_groups_router,
    effort as effort_router,
    process_steps as process_steps_router,
    processes as processes_router,
    regulations as regulations_router,
    sessions as sessions_router,
)
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS
from backend.routers.sessions import (
    _ATOMIC_STEP_DEFAULT_MAX_ATTEMPTS,
    _max_attempts_for_model,
)


def test_max_attempts_for_model_high_retry_models():
    for model in ("gemini-3.5-flash", "gemini-3-flash-preview", "gpt-5.4-mini"):
        assert _max_attempts_for_model(model) == 4


def test_max_attempts_for_model_default_for_strong_model():
    assert _max_attempts_for_model("gpt-5.4") == _ATOMIC_STEP_DEFAULT_MAX_ATTEMPTS
    assert _ATOMIC_STEP_DEFAULT_MAX_ATTEMPTS == 2


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


def _json_for_prompt(prompt: str, payload: dict) -> str:
    payload.setdefault("normadressat", _detect_addressee_from_prompt(prompt))
    return json.dumps(payload)


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


def _seed_step6_prerequisites(app_session_id: str) -> int:
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    db.update_session_summary(app_session_id, "Titel", "Zusammenfassung")
    for norm_addressee in (ADMINISTRATION, BUSINESS, CITIZENS):
        regulation_kwargs = {
            "applies_to_administration": norm_addressee == ADMINISTRATION,
            "applies_to_business": norm_addressee == BUSINESS,
            "applies_to_citizens": norm_addressee == CITIZENS,
            "is_business_information_obligation": norm_addressee == BUSINESS,
        }
        db.insert_regulation(
            session_id,
            f"§ {norm_addressee}",
            f"Vorgabe {norm_addressee}",
            **regulation_kwargs,
        )
        process_id = db.insert_process(
            session_id,
            f"Prozess {norm_addressee}",
            f"Beschreibung Prozess {norm_addressee}",
            norm_addressee=norm_addressee,
        )
        case_group_id = db.insert_case_group(
            session_id,
            process_id,
            f"Fallgruppe {norm_addressee}",
            f"Beschreibung Fallgruppe {norm_addressee}",
            norm_addressee=norm_addressee,
        )
        db.insert_process_step(
            session_id,
            case_group_id,
            f"Schritt {norm_addressee}",
            f"Beschreibung Schritt {norm_addressee}",
            norm_addressee=norm_addressee,
        )
    return session_id


def _upsert_process_tile(session_id: int, process_id: int, norm_addressee: str, row: int) -> None:
    db.upsert_tile(
        Tile(
            id=f"process_{process_id}",
            title=f"Prozess {norm_addressee}",
            text="Beschreibung",
            meta_information={"process_id": process_id, "change_status": "geaendert"},
            column=2,
            row=row,
            deletable=True,
            link_from_tile=[],
        ),
        session_id=session_id,
        norm_addressee=norm_addressee,
    )


def _upsert_case_group_tile(
    session_id: int,
    case_group_id: int,
    process_id: int,
    norm_addressee: str,
    row: int,
) -> None:
    db.upsert_tile(
        Tile(
            id=f"case_group_{case_group_id}",
            title=f"Fallgruppe {norm_addressee}",
            text="Beschreibung",
            meta_information={
                "case_group_id": case_group_id,
                "process_id": process_id,
                "change_status": "geaendert",
            },
            column=3,
            row=row,
            deletable=True,
            link_from_tile=[f"process_{process_id}"],
        ),
        session_id=session_id,
        norm_addressee=norm_addressee,
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

    async def fake_processes_llm(prompt, *_args, **_kwargs):
        session_id = db.get_session_id_by_app_id(app_session_id)
        assert session_id is not None
        regulations = db.list_regulations_for_session(session_id)
        return _json_for_prompt(
            prompt,
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

    async def fake_case_groups_llm(prompt, *_args, **_kwargs):
        session_id = db.get_session_id_by_app_id(app_session_id)
        assert session_id is not None
        processes = db.list_processes_for_session(session_id)
        return _json_for_prompt(
            prompt,
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

    async def fake_steps_llm(prompt, *_args, **_kwargs):
        session_id = db.get_session_id_by_app_id(app_session_id)
        assert session_id is not None
        case_groups = db.list_case_groups_for_session(session_id)
        return _json_for_prompt(
            prompt,
            {
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
                    },
                    {
                        "fallgruppen_id": str(case_groups[1]["case_group_id"]),
                        "taetigkeiten": [
                            {
                                "taetigkeit": "Schritt B1",
                                "beschreibung": "Beschreibung B1",
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
            return _json_for_prompt(
                prompt,
                {
                    "fallgruppen": [
                        {
                            "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                            "anzahl_betroffene_vorschlag": "10",
                            "haeufigkeit_pro_jahr_vorschlag": "2",
                        },
                        {
                            "fallgruppen_id": str(case_groups[1]["case_group_id"]),
                            "anzahl_betroffene_vorschlag": "5",
                            "haeufigkeit_pro_jahr_vorschlag": "1",
                        },
                    ]
                }
            )
        addressee = _detect_addressee_from_prompt(prompt)
        effort_fallgruppen = []
        for group in case_groups:
            group_id = int(group["case_group_id"])
            taetigkeiten = [
                {
                    "taetigkeiten_id": str(step["step_id"]),
                    "taetigkeit": step["step"],
                    "beschreibung": step["description"],
                    "personalaufwand_vorschlag": [
                        _personalaufwand_row(addressee, "10")
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
        return _json_for_prompt(
            prompt,
            {"fallgruppen": effort_fallgruppen}
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
        return _json_for_prompt(
            prompt,
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
        return _json_for_prompt(
            prompt,
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
        return _json_for_prompt(
            prompt,
            {
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
            return _json_for_prompt(
                prompt,
                {
                    "fallgruppen": [
                        {
                            "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                            "anzahl_betroffene_vorschlag": "10",
                            "haeufigkeit_pro_jahr_vorschlag": "2",
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
                "personalaufwand_vorschlag": [
                    _personalaufwand_row(addressee, "30")
                ],
                "sachaufwand_vorschlag": "10",
            }
        return _json_for_prompt(
            prompt,
            {
                "fallgruppen": [
                    {
                        "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                        "taetigkeiten": [effort_entry],
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
        return _json_for_prompt(
            prompt,
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
        return _json_for_prompt(
            prompt,
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
        return _json_for_prompt(
            prompt,
            {
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
            return _json_for_prompt(
                prompt,
                {
                    "fallgruppen": [
                        {
                            "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                            "anzahl_betroffene_vorschlag": "10",
                            "haeufigkeit_pro_jahr_vorschlag": "2",
                        }
                    ]
                }
            )
        return _json_for_prompt(
            prompt,
            {
                "fallgruppen": [
                    {
                        "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                        "taetigkeiten": [
                            {
                                "taetigkeiten_id": str(steps[0]["step_id"]),
                                "taetigkeit": steps[0]["step"],
                                "beschreibung": steps[0]["description"],
                                "personalaufwand_vorschlag": [
                                    _personalaufwand_row(addressee, "30")
                                ],
                                "sachaufwand_vorschlag": "10",
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


def test_run_all_accepts_empty_processes_for_applicable_addressee(test_client, monkeypatch):
    app_session_id = "RUNALL-EMPTY-PROCESSES"
    db.insert_law("current_empty_processes.txt", "aktuelles gesetz")
    db.insert_law("proposed_empty_processes.txt", "neuer entwurf")
    _patch_run_all_llms_for_all_addressees(monkeypatch, app_session_id)

    async def fake_processes_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        if addressee == CITIZENS:
            return json.dumps({"normadressat": CITIZENS, "prozesse": []})
        session_id = db.get_session_id_by_app_id(app_session_id)
        assert session_id is not None
        regulations = db.list_regulations_for_session_and_addressee(session_id, addressee)
        assert len(regulations) == 1
        regulation = regulations[0]
        return json.dumps(
            {
                "normadressat": addressee,
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
                ],
            }
        )

    monkeypatch.setattr(processes_router, "query_llm", fake_processes_llm)

    start_response = test_client.post(
        "/sessions/run-all/start",
        json={
            "app_session_id": app_session_id,
            "current_filename": "current_empty_processes.txt",
            "proposed_filename": "proposed_empty_processes.txt",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(test_client, start_response.json()["run_id"])

    assert payload["status"] == "completed"
    assert payload["ok"] is True
    assert payload["final_status"]["processes_ready_by_addressee"][CITIZENS] is True
    assert payload["final_status"]["case_groups_ready_by_addressee"][CITIZENS] is True
    assert payload["final_status"]["process_steps_ready_by_addressee"][CITIZENS] is True
    assert payload["final_status"]["effort_ready_by_addressee"][CITIZENS] is True
    assert payload["final_status"]["total_cost_ready_by_addressee"][CITIZENS] is True

    session_id = db.get_session_id_by_app_id(app_session_id)
    assert session_id is not None
    assert db.list_processes_for_session_and_addressee(session_id, CITIZENS) == []
    assert db.list_case_groups_for_session_and_addressee(session_id, CITIZENS) == []
    assert db.list_process_steps_for_session_and_addressee(session_id, CITIZENS) == []


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
                "personalaufwand_vorschlag": [
                    _personalaufwand_row(addressee, "30")
                ],
                "sachaufwand_vorschlag": "10",
            }
        return json.dumps(
            {
                "normadressat": addressee,
                "fallgruppen": [
                    {
                        "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                        "taetigkeiten": [effort_entry],
                    }
                ],
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

    async def fake_processes_llm(*_args, **_kwargs):
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_bezeichnung": "Fehlerprozess",
                        "prozess_beschreibung": "Beschreibung",
                        "vorgaben": [{"vorgaben_id": "999"}],
                    }
                ]
            }
        )

    monkeypatch.setattr(processes_router, "query_llm", fake_processes_llm)

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
    assert "Die Antwort für Wirtschaft konnte nicht verarbeitet werden" in payload["steps"][2]["message"]
    assert "Schritt erneut aus.\nTechnische Details:" in payload["steps"][2]["message"]
    assert "Technische Details: Prozesse bündeln / processes / Wirtschaft / process_compilation" in payload["steps"][2]["message"]
    assert "Vorgabe 999 not found in database" in payload["steps"][2]["message"]
    assert payload["final_status"]["summary_ready"] is True
    assert payload["final_status"]["regulations_ready"] is True
    assert payload["final_status"]["processes_ready"] is False
    assert "Die Antwort für Wirtschaft konnte nicht verarbeitet werden" in payload["last_error"]


def test_processes_step_partial_failure_keeps_valid_sibling_pending_and_applies_nothing(
    test_client,
    monkeypatch,
):
    app_session_id = "STEP-PROCESSES-ATOMIC-FAIL"
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    admin_reg = db.insert_regulation(
        session_id,
        "§ A",
        "Vorgabe Verwaltung",
        applies_to_administration=True,
        applies_to_business=False,
        applies_to_citizens=False,
    )
    business_reg = db.insert_regulation(
        session_id,
        "§ B",
        "Vorgabe Wirtschaft",
        applies_to_administration=False,
        applies_to_business=True,
        applies_to_citizens=False,
        is_business_information_obligation=True,
    )
    calls = {ADMINISTRATION: 0, BUSINESS: 0}

    async def first_processes_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        calls[addressee] += 1
        if addressee == BUSINESS:
            return json.dumps(
                {
                    "prozesse": [
                        {
                            "prozess_bezeichnung": "Prozess Wirtschaft",
                            "prozess_beschreibung": "Beschreibung",
                            "vorgaben": [{"vorgaben_id": "999"}],
                        }
                    ]
                }
            )
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_bezeichnung": "Prozess Verwaltung",
                        "prozess_beschreibung": "Beschreibung",
                        "vorgaben": [{"vorgaben_id": str(admin_reg)}],
                    }
                ]
            }
        )

    monkeypatch.setattr(processes_router, "query_llm", first_processes_llm)
    first_start = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "processes",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert first_start.status_code == 200
    first_done = _wait_for_run_completion(test_client, first_start.json()["run_id"])
    assert first_done["status"] == "failed"
    assert "Die Antwort für Wirtschaft konnte nicht verarbeitet werden" in first_done["last_error"]
    assert db.list_processes_for_session(session_id) == []
    assert not any(
        tile.id.startswith("process_")
        for addressee in (ADMINISTRATION, BUSINESS)
        for tile in db.fetch_tiles(session_id=session_id, norm_addressee=addressee)
    )

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT prompt_id, norm_addressee, answer_state, state_reason
        FROM llm_answers
        WHERE session_id = ? AND prompt_id = ?
        ORDER BY norm_addressee
        """,
        (session_id, PromptId.PROCESS_COMPILATION),
    )
    answer_rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    by_addressee = {row["norm_addressee"]: row for row in answer_rows}
    assert by_addressee[ADMINISTRATION]["answer_state"] == "pending"
    assert by_addressee[ADMINISTRATION]["state_reason"] == "waiting_for_paired_retry"
    assert by_addressee[BUSINESS]["answer_state"] == "invalid"
    assert by_addressee[BUSINESS]["state_reason"].startswith("session_update_failed")

    async def retry_processes_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        calls[addressee] += 1
        assert addressee == BUSINESS
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_bezeichnung": "Prozess Wirtschaft",
                        "prozess_beschreibung": "Beschreibung",
                        "vorgaben": [{"vorgaben_id": str(business_reg)}],
                    }
                ]
            }
        )

    monkeypatch.setattr(processes_router, "query_llm", retry_processes_llm)
    retry_start = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "processes",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert retry_start.status_code == 200
    retry_done = _wait_for_run_completion(test_client, retry_start.json()["run_id"])
    assert retry_done["status"] == "completed"
    assert calls == {ADMINISTRATION: 1, BUSINESS: _ATOMIC_STEP_DEFAULT_MAX_ATTEMPTS + 1}
    assert len(db.list_processes_for_session_and_addressee(session_id, ADMINISTRATION)) == 1
    assert len(db.list_processes_for_session_and_addressee(session_id, BUSINESS)) == 1


def test_atomic_step_does_not_publish_apply_success_before_transaction_commit(
    test_client,
    monkeypatch,
):
    app_session_id = "STEP-PROCESSES-ROLLBACK-MONITOR"
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    admin_reg = db.insert_regulation(
        session_id,
        "§ A",
        "Vorgabe Verwaltung",
        applies_to_administration=True,
        applies_to_business=False,
        applies_to_citizens=False,
    )
    business_reg = db.insert_regulation(
        session_id,
        "§ B",
        "Vorgabe Wirtschaft",
        applies_to_administration=False,
        applies_to_business=True,
        applies_to_citizens=False,
        is_business_information_obligation=True,
    )

    async def valid_processes_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        regulation_id = admin_reg if addressee == ADMINISTRATION else business_reg
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_bezeichnung": f"Prozess {addressee}",
                        "prozess_beschreibung": "Beschreibung",
                        "vorgaben": [{"vorgaben_id": str(regulation_id)}],
                    }
                ]
            }
        )

    original_apply = processes_router.apply_process_compilation

    def fail_after_first_addressee(*, session_id, norm_addressee, parsed, context):
        if norm_addressee == BUSINESS:
            raise RuntimeError("forced apply rollback")
        return original_apply(
            session_id=session_id,
            norm_addressee=norm_addressee,
            parsed=parsed,
            context=context,
        )

    monkeypatch.setattr(processes_router, "query_llm", valid_processes_llm)
    monkeypatch.setattr(
        processes_router,
        "apply_process_compilation",
        fail_after_first_addressee,
    )

    start_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "processes",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(test_client, start_response.json()["run_id"])

    assert payload["status"] == "failed"
    assert db.list_processes_for_session(session_id) == []
    rows = [
        row
        for row in db.list_recent_llm_answers_for_session(session_id)
        if row["prompt_id"] == PromptId.PROCESS_COMPILATION
    ]
    assert rows
    assert {row["answer_state"] for row in rows} == {"invalid"}
    events = asyncio.run(llm_monitor.get_recent_events(app_session_id, limit=50))
    assert not [
        event
        for event in events
        if event["event_type"] == "llm_apply_succeeded"
        and event["prompt_id"] == PromptId.PROCESS_COMPILATION
    ]


def test_case_group_step_partial_failure_applies_nothing(test_client, monkeypatch):
    app_session_id = "STEP-CASE-GROUPS-ATOMIC-FAIL"
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    db.insert_regulation(
        session_id,
        "§ A",
        "Vorgabe Verwaltung",
        applies_to_administration=True,
        applies_to_business=False,
        applies_to_citizens=False,
    )
    db.insert_regulation(
        session_id,
        "§ B",
        "Vorgabe Wirtschaft",
        applies_to_administration=False,
        applies_to_business=True,
        applies_to_citizens=False,
        is_business_information_obligation=True,
    )
    admin_process = db.insert_process(
        session_id,
        "Prozess Verwaltung",
        "Beschreibung",
        norm_addressee=ADMINISTRATION,
    )
    db.insert_process(
        session_id,
        "Prozess Wirtschaft",
        "Beschreibung",
        norm_addressee=BUSINESS,
    )

    async def case_groups_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        process_id = admin_process if addressee == ADMINISTRATION else 999999
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_id": str(process_id),
                        "fallgruppen": [
                            {
                                "fallgruppe_bezeichnung": f"Fallgruppe {addressee}",
                                "fallgruppe_beschreibung": "Beschreibung",
                            }
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr(case_groups_router, "query_llm", case_groups_llm)
    start_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "case_groups",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(test_client, start_response.json()["run_id"])

    assert payload["status"] == "failed"
    assert "Die Antwort für Wirtschaft konnte nicht verarbeitet werden" in payload["last_error"]
    assert db.list_case_groups_for_session(session_id) == []
    rows = [
        row
        for row in db.list_recent_llm_answers_for_session(session_id)
        if row["prompt_id"] == PromptId.CASE_GROUP_DEVELOPMENT
    ]
    by_addressee = {row["norm_addressee"]: row for row in rows}
    assert by_addressee[ADMINISTRATION]["answer_state"] == "pending"
    assert by_addressee[ADMINISTRATION]["state_reason"] == "waiting_for_paired_retry"
    assert by_addressee[BUSINESS]["answer_state"] == "invalid"


def test_process_step_step_partial_failure_applies_nothing(test_client, monkeypatch):
    app_session_id = "STEP-PROCESS-STEPS-ATOMIC-FAIL"
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    db.insert_regulation(
        session_id,
        "§ A",
        "Vorgabe Verwaltung",
        applies_to_administration=True,
        applies_to_business=False,
        applies_to_citizens=False,
    )
    db.insert_regulation(
        session_id,
        "§ B",
        "Vorgabe Wirtschaft",
        applies_to_administration=False,
        applies_to_business=True,
        applies_to_citizens=False,
        is_business_information_obligation=True,
    )
    admin_process = db.insert_process(
        session_id,
        "Prozess Verwaltung",
        "Beschreibung",
        norm_addressee=ADMINISTRATION,
    )
    business_process = db.insert_process(
        session_id,
        "Prozess Wirtschaft",
        "Beschreibung",
        norm_addressee=BUSINESS,
    )
    admin_case_group = db.insert_case_group(
        session_id,
        admin_process,
        "Fallgruppe Verwaltung",
        "Beschreibung",
        norm_addressee=ADMINISTRATION,
    )
    db.insert_case_group(
        session_id,
        business_process,
        "Fallgruppe Wirtschaft",
        "Beschreibung",
        norm_addressee=BUSINESS,
    )

    async def process_steps_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        case_group_id = admin_case_group if addressee == ADMINISTRATION else 999999
        return json.dumps(
            {
                "fallgruppen": [
                    {
                        "fallgruppen_id": str(case_group_id),
                        "taetigkeiten": [
                            {
                                "taetigkeit": f"Schritt {addressee}",
                                "beschreibung": "Beschreibung",
                            }
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr(process_steps_router, "query_llm", process_steps_llm)
    start_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "process_steps",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(test_client, start_response.json()["run_id"])

    assert payload["status"] == "failed"
    assert "Die Antwort für Wirtschaft konnte nicht verarbeitet werden" in payload["last_error"]
    assert db.list_process_steps_for_session(session_id) == []
    rows = [
        row
        for row in db.list_recent_llm_answers_for_session(session_id)
        if row["prompt_id"] == PromptId.PROCESS_STEP_ANALYSIS
    ]
    by_addressee = {row["norm_addressee"]: row for row in rows}
    assert by_addressee[ADMINISTRATION]["answer_state"] == "pending"
    assert by_addressee[ADMINISTRATION]["state_reason"] == "waiting_for_paired_retry"
    assert by_addressee[BUSINESS]["answer_state"] == "invalid"


def test_single_step_success_normalizes_change_status_for_processes_case_groups_and_steps(
    test_client,
    monkeypatch,
):
    app_session_id = "STEP-CHANGE-STATUS-NORMALIZE"
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    regulation_id = db.insert_regulation(
        session_id,
        "§ A",
        "Vorgabe Verwaltung",
        applies_to_administration=True,
        applies_to_business=False,
        applies_to_citizens=False,
    )

    async def processes_llm(prompt, *_args, **_kwargs):
        assert _detect_addressee_from_prompt(prompt) == ADMINISTRATION
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_bezeichnung": "Prozess Verwaltung",
                        "prozess_beschreibung": "Beschreibung",
                        "change_status": "new",
                        "vorgaben": [{"vorgaben_id": str(regulation_id)}],
                    }
                ]
            }
        )

    monkeypatch.setattr(processes_router, "query_llm", processes_llm)
    response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "processes",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert response.status_code == 200
    assert _wait_for_run_completion(test_client, response.json()["run_id"])["status"] == "completed"
    process = db.list_processes_for_session_and_addressee(session_id, ADMINISTRATION)[0]
    assert process["change_status"] == "eingefuehrt"
    process_tile = next(
        tile
        for tile in db.fetch_tiles(session_id=session_id, norm_addressee=ADMINISTRATION)
        if tile.id == f"process_{process['process_id']}"
    )
    assert process_tile.meta_information["change_status"] == "eingefuehrt"

    async def case_groups_llm(prompt, *_args, **_kwargs):
        assert _detect_addressee_from_prompt(prompt) == ADMINISTRATION
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_id": str(process["process_id"]),
                        "fallgruppen": [
                            {
                                "fallgruppe_bezeichnung": "Fallgruppe Verwaltung",
                                "fallgruppe_beschreibung": "Beschreibung",
                                "status": "deleted",
                            }
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr(case_groups_router, "query_llm", case_groups_llm)
    response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "case_groups",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert response.status_code == 200
    assert _wait_for_run_completion(test_client, response.json()["run_id"])["status"] == "completed"
    case_group = db.list_case_groups_for_session_and_addressee(session_id, ADMINISTRATION)[0]
    assert case_group["change_status"] == "abgeschafft"
    case_group_tile = next(
        tile
        for tile in db.fetch_tiles(session_id=session_id, norm_addressee=ADMINISTRATION)
        if tile.id == f"case_group_{case_group['case_group_id']}"
    )
    assert case_group_tile.meta_information["change_status"] == "abgeschafft"

    async def process_steps_llm(prompt, *_args, **_kwargs):
        assert _detect_addressee_from_prompt(prompt) == ADMINISTRATION
        return json.dumps(
            {
                "fallgruppen": [
                    {
                        "fallgruppen_id": str(case_group["case_group_id"]),
                        "taetigkeiten": [
                            {
                                "taetigkeit": "Schritt Verwaltung",
                                "beschreibung": "Beschreibung",
                                "status_change": "unchanged",
                            }
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr(process_steps_router, "query_llm", process_steps_llm)
    response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "process_steps",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert response.status_code == 200
    assert _wait_for_run_completion(test_client, response.json()["run_id"])["status"] == "completed"
    step = db.list_process_steps_for_session_and_addressee(session_id, ADMINISTRATION)[0]
    assert step["change_status"] == "unveraendert"
    step_tile = next(
        tile
        for tile in db.fetch_tiles(session_id=session_id, norm_addressee=ADMINISTRATION)
        if tile.id == f"step_{step['step_id']}"
    )
    assert step_tile.meta_information["change_status"] == "unveraendert"


def test_case_group_apply_failure_rolls_back_rows_tiles_and_answers(
    test_client,
    monkeypatch,
):
    app_session_id = "STEP-CASE-GROUPS-APPLY-ROLLBACK"
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    db.insert_regulation(
        session_id,
        "§ A",
        "Vorgabe Verwaltung",
        applies_to_administration=True,
        applies_to_business=False,
        applies_to_citizens=False,
    )
    db.insert_regulation(
        session_id,
        "§ B",
        "Vorgabe Wirtschaft",
        applies_to_administration=False,
        applies_to_business=True,
        applies_to_citizens=False,
        is_business_information_obligation=True,
    )
    admin_process = db.insert_process(
        session_id,
        "Prozess Verwaltung",
        "Beschreibung",
        norm_addressee=ADMINISTRATION,
    )
    business_process = db.insert_process(
        session_id,
        "Prozess Wirtschaft",
        "Beschreibung",
        norm_addressee=BUSINESS,
    )
    _upsert_process_tile(session_id, admin_process, ADMINISTRATION, row=0)
    _upsert_process_tile(session_id, business_process, BUSINESS, row=0)

    async def valid_case_groups_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        process_id = admin_process if addressee == ADMINISTRATION else business_process
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_id": str(process_id),
                        "fallgruppen": [
                            {
                                "fallgruppe_bezeichnung": f"Fallgruppe {addressee}",
                                "fallgruppe_beschreibung": "Beschreibung",
                            }
                        ],
                    }
                ]
            }
        )

    original_apply = case_groups_router.apply_case_group_development

    def fail_on_business_apply(*, session_id, norm_addressee, parsed, context):
        if norm_addressee == BUSINESS:
            raise RuntimeError("forced case-group apply rollback")
        return original_apply(
            session_id=session_id,
            norm_addressee=norm_addressee,
            parsed=parsed,
            context=context,
        )

    monkeypatch.setattr(case_groups_router, "query_llm", valid_case_groups_llm)
    monkeypatch.setattr(
        case_groups_router,
        "apply_case_group_development",
        fail_on_business_apply,
    )
    response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "case_groups",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert response.status_code == 200
    payload = _wait_for_run_completion(test_client, response.json()["run_id"])

    assert payload["status"] == "failed"
    assert db.list_case_groups_for_session(session_id) == []
    assert not any(
        tile.id.startswith("case_group_")
        for addressee in (ADMINISTRATION, BUSINESS)
        for tile in db.fetch_tiles(session_id=session_id, norm_addressee=addressee)
    )
    rows = [
        row
        for row in db.list_recent_llm_answers_for_session(session_id)
        if row["prompt_id"] == PromptId.CASE_GROUP_DEVELOPMENT
    ]
    assert {row["answer_state"] for row in rows} == {"invalid"}
    events = asyncio.run(llm_monitor.get_recent_events(app_session_id, limit=50))
    assert not [
        event
        for event in events
        if event["event_type"] == "llm_apply_succeeded"
        and event["prompt_id"] == PromptId.CASE_GROUP_DEVELOPMENT
    ]


def test_process_step_apply_failure_rolls_back_rows_tiles_links_and_answers(
    test_client,
    monkeypatch,
):
    app_session_id = "STEP-PROCESS-STEPS-APPLY-ROLLBACK"
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    admin_process = db.insert_process(
        session_id,
        "Prozess Verwaltung",
        "Beschreibung",
        norm_addressee=ADMINISTRATION,
    )
    business_process = db.insert_process(
        session_id,
        "Prozess Wirtschaft",
        "Beschreibung",
        norm_addressee=BUSINESS,
    )
    db.insert_regulation(
        session_id,
        "§ A",
        "Vorgabe Verwaltung",
        process_id=admin_process,
        applies_to_administration=True,
        applies_to_business=False,
        applies_to_citizens=False,
    )
    db.insert_regulation(
        session_id,
        "§ B",
        "Vorgabe Wirtschaft",
        process_id=business_process,
        applies_to_administration=False,
        applies_to_business=True,
        applies_to_citizens=False,
        is_business_information_obligation=True,
    )
    admin_case_group = db.insert_case_group(
        session_id,
        admin_process,
        "Fallgruppe Verwaltung",
        "Beschreibung",
        norm_addressee=ADMINISTRATION,
    )
    business_case_group = db.insert_case_group(
        session_id,
        business_process,
        "Fallgruppe Wirtschaft",
        "Beschreibung",
        norm_addressee=BUSINESS,
    )
    _upsert_process_tile(session_id, admin_process, ADMINISTRATION, row=0)
    _upsert_process_tile(session_id, business_process, BUSINESS, row=0)
    _upsert_case_group_tile(
        session_id, admin_case_group, admin_process, ADMINISTRATION, row=0
    )
    _upsert_case_group_tile(
        session_id, business_case_group, business_process, BUSINESS, row=0
    )

    async def valid_process_steps_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        case_group_id = (
            admin_case_group if addressee == ADMINISTRATION else business_case_group
        )
        return json.dumps(
            {
                "fallgruppen": [
                    {
                        "fallgruppen_id": str(case_group_id),
                        "taetigkeiten": [
                            {
                                "taetigkeit": f"Schritt {addressee}",
                                "beschreibung": "Beschreibung",
                            }
                        ],
                    }
                ]
            }
        )

    original_apply = process_steps_router.apply_process_step_analysis

    def fail_on_business_apply(*, session_id, norm_addressee, parsed, context):
        if norm_addressee == BUSINESS:
            raise RuntimeError("forced process-step apply rollback")
        return original_apply(
            session_id=session_id,
            norm_addressee=norm_addressee,
            parsed=parsed,
            context=context,
        )

    monkeypatch.setattr(process_steps_router, "query_llm", valid_process_steps_llm)
    monkeypatch.setattr(
        process_steps_router,
        "apply_process_step_analysis",
        fail_on_business_apply,
    )
    response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "process_steps",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert response.status_code == 200
    payload = _wait_for_run_completion(test_client, response.json()["run_id"])

    assert payload["status"] == "failed"
    assert db.list_process_steps_for_session(session_id) == []
    assert not any(
        tile.id.startswith("step_")
        for addressee in (ADMINISTRATION, BUSINESS)
        for tile in db.fetch_tiles(session_id=session_id, norm_addressee=addressee)
    )
    rows = [
        row
        for row in db.list_recent_llm_answers_for_session(session_id)
        if row["prompt_id"] == PromptId.PROCESS_STEP_ANALYSIS
    ]
    assert {row["answer_state"] for row in rows} == {"invalid"}
    events = asyncio.run(llm_monitor.get_recent_events(app_session_id, limit=50))
    assert not [
        event
        for event in events
        if event["event_type"] == "llm_apply_succeeded"
        and event["prompt_id"] == PromptId.PROCESS_STEP_ANALYSIS
    ]


def test_single_step_existing_and_skipped_addressees_do_not_query_llm(
    test_client,
    monkeypatch,
):
    app_session_id = "STEP-EXISTING-SKIPPED-NO-QUERY"
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    db.insert_regulation(
        session_id,
        "§ A",
        "Vorgabe Verwaltung",
        applies_to_administration=True,
        applies_to_business=False,
        applies_to_citizens=False,
    )
    db.insert_regulation(
        session_id,
        "§ B",
        "Vorgabe Wirtschaft",
        applies_to_administration=False,
        applies_to_business=True,
        applies_to_citizens=False,
        is_business_information_obligation=True,
    )
    db.insert_process(
        session_id,
        "Bestehender Prozess Verwaltung",
        "Beschreibung",
        norm_addressee=ADMINISTRATION,
    )
    calls: list[str] = []

    async def business_only_processes_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        calls.append(addressee)
        assert addressee == BUSINESS
        regulations = db.list_regulations_for_session_and_addressee(
            session_id,
            BUSINESS,
        )
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_bezeichnung": "Prozess Wirtschaft",
                        "prozess_beschreibung": "Beschreibung",
                        "vorgaben": [
                            {"vorgaben_id": str(regulations[0]["regulation_id"])}
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr(processes_router, "query_llm", business_only_processes_llm)
    response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "processes",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert response.status_code == 200
    payload = _wait_for_run_completion(test_client, response.json()["run_id"])

    assert payload["status"] == "completed"
    assert calls == [BUSINESS]
    assert len(db.list_processes_for_session_and_addressee(session_id, ADMINISTRATION)) == 1
    assert len(db.list_processes_for_session_and_addressee(session_id, BUSINESS)) == 1
    assert db.list_processes_for_session_and_addressee(session_id, CITIZENS) == []


def test_effort_step_stages_all_normal_prompts_concurrently(test_client, monkeypatch):
    app_session_id = "STEP-EFFORT-CONCURRENT"
    session_id = _seed_step6_prerequisites(app_session_id)
    started: list[tuple[str, str]] = []
    gate: dict[str, asyncio.Event] = {}

    async def gated_effort_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        prompt_kind = "effort" if _is_effort_prompt(prompt) else "cases"
        if "event" not in gate:
            gate["event"] = asyncio.Event()
        started.append((prompt_kind, addressee))
        if len(started) == 6:
            gate["event"].set()
        await asyncio.wait_for(gate["event"].wait(), timeout=1.0)

        processes = db.list_processes_for_session_and_addressee(session_id, addressee)
        case_groups = db.list_case_groups_for_session_and_addressee(session_id, addressee)
        steps = db.list_process_steps_for_session_and_addressee(session_id, addressee)
        if prompt_kind == "cases":
            return json.dumps(
                {
                    "fallgruppen": [
                        {
                            "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                            "anzahl_betroffene_vorschlag": "10",
                            "haeufigkeit_pro_jahr_vorschlag": "2",
                        }
                    ]
                }
            )
        if addressee == CITIZENS:
            effort_entry = {
                "taetigkeiten_id": str(steps[0]["step_id"]),
                "zeitaufwand_in_min_vorschlag": "30",
                "sachaufwand_vorschlag": "10",
            }
        else:
            effort_entry = {
                "taetigkeiten_id": str(steps[0]["step_id"]),
                "personalaufwand_vorschlag": [
                    _personalaufwand_row(addressee, "30")
                ],
                "sachaufwand_vorschlag": "10",
            }
        return json.dumps(
            {
                "fallgruppen": [
                    {
                        "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                        "taetigkeiten": [effort_entry],
                    }
                ]
            }
        )

    monkeypatch.setattr(effort_router, "query_llm", gated_effort_llm)
    response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "effort",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert response.status_code == 200
    payload = _wait_for_run_completion(test_client, response.json()["run_id"])

    assert payload["status"] == "completed"
    assert set(started) == {
        ("cases", ADMINISTRATION),
        ("effort", ADMINISTRATION),
        ("cases", BUSINESS),
        ("effort", BUSINESS),
        ("cases", CITIZENS),
        ("effort", CITIZENS),
    }
    assert db.has_effort_metrics(session_id, ADMINISTRATION)
    assert db.has_effort_metrics(session_id, BUSINESS)
    assert db.has_effort_metrics(session_id, CITIZENS)


def test_effort_step_parse_failure_applies_no_sibling_metrics_and_keeps_valid_pending(
    test_client,
    monkeypatch,
):
    app_session_id = "STEP-EFFORT-ATOMIC-FAIL"
    session_id = _seed_step6_prerequisites(app_session_id)

    async def fake_effort_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        processes = db.list_processes_for_session_and_addressee(session_id, addressee)
        case_groups = db.list_case_groups_for_session_and_addressee(session_id, addressee)
        steps = db.list_process_steps_for_session_and_addressee(session_id, addressee)
        if not _is_effort_prompt(prompt):
            return json.dumps(
                {
                    "fallgruppen": [
                        {
                            "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                            "anzahl_betroffene_vorschlag": "10",
                            "haeufigkeit_pro_jahr_vorschlag": "2",
                        }
                    ]
                }
            )
        if addressee == CITIZENS:
            effort_entry = {
                "taetigkeiten_id": str(steps[0]["step_id"]),
                "zeitaufwand_in_min_vorschlag": "30",
                "sachaufwand_vorschlag": "10",
            }
        elif addressee == BUSINESS:
            effort_entry = {
                "taetigkeiten_id": str(steps[0]["step_id"]),
                "personalaufwand_vorschlag": [
                    {"qualifikation": "niedrig", "zeitaufwand_in_min": "30"}
                ],
            }
        else:
            effort_entry = {
                "taetigkeiten_id": str(steps[0]["step_id"]),
                "personalaufwand_vorschlag": [_personalaufwand_row(addressee, "30")],
                "sachaufwand_vorschlag": "10",
            }
        return json.dumps(
            {
                "fallgruppen": [
                    {
                        "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                        "taetigkeiten": [effort_entry],
                    }
                ]
            }
        )

    monkeypatch.setattr(effort_router, "query_llm", fake_effort_llm)
    start_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "effort",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(test_client, start_response.json()["run_id"])
    assert payload["status"] == "failed"
    assert "Die Antwort für Wirtschaft konnte nicht verarbeitet werden" in payload["last_error"]
    for addressee in (ADMINISTRATION, BUSINESS, CITIZENS):
        assert not db.has_effort_metrics(session_id, addressee)

    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT prompt_id, norm_addressee, answer_state, state_reason
        FROM llm_answers
        WHERE session_id = ? AND prompt_id IN (?, ?)
        """,
        (session_id, PromptId.CASES_CALCULATION, PromptId.EFFORT_CALCULATION),
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    by_key = {(row["prompt_id"], row["norm_addressee"]): row for row in rows}
    for addressee in (ADMINISTRATION, CITIZENS):
        assert by_key[(PromptId.CASES_CALCULATION, addressee)]["answer_state"] == "pending"
        assert by_key[(PromptId.EFFORT_CALCULATION, addressee)]["answer_state"] == "pending"
    assert by_key[(PromptId.CASES_CALCULATION, BUSINESS)]["answer_state"] == "invalid"
    assert by_key[(PromptId.EFFORT_CALCULATION, BUSINESS)]["answer_state"] == "invalid"


def test_effort_step_tile_refresh_failure_rolls_back_metrics_and_answers(
    test_client,
    monkeypatch,
):
    app_session_id = "STEP-EFFORT-TILE-REFRESH-ROLLBACK"
    session_id = _seed_step6_prerequisites(app_session_id)

    async def valid_effort_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        processes = db.list_processes_for_session_and_addressee(session_id, addressee)
        case_groups = db.list_case_groups_for_session_and_addressee(session_id, addressee)
        steps = db.list_process_steps_for_session_and_addressee(session_id, addressee)
        if not _is_effort_prompt(prompt):
            return json.dumps(
                {
                    "fallgruppen": [
                        {
                            "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                            "anzahl_betroffene_vorschlag": "10",
                            "haeufigkeit_pro_jahr_vorschlag": "2",
                        }
                    ]
                }
            )
        if addressee == CITIZENS:
            effort_entry = {
                "taetigkeiten_id": str(steps[0]["step_id"]),
                "zeitaufwand_in_min_vorschlag": "30",
                "sachaufwand_vorschlag": "10",
            }
        else:
            effort_entry = {
                "taetigkeiten_id": str(steps[0]["step_id"]),
                "personalaufwand_vorschlag": [_personalaufwand_row(addressee, "30")],
                "sachaufwand_vorschlag": "10",
            }
        return json.dumps(
            {
                "fallgruppen": [
                    {
                        "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                        "taetigkeiten": [effort_entry],
                    }
                ]
            }
        )

    original_refresh = effort_router.refresh_effort_tiles

    def fail_on_business_refresh(*, session_id, norm_addressee):
        if norm_addressee == BUSINESS:
            raise RuntimeError("forced tile refresh failure")
        original_refresh(session_id=session_id, norm_addressee=norm_addressee)

    monkeypatch.setattr(effort_router, "query_llm", valid_effort_llm)
    monkeypatch.setattr(effort_router, "refresh_effort_tiles", fail_on_business_refresh)
    start_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "effort",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(test_client, start_response.json()["run_id"])

    assert payload["status"] == "failed"
    assert "forced tile refresh failure" in payload["last_error"]
    for addressee in (ADMINISTRATION, BUSINESS, CITIZENS):
        assert not db.has_effort_metrics(session_id, addressee)
    assert db.list_session_personnel_effort(session_id) == []
    rows = [
        row
        for row in db.list_recent_llm_answers_for_session(session_id)
        if row["prompt_id"] in {PromptId.CASES_CALCULATION, PromptId.EFFORT_CALCULATION}
    ]
    assert rows
    assert {row["answer_state"] for row in rows} == {"invalid"}


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

    async def slow_processes_llm(*_args, **_kwargs):
        reached_processes.set()
        await asyncio.sleep(0.3)
        regulations = db.list_regulations_for_session_and_addressee(
            session_id,
            ADMINISTRATION,
        )
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_bezeichnung": "Prozess Verwaltung",
                        "prozess_beschreibung": "Beschreibung",
                        "vorgaben": [
                            {"vorgaben_id": str(regulations[0]["regulation_id"])}
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr(processes_router, "query_llm", slow_processes_llm)

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


def test_single_step_run_executes_shared_step_runner(test_client, monkeypatch):
    app_session_id = "STEP-RUN-PROCESSES"
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    db.insert_regulation(session_id, "§ 1", "Beschreibung")

    async def fake_processes_llm(*_args, **_kwargs):
        regulations = db.list_regulations_for_session_and_addressee(
            session_id,
            ADMINISTRATION,
        )
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_bezeichnung": "Prozess administration",
                        "prozess_beschreibung": "Beschreibung",
                        "vorgaben": [
                            {"vorgaben_id": str(regulations[0]["regulation_id"])}
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr(processes_router, "query_llm", fake_processes_llm)

    start_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "processes",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    run_id = start_response.json()["run_id"]

    deadline = time.time() + 2.0
    payload = None
    while time.time() < deadline:
        response = test_client.get(f"/sessions/step-runs/{run_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] != "running":
            break
        time.sleep(0.05)

    assert payload is not None
    assert payload["status"] == "completed"
    assert payload["ok"] is True
    assert payload["steps"] == [
        {"key": "processes", "label": "Prozesse bündeln", "status": "completed", "message": None}
    ]
    assert payload["final_status"]["processes_ready"] is True


def test_undo_rejects_while_workflow_run_is_active(test_client, monkeypatch):
    app_session_id = "UNDO-ACTIVE-RUN"
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    db.update_session_summary(app_session_id, "Titel", "Zusammenfassung")
    regulation_id = db.insert_regulation(
        session_id,
        "§ 1",
        "Beschreibung",
        applies_to_administration=True,
        applies_to_business=False,
        applies_to_citizens=False,
    )

    async def slow_processes_llm(*_args, **_kwargs):
        await asyncio.sleep(1.0)
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_bezeichnung": "Prozess Verwaltung",
                        "prozess_beschreibung": "Beschreibung",
                        "vorgaben": [{"vorgaben_id": str(regulation_id)}],
                    }
                ]
            }
        )

    monkeypatch.setattr(processes_router, "query_llm", slow_processes_llm)

    start_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "processes",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    run_id = start_response.json()["run_id"]

    undo_response = test_client.post(
        "/sessions/undo",
        json={"app_session_id": app_session_id},
    )

    assert undo_response.status_code == 409
    assert "lauf zuerst abbrechen" in undo_response.json()["detail"].lower()

    cancel_response = test_client.post(f"/sessions/step-runs/{run_id}/cancel")
    assert cancel_response.status_code == 200
    done = _wait_for_run_completion(test_client, run_id, timeout_s=5.0)
    assert done["status"] == "cancelled"


def test_single_step_run_effort_uses_deep_research_when_enabled(
    test_client,
    monkeypatch,
):
    app_session_id = "STEP-RUN-EFFORT-DR"
    session_id = _seed_step6_prerequisites(app_session_id)
    db.update_case_group_research_enabled(session_id, True)
    calls = {"cases": 0, "effort": 0}

    async def fake_effort_llm(prompt, *_args, **_kwargs):
        if not _is_effort_prompt(prompt):
            calls["cases"] += 1
            raise AssertionError("cases_calculation should be replaced by Deep Research")
        calls["effort"] += 1
        addressee = _detect_addressee_from_prompt(prompt)
        processes = db.list_processes_for_session_and_addressee(session_id, addressee)
        case_groups = db.list_case_groups_for_session_and_addressee(session_id, addressee)
        steps = db.list_process_steps_for_session_and_addressee(session_id, addressee)
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
                "personalaufwand_vorschlag": [
                    _personalaufwand_row(addressee, "30")
                ],
                "sachaufwand_vorschlag": "10",
            }
        return json.dumps(
            {
                "normadressat": addressee,
                "fallgruppen": [
                    {
                        "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                        "taetigkeiten": [effort_entry],
                    }
                ],
            }
        )

    async def fake_run_deep_research(*_args, **_kwargs):
        processes = []
        for group in db.list_case_groups_for_session(session_id):
            processes.append(
                {
                    "prozess_id": str(group["process_id"]),
                    "normadressat": group["norm_addressee"],
                    "fallgruppen": [
                        {
                            "fallgruppen_id": str(group["case_group_id"]),
                            "anzahl_betroffene_gueltig": "10",
                            "haeufigkeit_pro_jahr_gueltig": "1",
                            "anzahl_betroffene_vorschlag": "20",
                            "haeufigkeit_pro_jahr_vorschlag": "2",
                            "confidence": {
                                "anzahl_betroffene_gueltig": "high",
                                "haeufigkeit_pro_jahr_gueltig": "high",
                                "anzahl_betroffene_vorschlag": "medium",
                                "haeufigkeit_pro_jahr_vorschlag": "medium",
                            },
                            "erklaerungen": {
                                "anzahl_betroffene_gueltig": "Begründung gültig.",
                                "haeufigkeit_pro_jahr_gueltig": "Begründung Häufigkeit.",
                                "anzahl_betroffene_vorschlag": "Begründung Entwurf.",
                                "haeufigkeit_pro_jahr_vorschlag": "Begründung Häufigkeit Entwurf.",
                            },
                        }
                    ],
                }
            )
        report_text = json.dumps({"prozesse": processes})
        return DeepResearchResult(
            agent="test-agent",
            interaction_id="step-dr",
            report_text=report_text,
            response_json={"status": "completed"},
        )

    monkeypatch.setattr(effort_router, "query_llm", fake_effort_llm)
    monkeypatch.setattr(sessions_router, "run_deep_research", fake_run_deep_research)

    start_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "effort",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(test_client, start_response.json()["run_id"])

    assert payload["status"] == "completed"
    assert payload["ok"] is True
    assert payload["final_status"]["effort_ready"] is True
    assert payload["final_status"]["total_cost_ready"] is False
    assert calls == {"cases": 0, "effort": 3}
    assert db.get_latest_deep_research_run(session_id, "case_group_metrics")["status"] == "parsed"
    assert "cases_calculation" not in {
        row["prompt_id"] for row in db.list_recent_llm_answers_for_session(session_id)
    }


def test_single_step_run_effort_reuses_waiting_effort_after_completed_deep_research(
    test_client,
    monkeypatch,
):
    app_session_id = "STEP-RUN-EFFORT-DR-REUSE-WAITING"
    session_id = _seed_step6_prerequisites(app_session_id)
    db.update_case_group_research_enabled(session_id, True)

    effort_payloads: dict[str, str] = {}

    async def stage_effort_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        processes = db.list_processes_for_session_and_addressee(session_id, addressee)
        case_groups = db.list_case_groups_for_session_and_addressee(session_id, addressee)
        steps = db.list_process_steps_for_session_and_addressee(session_id, addressee)
        if addressee == CITIZENS:
            effort_entry = {
                "taetigkeiten_id": str(steps[0]["step_id"]),
                "zeitaufwand_in_min_vorschlag": "30",
                "sachaufwand_vorschlag": "10",
            }
        else:
            effort_entry = {
                "taetigkeiten_id": str(steps[0]["step_id"]),
                "personalaufwand_vorschlag": [
                    _personalaufwand_row(addressee, "30")
                ],
                "sachaufwand_vorschlag": "10",
            }
        response = json.dumps(
            {
                "normadressat": addressee,
                "fallgruppen": [
                    {
                        "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                        "taetigkeiten": [effort_entry],
                    }
                ],
            }
        )
        effort_payloads[addressee] = response
        return response

    async def cancelled_after_effort_staging(*_args, **_kwargs):
        while len(effort_payloads) < 2:
            await asyncio.sleep(0.01)
        raise asyncio.CancelledError

    monkeypatch.setattr(effort_router, "query_llm", stage_effort_llm)
    monkeypatch.setattr(sessions_router, "run_deep_research", cancelled_after_effort_staging)

    start_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "effort",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    first = _wait_for_run_completion(test_client, start_response.json()["run_id"])
    assert first["status"] == "cancelled"

    for row in db.list_recent_llm_answers_for_session(session_id):
        if row["prompt_id"] == PromptId.EFFORT_CALCULATION:
            db.update_llm_answer_state_reason(
                int(row["answer_id"]),
                "waiting_for_session_update",
                state=db.LLM_ANSWER_STATE_PENDING,
            )

    processes = []
    for group in db.list_case_groups_for_session(session_id):
        processes.append(
            {
                "prozess_id": str(group["process_id"]),
                "normadressat": group["norm_addressee"],
                "fallgruppen": [
                    {
                        "fallgruppen_id": str(group["case_group_id"]),
                        "anzahl_betroffene_gueltig": "10",
                        "haeufigkeit_pro_jahr_gueltig": "1",
                        "anzahl_betroffene_vorschlag": "20",
                        "haeufigkeit_pro_jahr_vorschlag": "2",
                        "confidence": {
                            "anzahl_betroffene_gueltig": "high",
                            "haeufigkeit_pro_jahr_gueltig": "high",
                            "anzahl_betroffene_vorschlag": "medium",
                            "haeufigkeit_pro_jahr_vorschlag": "medium",
                        },
                        "erklaerungen": {
                            "anzahl_betroffene_gueltig": "Begründung gültig.",
                            "haeufigkeit_pro_jahr_gueltig": "Begründung Häufigkeit.",
                            "anzahl_betroffene_vorschlag": "Begründung Entwurf.",
                            "haeufigkeit_pro_jahr_vorschlag": "Begründung Häufigkeit Entwurf.",
                        },
                    }
                ],
            }
        )
    run_id = db.create_deep_research_run(
        session_id=session_id,
        purpose="case_group_metrics",
        agent="test-agent",
        status="running",
        prompt_text="prompt",
    )
    db.update_deep_research_run(
        run_id,
        status="completed",
        report_md=json.dumps({"prozesse": processes}),
        response_json={"status": "completed"},
    )

    async def fail_if_effort_requeried(*_args, **_kwargs):
        raise AssertionError("matching waiting effort answers should be reused")

    monkeypatch.setattr(effort_router, "query_llm", fail_if_effort_requeried)

    retry_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "effort",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert retry_response.status_code == 200
    retry = _wait_for_run_completion(test_client, retry_response.json()["run_id"])

    assert retry["status"] == "completed"
    assert retry["final_status"]["effort_ready"] is True
    assert db.get_latest_deep_research_run(session_id, "case_group_metrics")["status"] == "parsed"
    effort_rows = [
        row
        for row in db.list_recent_llm_answers_for_session(session_id)
        if row["prompt_id"] == PromptId.EFFORT_CALCULATION
    ]
    assert len(effort_rows) == len(effort_payloads)
    assert {row["answer_state"] for row in effort_rows} == {"active"}


def test_single_step_run_effort_deep_research_timeout_leaves_step_incomplete(
    test_client,
    monkeypatch,
):
    app_session_id = "STEP-RUN-EFFORT-DR-TIMEOUT"
    session_id = _seed_step6_prerequisites(app_session_id)
    db.update_case_group_research_enabled(session_id, True)
    calls = {"cases": 0}

    async def fake_effort_llm(prompt, *_args, **_kwargs):
        if not _is_effort_prompt(prompt):
            calls["cases"] += 1
            raise AssertionError("cases_calculation should not run in Deep Research mode")
        await asyncio.sleep(10.0)

    async def timed_out_deep_research(*_args, **_kwargs):
        raise DeepResearchError("Gemini Deep Research timed out after 1800 seconds")

    monkeypatch.setattr(effort_router, "query_llm", fake_effort_llm)
    monkeypatch.setattr(sessions_router, "run_deep_research", timed_out_deep_research)

    start_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "effort",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(
        test_client,
        start_response.json()["run_id"],
        timeout_s=10.0,
    )

    assert payload["status"] == "failed"
    assert payload["ok"] is False
    assert payload["final_status"]["effort_ready"] is False
    assert payload["final_status"]["case_group_research_status"] == "failed"
    assert calls == {"cases": 0}
    run = db.get_latest_deep_research_run(session_id, "case_group_metrics")
    assert run is not None
    assert run["status"] == "failed"
    assert "timed out" in run["error"]


def test_single_step_run_effort_deep_research_running_does_not_start_effort(
    test_client,
    monkeypatch,
):
    app_session_id = "STEP-RUN-EFFORT-DR-RUNNING"
    session_id = _seed_step6_prerequisites(app_session_id)
    db.update_case_group_research_enabled(session_id, True)
    db.create_deep_research_run(
        session_id=session_id,
        purpose="case_group_metrics",
        agent="deep-research-test",
        status="running",
        prompt_text="prompt",
    )

    async def fail_if_called(*_args, **_kwargs):
        raise AssertionError("effort_calculation should not start while DR is already running")

    monkeypatch.setattr(effort_router, "query_llm", fail_if_called)

    start_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "effort",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(
        test_client,
        start_response.json()["run_id"],
        timeout_s=10.0,
    )

    assert payload["status"] == "failed"
    assert "Deep Research for case groups is already running" in payload["last_error"]
    assert [
        row
        for row in db.list_recent_llm_answers_for_session(session_id)
        if row["prompt_id"] == PromptId.EFFORT_CALCULATION
    ] == []


def test_single_step_run_effort_cancel_promotes_staged_effort_for_retry(
    test_client,
    monkeypatch,
):
    app_session_id = "STEP-RUN-EFFORT-DR-CANCEL-RETRY"
    session_id = _seed_step6_prerequisites(app_session_id)
    db.update_case_group_research_enabled(session_id, True)

    async def fake_effort_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        return json.dumps(
            {
                "normadressat": addressee,
                "fallgruppen": [],
            }
        )

    async def slow_deep_research(*_args, **_kwargs):
        await asyncio.sleep(10.0)

    monkeypatch.setattr(effort_router, "query_llm", fake_effort_llm)
    monkeypatch.setattr(sessions_router, "run_deep_research", slow_deep_research)

    start_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "effort",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    run_id = start_response.json()["run_id"]

    deadline = time.time() + 3.0
    while time.time() < deadline:
        rows = [
            row
            for row in db.list_recent_llm_answers_for_session(session_id)
            if row["prompt_id"] == PromptId.EFFORT_CALCULATION
            and row["answer_state"] == "pending"
        ]
        if len(rows) >= 2:
            break
        time.sleep(0.05)
    else:
        pytest.fail("effort answers were not staged before cancellation")

    cancel_response = test_client.post(f"/sessions/step-runs/{run_id}/cancel")
    assert cancel_response.status_code == 200
    payload = _wait_for_run_completion(test_client, run_id, timeout_s=10.0)
    assert payload["status"] == "cancelled"

    rows = [
        row
        for row in db.list_recent_llm_answers_for_session(session_id)
        if row["prompt_id"] == PromptId.EFFORT_CALCULATION
    ]
    assert {row["state_reason"] for row in rows} == {"waiting_for_paired_retry"}


def test_single_step_run_effort_cancel_preserves_completed_normal_answer_for_retry(
    test_client,
    monkeypatch,
):
    app_session_id = "STEP-RUN-EFFORT-CANCEL-PARTIAL-STAGED"
    session_id = _seed_step6_prerequisites(app_session_id)
    call_count = 0
    completed_key: tuple[str, str] | None = None

    def cases_payload(addressee: str) -> str:
        processes = db.list_processes_for_session_and_addressee(session_id, addressee)
        case_groups = db.list_case_groups_for_session_and_addressee(session_id, addressee)
        return json.dumps(
            {
                "fallgruppen": [
                    {
                        "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                        "anzahl_betroffene_vorschlag": "10",
                        "haeufigkeit_pro_jahr_vorschlag": "1",
                    }
                ]
            }
        )

    def effort_payload(addressee: str) -> str:
        processes = db.list_processes_for_session_and_addressee(session_id, addressee)
        case_groups = db.list_case_groups_for_session_and_addressee(session_id, addressee)
        steps = db.list_process_steps_for_session_and_addressee(session_id, addressee)
        if addressee == CITIZENS:
            effort_entry = {
                "taetigkeiten_id": str(steps[0]["step_id"]),
                "zeitaufwand_in_min_vorschlag": "30",
                "sachaufwand_vorschlag": "10",
            }
        else:
            effort_entry = {
                "taetigkeiten_id": str(steps[0]["step_id"]),
                "personalaufwand_vorschlag": [_personalaufwand_row(addressee, "30")],
                "sachaufwand_vorschlag": "10",
            }
        return json.dumps(
            {
                "fallgruppen": [
                    {
                        "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                        "taetigkeiten": [effort_entry],
                    }
                ]
            }
        )

    def response_for_prompt(prompt: str) -> tuple[tuple[str, str], str]:
        addressee = _detect_addressee_from_prompt(prompt)
        if _is_effort_prompt(prompt):
            return (PromptId.EFFORT_CALCULATION, addressee), effort_payload(addressee)
        return (PromptId.CASES_CALCULATION, addressee), cases_payload(addressee)

    async def one_fast_answer_then_slow(prompt, *_args, **_kwargs):
        nonlocal call_count
        nonlocal completed_key
        call_count += 1
        if call_count == 1:
            key, response = response_for_prompt(prompt)
            completed_key = key
            return response
        await asyncio.sleep(10.0)

    monkeypatch.setattr(effort_router, "query_llm", one_fast_answer_then_slow)

    start_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "effort",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    run_id = start_response.json()["run_id"]

    deadline = time.time() + 3.0
    staged_rows = []
    while time.time() < deadline:
        staged_rows = [
            row
            for row in db.list_recent_llm_answers_for_session(session_id)
            if row["prompt_id"] in {PromptId.CASES_CALCULATION, PromptId.EFFORT_CALCULATION}
            and row["answer_state"] == "pending"
            and row["state_reason"] == "waiting_for_session_update"
        ]
        if staged_rows:
            break
        time.sleep(0.05)
    else:
        pytest.fail("one answer was not staged before cancellation")

    cancel_response = test_client.post(f"/sessions/step-runs/{run_id}/cancel")
    assert cancel_response.status_code == 200
    payload = _wait_for_run_completion(test_client, run_id, timeout_s=10.0)
    assert payload["status"] == "cancelled"

    rows = [
        row
        for row in db.list_recent_llm_answers_for_session(session_id)
        if row["prompt_id"] in {PromptId.CASES_CALCULATION, PromptId.EFFORT_CALCULATION}
    ]
    staged_after_cancel = [
        row
        for row in rows
        if row["answer_state"] == "pending"
        and row["state_reason"] == "waiting_for_paired_retry"
    ]
    assert len(staged_after_cancel) == 1
    assert db.list_session_personnel_effort(session_id) == []

    retry_calls: list[tuple[str, str]] = []

    async def retry_missing_answers(prompt, *_args, **_kwargs):
        key, response = response_for_prompt(prompt)
        retry_calls.append(key)
        assert key != completed_key
        return response

    monkeypatch.setattr(effort_router, "query_llm", retry_missing_answers)
    retry_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "effort",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert retry_response.status_code == 200
    retry_payload = _wait_for_run_completion(test_client, retry_response.json()["run_id"])
    assert retry_payload["status"] == "completed"
    assert retry_payload["final_status"]["effort_ready"] is True
    assert completed_key not in retry_calls
    assert db.list_session_personnel_effort(session_id) != []


def test_single_step_run_effort_cancel_clears_normal_llm_monitor_pending(
    test_client,
    monkeypatch,
):
    app_session_id = "STEP-RUN-EFFORT-CANCEL"
    _seed_step6_prerequisites(app_session_id)

    async def slow_effort_llm(*_args, **_kwargs):
        await asyncio.sleep(10.0)

    monkeypatch.setattr(effort_router, "query_llm", slow_effort_llm)

    start_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "effort",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    run_id = start_response.json()["run_id"]

    deadline = time.time() + 3.0
    pending = []
    while time.time() < deadline:
        pending = asyncio.run(llm_monitor.get_pending(app_session_id))
        if len(pending) >= 2:
            break
        time.sleep(0.05)
    assert {row["prompt_id"] for row in pending} == {
        "cases_calculation",
        "effort_calculation",
    }

    cancel_response = test_client.post(f"/sessions/step-runs/{run_id}/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["accepted"] is True

    payload = _wait_for_run_completion(test_client, run_id, timeout_s=10.0)
    assert payload["status"] == "cancelled"
    assert payload["ok"] is False
    assert payload["final_status"]["effort_ready"] is False
    assert asyncio.run(llm_monitor.get_pending(app_session_id)) == []

    events = asyncio.run(llm_monitor.get_recent_events(app_session_id, limit=20))
    cancelled = [
        event
        for event in events
        if event["event_type"] == "llm_query_failed"
        and event.get("error_kind") == "cancelled"
    ]
    assert {event["prompt_id"] for event in cancelled} == {
        "cases_calculation",
        "effort_calculation",
    }


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

    async def failing_processes_llm(*_args, **_kwargs):
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_bezeichnung": "Fehlerprozess",
                        "prozess_beschreibung": "Beschreibung",
                        "vorgaben": [{"vorgaben_id": "999"}],
                    }
                ]
            }
        )

    monkeypatch.setattr(processes_router, "query_llm", failing_processes_llm)

    first_start = test_client.post(
        "/sessions/run-all/start",
        json={"app_session_id": app_session_id, "model": "test-model"},
    )
    assert first_start.status_code == 200
    first_done = _wait_for_run_completion(test_client, first_start.json()["run_id"])
    assert first_done["status"] == "failed"
    assert "Die Antwort für Wirtschaft konnte nicht verarbeitet werden" in first_done["last_error"]

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


def test_is_retryable_atomic_step_error_only_matches_422():
    from fastapi import HTTPException

    assert (
        sessions_router._is_retryable_atomic_step_error(
            HTTPException(status_code=422, detail="No process steps parsed")
        )
        is True
    )
    for code in (400, 404, 409, 500, 502):
        assert (
            sessions_router._is_retryable_atomic_step_error(
                HTTPException(status_code=code, detail="x")
            )
            is False
        )
    assert sessions_router._is_retryable_atomic_step_error(RuntimeError("x")) is False
    assert sessions_router._is_retryable_atomic_step_error(ValueError("x")) is False


def test_process_step_retries_once_when_first_output_violates_skeleton(
    test_client,
    monkeypatch,
):
    app_session_id = "STEP-PROCESS-STEPS-RETRY-SUCCESS"
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    db.insert_regulation(
        session_id,
        "§ B",
        "Vorgabe Wirtschaft",
        applies_to_administration=False,
        applies_to_business=True,
        applies_to_citizens=False,
        is_business_information_obligation=True,
    )
    business_process = db.insert_process(
        session_id,
        "Prozess Wirtschaft",
        "Beschreibung",
        norm_addressee=BUSINESS,
    )
    case_group_1 = db.insert_case_group(
        session_id,
        business_process,
        "Fallgruppe 1",
        "Beschreibung",
        norm_addressee=BUSINESS,
    )
    case_group_2 = db.insert_case_group(
        session_id,
        business_process,
        "Fallgruppe 2",
        "Beschreibung",
        norm_addressee=BUSINESS,
    )
    _upsert_process_tile(session_id, business_process, BUSINESS, row=1)
    _upsert_case_group_tile(session_id, case_group_1, business_process, BUSINESS, row=1)
    _upsert_case_group_tile(session_id, case_group_2, business_process, BUSINESS, row=2)
    calls = {BUSINESS: 0}

    async def flaky_steps_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        assert addressee == BUSINESS
        calls[addressee] += 1
        fallgruppen = [
            {
                "fallgruppen_id": str(case_group_1),
                "taetigkeiten": [
                    {"taetigkeit": "Schritt 1", "beschreibung": "Beschreibung 1"}
                ],
            }
        ]
        if calls[addressee] >= 2:
            fallgruppen.append(
                {
                    "fallgruppen_id": str(case_group_2),
                    "taetigkeiten": [
                        {"taetigkeit": "Schritt 2", "beschreibung": "Beschreibung 2"}
                    ],
                }
            )
        return _json_for_prompt(prompt, {"fallgruppen": fallgruppen})

    monkeypatch.setattr(process_steps_router, "query_llm", flaky_steps_llm)
    start_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "process_steps",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(test_client, start_response.json()["run_id"])

    assert payload["status"] == "completed"
    assert calls == {BUSINESS: 2}
    steps = db.list_process_steps_for_session_and_addressee(session_id, BUSINESS)
    covered = {int(step["case_group_id"]) for step in steps}
    assert covered == {case_group_1, case_group_2}


def test_process_step_exhausts_retry_and_keeps_partial_failure_state(
    test_client,
    monkeypatch,
):
    app_session_id = "STEP-PROCESS-STEPS-RETRY-EXHAUSTED"
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    db.insert_regulation(
        session_id,
        "§ A",
        "Vorgabe Verwaltung",
        applies_to_administration=True,
        applies_to_business=False,
        applies_to_citizens=False,
    )
    db.insert_regulation(
        session_id,
        "§ B",
        "Vorgabe Wirtschaft",
        applies_to_administration=False,
        applies_to_business=True,
        applies_to_citizens=False,
        is_business_information_obligation=True,
    )
    admin_process = db.insert_process(
        session_id,
        "Prozess Verwaltung",
        "Beschreibung",
        norm_addressee=ADMINISTRATION,
    )
    business_process = db.insert_process(
        session_id,
        "Prozess Wirtschaft",
        "Beschreibung",
        norm_addressee=BUSINESS,
    )
    admin_case_group = db.insert_case_group(
        session_id,
        admin_process,
        "Fallgruppe Verwaltung",
        "Beschreibung",
        norm_addressee=ADMINISTRATION,
    )
    db.insert_case_group(
        session_id,
        business_process,
        "Fallgruppe Wirtschaft",
        "Beschreibung",
        norm_addressee=BUSINESS,
    )
    calls = {ADMINISTRATION: 0, BUSINESS: 0}

    async def steps_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        calls[addressee] += 1
        case_group_id = admin_case_group if addressee == ADMINISTRATION else 999999
        return _json_for_prompt(
            prompt,
            {
                "fallgruppen": [
                    {
                        "fallgruppen_id": str(case_group_id),
                        "taetigkeiten": [
                            {"taetigkeit": f"Schritt {addressee}", "beschreibung": "B"}
                        ],
                    }
                ]
            },
        )

    monkeypatch.setattr(process_steps_router, "query_llm", steps_llm)
    start_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "process_steps",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(test_client, start_response.json()["run_id"])

    assert payload["status"] == "failed"
    assert "Die Antwort für Wirtschaft konnte nicht verarbeitet werden" in payload["last_error"]
    assert calls == {ADMINISTRATION: 1, BUSINESS: _ATOMIC_STEP_DEFAULT_MAX_ATTEMPTS}
    assert db.list_process_steps_for_session(session_id) == []
    rows = [
        row
        for row in db.list_recent_llm_answers_for_session(session_id)
        if row["prompt_id"] == PromptId.PROCESS_STEP_ANALYSIS
    ]
    admin_rows = [row for row in rows if row["norm_addressee"] == ADMINISTRATION]
    business_rows = [row for row in rows if row["norm_addressee"] == BUSINESS]
    assert len(admin_rows) == 1
    assert admin_rows[0]["answer_state"] == "pending"
    assert admin_rows[0]["state_reason"] == "waiting_for_paired_retry"
    assert business_rows
    assert all(row["answer_state"] == "invalid" for row in business_rows)
    assert any(
        str(row["state_reason"]).startswith("session_update_failed")
        for row in business_rows
    )


def test_effort_step_retries_failed_page_and_reuses_successful_pages(
    test_client,
    monkeypatch,
):
    app_session_id = "STEP-EFFORT-RETRY-SUCCESS"
    session_id = _seed_step6_prerequisites(app_session_id)
    calls: dict[tuple[str, str], int] = {}

    async def flaky_effort_llm(prompt, *_args, **_kwargs):
        addressee = _detect_addressee_from_prompt(prompt)
        prompt_kind = "effort" if _is_effort_prompt(prompt) else "cases"
        calls[(prompt_kind, addressee)] = calls.get((prompt_kind, addressee), 0) + 1
        case_groups = db.list_case_groups_for_session_and_addressee(session_id, addressee)
        steps = db.list_process_steps_for_session_and_addressee(session_id, addressee)
        if prompt_kind == "cases":
            return json.dumps(
                {
                    "fallgruppen": [
                        {
                            "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                            "anzahl_betroffene_vorschlag": "10",
                            "haeufigkeit_pro_jahr_vorschlag": "2",
                        }
                    ]
                }
            )
        if addressee == BUSINESS and calls[(prompt_kind, addressee)] == 1:
            return json.dumps(
                {
                    "fallgruppen": [
                        {
                            "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                            "taetigkeiten": [],
                        }
                    ]
                }
            )
        if addressee == CITIZENS:
            effort_entry = {
                "taetigkeiten_id": str(steps[0]["step_id"]),
                "zeitaufwand_in_min_vorschlag": "30",
                "sachaufwand_vorschlag": "10",
            }
        else:
            effort_entry = {
                "taetigkeiten_id": str(steps[0]["step_id"]),
                "personalaufwand_vorschlag": [_personalaufwand_row(addressee, "30")],
                "sachaufwand_vorschlag": "10",
            }
        return json.dumps(
            {
                "fallgruppen": [
                    {
                        "fallgruppen_id": str(case_groups[0]["case_group_id"]),
                        "taetigkeiten": [effort_entry],
                    }
                ]
            }
        )

    monkeypatch.setattr(effort_router, "query_llm", flaky_effort_llm)
    start_response = test_client.post(
        "/sessions/step-runs/start",
        json={
            "app_session_id": app_session_id,
            "step_key": "effort",
            "model": "test-model",
            "provider": "openai",
        },
    )
    assert start_response.status_code == 200
    payload = _wait_for_run_completion(test_client, start_response.json()["run_id"])

    assert payload["status"] == "completed"
    assert calls[("effort", BUSINESS)] == 2
    assert calls[("cases", BUSINESS)] == 2
    assert calls[("effort", ADMINISTRATION)] == 1
    assert calls[("cases", ADMINISTRATION)] == 1
    assert calls[("effort", CITIZENS)] == 1
    assert calls[("cases", CITIZENS)] == 1
    for addressee in (ADMINISTRATION, BUSINESS, CITIZENS):
        assert db.has_effort_metrics(session_id, addressee)
