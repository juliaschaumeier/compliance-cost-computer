import json

from backend.core import db
from tests.activity_helpers import ea_payload_for_session


def _seed_case_group(session_id: int) -> tuple[int, int]:
    process_id = db.insert_process(session_id, "Prozess A", "Beschreibung Prozess")
    case_group_id = db.insert_case_group(
        session_id,
        process_id,
        "Fallgruppe A",
        "Beschreibung Fallgruppe",
    )
    return process_id, case_group_id


def _seed_step(session_id: int, case_group_id: int) -> int:
    return db.insert_process_step(
        session_id,
        case_group_id,
        "Schritt 1",
        "Beschreibung Schritt 1",
    )


def _decode_audit_value(value: str | None) -> object:
    if value is None:
        return None
    return json.loads(value)


def test_sessions_pay_rates_get_and_post(test_client):
    session_id, _ = db.upsert_session("EDIT-RATES", "test-model")

    get_response = test_client.get(
        "/sessions/pay-rates",
        params={"app_session_id": "EDIT-RATES"},
    )
    assert get_response.status_code == 200
    initial = get_response.json()
    assert initial["app_session_id"] == "EDIT-RATES"
    assert initial["administration_level"] == "bund"
    assert initial["active"]["a"] == initial["defaults"]["a"]

    post_response = test_client.post(
        "/sessions/pay-rates",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-RATES",
            "administration_level": "bund",
            "edited_a": 99.5,
            "edited_b": None,
            "edited_c": None,
            "edited_d": None,
        }),
    )
    assert post_response.status_code == 200
    updated = post_response.json()
    assert updated["edited"]["a"] == 99.5
    assert updated["active"]["a"] == 99.5

    session_rates = db.get_session_pay_rates(session_id)
    assert session_rates is not None
    assert session_rates["edited"]["a"] == 99.5
    assert session_rates["active"]["a"] == 99.5

    addressee_rates = db.get_session_pay_rates_for_addressee(
        session_id,
        "administration",
    )
    assert addressee_rates is not None
    assert addressee_rates["editable"] is True
    assert addressee_rates["active"]["a"] == 99.5


def test_sessions_pay_rates_reject_unknown_level(test_client):
    session_id, _ = db.upsert_session("EDIT-RATES-UNKNOWN", "test-model")
    response = test_client.post(
        "/sessions/pay-rates",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-RATES-UNKNOWN",
            "administration_level": "invalid-level",
            "edited_a": None,
            "edited_b": None,
            "edited_c": None,
            "edited_d": None,
        }),
    )
    assert response.status_code == 422
    assert "Unknown administration_level" in response.json()["detail"]


def test_sessions_pay_rates_support_business_overrides(test_client):
    session_id, _ = db.upsert_session("EDIT-RATES-BUSINESS", "test-model")

    get_response = test_client.get(
        "/sessions/pay-rates",
        params={
            "app_session_id": "EDIT-RATES-BUSINESS",
            "norm_addressee": "business",
        },
    )
    assert get_response.status_code == 200
    initial = get_response.json()
    assert initial["norm_addressee"] == "business"
    assert initial["editable"] is True
    assert initial["administration_level"] is None
    assert initial["active"]["a"] == initial["defaults"]["a"] == 26.1

    post_response = test_client.post(
        "/sessions/pay-rates",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-RATES-BUSINESS",
            "norm_addressee": "business",
            "administration_level": None,
            "edited_a": 41.5,
            "edited_b": None,
            "edited_c": None,
            "edited_d": None,
        }),
    )
    assert post_response.status_code == 200
    updated = post_response.json()
    assert updated["norm_addressee"] == "business"
    assert updated["editable"] is True
    assert updated["edited"]["a"] == 41.5
    assert updated["active"]["a"] == 41.5

    session_rates = db.get_session_pay_rates_for_addressee(session_id, "business")
    assert session_rates is not None
    assert session_rates["edited"]["a"] == 41.5
    assert session_rates["active"]["a"] == 41.5


def test_sessions_pay_rates_reject_administration_level_for_business(test_client):
    session_id, _ = db.upsert_session("EDIT-RATES-BUSINESS-LEVEL", "test-model")
    response = test_client.post(
        "/sessions/pay-rates",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-RATES-BUSINESS-LEVEL",
            "norm_addressee": "business",
            "administration_level": "bund",
            "edited_a": 41.5,
            "edited_b": None,
            "edited_c": None,
            "edited_d": None,
        }),
    )
    assert response.status_code == 422
    assert "only supported for administration" in response.json()["detail"]


def test_sessions_pay_rates_reject_citizens_updates(test_client):
    session_id, _ = db.upsert_session("EDIT-RATES-CITIZENS", "test-model")

    get_response = test_client.get(
        "/sessions/pay-rates",
        params={
            "app_session_id": "EDIT-RATES-CITIZENS",
            "norm_addressee": "citizens",
        },
    )
    assert get_response.status_code == 200
    payload = get_response.json()
    assert payload["norm_addressee"] == "citizens"
    assert payload["editable"] is False
    assert payload["active"]["a"] == 0.0

    post_response = test_client.post(
        "/sessions/pay-rates",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-RATES-CITIZENS",
            "norm_addressee": "citizens",
            "edited_a": 1.0,
            "edited_b": None,
            "edited_c": None,
            "edited_d": None,
        }),
    )
    assert post_response.status_code == 422
    assert "not editable" in post_response.json()["detail"]


def test_sessions_pay_rates_reject_negative_edited_value(test_client):
    session_id, _ = db.upsert_session("EDIT-RATES-NEG", "test-model")
    response = test_client.post(
        "/sessions/pay-rates",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-RATES-NEG",
            "administration_level": "bund",
            "edited_a": -1,
            "edited_b": None,
            "edited_c": None,
            "edited_d": None,
        }),
    )
    assert response.status_code == 422
    assert "must be non-negative" in response.json()["detail"]


def test_sessions_pay_rates_reject_noop_payload(test_client):
    session_id, _ = db.upsert_session("EDIT-RATES-NOOP", "test-model")
    response = test_client.post(
        "/sessions/pay-rates",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-RATES-NOOP",
            "administration_level": "bund",
            "edited_a": None,
            "edited_b": None,
            "edited_c": None,
            "edited_d": None,
        }),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "No changes in payload"
    assert db.list_edit_audit_for_session(session_id) == []


def test_sessions_edit_audit_returns_logged_changes(test_client):
    session_id, _ = db.upsert_session("EDIT-AUDIT", "test-model")
    update_response = test_client.post(
        "/sessions/pay-rates",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-AUDIT",
            "administration_level": "bund",
            "edited_a": 88.0,
            "edited_b": None,
            "edited_c": None,
            "edited_d": None,
        }),
    )
    assert update_response.status_code == 200

    audit_response = test_client.get(
        "/sessions/edit-audit",
        params={"app_session_id": "EDIT-AUDIT"},
    )
    assert audit_response.status_code == 200
    payload = audit_response.json()
    assert payload["app_session_id"] == "EDIT-AUDIT"
    assert payload["rows"]
    first = payload["rows"][0]
    assert first["entity_type"] == "pay_rate"
    assert first["field_name"] in {"edited_a", "default_a", "administration_level"}


def test_case_groups_editable_and_bulk_update(test_client):
    session_id, _ = db.upsert_session("EDIT-CASES", "test-model")
    _process_id, case_group_id = _seed_case_group(session_id)
    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=case_group_id,
        addressees_current=10,
        annual_frequency_current=2,
        addressees_proposed=11,
        annual_frequency_proposed=2,
    )

    get_before = test_client.get(
        "/case-groups/editable",
        params={"app_session_id": "EDIT-CASES"},
    )
    assert get_before.status_code == 200
    before_row = get_before.json()["rows"][0]
    assert before_row["addressees_current_effective"] == 10
    assert before_row["cases_current_effective"] == 20

    update_response = test_client.post(
        "/case-groups/bulk-update",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-CASES",
            "rows": [
                {
                    "case_group_id": case_group_id,
                    "addressees_current": 13,
                    "annual_frequency_current": 3,
                    "addressees_proposed": 15,
                    "annual_frequency_proposed": 4,
                }
            ],
        }),
    )
    assert update_response.status_code == 200
    assert update_response.json()["updated"] == 1

    get_after = test_client.get(
        "/case-groups/editable",
        params={"app_session_id": "EDIT-CASES"},
    )
    assert get_after.status_code == 200
    after_row = get_after.json()["rows"][0]
    assert after_row["addressees_current_edited"] == 13
    assert after_row["annual_frequency_current_edited"] == 3
    assert after_row["cases_current_effective"] == 39
    assert after_row["addressees_proposed_edited"] == 15
    assert after_row["annual_frequency_proposed_edited"] == 4
    assert after_row["cases_proposed_effective"] == 60


def test_case_groups_audit_logs_effective_values(test_client):
    session_id, _ = db.upsert_session("EDIT-CASES-AUDIT-EFFECTIVE", "test-model")
    _process_id, case_group_id = _seed_case_group(session_id)
    db.update_case_group_metrics(
        session_id=session_id,
        case_group_id=case_group_id,
        addressees_current=10,
        annual_frequency_current=2,
        addressees_proposed=12,
        annual_frequency_proposed=2,
    )

    response = test_client.post(
        "/case-groups/bulk-update",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-CASES-AUDIT-EFFECTIVE",
            "rows": [{"case_group_id": case_group_id, "addressees_current": 13}],
        }),
    )
    assert response.status_code == 200

    audit_rows = db.list_edit_audit_for_session(session_id)
    addressees_entry = next(
        row
        for row in audit_rows
        if row["entity_type"] == "case_group"
        and row["entity_id"] == case_group_id
        and row["field_name"] == "addressees_current"
    )
    assert _decode_audit_value(addressees_entry["old_value"]) == 10
    assert _decode_audit_value(addressees_entry["new_value"]) == 13


def test_case_groups_bulk_update_rejects_negative_values(test_client):
    session_id, _ = db.upsert_session("EDIT-CASES-NEG", "test-model")
    _process_id, case_group_id = _seed_case_group(session_id)

    response = test_client.post(
        "/case-groups/bulk-update",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-CASES-NEG",
            "rows": [
                {
                    "case_group_id": case_group_id,
                    "addressees_current": -1,
                }
            ],
        }),
    )
    assert response.status_code == 422
    assert "must be non-negative" in response.json()["detail"]


def test_case_groups_editable_rejects_invalid_app_session_id(test_client):
    response = test_client.get(
        "/case-groups/editable",
        params={"app_session_id": "bad id"},
    )
    assert response.status_code == 422


def test_case_groups_bulk_update_rejects_unknown_case_group_ids(test_client):
    session_id, _ = db.upsert_session("EDIT-CASES-MISSING", "test-model")
    response = test_client.post(
        "/case-groups/bulk-update",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-CASES-MISSING",
            "rows": [
                {
                    "case_group_id": 999999,
                    "addressees_current": 1,
                }
            ],
        }),
    )
    assert response.status_code == 422
    assert "Unknown case_group_id values for this session" in response.json()["detail"]


def test_case_groups_bulk_update_rejects_case_group_from_other_session(test_client):
    session_a_id, _ = db.upsert_session("EDIT-CASES-A", "test-model")
    _process_id, case_group_id = _seed_case_group(session_a_id)
    session_b_id, _ = db.upsert_session("EDIT-CASES-B", "test-model")

    response = test_client.post(
        "/case-groups/bulk-update",
        json=ea_payload_for_session(session_b_id, {
            "app_session_id": "EDIT-CASES-B",
            "rows": [
                {
                    "case_group_id": case_group_id,
                    "addressees_current": 1,
                }
            ],
        }),
    )
    assert response.status_code == 422
    assert "Unknown case_group_id values for this session" in response.json()["detail"]


def test_case_groups_bulk_update_rejects_duplicate_ids(test_client):
    session_id, _ = db.upsert_session("EDIT-CASES-DUP", "test-model")
    _process_id, case_group_id = _seed_case_group(session_id)
    response = test_client.post(
        "/case-groups/bulk-update",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-CASES-DUP",
            "rows": [
                {"case_group_id": case_group_id, "addressees_current": 1},
                {"case_group_id": case_group_id, "addressees_current": 2},
            ],
        }),
    )
    assert response.status_code == 422
    assert "Duplicate case_group_id values in payload" in response.json()["detail"]


def test_case_groups_bulk_update_rejects_empty_rows(test_client):
    session_id, _ = db.upsert_session("EDIT-CASES-EMPTY", "test-model")
    response = test_client.post(
        "/case-groups/bulk-update",
        json=ea_payload_for_session(session_id, {"app_session_id": "EDIT-CASES-EMPTY", "rows": []}),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "rows must not be empty"


def test_case_groups_bulk_update_rejects_noop_payload(test_client):
    session_id, _ = db.upsert_session("EDIT-CASES-NOOP", "test-model")
    _process_id, case_group_id = _seed_case_group(session_id)
    response = test_client.post(
        "/case-groups/bulk-update",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-CASES-NOOP",
            "rows": [{"case_group_id": case_group_id}],
        }),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "No changes in payload"
    assert db.list_edit_audit_for_session(session_id) == []


def test_process_steps_editable_and_bulk_update(test_client):
    session_id, _ = db.upsert_session("EDIT-STEPS", "test-model")
    _process_id, case_group_id = _seed_case_group(session_id)
    step_id = _seed_step(session_id, case_group_id)
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=step_id,
        hourly_rates_current={},
        time_required_current={"a": 2, "b": None, "c": None, "d": None},
        expenses_current=5,
        hourly_rates_proposed={},
        time_required_proposed={"a": 3, "b": None, "c": None, "d": None},
        expenses_proposed=6,
    )

    get_before = test_client.get(
        "/process-steps/editable",
        params={
            "app_session_id": "EDIT-STEPS",
            "case_group_id": case_group_id,
        },
    )
    assert get_before.status_code == 200
    before_row = get_before.json()["rows"][0]
    assert before_row["time_required_in_min_a_current_effective"] == 2
    assert before_row["expenses_current_effective"] == 5

    update_response = test_client.post(
        "/process-steps/bulk-update",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-STEPS",
            "rows": [
                {
                    "step_id": step_id,
                    "time_required_in_min_a_current": 7,
                    "expenses_current": 8,
                    "time_required_in_min_a_proposed": 9,
                    "expenses_proposed": 10,
                }
            ],
        }),
    )
    assert update_response.status_code == 200
    assert update_response.json()["updated"] == 1

    get_after = test_client.get(
        "/process-steps/editable",
        params={
            "app_session_id": "EDIT-STEPS",
            "case_group_id": case_group_id,
        },
    )
    assert get_after.status_code == 200
    after_row = get_after.json()["rows"][0]
    assert after_row["time_required_in_min_a_current_edited"] == 7
    assert after_row["expenses_current_edited"] == 8
    assert after_row["time_required_in_min_a_current_effective"] == 7
    assert after_row["time_required_in_min_a_proposed_edited"] == 9
    assert after_row["expenses_proposed_edited"] == 10
    assert after_row["time_required_in_min_a_proposed_effective"] == 9


def test_process_steps_audit_logs_effective_values(test_client):
    session_id, _ = db.upsert_session("EDIT-STEPS-AUDIT-EFFECTIVE", "test-model")
    _process_id, case_group_id = _seed_case_group(session_id)
    step_id = _seed_step(session_id, case_group_id)
    db.update_process_step_effort_split(
        session_id=session_id,
        step_id=step_id,
        hourly_rates_current={},
        time_required_current={"a": 2, "b": None, "c": None, "d": None},
        expenses_current=5,
        hourly_rates_proposed={},
        time_required_proposed={"a": 3, "b": None, "c": None, "d": None},
        expenses_proposed=6,
    )

    response = test_client.post(
        "/process-steps/bulk-update",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-STEPS-AUDIT-EFFECTIVE",
            "rows": [{"step_id": step_id, "time_required_in_min_a_current": 7}],
        }),
    )
    assert response.status_code == 200

    audit_rows = db.list_edit_audit_for_session(session_id)
    duration_entry = next(
        row
        for row in audit_rows
        if row["entity_type"] == "process_step"
        and row["entity_id"] == step_id
        and row["field_name"] == "time_required_in_min_a_current"
    )
    assert _decode_audit_value(duration_entry["old_value"]) == 2
    assert _decode_audit_value(duration_entry["new_value"]) == 7


def test_process_steps_bulk_update_rejects_negative_values(test_client):
    session_id, _ = db.upsert_session("EDIT-STEPS-NEG", "test-model")
    _process_id, case_group_id = _seed_case_group(session_id)
    step_id = _seed_step(session_id, case_group_id)

    response = test_client.post(
        "/process-steps/bulk-update",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-STEPS-NEG",
            "rows": [
                {
                    "step_id": step_id,
                    "time_required_in_min_a_current": -2,
                }
            ],
        }),
    )
    assert response.status_code == 422
    assert "must be non-negative" in response.json()["detail"]


def test_process_steps_editable_rejects_invalid_app_session_id(test_client):
    response = test_client.get(
        "/process-steps/editable",
        params={"app_session_id": "bad id"},
    )
    assert response.status_code == 422


def test_process_steps_bulk_update_rejects_unknown_step_ids(test_client):
    session_id, _ = db.upsert_session("EDIT-STEPS-MISSING", "test-model")
    response = test_client.post(
        "/process-steps/bulk-update",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-STEPS-MISSING",
            "rows": [
                {
                    "step_id": 999999,
                    "time_required_in_min_a_current": 1,
                }
            ],
        }),
    )
    assert response.status_code == 422
    assert "Unknown step_id values for this session" in response.json()["detail"]


def test_process_steps_bulk_update_rejects_step_from_other_session(test_client):
    session_a_id, _ = db.upsert_session("EDIT-STEPS-A", "test-model")
    _process_id, case_group_id = _seed_case_group(session_a_id)
    step_id = _seed_step(session_a_id, case_group_id)
    session_b_id, _ = db.upsert_session("EDIT-STEPS-B", "test-model")

    response = test_client.post(
        "/process-steps/bulk-update",
        json=ea_payload_for_session(session_b_id, {
            "app_session_id": "EDIT-STEPS-B",
            "rows": [
                {
                    "step_id": step_id,
                    "time_required_in_min_a_current": 1,
                }
            ],
        }),
    )
    assert response.status_code == 422
    assert "Unknown step_id values for this session" in response.json()["detail"]


def test_process_steps_bulk_update_rejects_duplicate_ids(test_client):
    session_id, _ = db.upsert_session("EDIT-STEPS-DUP", "test-model")
    _process_id, case_group_id = _seed_case_group(session_id)
    step_id = _seed_step(session_id, case_group_id)
    response = test_client.post(
        "/process-steps/bulk-update",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-STEPS-DUP",
            "rows": [
                {"step_id": step_id, "time_required_in_min_a_current": 1},
                {"step_id": step_id, "time_required_in_min_a_current": 2},
            ],
        }),
    )
    assert response.status_code == 422
    assert "Duplicate step_id values in payload" in response.json()["detail"]


def test_process_steps_bulk_update_rejects_empty_rows(test_client):
    session_id, _ = db.upsert_session("EDIT-STEPS-EMPTY", "test-model")
    response = test_client.post(
        "/process-steps/bulk-update",
        json=ea_payload_for_session(session_id, {"app_session_id": "EDIT-STEPS-EMPTY", "rows": []}),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "rows must not be empty"


def test_process_steps_bulk_update_rejects_noop_payload(test_client):
    session_id, _ = db.upsert_session("EDIT-STEPS-NOOP", "test-model")
    _process_id, case_group_id = _seed_case_group(session_id)
    step_id = _seed_step(session_id, case_group_id)
    response = test_client.post(
        "/process-steps/bulk-update",
        json=ea_payload_for_session(session_id, {
            "app_session_id": "EDIT-STEPS-NOOP",
            "rows": [{"step_id": step_id}],
        }),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "No changes in payload"
    assert db.list_edit_audit_for_session(session_id) == []
