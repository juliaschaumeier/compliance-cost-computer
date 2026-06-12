import json

from backend.core import db
from backend.core.models import Tile
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS
from backend.routers import (
    case_groups as case_groups_router,
    effort as effort_router,
    process_steps as process_steps_router,
    processes as processes_router,
)


def _is_effort_prompt(prompt: str) -> bool:
    return "prozessschritte differenziert werden" in prompt.lower()


def _seed_regulation_tile(session_id: int, regulation_id: int, title: str, addressee: str) -> None:
    db.upsert_tile(
        Tile(
            id=f"regulation_{regulation_id}",
            title=title,
            text="",
            meta_information={"regulation_id": regulation_id},
            column=1,
            row=0,
            deletable=True,
            link_from_tile=[],
        ),
        session_id=session_id,
        norm_addressee=addressee,
    )


def _run_addressee_flow(test_client, monkeypatch, app_session_id: str, addressee: str) -> dict:
    session_id = db.get_session_id_by_app_id(app_session_id)
    assert session_id is not None

    regulation_kwargs = {
        "applies_to_administration": addressee == ADMINISTRATION,
        "applies_to_business": addressee == BUSINESS,
        "applies_to_citizens": addressee == CITIZENS,
        "is_business_information_obligation": addressee == BUSINESS,
    }
    regulation_id = db.insert_regulation(
        session_id,
        f"§ {addressee}",
        f"Vorgabe {addressee}",
        **regulation_kwargs,
    )
    _seed_regulation_tile(session_id, regulation_id, f"Regulation {addressee}", addressee)

    async def fake_processes_llm(*_args, **_kwargs):
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_bezeichnung": f"Prozess {addressee}",
                        "prozess_beschreibung": f"Beschreibung Prozess {addressee}",
                        "vorgaben": [
                            {
                                "vorgaben_id": str(regulation_id),
                                "normzitat": f"§ {addressee}",
                                "beschreibung": f"Vorgabe {addressee}",
                            }
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr(processes_router, "query_llm", fake_processes_llm)
    compile_resp = test_client.post(
        "/processes/compile",
        json={
            "app_session_id": app_session_id,
            "model": "test-model",
            "provider": "openai",
            "norm_addressee": addressee,
        },
    )
    assert compile_resp.status_code == 200

    process = db.list_processes_for_session_and_addressee(session_id, addressee)[0]

    async def fake_case_groups_llm(*_args, **_kwargs):
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

    monkeypatch.setattr(case_groups_router, "query_llm", fake_case_groups_llm)
    case_resp = test_client.post(
        "/case-groups/develop",
        json={
            "app_session_id": app_session_id,
            "model": "test-model",
            "provider": "openai",
            "norm_addressee": addressee,
        },
    )
    assert case_resp.status_code == 200

    case_group = db.list_case_groups_for_session_and_addressee(session_id, addressee)[0]

    async def fake_steps_llm(*_args, **_kwargs):
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_id": str(process["process_id"]),
                        "fallgruppen": [
                            {
                                "fallgruppen_id": str(case_group["case_group_id"]),
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

    monkeypatch.setattr(process_steps_router, "query_llm", fake_steps_llm)
    steps_resp = test_client.post(
        "/process-steps/analyze",
        json={
            "app_session_id": app_session_id,
            "model": "test-model",
            "provider": "openai",
            "norm_addressee": addressee,
        },
    )
    assert steps_resp.status_code == 200

    step = db.list_process_steps_for_session_and_addressee(session_id, addressee)[0]

    async def fake_effort_llm(prompt, *_args, **_kwargs):
        if not _is_effort_prompt(prompt):
            return json.dumps(
                {
                    "prozesse": [
                        {
                            "prozess_id": str(process["process_id"]),
                            "fallgruppen": [
                                {
                                    "fallgruppen_id": str(case_group["case_group_id"]),
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
                "taetigkeiten_id": str(step["step_id"]),
                "taetigkeit": step["step"],
                "beschreibung": step["description"],
                "zeitaufwand_in_min_vorschlag": "30",
                "sachaufwand_vorschlag": "10",
            }
        else:
            # Row-based contract: the LLM returns only qualifikation + lohnquelle +
            # time; the backend resolves the wage from the table
            # (admin/bund/einfacher_und_mittlerer_dienst = 33.8,
            # business/gesamtwirtschaft/niedrig = 26.1).
            qualifikation, lohnquelle = (
                ("niedrig", "gesamtwirtschaft")
                if addressee == BUSINESS
                else ("einfacher_und_mittlerer_dienst", "bund")
            )
            effort_entry = {
                "taetigkeiten_id": str(step["step_id"]),
                "taetigkeit": step["step"],
                "beschreibung": step["description"],
                "personalaufwand_vorschlag": [
                    {
                        "qualifikation": qualifikation,
                        "lohnquelle": lohnquelle,
                        "zeitaufwand_in_min": "30",
                    }
                ],
                "sachaufwand_vorschlag": "10",
            }
        return json.dumps(
            {
                "prozesse": [
                    {
                        "prozess_id": str(process["process_id"]),
                        "fallgruppen": [
                            {
                                "fallgruppen_id": str(case_group["case_group_id"]),
                                "taetigkeiten": [effort_entry],
                            }
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr(effort_router, "query_llm", fake_effort_llm)
    effort_resp = test_client.post(
        "/effort/calculate",
        json={
            "app_session_id": app_session_id,
            "model": "test-model",
            "provider": "openai",
            "norm_addressee": addressee,
        },
    )
    assert effort_resp.status_code == 200
    effort_payload = effort_resp.json()
    assert effort_payload["case_groups_updated"] == 1
    assert effort_payload["steps_updated"] == 1

    cost_resp = test_client.post(
        "/costs/compute",
        json={"app_session_id": app_session_id, "norm_addressee": addressee},
    )
    assert cost_resp.status_code == 200
    cost_payload = cost_resp.json()

    if addressee == ADMINISTRATION:
        # (33.8 * 30/60 + 10 Sachaufwand) * (10 * 2 Faelle) = 26.9 * 20 = 538.0
        assert cost_payload["total_cost"] == 538.0
        assert cost_payload["bureaucracy_cost"] is None
        assert cost_payload["total_time_minutes"] is None
    elif addressee == BUSINESS:
        # (26.1 * 30/60 + 10 Sachaufwand) * (10 * 2 Faelle) = 23.05 * 20 = 461.0
        assert cost_payload["total_cost"] == 461.0
        assert cost_payload["bureaucracy_cost"] == 461.0
        assert cost_payload["other_cost"] == 0.0
    else:
        assert cost_payload["total_cost"] is None
        assert cost_payload["total_time_minutes"] == 600.0
        assert cost_payload["total_expenses"] == 200.0

    tiles = db.fetch_tiles(session_id=session_id, norm_addressee=addressee)
    assert any(tile.id == f"process_{process['process_id']}" for tile in tiles)
    assert any(tile.id == f"case_group_{case_group['case_group_id']}" for tile in tiles)
    assert any(tile.id == f"step_{step['step_id']}" for tile in tiles)
    assert any(tile.id == "total_cost" for tile in tiles)

    return {
        "regulation_id": regulation_id,
        "process_id": process["process_id"],
        "case_group_id": case_group["case_group_id"],
        "step_id": step["step_id"],
        "cost_payload": cost_payload,
    }


def test_all_norm_addressees_run_full_flow_and_update_status_maps(test_client, monkeypatch):
    app_session_id = "ALL-ADDRESSEES-INTEGRATION"
    session_id, _ = db.upsert_session(app_session_id, "test-model")

    results = {
        addressee: _run_addressee_flow(test_client, monkeypatch, app_session_id, addressee)
        for addressee in (ADMINISTRATION, BUSINESS, CITIZENS)
    }

    assert db.list_processes_for_session_and_addressee(session_id, ADMINISTRATION)
    assert db.list_processes_for_session_and_addressee(session_id, BUSINESS)
    assert db.list_processes_for_session_and_addressee(session_id, CITIZENS)

    admin_reg = db.list_regulations_for_session_and_addressee(session_id, ADMINISTRATION)
    business_reg = db.list_regulations_for_session_and_addressee(session_id, BUSINESS)
    citizens_reg = db.list_regulations_for_session_and_addressee(session_id, CITIZENS)
    assert {row["regulation_id"] for row in admin_reg} == {results[ADMINISTRATION]["regulation_id"]}
    assert {row["regulation_id"] for row in business_reg} == {results[BUSINESS]["regulation_id"]}
    assert {row["regulation_id"] for row in citizens_reg} == {results[CITIZENS]["regulation_id"]}

    status_resp = test_client.get(
        "/sessions/status",
        params={"app_session_id": app_session_id},
    )
    assert status_resp.status_code == 200
    status = status_resp.json()
    assert status["processes_ready_by_addressee"] == {
        ADMINISTRATION: True,
        BUSINESS: True,
        CITIZENS: True,
    }
    assert status["case_groups_ready_by_addressee"] == {
        ADMINISTRATION: True,
        BUSINESS: True,
        CITIZENS: True,
    }
    assert status["process_steps_ready_by_addressee"] == {
        ADMINISTRATION: True,
        BUSINESS: True,
        CITIZENS: True,
    }
    assert status["effort_ready_by_addressee"] == {
        ADMINISTRATION: True,
        BUSINESS: True,
        CITIZENS: True,
    }
    assert status["total_cost_ready_by_addressee"] == {
        ADMINISTRATION: True,
        BUSINESS: True,
        CITIZENS: True,
    }
