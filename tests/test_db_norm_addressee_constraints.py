import inspect
import re
import sqlite3
from pathlib import Path

import pytest

from backend.core import config, db
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS


def test_db_module_uses_constants_not_hardcoded_norm_addressee_literals():
    """Regression: db.py muss norm_addressee-Vergleiche über die Konstanten
    ADMINISTRATION/BUSINESS/CITIZENS machen, nicht über hardcoded Strings.
    Inkonsistente Nutzung führte bereits dazu, dass der Citizens-Guard
    fragil gegen Konstanten-Umbenennung wurde. SQL-String-Literale
    (Trigger, CHECK-Constraints) sind erlaubt — nur Python-Vergleiche
    sind hier im Fokus."""
    source = Path(inspect.getfile(db)).read_text(encoding="utf-8")
    forbidden_patterns = [
        r'==\s*"administration"',
        r"==\s*'administration'",
        r'==\s*"business"',
        r"==\s*'business'",
        r'==\s*"citizens"',
        r"==\s*'citizens'",
        r'!=\s*"administration"',
        r"!=\s*'administration'",
        r'!=\s*"business"',
        r"!=\s*'business'",
        r'!=\s*"citizens"',
        r"!=\s*'citizens'",
    ]
    offenders = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for pattern in forbidden_patterns:
            if re.search(pattern, line):
                offenders.append(f"{lineno}: {stripped}")
                break
    assert not offenders, (
        "Hardcoded norm_addressee string literals in db.py. Use the "
        "ADMINISTRATION/BUSINESS/CITIZENS constants instead:\n"
        + "\n".join(offenders)
    )


def test_pragma_foreign_keys_is_enabled_on_every_fresh_connection(tmp_path, monkeypatch):
    """Defense in depth: _open_connection muss PRAGMA foreign_keys=ON
    ausnahmslos setzen, sonst sind Cascade-Regeln wirkungslos."""
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "test.db")
    db.init_db()
    conn = db.get_conn()
    try:
        value = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert value == 1


    finally:
        conn.close()
    # Frische Verbindung erzeugen, ebenfalls FK an
    fresh = db._open_connection()
    try:
        assert fresh.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        fresh.close()


def test_session_delete_cascades_regulations_and_processes(tmp_path, monkeypatch):
    """Systemkritisch: Loeschen einer Session muss alle abhaengigen
    Rows (Regulations, Prozesse, Fallgruppen, Steps) per Cascade
    entfernen. Verwaiste Rows wuerden spaetere Kostenberechnungen
    kontaminieren."""
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "test.db")
    db.init_db()
    session_id, _ = db.upsert_session("CASCADE-DELETE", "test-model")
    regulation_id = db.insert_regulation(
        session_id,
        "§ 1",
        "Vorgabe",
        applies_to_administration=True,
        applies_to_business=True,
    )
    process_id = db.insert_process(
        session_id, "Prozess", "Beschreibung", norm_addressee=ADMINISTRATION
    )
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Fallgruppe",
        "Beschreibung",
        norm_addressee=ADMINISTRATION,
    )
    step_id = db.insert_process_step(
        session_id,
        case_group_id,
        "Schritt",
        "Beschreibung",
        norm_addressee=ADMINISTRATION,
    )
    assert regulation_id and process_id and case_group_id and step_id

    conn = db.get_conn()
    try:
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM regulations WHERE session_id = ?", (session_id,)
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM processes WHERE session_id = ?", (session_id,)
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM case_groups WHERE session_id = ?", (session_id,)
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM process_steps WHERE session_id = ?", (session_id,)
            ).fetchone()[0]
            == 0
        )
    finally:
        conn.close()


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "test.db")
    db.init_db()
    session_id, _ = db.upsert_session("FK-CHECK", "test-model")
    process_id = db.insert_process(session_id, "Prozess A", "Beschreibung Prozess")
    case_group_id = db.insert_case_group(
        session_id, process_id, "Fallgruppe A", "Beschreibung Fallgruppe"
    )
    step_id = db.insert_process_step(
        session_id, case_group_id, "Schritt A", "Beschreibung Schritt A"
    )
    regulation_id = db.insert_regulation(session_id, "§ 1", "Beschreibung Vorgabe")
    conn = db.get_conn()
    try:
        yield {
            "conn": conn,
            "session_id": session_id,
            "process_id": process_id,
            "case_group_id": case_group_id,
            "step_id": step_id,
            "regulation_id": regulation_id,
        }
    finally:
        conn.close()


def test_processes_reject_invalid_norm_addressee(seeded_db):
    conn = seeded_db["conn"]
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO processes (
                session_id,
                norm_addressee,
                process,
                description,
                change_status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                seeded_db["session_id"],
                "invalid",
                "Fehlerprozess",
                "Beschreibung",
                "neu",
            ),
        )


def test_regulation_process_links_require_matching_session_and_addressee(seeded_db):
    conn = seeded_db["conn"]
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO regulation_process_links_by_addressee (
                session_id,
                norm_addressee,
                regulation_id,
                process_id
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                seeded_db["session_id"],
                "business",
                seeded_db["regulation_id"],
                seeded_db["process_id"],
            ),
        )


def test_update_regulation_process_links_and_lists_by_addressee(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "addressee_links.db")
    db.init_db()

    session_id, _ = db.upsert_session("ADDRESSEE-LINKS", "test-model")
    regulation_id = db.insert_regulation(
        session_id,
        "§ 2",
        "Beschreibung Vorgabe B",
        applies_to_administration=True,
        applies_to_business=True,
        applies_to_citizens=False,
    )
    admin_process_id = db.insert_process(
        session_id,
        "Verwaltungsprozess",
        "Beschreibung Verwaltung",
        norm_addressee="administration",
    )
    business_process_id = db.insert_process(
        session_id,
        "Wirtschaftsprozess",
        "Beschreibung Wirtschaft",
        norm_addressee="business",
    )

    assert db.update_regulation_process(regulation_id, business_process_id, "business") is True
    assert db.update_regulation_process(regulation_id, business_process_id, "business") is False
    assert db.update_regulation_process(regulation_id, admin_process_id, "administration") is True

    admin_rows = db.list_regulations_for_session_and_addressee(session_id, "administration")
    business_rows = db.list_regulations_for_session_and_addressee(session_id, "business")
    citizens_rows = db.list_regulations_for_session_and_addressee(session_id, "citizens")

    assert len(admin_rows) == 1
    assert admin_rows[0]["regulation_id"] == regulation_id
    assert admin_rows[0]["process_id"] == admin_process_id

    assert len(business_rows) == 1
    assert business_rows[0]["regulation_id"] == regulation_id
    assert business_rows[0]["process_id"] == business_process_id

    assert citizens_rows == []

    conn = db.get_conn()
    try:
        stored_links = conn.execute(
            """
            SELECT session_id, norm_addressee, regulation_id, process_id
            FROM regulation_process_links_by_addressee
            ORDER BY norm_addressee, regulation_id
            """
        ).fetchall()
    finally:
        conn.close()

    assert [tuple(row) for row in stored_links] == [
        (session_id, "business", regulation_id, business_process_id)
    ]


def test_citizens_effort_rejects_hourly_rates(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "citizens_rates.db")
    db.init_db()

    session_id, _ = db.upsert_session("CITIZENS-RATES", "test-model")
    process_id = db.insert_process(
        session_id,
        "Buergerprozess",
        "Beschreibung",
        norm_addressee=CITIZENS,
    )
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Fallgruppe",
        "Beschreibung",
        norm_addressee=CITIZENS,
    )
    step_id = db.insert_process_step(
        session_id,
        case_group_id,
        "Schritt",
        "Beschreibung",
        norm_addressee=CITIZENS,
    )

    with pytest.raises(ValueError, match="must not persist hourly rates"):
        db.upsert_process_step_effort_split_by_addressee(
            session_id=session_id,
            step_id=step_id,
            norm_addressee=CITIZENS,
            hourly_rates_current={"a": 20, "b": None, "c": None, "d": None},
            time_required_current={"a": 5, "b": None, "c": None, "d": None},
            expenses_current=None,
            hourly_rates_proposed={"a": None, "b": None, "c": None, "d": None},
            time_required_proposed={"a": 6, "b": None, "c": None, "d": None},
            expenses_proposed=None,
        )


def test_citizens_effort_trigger_rejects_direct_hourly_rate_updates(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "citizens_rates_trigger.db")
    db.init_db()

    session_id, _ = db.upsert_session("CITIZENS-RATES-TRIGGER", "test-model")
    process_id = db.insert_process(
        session_id,
        "Buergerprozess",
        "Beschreibung",
        norm_addressee=CITIZENS,
    )
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Fallgruppe",
        "Beschreibung",
        norm_addressee=CITIZENS,
    )
    step_id = db.insert_process_step(
        session_id,
        case_group_id,
        "Schritt",
        "Beschreibung",
        norm_addressee=CITIZENS,
    )

    conn = db.get_conn()
    try:
        with pytest.raises(
            sqlite3.IntegrityError,
            match="Citizens process steps must not persist hourly rates",
        ):
            conn.execute(
                """
                UPDATE process_steps
                SET hourly_rate_a_proposed = 999
                WHERE session_id = ? AND step_id = ? AND norm_addressee = 'citizens'
                """,
                (session_id, step_id),
            )
            conn.commit()
    finally:
        conn.close()


def test_get_default_pay_rates_for_business_uses_handbook_overall_defaults(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "business_defaults.db")
    db.init_db()

    defaults = db.get_default_pay_rates_for_addressee(BUSINESS)
    assert defaults == {"a": 26.1, "b": 37.1, "c": 62.4, "d": 38.6}


def test_get_session_pay_rates_for_business_uses_editable_business_defaults(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "session_business_rates.db")
    db.init_db()

    session_id, _ = db.upsert_session("SESSION-BUSINESS-RATES", "test-model")
    pay_rates = db.get_session_pay_rates_for_addressee(session_id, BUSINESS)

    assert pay_rates is not None
    assert pay_rates["norm_addressee"] == BUSINESS
    assert pay_rates["editable"] is True
    assert pay_rates["administration_level"] is None
    assert pay_rates["defaults"] == {"a": 26.1, "b": 37.1, "c": 62.4, "d": 38.6}
    assert pay_rates["edited"] == {"a": None, "b": None, "c": None, "d": None}
    assert pay_rates["active"] == {"a": 26.1, "b": 37.1, "c": 62.4, "d": 38.6}


def test_get_session_pay_rates_for_citizens_returns_zero_rates(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "session_citizens_rates.db")
    db.init_db()

    session_id, _ = db.upsert_session("SESSION-CITIZENS-RATES", "test-model")
    pay_rates = db.get_session_pay_rates_for_addressee(session_id, CITIZENS)

    assert pay_rates is not None
    assert pay_rates["norm_addressee"] == CITIZENS
    assert pay_rates["editable"] is False
    assert pay_rates["administration_level"] is None
    assert pay_rates["defaults"] == {"a": 0.0, "b": 0.0, "c": 0.0, "d": 0.0}
    assert pay_rates["edited"] == {"a": None, "b": None, "c": None, "d": None}
    assert pay_rates["active"] == {"a": 0.0, "b": 0.0, "c": 0.0, "d": 0.0}


def test_replace_mirror_matches_rejects_inconsistent_reverse_sync_flags(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "mirror_symmetry.db")
    db.init_db()

    session_id, _ = db.upsert_session("MIRROR-SYMMETRY", "test-model")
    admin_process_id = db.insert_process(
        session_id,
        "Verwaltungsprozess",
        "Beschreibung Verwaltung",
        norm_addressee="administration",
    )
    business_process_id = db.insert_process(
        session_id,
        "Wirtschaftsprozess",
        "Beschreibung Wirtschaft",
        norm_addressee="business",
    )
    admin_case_group_id = db.insert_case_group(
        session_id,
        admin_process_id,
        "Fallgruppe Verwaltung",
        "Beschreibung",
        norm_addressee="administration",
    )
    business_case_group_id = db.insert_case_group(
        session_id,
        business_process_id,
        "Fallgruppe Wirtschaft",
        "Beschreibung",
        norm_addressee="business",
    )

    with pytest.raises(ValueError, match="reverse pairs must agree on sync_cases"):
        db.replace_mirror_matches(
            session_id,
            [
                {
                    "mirror_anchor_key": "gemeinsamer-fall",
                    "shared_situation": "Test",
                    "source_norm_addressee": "administration",
                    "target_norm_addressee": "business",
                    "source_process_id": admin_process_id,
                    "target_process_id": business_process_id,
                    "source_case_group_id": admin_case_group_id,
                    "target_case_group_id": business_case_group_id,
                    "relation_type": "mirrored_case_group",
                    "sync_addressees": True,
                    "sync_frequency": True,
                    "sync_cases": True,
                    "reason": "Hinrichtung A->B",
                },
                {
                    "mirror_anchor_key": "gemeinsamer-fall",
                    "shared_situation": "Test",
                    "source_norm_addressee": "business",
                    "target_norm_addressee": "administration",
                    "source_process_id": business_process_id,
                    "target_process_id": admin_process_id,
                    "source_case_group_id": business_case_group_id,
                    "target_case_group_id": admin_case_group_id,
                    "relation_type": "mirrored_case_group",
                    "sync_addressees": True,
                    "sync_frequency": True,
                    "sync_cases": False,
                    "reason": "Rueckrichtung B->A",
                },
            ],
        )


def _seed_step_with_fields(
    session_id: int,
    norm_addressee: str,
    *,
    hourly_rate_a_current=None,
    time_required_in_min_a_current=None,
    expenses_current=None,
    execution_per_case=None,
) -> int:
    process_id = db.insert_process(
        session_id, f"Prozess {norm_addressee}", "", norm_addressee=norm_addressee
    )
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        f"Fallgruppe {norm_addressee}",
        "",
        norm_addressee=norm_addressee,
    )
    db.upsert_case_group_metrics_by_addressee(
        session_id=session_id,
        case_group_id=case_group_id,
        norm_addressee=norm_addressee,
        addressees_current=10,
        annual_frequency_current=2,
        addressees_proposed=10,
        annual_frequency_proposed=2,
    )
    step_id = db.insert_process_step(
        session_id, case_group_id, f"Schritt {norm_addressee}", "",
        norm_addressee=norm_addressee,
    )
    conn = db.get_conn()
    conn.execute(
        """
        UPDATE process_steps
        SET hourly_rate_a_current = ?,
            time_required_in_min_a_current = ?,
            expenses_current = ?,
            execution_per_case = ?
        WHERE step_id = ? AND session_id = ? AND norm_addressee = ?
        """,
        (
            hourly_rate_a_current,
            time_required_in_min_a_current,
            expenses_current,
            execution_per_case,
            step_id,
            session_id,
            norm_addressee,
        ),
    )
    conn.commit()
    conn.close()
    return step_id


def test_has_effort_metrics_rejects_step_with_only_hourly_rate(tmp_path, monkeypatch):
    """Regression: Ready-Check akzeptierte bisher Steps, die nur hourly_rate_*
    gesetzt hatten, ohne time oder expenses. Effort-Router meldete dann
    "existing", compute_costs warf anschliessend 422. Fix: has_effort_metrics
    schaut auf dieselben Felder wie _has_step_cost_inputs."""
    monkeypatch.setattr(
        config.settings, "db_path", tmp_path / "ready_only_rate.db"
    )
    db.init_db()
    session_id, _ = db.upsert_session("READY-RATE", "test-model")
    _seed_step_with_fields(
        session_id, ADMINISTRATION, hourly_rate_a_current=50.0
    )
    assert db.has_effort_metrics(session_id, ADMINISTRATION) is False


def test_has_effort_metrics_rejects_step_with_only_execution_per_case(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        config.settings, "db_path", tmp_path / "ready_only_exec.db"
    )
    db.init_db()
    session_id, _ = db.upsert_session("READY-EXEC", "test-model")
    _seed_step_with_fields(
        session_id, BUSINESS, execution_per_case=True
    )
    assert db.has_effort_metrics(session_id, BUSINESS) is False


def test_has_effort_metrics_accepts_step_with_time_only(tmp_path, monkeypatch):
    """Positiv: Ein Step mit gesetzter Zeit (ohne expenses) ist ready."""
    monkeypatch.setattr(
        config.settings, "db_path", tmp_path / "ready_time_only.db"
    )
    db.init_db()
    session_id, _ = db.upsert_session("READY-TIME", "test-model")
    _seed_step_with_fields(
        session_id, CITIZENS, time_required_in_min_a_current=30.0
    )
    assert db.has_effort_metrics(session_id, CITIZENS) is True


def test_has_effort_metrics_accepts_step_with_expenses_only(tmp_path, monkeypatch):
    """Positiv: Ein Step mit nur expenses (z.B. Porto) ist ready."""
    monkeypatch.setattr(
        config.settings, "db_path", tmp_path / "ready_expenses_only.db"
    )
    db.init_db()
    session_id, _ = db.upsert_session("READY-EXP", "test-model")
    _seed_step_with_fields(
        session_id, CITIZENS, expenses_current=5.0
    )
    assert db.has_effort_metrics(session_id, CITIZENS) is True


def test_delete_case_groups_for_session_preserves_unrelated_mirror_matches(
    tmp_path, monkeypatch
):
    """Regression: NA-spezifisches delete_case_groups_for_session (z.B. für
    business) darf nur mirror_matches löschen, bei denen business als Source
    oder Target vorkommt. Ein unberührtes admin<->citizens-Paar muss
    überleben. Vorher räumte der Kompensations-DELETE die gesamte Session."""
    monkeypatch.setattr(
        config.settings, "db_path", tmp_path / "mirror_delete_preserve.db"
    )
    db.init_db()

    session_id, _ = db.upsert_session("MIRROR-DELETE-PRESERVE", "test-model")
    admin_process = db.insert_process(
        session_id, "Admin-Prozess", "", norm_addressee=ADMINISTRATION
    )
    business_process = db.insert_process(
        session_id, "Business-Prozess", "", norm_addressee=BUSINESS
    )
    citizens_process = db.insert_process(
        session_id, "Citizens-Prozess", "", norm_addressee=CITIZENS
    )
    admin_cg_for_business = db.insert_case_group(
        session_id, admin_process, "Admin-CG (biz)", "", norm_addressee=ADMINISTRATION
    )
    business_cg = db.insert_case_group(
        session_id, business_process, "Business-CG", "", norm_addressee=BUSINESS
    )
    admin_cg_for_citizens = db.insert_case_group(
        session_id, admin_process, "Admin-CG (cit)", "", norm_addressee=ADMINISTRATION
    )
    citizens_cg = db.insert_case_group(
        session_id, citizens_process, "Citizens-CG", "", norm_addressee=CITIZENS
    )

    db.replace_mirror_matches(
        session_id,
        [
            {
                "mirror_anchor_key": "anchor-admin-business",
                "shared_situation": "Meldepflicht",
                "source_norm_addressee": ADMINISTRATION,
                "target_norm_addressee": BUSINESS,
                "source_process_id": admin_process,
                "target_process_id": business_process,
                "source_case_group_id": admin_cg_for_business,
                "target_case_group_id": business_cg,
                "relation_type": "mirrored_case_group",
                "sync_addressees": True,
                "sync_frequency": True,
                "sync_cases": True,
                "reason": "admin<->business",
            },
            {
                "mirror_anchor_key": "anchor-admin-business",
                "shared_situation": "Meldepflicht",
                "source_norm_addressee": BUSINESS,
                "target_norm_addressee": ADMINISTRATION,
                "source_process_id": business_process,
                "target_process_id": admin_process,
                "source_case_group_id": business_cg,
                "target_case_group_id": admin_cg_for_business,
                "relation_type": "mirrored_case_group",
                "sync_addressees": True,
                "sync_frequency": True,
                "sync_cases": True,
                "reason": "business<->admin",
            },
            {
                "mirror_anchor_key": "anchor-admin-citizens",
                "shared_situation": "Antrag",
                "source_norm_addressee": ADMINISTRATION,
                "target_norm_addressee": CITIZENS,
                "source_process_id": admin_process,
                "target_process_id": citizens_process,
                "source_case_group_id": admin_cg_for_citizens,
                "target_case_group_id": citizens_cg,
                "relation_type": "mirrored_case_group",
                "sync_addressees": True,
                "sync_frequency": True,
                "sync_cases": True,
                "reason": "admin<->citizens",
            },
            {
                "mirror_anchor_key": "anchor-admin-citizens",
                "shared_situation": "Antrag",
                "source_norm_addressee": CITIZENS,
                "target_norm_addressee": ADMINISTRATION,
                "source_process_id": citizens_process,
                "target_process_id": admin_process,
                "source_case_group_id": citizens_cg,
                "target_case_group_id": admin_cg_for_citizens,
                "relation_type": "mirrored_case_group",
                "sync_addressees": True,
                "sync_frequency": True,
                "sync_cases": True,
                "reason": "citizens<->admin",
            },
        ],
    )

    assert len(db.list_mirror_matches(session_id)) == 4

    db.delete_case_groups_for_session(session_id, norm_addressee=BUSINESS)

    remaining = db.list_mirror_matches(session_id)
    anchors = {match["mirror_anchor_key"] for match in remaining}
    assert anchors == {"anchor-admin-citizens"}
    assert len(remaining) == 2
    for match in remaining:
        assert ADMINISTRATION in (
            match["source_norm_addressee"],
            match["target_norm_addressee"],
        )
        assert CITIZENS in (
            match["source_norm_addressee"],
            match["target_norm_addressee"],
        )


def test_delete_processes_for_session_preserves_unrelated_mirror_matches(
    tmp_path, monkeypatch
):
    """Symmetrischer Regressionstest zu delete_processes_for_session."""
    monkeypatch.setattr(
        config.settings, "db_path", tmp_path / "mirror_delete_processes.db"
    )
    db.init_db()

    session_id, _ = db.upsert_session("MIRROR-DELETE-PROCESSES", "test-model")
    admin_process = db.insert_process(
        session_id, "Admin-Prozess", "", norm_addressee=ADMINISTRATION
    )
    business_process = db.insert_process(
        session_id, "Business-Prozess", "", norm_addressee=BUSINESS
    )
    citizens_process = db.insert_process(
        session_id, "Citizens-Prozess", "", norm_addressee=CITIZENS
    )

    db.replace_mirror_matches(
        session_id,
        [
            {
                "mirror_anchor_key": "anchor-ab",
                "shared_situation": "",
                "source_norm_addressee": ADMINISTRATION,
                "target_norm_addressee": BUSINESS,
                "source_process_id": admin_process,
                "target_process_id": business_process,
                "source_case_group_id": None,
                "target_case_group_id": None,
                "relation_type": "mirrored_process",
                "sync_addressees": False,
                "sync_frequency": False,
                "sync_cases": False,
                "reason": "",
            },
            {
                "mirror_anchor_key": "anchor-ab",
                "shared_situation": "",
                "source_norm_addressee": BUSINESS,
                "target_norm_addressee": ADMINISTRATION,
                "source_process_id": business_process,
                "target_process_id": admin_process,
                "source_case_group_id": None,
                "target_case_group_id": None,
                "relation_type": "mirrored_process",
                "sync_addressees": False,
                "sync_frequency": False,
                "sync_cases": False,
                "reason": "",
            },
            {
                "mirror_anchor_key": "anchor-ac",
                "shared_situation": "",
                "source_norm_addressee": ADMINISTRATION,
                "target_norm_addressee": CITIZENS,
                "source_process_id": admin_process,
                "target_process_id": citizens_process,
                "source_case_group_id": None,
                "target_case_group_id": None,
                "relation_type": "mirrored_process",
                "sync_addressees": False,
                "sync_frequency": False,
                "sync_cases": False,
                "reason": "",
            },
            {
                "mirror_anchor_key": "anchor-ac",
                "shared_situation": "",
                "source_norm_addressee": CITIZENS,
                "target_norm_addressee": ADMINISTRATION,
                "source_process_id": citizens_process,
                "target_process_id": admin_process,
                "source_case_group_id": None,
                "target_case_group_id": None,
                "relation_type": "mirrored_process",
                "sync_addressees": False,
                "sync_frequency": False,
                "sync_cases": False,
                "reason": "",
            },
        ],
    )

    assert len(db.list_mirror_matches(session_id)) == 4
    db.delete_processes_for_session(session_id, norm_addressee=BUSINESS)
    remaining = db.list_mirror_matches(session_id)
    anchors = {match["mirror_anchor_key"] for match in remaining}
    assert anchors == {"anchor-ac"}
    assert len(remaining) == 2


def test_init_db_migrates_addressee_metrics_into_parent_tables(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "db_path", tmp_path / "legacy_addressee_metrics.db")
    db.init_db()

    session_id, _ = db.upsert_session("LEGACY-METRICS", "test-model")
    process_id = db.insert_process(
        session_id,
        "Prozess B",
        "Beschreibung Prozess B",
        norm_addressee="business",
    )
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Fallgruppe B",
        "Beschreibung Fallgruppe B",
        norm_addressee="business",
    )
    step_id = db.insert_process_step(
        session_id,
        case_group_id,
        "Schritt B",
        "Beschreibung Schritt B",
        norm_addressee="business",
    )

    conn = db.get_conn()
    try:
        conn.execute(
            """
            CREATE TABLE case_group_metrics_by_addressee (
                session_id INTEGER NOT NULL,
                case_group_id INTEGER NOT NULL,
                norm_addressee TEXT NOT NULL,
                addressees_current REAL,
                annual_frequency_current REAL,
                cases_current REAL,
                addressees_proposed REAL,
                annual_frequency_proposed REAL,
                cases_proposed REAL,
                PRIMARY KEY (session_id, case_group_id, norm_addressee)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE process_step_effort_metrics_by_addressee (
                session_id INTEGER NOT NULL,
                step_id INTEGER NOT NULL,
                norm_addressee TEXT NOT NULL,
                hourly_rate_a_current REAL,
                hourly_rate_b_current REAL,
                hourly_rate_c_current REAL,
                hourly_rate_d_current REAL,
                time_required_in_min_a_current REAL,
                time_required_in_min_b_current REAL,
                time_required_in_min_c_current REAL,
                time_required_in_min_d_current REAL,
                expenses_current REAL,
                hourly_rate_a_proposed REAL,
                hourly_rate_b_proposed REAL,
                hourly_rate_c_proposed REAL,
                hourly_rate_d_proposed REAL,
                time_required_in_min_a_proposed REAL,
                time_required_in_min_b_proposed REAL,
                time_required_in_min_c_proposed REAL,
                time_required_in_min_d_proposed REAL,
                expenses_proposed REAL,
                execution_per_case INTEGER,
                PRIMARY KEY (session_id, step_id, norm_addressee)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE process_step_costs_by_addressee (
                session_id INTEGER NOT NULL,
                step_id INTEGER NOT NULL,
                norm_addressee TEXT NOT NULL,
                cost_current REAL,
                cost_proposed REAL,
                bureaucracy_cost_current REAL,
                bureaucracy_cost_proposed REAL,
                other_cost_current REAL,
                other_cost_proposed REAL,
                PRIMARY KEY (session_id, step_id, norm_addressee)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO case_group_metrics_by_addressee (
                session_id,
                case_group_id,
                norm_addressee,
                addressees_proposed,
                annual_frequency_proposed,
                cases_proposed
            )
            VALUES (?, ?, 'business', 10, 2, 20)
            """,
            (session_id, case_group_id),
        )
        conn.execute(
            """
            INSERT INTO process_step_effort_metrics_by_addressee (
                session_id,
                step_id,
                norm_addressee,
                hourly_rate_a_proposed,
                time_required_in_min_a_proposed,
                expenses_proposed,
                execution_per_case
            )
            VALUES (?, ?, 'business', 55, 30, 5, 0)
            """,
            (session_id, step_id),
        )
        conn.execute(
            """
            INSERT INTO process_step_costs_by_addressee (
                session_id,
                step_id,
                norm_addressee,
                cost_current,
                cost_proposed,
                bureaucracy_cost_proposed,
                other_cost_proposed
            )
            VALUES (?, ?, 'business', 11, 25, 10, 15)
            """,
            (session_id, step_id),
        )
        conn.commit()
    finally:
        conn.close()

    db.init_db()

    check = sqlite3.connect(config.settings.db_path)
    check.row_factory = sqlite3.Row
    try:
        tables = {
            row["name"]
            for row in check.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert "case_group_metrics_by_addressee" not in tables
        assert "process_step_effort_metrics_by_addressee" not in tables
        assert "process_step_costs_by_addressee" not in tables

        case_group = check.execute(
            """
            SELECT addressees_proposed, annual_frequency_proposed, cases_proposed
            FROM case_groups
            WHERE session_id = ? AND case_group_id = ? AND norm_addressee = 'business'
            """,
            (session_id, case_group_id),
        ).fetchone()
        assert case_group["addressees_proposed"] == 10
        assert case_group["annual_frequency_proposed"] == 2
        assert case_group["cases_proposed"] == 20

        step = check.execute(
            """
            SELECT
                hourly_rate_a_proposed,
                time_required_in_min_a_proposed,
                expenses_proposed,
                execution_per_case,
                cost_current,
                cost_proposed
            FROM process_steps
            WHERE session_id = ? AND step_id = ? AND norm_addressee = 'business'
            """,
            (session_id, step_id),
        ).fetchone()
        assert step["hourly_rate_a_proposed"] == 55
        assert step["time_required_in_min_a_proposed"] == 30
        assert step["expenses_proposed"] == 5
        assert step["execution_per_case"] == 0
        assert step["cost_current"] == 11
        assert step["cost_proposed"] == 25
    finally:
        check.close()
