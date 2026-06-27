import pytest
from fastapi import HTTPException

from backend.core import db
from backend.core.norm_addressees import ADMINISTRATION, CITIZENS
from backend.core.prompts import PromptId
from backend.routers import case_groups as case_groups_router
from backend.routers import effort as effort_router
from backend.routers import process_steps as process_steps_router
from backend.routers import processes as processes_router


def _seed_process_context(app_session_id: str = "PARSER-PROCESSES") -> tuple[int, int, dict]:
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    regulation_id = db.insert_regulation(
        session_id,
        "§ 1",
        "Regelung A",
        applies_to_administration=True,
    )
    _prompt, context = processes_router.build_process_compilation_prompt(
        session_id=session_id,
        norm_addressee=ADMINISTRATION,
    )
    return session_id, regulation_id, context


def _seed_case_group_context(app_session_id: str = "PARSER-CASE-GROUPS") -> tuple[int, int, dict]:
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    process_id = db.insert_process(
        session_id,
        "Prozess A",
        "Beschreibung Prozess",
        norm_addressee=ADMINISTRATION,
    )
    _prompt, context = case_groups_router.build_case_group_development_prompt(
        session_id=session_id,
        norm_addressee=ADMINISTRATION,
    )
    return session_id, process_id, context


def _seed_process_step_context(
    app_session_id: str = "PARSER-STEPS",
) -> tuple[int, int, int, int, dict]:
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    process_id = db.insert_process(
        session_id,
        "Prozess A",
        "Beschreibung Prozess",
        norm_addressee=ADMINISTRATION,
    )
    regulation_id = db.insert_regulation(
        session_id,
        "§ 1",
        "Regelung A",
        process_id=process_id,
        applies_to_administration=True,
    )
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Fallgruppe A",
        "Beschreibung Fallgruppe",
        norm_addressee=ADMINISTRATION,
    )
    _prompt, context = process_steps_router.build_process_step_analysis_prompt(
        session_id=session_id,
        norm_addressee=ADMINISTRATION,
    )
    return session_id, process_id, regulation_id, case_group_id, context


def _seed_effort_context(
    app_session_id: str = "PARSER-EFFORT",
    norm_addressee: str = ADMINISTRATION,
) -> tuple[int, int, int, dict]:
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    process_id = db.insert_process(
        session_id,
        "Prozess A",
        "Beschreibung Prozess",
        norm_addressee=norm_addressee,
    )
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Fallgruppe A",
        "Beschreibung Fallgruppe",
        norm_addressee=norm_addressee,
    )
    step_id = db.insert_process_step(
        session_id,
        case_group_id,
        "Schritt A",
        "Beschreibung Schritt",
        norm_addressee=norm_addressee,
    )
    context = effort_router.prepare_effort_calculation(
        session_id=session_id,
        norm_addressee=norm_addressee,
        skip_cases_calculation=False,
    )
    return session_id, case_group_id, step_id, context


def _cases_payload(case_group_id: int) -> str:
    return f"""
    {{
      "prozesse": [
        {{
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "anzahl_betroffene_vorschlag": "10",
              "haeufigkeit_pro_jahr_vorschlag": "2"
            }}
          ]
        }}
      ]
    }}
    """


def _org_effort_payload(
    case_group_id: int,
    step_id: int,
    *,
    entry_fields: str,
) -> str:
    return f"""
    {{
      "prozesse": [
        {{
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "anzahl_betroffene_vorschlag": "10",
              "haeufigkeit_pro_jahr_vorschlag": "2",
              "taetigkeiten": [
                {{
                  "taetigkeiten_id": "{step_id}",
                  {entry_fields}
                }}
              ]
            }}
          ]
        }}
      ]
    }}
    """


def _parse_effort(
    *,
    session_id: int,
    context: dict,
    cases_text: str,
    effort_text: str,
    norm_addressee: str = ADMINISTRATION,
) -> tuple[list[dict], list[dict]]:
    return effort_router.parse_effort_calculation_outputs(
        session_id=session_id,
        norm_addressee=norm_addressee,
        context=context,
        cases_text=cases_text,
        effort_text=effort_text,
        cases_answer_id=None,
        effort_answer_id=0,
    )


def test_process_parser_accepts_mismatched_text_when_id_matches():
    _session_id, regulation_id, context = _seed_process_context()
    payload = f"""
    {{
      "prozesse": [
        {{
          "prozess_bezeichnung": "Prozess A",
          "prozess_beschreibung": "Beschreibung A",
          "vorgaben": [
            {{"vorgaben_id": "{regulation_id}", "normzitat": "§ X", "beschreibung": "Andere Beschreibung"}}
          ]
        }}
      ]
    }}
    """

    parsed, _fallbacks = processes_router.parse_process_compilation_answer(
        response_text=payload,
        norm_addressee=ADMINISTRATION,
        context=context,
    )

    assert parsed[0]["vorgaben"][0]["vorgaben_id"] == regulation_id


def test_process_parser_accepts_explicit_empty_process_list():
    _session_id, _regulation_id, context = _seed_process_context("PARSER-PROCESSES-EMPTY")

    parsed, _fallbacks = processes_router.parse_process_compilation_answer(
        response_text='{"prozesse": []}',
        norm_addressee=ADMINISTRATION,
        context=context,
    )

    assert parsed == []


def test_process_parser_rejects_unusable_non_empty_process_list():
    _session_id, _regulation_id, context = _seed_process_context("PARSER-PROCESSES-EMPTY-OBJECT")

    with pytest.raises(HTTPException) as exc_info:
        processes_router.parse_process_compilation_answer(
            response_text='{"prozesse": [{}]}',
            norm_addressee=ADMINISTRATION,
            context=context,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "No processes parsed"


def test_process_parser_rejects_duplicate_vorgaben():
    _session_id, regulation_id, context = _seed_process_context()
    payload = f"""
    {{
      "prozesse": [
        {{
          "prozess_bezeichnung": "Prozess A",
          "vorgaben": [{{"vorgaben_id": "{regulation_id}"}}]
        }},
        {{
          "prozess_bezeichnung": "Prozess B",
          "vorgaben": [{{"vorgaben_id": "{regulation_id}"}}]
        }}
      ]
    }}
    """

    with pytest.raises(HTTPException) as exc_info:
        processes_router.parse_process_compilation_answer(
            response_text=payload,
            norm_addressee=ADMINISTRATION,
            context=context,
        )

    assert exc_info.value.status_code == 422
    assert (
        f"Vorgaben mehrfach zu Prozessen zugeordnet: {regulation_id}"
        in exc_info.value.detail
    )


def test_process_parser_rejects_already_linked_regulation():
    _session_id, regulation_id, context = _seed_process_context("PARSER-PROCESSES-LINKED")
    context["regulation_lookup"][regulation_id]["process_id"] = 123
    payload = f"""
    {{
      "prozesse": [
        {{
          "prozess_bezeichnung": "Prozess A",
          "vorgaben": [{{"vorgaben_id": "{regulation_id}"}}]
        }}
      ]
    }}
    """

    with pytest.raises(HTTPException) as exc_info:
        processes_router.parse_process_compilation_answer(
            response_text=payload,
            norm_addressee=ADMINISTRATION,
            context=context,
        )

    assert exc_info.value.status_code == 409
    assert "Regulations already linked" in exc_info.value.detail


def test_case_group_parser_rejects_unknown_process_id():
    _session_id, _process_id, context = _seed_case_group_context()
    payload = """
    {
      "prozesse": [
        {
          "prozess_id": "999",
          "fallgruppen": [
            {
              "fallgruppe_bezeichnung": "Fallgruppe X",
              "fallgruppe_beschreibung": "Beschreibung"
            }
          ]
        }
      ]
    }
    """

    with pytest.raises(HTTPException) as exc_info:
        case_groups_router.parse_case_group_development_answer(
            response_text=payload,
            norm_addressee=ADMINISTRATION,
            context=context,
        )

    assert exc_info.value.status_code == 422
    assert "Unknown process_id values: 999" == exc_info.value.detail


def test_process_step_parser_rejects_unknown_case_group_id():
    _session_id, _process_id, _regulation_id, _case_group_id, context = (
        _seed_process_step_context()
    )
    payload = """
    {
      "prozesse": [
        {
          "fallgruppen": [
            {
              "fallgruppen_id": "999",
              "taetigkeiten": [
                {"taetigkeit": "Schritt X", "beschreibung": "Beschreibung"}
              ]
            }
          ]
        }
      ]
    }
    """

    with pytest.raises(HTTPException) as exc_info:
        process_steps_router.parse_process_step_analysis_answer(
            response_text=payload,
            norm_addressee=ADMINISTRATION,
            context=context,
        )

    assert exc_info.value.status_code == 422
    assert "Unknown fallgruppen_id values: 999" == exc_info.value.detail


def test_process_step_parser_rejects_unknown_regulation_links():
    _session_id, _process_id, _regulation_id, case_group_id, context = (
        _seed_process_step_context("PARSER-STEPS-BAD-LINK")
    )
    payload = f"""
    {{
      "prozesse": [
        {{
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "taetigkeiten": [
                {{
                  "taetigkeit": "Schritt X",
                  "beschreibung": "Beschreibung",
                  "vorgaben_ids": [999]
                }}
              ]
            }}
          ]
        }}
      ]
    }}
    """

    with pytest.raises(HTTPException) as exc_info:
        process_steps_router.parse_process_step_analysis_answer(
            response_text=payload,
            norm_addressee=ADMINISTRATION,
            context=context,
        )

    assert exc_info.value.status_code == 422
    assert "Unknown vorgaben_ids in process steps" in exc_info.value.detail


def test_process_step_parser_keeps_flattened_fallgruppen_fallback():
    _session_id, _process_id, _regulation_id, case_group_id, context = (
        _seed_process_step_context("PARSER-STEPS-FALLBACK")
    )
    payload = f"""
    {{
      "fallgruppen": [
        {{
          "fallgruppen_id": "{case_group_id}",
          "taetigkeiten": [
            {{"taetigkeit": "Schritt X", "beschreibung": "Aus fallback parser"}}
          ]
        }}
      ]
    }}
    """

    parsed, fallback_kinds = process_steps_router.parse_process_step_analysis_answer(
        response_text=payload,
        norm_addressee=ADMINISTRATION,
        context=context,
    )

    assert parsed[0]["case_group_id"] == case_group_id
    assert "process_steps_flattened_fallgruppen" in fallback_kinds


def test_effort_parser_logs_alias_fallbacks(monkeypatch):
    session_id, case_group_id, step_id, context = _seed_effort_context(
        "PARSER-EFFORT-FALLBACK"
    )
    cases_text = f"""
    {{
      "prozesse": [
        {{
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "anzahl_betroffene_current": "10",
              "haeufigkeit_pro_jahr_current": "3",
              "anzahl_betroffene_proposed": "12",
              "haeufigkeit_pro_jahr_proposed": "4"
            }}
          ]
        }}
      ]
    }}
    """
    effort_text = _org_effort_payload(
        case_group_id,
        step_id,
        entry_fields="""
        "personalaufwand_gueltig": [
          {"qualifikation": "einfacher_und_mittlerer_dienst", "lohnquelle": "bund", "zeitaufwand_in_min": "15"}
        ],
        "sachaufwand_current": "5",
        "personalaufwand_vorschlag": [
          {"qualifikation": "einfacher_und_mittlerer_dienst", "lohnquelle": "bund", "zeitaufwand_in_min": "10"}
        ],
        "sachaufwand_proposed": "6"
        """,
    )
    fallback_kinds: list[str] = []

    def fake_mark_llm_parse_fallback(*, fallback_kind, **_kwargs):
        fallback_kinds.append(str(fallback_kind))

    monkeypatch.setattr(
        effort_router,
        "mark_llm_parse_fallback",
        fake_mark_llm_parse_fallback,
    )

    _parse_effort(
        session_id=session_id,
        context=context,
        cases_text=cases_text,
        effort_text=effort_text,
    )

    assert "cases_legacy_english_alias" in fallback_kinds
    assert "effort_legacy_english_alias" in fallback_kinds


def test_effort_parser_rejects_invalid_cases_json_payload():
    session_id, case_group_id, step_id, context = _seed_effort_context(
        "PARSER-EFFORT-BAD-CASES"
    )
    effort_text = _org_effort_payload(
        case_group_id,
        step_id,
        entry_fields="""
        "personalaufwand_vorschlag": [
          {"qualifikation": "einfacher_und_mittlerer_dienst", "lohnquelle": "bund", "zeitaufwand_in_min": "10"}
        ]
        """,
    )

    with pytest.raises(HTTPException) as exc_info:
        _parse_effort(
            session_id=session_id,
            context=context,
            cases_text="kein json vorhanden",
            effort_text=effort_text,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == (
        "Invalid cases_calculation payload: no JSON object found in LLM response"
    )


def test_effort_parser_rejects_unknown_case_group_id():
    session_id, case_group_id, step_id, context = _seed_effort_context(
        "PARSER-EFFORT-UNKNOWN-GROUP"
    )
    effort_text = _org_effort_payload(
        case_group_id,
        step_id,
        entry_fields="""
        "personalaufwand_vorschlag": [
          {"qualifikation": "einfacher_und_mittlerer_dienst", "lohnquelle": "bund", "zeitaufwand_in_min": "10"}
        ]
        """,
    )

    with pytest.raises(HTTPException) as exc_info:
        _parse_effort(
            session_id=session_id,
            context=context,
            cases_text=_cases_payload(999),
            effort_text=effort_text,
        )

    assert exc_info.value.status_code == 422
    assert "Unknown fallgruppen_id values: 999" == exc_info.value.detail


def test_effort_parser_rejects_unknown_step_id():
    session_id, case_group_id, _step_id, context = _seed_effort_context(
        "PARSER-EFFORT-UNKNOWN-STEP"
    )
    effort_text = _org_effort_payload(
        case_group_id,
        999,
        entry_fields="""
        "personalaufwand_vorschlag": [
          {"qualifikation": "einfacher_und_mittlerer_dienst", "lohnquelle": "bund", "zeitaufwand_in_min": "10"}
        ]
        """,
    )

    with pytest.raises(HTTPException) as exc_info:
        _parse_effort(
            session_id=session_id,
            context=context,
            cases_text=_cases_payload(case_group_id),
            effort_text=effort_text,
        )

    assert exc_info.value.status_code == 422
    assert "Unknown taetigkeiten_id values: 999" == exc_info.value.detail


def test_effort_parser_rejects_missing_step_id_after_empty_effort_entry():
    session_id, case_group_id, step_id, _context = _seed_effort_context(
        "PARSER-EFFORT-MISSING-STEP"
    )
    missing_step_id = db.insert_process_step(
        session_id,
        case_group_id,
        "Schritt ohne Aufwand",
        "Beschreibung Schritt ohne Aufwand",
        norm_addressee=ADMINISTRATION,
    )
    context = effort_router.prepare_effort_calculation(
        session_id=session_id,
        norm_addressee=ADMINISTRATION,
        skip_cases_calculation=False,
    )
    effort_text = f"""
    {{
      "prozesse": [
        {{
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "taetigkeiten": [
                {{
                  "taetigkeiten_id": "{step_id}",
                  "personalaufwand_vorschlag": [
                    {{"qualifikation": "einfacher_und_mittlerer_dienst", "lohnquelle": "bund", "zeitaufwand_in_min": "10"}}
                  ]
                }},
                {{
                  "taetigkeiten_id": "{missing_step_id}",
                  "personalaufwand_gueltig": [],
                  "personalaufwand_vorschlag": [],
                  "sachaufwand_gueltig": "",
                  "sachaufwand_vorschlag": ""
                }}
              ]
            }}
          ]
        }}
      ]
    }}
    """

    with pytest.raises(HTTPException) as exc_info:
        _parse_effort(
            session_id=session_id,
            context=context,
            cases_text=_cases_payload(case_group_id),
            effort_text=effort_text,
        )

    assert exc_info.value.status_code == 422
    assert (
        exc_info.value.detail
        == f"Missing effort for taetigkeiten_id values: {missing_step_id}"
    )


def test_effort_parser_rejects_citizens_roles_payload():
    session_id, case_group_id, step_id, context = _seed_effort_context(
        "PARSER-EFFORT-CITIZENS-ROLES",
        norm_addressee=CITIZENS,
    )
    effort_text = _org_effort_payload(
        case_group_id,
        step_id,
        entry_fields="""
        "rollen_gueltig": [
          {"lohngruppe": "a", "zeitaufwand_in_min": "10"}
        ]
        """,
    )

    with pytest.raises(HTTPException) as exc_info:
        _parse_effort(
            session_id=session_id,
            context=context,
            cases_text=_cases_payload(case_group_id),
            effort_text=effort_text,
            norm_addressee=CITIZENS,
        )

    assert exc_info.value.status_code == 422
    assert "Invalid effort_calculation payload for citizens" in exc_info.value.detail
    assert "rollen_gueltig" in exc_info.value.detail


@pytest.mark.parametrize(
    ("app_session_id", "entry_fields", "expected_detail"),
    [
        (
            "PARSER-EFFORT-INVALID-LOHNQUELLE",
            """
            "personalaufwand_gueltig": [
              {"qualifikation": "gehobener_dienst", "lohnquelle": "voellig_ungueltig", "zeitaufwand_in_min": "30"}
            ],
            "personalaufwand_vorschlag": []
            """,
            "lohnquelle",
        ),
        (
            "PARSER-EFFORT-MISSING-LOHNQUELLE",
            """
            "personalaufwand_gueltig": [
              {"qualifikation": "gehobener_dienst", "zeitaufwand_in_min": "30"}
            ],
            "personalaufwand_vorschlag": []
            """,
            "fehlende `lohnquelle`",
        ),
        (
            "PARSER-EFFORT-MISSING-QUALIFIKATION",
            """
            "personalaufwand_gueltig": [
              {"qualifikation": "", "lohnquelle": "bund", "zeitaufwand_in_min": "30"}
            ],
            "personalaufwand_vorschlag": []
            """,
            "ohne `qualifikation`",
        ),
        (
            "PARSER-EFFORT-DUPLICATE-PERSONNEL",
            """
            "personalaufwand_gueltig": [
              {"qualifikation": "gehobener_dienst", "lohnquelle": "bund", "zeitaufwand_in_min": "30"},
              {"qualifikation": "gehobener_dienst", "lohnquelle": "bund", "zeitaufwand_in_min": "10"}
            ],
            "personalaufwand_vorschlag": []
            """,
            "doppelte kombination",
        ),
        (
            "PARSER-EFFORT-SLOT-LETTER",
            """
            "personalaufwand_gueltig": [
              {"qualifikation": "a", "lohnquelle": "bund", "zeitaufwand_in_min": "30"}
            ],
            "personalaufwand_vorschlag": []
            """,
            "unbekannte `qualifikation`",
        ),
        (
            "PARSER-EFFORT-MIXED-LEGACY",
            """
            "personalaufwand_gueltig": [
              {"qualifikation": "gehobener_dienst", "lohnquelle": "bund", "zeitaufwand_in_min": "30"}
            ],
            "stundenlohn_satz_a_vorschlag": "45",
            "zeitaufwand_in_min_a_vorschlag": "20"
            """,
            "stundenlohn_satz",
        ),
        (
            "PARSER-EFFORT-LEGACY-FLAT",
            """
            "stundenlohn_satz_a_gueltig": "40",
            "zeitaufwand_in_min_a_gueltig": "30",
            "stundenlohn_satz_a_vorschlag": "42",
            "zeitaufwand_in_min_a_vorschlag": "25"
            """,
            "stundenlohn_satz",
        ),
        (
            "PARSER-EFFORT-LEGACY-ROLLEN",
            """
            "rollen_gueltig": [
              {"rolle": "Sachbearbeitung", "zeitaufwand_in_min": "10"}
            ],
            "personalaufwand_vorschlag": []
            """,
            "rollen_gueltig",
        ),
    ],
)
def test_effort_parser_rejects_invalid_personnel_effort_rows(
    app_session_id,
    entry_fields,
    expected_detail,
):
    session_id, case_group_id, step_id, context = _seed_effort_context(app_session_id)
    effort_text = _org_effort_payload(
        case_group_id,
        step_id,
        entry_fields=entry_fields,
    )

    with pytest.raises(HTTPException) as exc_info:
        _parse_effort(
            session_id=session_id,
            context=context,
            cases_text=_cases_payload(case_group_id),
            effort_text=effort_text,
        )

    assert exc_info.value.status_code == 422
    assert expected_detail in str(exc_info.value.detail).lower()


def test_effort_parser_keeps_row_personnel_effort_model():
    session_id, case_group_id, step_id, context = _seed_effort_context(
        "PARSER-EFFORT-ROWS"
    )
    effort_text = _org_effort_payload(
        case_group_id,
        step_id,
        entry_fields="""
        "personalaufwand_gueltig": [
          {"qualifikation": "einfacher_und_mittlerer_dienst", "lohnquelle": "bund", "zeitaufwand_in_min": "15"},
          {"qualifikation": "gehobener_dienst", "lohnquelle": "laender", "zeitaufwand_in_min": "10"}
        ],
        "personalaufwand_vorschlag": [
          {"qualifikation": "hoeherer_dienst", "lohnquelle": "bund", "zeitaufwand_in_min": "8"}
        ],
        "sachaufwand_vorschlag": "6"
        """,
    )

    _parsed_cases, parsed_effort = _parse_effort(
        session_id=session_id,
        context=context,
        cases_text=_cases_payload(case_group_id),
        effort_text=effort_text,
    )

    rows = parsed_effort[0]["personnel_effort_rows"]
    assert [
        (row["period"], row["qualification"], row["wage_source_value"])
        for row in rows
    ] == [
        ("current", "einfacher_und_mittlerer_dienst", "bund"),
        ("current", "gehobener_dienst", "laender"),
        ("proposed", "hoeherer_dienst", "bund"),
    ]
    assert parsed_effort[0]["time_required_current"]["a"] == 15
    assert parsed_effort[0]["time_required_current"]["b"] == 10
    assert parsed_effort[0]["time_required_proposed"]["c"] == 8
    assert parsed_effort[0]["hourly_rates_current"]["a"] is not None


def test_process_step_parser_rejects_duplicate_case_group_id():
    # #13/#25: Dieselbe fallgruppen_id unter zwei Prozessen -> zwei Step-Ketten
    # fuer eine Fallgruppe -> 422 vor der Persistenz statt stillem
    # last-write-wins.
    _session_id, _process_id, _regulation_id, case_group_id, context = (
        _seed_process_step_context("PARSER-STEPS-DUP-FALLGRUPPE")
    )
    payload = f"""
    {{
      "prozesse": [
        {{
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "taetigkeiten": [
                {{"taetigkeit": "Schritt A", "beschreibung": "Erste Kette"}}
              ]
            }}
          ]
        }},
        {{
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "taetigkeiten": [
                {{"taetigkeit": "Schritt B", "beschreibung": "Zweite Kette"}}
              ]
            }}
          ]
        }}
      ]
    }}
    """

    with pytest.raises(HTTPException) as exc_info:
        process_steps_router.parse_process_step_analysis_answer(
            response_text=payload,
            norm_addressee=ADMINISTRATION,
            context=context,
        )

    assert exc_info.value.status_code == 422
    assert "Duplicate fallgruppen_id values" in exc_info.value.detail
    assert str(case_group_id) in exc_info.value.detail


def test_effort_parser_rejects_duplicate_case_group_id():
    # #13/#25: Dieselbe fallgruppen_id zweimal in den Kennzahlen -> 422 statt
    # stillem last-write-wins-Ueberschreiben.
    session_id, case_group_id, step_id, context = _seed_effort_context(
        "PARSER-EFFORT-DUP-GROUP"
    )
    cases_text = f"""
    {{
      "prozesse": [
        {{
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "anzahl_betroffene_vorschlag": "10",
              "haeufigkeit_pro_jahr_vorschlag": "2"
            }},
            {{
              "fallgruppen_id": "{case_group_id}",
              "anzahl_betroffene_vorschlag": "12",
              "haeufigkeit_pro_jahr_vorschlag": "2"
            }}
          ]
        }}
      ]
    }}
    """
    effort_text = _org_effort_payload(
        case_group_id,
        step_id,
        entry_fields="""
        "personalaufwand_vorschlag": [
          {"qualifikation": "einfacher_und_mittlerer_dienst", "lohnquelle": "bund", "zeitaufwand_in_min": "10"}
        ]
        """,
    )

    with pytest.raises(HTTPException) as exc_info:
        _parse_effort(
            session_id=session_id,
            context=context,
            cases_text=cases_text,
            effort_text=effort_text,
        )

    assert exc_info.value.status_code == 422
    assert "Duplicate fallgruppen_id values" in exc_info.value.detail
    assert str(case_group_id) in exc_info.value.detail


def test_effort_parser_rejects_missing_case_group_metrics():
    # #13/#25: Jede Fallgruppe des Normadressaten muss Kennzahlen erhalten;
    # fehlt eine, 422 statt spaeter blockierendem effort_ready.
    session_id, _ = db.upsert_session("PARSER-EFFORT-MISSING-GROUP", "test-model")
    process_id = db.insert_process(
        session_id, "Prozess A", "Beschreibung Prozess", norm_addressee=ADMINISTRATION
    )
    case_group_one = db.insert_case_group(
        session_id, process_id, "Fallgruppe A", "Beschreibung Fallgruppe",
        norm_addressee=ADMINISTRATION,
    )
    case_group_two = db.insert_case_group(
        session_id, process_id, "Fallgruppe B", "Beschreibung Fallgruppe",
        norm_addressee=ADMINISTRATION,
    )
    step_id = db.insert_process_step(
        session_id, case_group_one, "Schritt A", "Beschreibung Schritt",
        norm_addressee=ADMINISTRATION,
    )
    context = effort_router.prepare_effort_calculation(
        session_id=session_id,
        norm_addressee=ADMINISTRATION,
        skip_cases_calculation=False,
    )
    effort_text = _org_effort_payload(
        case_group_one,
        step_id,
        entry_fields="""
        "personalaufwand_vorschlag": [
          {"qualifikation": "einfacher_und_mittlerer_dienst", "lohnquelle": "bund", "zeitaufwand_in_min": "10"}
        ]
        """,
    )

    with pytest.raises(HTTPException) as exc_info:
        _parse_effort(
            session_id=session_id,
            context=context,
            cases_text=_cases_payload(case_group_one),
            effort_text=effort_text,
        )

    assert exc_info.value.status_code == 422
    assert "Missing metrics for fallgruppen_id values" in exc_info.value.detail
    assert str(case_group_two) in exc_info.value.detail


def test_effort_parser_rejects_duplicate_step_id():
    # #13/#25: Dieselbe taetigkeiten_id zweimal in den Aufwandswerten -> 422.
    session_id, case_group_id, step_id, context = _seed_effort_context(
        "PARSER-EFFORT-DUP-STEP"
    )
    effort_text = f"""
    {{
      "prozesse": [
        {{
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "anzahl_betroffene_vorschlag": "10",
              "haeufigkeit_pro_jahr_vorschlag": "2",
              "taetigkeiten": [
                {{
                  "taetigkeiten_id": "{step_id}",
                  "personalaufwand_vorschlag": [
                    {{"qualifikation": "einfacher_und_mittlerer_dienst", "lohnquelle": "bund", "zeitaufwand_in_min": "10"}}
                  ]
                }},
                {{
                  "taetigkeiten_id": "{step_id}",
                  "personalaufwand_vorschlag": [
                    {{"qualifikation": "gehobener_dienst", "lohnquelle": "laender", "zeitaufwand_in_min": "12"}}
                  ]
                }}
              ]
            }}
          ]
        }}
      ]
    }}
    """

    with pytest.raises(HTTPException) as exc_info:
        _parse_effort(
            session_id=session_id,
            context=context,
            cases_text=_cases_payload(case_group_id),
            effort_text=effort_text,
        )

    assert exc_info.value.status_code == 422
    assert "Duplicate taetigkeiten_id values" in exc_info.value.detail
    assert str(step_id) in exc_info.value.detail


def test_effort_parser_rejects_missing_step_effort():
    # #13/#25: Jeder Schritt des Normadressaten muss einen Aufwandswert
    # erhalten; fehlt einer, 422 (symmetrisch zu den Fallgruppen).
    session_id, _ = db.upsert_session("PARSER-EFFORT-MISSING-STEP", "test-model")
    process_id = db.insert_process(
        session_id, "Prozess A", "Beschreibung Prozess", norm_addressee=ADMINISTRATION
    )
    case_group_id = db.insert_case_group(
        session_id, process_id, "Fallgruppe A", "Beschreibung Fallgruppe",
        norm_addressee=ADMINISTRATION,
    )
    step_one = db.insert_process_step(
        session_id, case_group_id, "Schritt A", "Beschreibung Schritt",
        norm_addressee=ADMINISTRATION,
    )
    step_two = db.insert_process_step(
        session_id, case_group_id, "Schritt B", "Beschreibung Schritt",
        norm_addressee=ADMINISTRATION,
    )
    context = effort_router.prepare_effort_calculation(
        session_id=session_id,
        norm_addressee=ADMINISTRATION,
        skip_cases_calculation=False,
    )
    effort_text = _org_effort_payload(
        case_group_id,
        step_one,
        entry_fields="""
        "personalaufwand_vorschlag": [
          {"qualifikation": "einfacher_und_mittlerer_dienst", "lohnquelle": "bund", "zeitaufwand_in_min": "10"}
        ]
        """,
    )

    with pytest.raises(HTTPException) as exc_info:
        _parse_effort(
            session_id=session_id,
            context=context,
            cases_text=_cases_payload(case_group_id),
            effort_text=effort_text,
        )

    assert exc_info.value.status_code == 422
    assert "Missing effort for taetigkeiten_id values" in exc_info.value.detail
    assert str(step_two) in exc_info.value.detail


def test_process_step_parser_rejects_missing_case_group():
    # #13/#25: Schritt 5 muss zu JEDER Fallgruppe des Normadressaten Schritte
    # liefern; laesst die KI eine aus, 422 vor der Persistenz
    # (Schritt-5-Vollstaendigkeit, die Schritt 6 nicht zuverlaessig auffaengt).
    session_id, process_id, _regulation_id, case_group_id, _context = (
        _seed_process_step_context("PARSER-STEPS-MISSING-FALLGRUPPE")
    )
    second_case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Fallgruppe B",
        "Beschreibung Fallgruppe B",
        norm_addressee=ADMINISTRATION,
    )
    # Kontext neu bauen, damit die zweite Fallgruppe im case_group_lookup steht.
    _prompt, context = process_steps_router.build_process_step_analysis_prompt(
        session_id=session_id,
        norm_addressee=ADMINISTRATION,
    )
    payload = f"""
    {{
      "prozesse": [
        {{
          "fallgruppen": [
            {{
              "fallgruppen_id": "{case_group_id}",
              "taetigkeiten": [
                {{"taetigkeit": "Schritt A", "beschreibung": "Nur erste Fallgruppe"}}
              ]
            }}
          ]
        }}
      ]
    }}
    """

    with pytest.raises(HTTPException) as exc_info:
        process_steps_router.parse_process_step_analysis_answer(
            response_text=payload,
            norm_addressee=ADMINISTRATION,
            context=context,
        )

    assert exc_info.value.status_code == 422
    assert "Missing process steps for fallgruppen_id values" in exc_info.value.detail
    assert str(second_case_group_id) in exc_info.value.detail
