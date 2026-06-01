from backend.core import db
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS


def test_pay_rate_defaults_contains_all_administration_levels():
    # list_pay_rate_defaults liefert per Default NUR administration-Zeilen
    # (source_value als administration_level aliased), keine WZ-Abschnitte.
    levels = {
        str(row.get("administration_level") or "").strip().lower()
        for row in db.list_pay_rate_defaults()
    }
    assert {
        "bund",
        "laender",
        "kommunen",
        "sozialversicherung",
        "durchschnitt",
    } <= levels
    # WZ-Abschnitte duerfen hier NICHT als gueltige Verwaltungs-Level auftauchen.
    assert "k" not in levels
    assert "gesamtwirtschaft" not in levels


def test_list_pay_rate_defaults_business_returns_section_rows():
    sources = {
        str(row.get("administration_level") or "").strip()
        for row in db.list_pay_rate_defaults(BUSINESS)
    }
    assert {"K", "gesamtwirtschaft"} <= sources
    # Verwaltungsebenen duerfen hier nicht auftauchen.
    assert "bund" not in sources


def test_resolve_pay_rate_defaults_for_laender():
    rates = db.get_default_pay_rates_for_addressee(
        ADMINISTRATION, source_value="laender"
    )
    assert rates == {"a": 30.5, "b": 43.2, "c": 69.3, "d": 46.7}


def test_resolve_pay_rate_defaults_admin_fallback_to_bund():
    # Unbekannte administration-source faellt auf Bund zurueck.
    assert db.get_default_pay_rates_for_addressee(
        ADMINISTRATION, source_value="ZZZ"
    ) == {"a": 33.8, "b": 40.4, "c": 67.6, "d": 44.4}


def test_resolve_business_section_defaults_known_and_fallback():
    assert db.get_default_pay_rates_for_addressee(BUSINESS, source_value="K") == {
        "a": 29.0,
        "b": 54.4,
        "c": 93.1,
        "d": 57.9,
    }
    assert db.get_default_pay_rates_for_addressee(
        BUSINESS, source_value="gesamtwirtschaft"
    ) == {
        "a": 26.1,
        "b": 37.1,
        "c": 62.4,
        "d": 38.6,
    }
    # Unbekanntes Label faellt auf Gesamtwirtschaft zurueck.
    assert db.get_default_pay_rates_for_addressee(BUSINESS, source_value="ZZZ") == {
        "a": 26.1,
        "b": 37.1,
        "c": 62.4,
        "d": 38.6,
    }
    # Fehlendes Label (None) ebenfalls -> Gesamtwirtschaft.
    assert db.get_default_pay_rates_for_addressee(BUSINESS, source_value=None) == {
        "a": 26.1,
        "b": 37.1,
        "c": 62.4,
        "d": 38.6,
    }


def _seed_session_with_used_row(norm_addressee, source_value, hourly_rates):
    session_id, case_group_id = _seed_session(norm_addressee)
    _persist_step(
        session_id,
        case_group_id,
        norm_addressee,
        hourly_rates=hourly_rates,
        role_sources=[
            {
                "slot": slot,
                "role": "",
                "source_kind": "x",
                "source_value": source_value,
            }
            for slot in hourly_rates
            if hourly_rates[slot] is not None
        ],
    )
    return session_id


def test_session_pay_rates_admin_uses_full_level_row():
    session_id = _seed_session_with_used_row(
        ADMINISTRATION,
        "laender",
        {"a": 35.0, "b": 42.0, "c": None, "d": None},
    )
    pay_rates = db.get_session_pay_rates_for_addressee(session_id, ADMINISTRATION)
    assert pay_rates is not None
    assert pay_rates["administration_level"] == "laender"
    # Vollstaendige Laender-Zeile aus Stammdaten (kein Bund-d, keine gemischte Zeile).
    assert pay_rates["defaults"] == {"a": 30.5, "b": 43.2, "c": 69.3, "d": 46.7}
    assert pay_rates["wage_source_label"] is None


def test_session_pay_rates_business_uses_full_section_row():
    session_id = _seed_session_with_used_row(
        BUSINESS,
        "K",
        {"a": None, "b": None, "c": 51.0, "d": None},
    )
    pay_rates = db.get_session_pay_rates_for_addressee(session_id, BUSINESS)
    assert pay_rates is not None
    assert pay_rates["wage_source_label"] == "K"
    assert pay_rates["defaults"] == {"a": 29.0, "b": 54.4, "c": 93.1, "d": 57.9}


def _seed_session(norm_addressee):
    app_id = f"WAGE-BASELINE-{norm_addressee.upper()}"
    session_id, _ = db.upsert_session(app_id, "test-model")
    process_id = db.insert_process(
        session_id, "Prozess", "Beschreibung", norm_addressee=norm_addressee
    )
    case_group_id = db.insert_case_group(
        session_id, process_id, "Fallgruppe", "Beschreibung", norm_addressee=norm_addressee
    )
    return session_id, case_group_id


def _persist_step(session_id, case_group_id, norm_addressee, *, hourly_rates, role_sources):
    step_id = db.insert_process_step(
        session_id, case_group_id, "Schritt", "Beschreibung", norm_addressee=norm_addressee
    )
    db.upsert_process_step_effort_split_by_addressee(
        session_id=session_id,
        step_id=step_id,
        norm_addressee=norm_addressee,
        hourly_rates_current=hourly_rates,
        time_required_current={"a": None, "b": None, "c": None, "d": None},
        expenses_current=None,
        hourly_rates_proposed=hourly_rates,
        time_required_proposed={"a": None, "b": None, "c": None, "d": None},
        expenses_proposed=None,
        role_sources_current=role_sources,
        role_sources_proposed=role_sources,
    )
    return step_id


def test_baseline_returns_dominant_label_for_administration():
    session_id, case_group_id = _seed_session(ADMINISTRATION)
    _persist_step(
        session_id,
        case_group_id,
        ADMINISTRATION,
        hourly_rates={"a": 35.0, "b": 42.0, "c": None, "d": None},
        role_sources=[
            {"slot": "a", "role": "", "source_kind": "verwaltungsebene", "source_value": "laender"},
            {"slot": "b", "role": "", "source_kind": "verwaltungsebene", "source_value": "laender"},
        ],
    )

    assert db.get_used_wage_baseline(session_id, ADMINISTRATION) == "laender"


def test_baseline_returns_dominant_label_for_business():
    session_id, case_group_id = _seed_session(BUSINESS)
    _persist_step(
        session_id,
        case_group_id,
        BUSINESS,
        hourly_rates={"a": None, "b": None, "c": 51.0, "d": None},
        role_sources=[
            {"slot": "c", "role": "", "source_kind": "wirtschaftsabschnitt", "source_value": "K"},
        ],
    )

    assert db.get_used_wage_baseline(session_id, BUSINESS) == "K"


def test_baseline_returns_none_without_role_sources():
    session_id, case_group_id = _seed_session(ADMINISTRATION)
    _persist_step(
        session_id,
        case_group_id,
        ADMINISTRATION,
        hourly_rates={"a": 35.0, "b": None, "c": None, "d": None},
        role_sources=None,
    )

    assert db.get_used_wage_baseline(session_id, ADMINISTRATION) is None


def test_baseline_picks_dominant_row_on_mixed_sources():
    session_id, case_group_id = _seed_session(BUSINESS)
    # Zwei Schritte mit "R", einer mit "K" -> "R" dominiert.
    _persist_step(
        session_id,
        case_group_id,
        BUSINESS,
        hourly_rates={"a": None, "b": 32.2, "c": None, "d": None},
        role_sources=[
            {"slot": "b", "role": "", "source_kind": "wirtschaftsabschnitt", "source_value": "R"},
        ],
    )
    _persist_step(
        session_id,
        case_group_id,
        BUSINESS,
        hourly_rates={"a": None, "b": 32.2, "c": None, "d": None},
        role_sources=[
            {"slot": "b", "role": "", "source_kind": "wirtschaftsabschnitt", "source_value": "R"},
        ],
    )
    _persist_step(
        session_id,
        case_group_id,
        BUSINESS,
        hourly_rates={"a": None, "b": None, "c": 51.0, "d": None},
        role_sources=[
            {"slot": "c", "role": "", "source_kind": "wirtschaftsabschnitt", "source_value": "K"},
        ],
    )

    assert db.get_used_wage_baseline(session_id, BUSINESS) == "R"
