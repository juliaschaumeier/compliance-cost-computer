from backend.core import db


def _seed_session(app_session_id: str, title: str, citation: str) -> None:
    current_name = f"{app_session_id}_current.txt"
    proposed_name = f"{app_session_id}_proposed.txt"
    db.insert_law(current_name, f"{app_session_id} current text")
    db.insert_law(proposed_name, f"{app_session_id} proposed text")
    session_id, _ = db.upsert_session(app_session_id, "test-model")
    db.update_session_documents(app_session_id, current_name, proposed_name)
    db.update_session_summary(app_session_id, title, f"{title} summary")
    db.insert_regulation(session_id, citation, f"Beschreibung {citation}")


def test_export_session_uses_requested_session_snapshot(test_client):
    _seed_session("EXPORT-A", "Titel A", "§ A")
    _seed_session("EXPORT-B", "Titel B", "§ B")

    rebuild_resp = test_client.post(
        "/tiles/rebuild", json={"app_session_id": "EXPORT-A"}
    )
    assert rebuild_resp.status_code == 200

    export_resp = test_client.get(
        "/sessions/export", params={"app_session_id": "EXPORT-B"}
    )
    assert export_resp.status_code == 200
    payload = export_resp.json()
    markdown = payload["markdown"]

    assert payload["filename"] == "ccc_session_EXPORT-B.md"
    assert "Titel B" in markdown
    assert "§ B" in markdown
    assert "§ A" not in markdown
