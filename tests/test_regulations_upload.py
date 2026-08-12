import json

from backend.core import db


def _legisllm_payload(
    title: str = "Einführung einer Freigrenze für Einnahmen",
    original_norm: dict | None = None,
    amended_norm: dict | None = None,
) -> bytes:
    payload = {
        "exportiertAm": "2026-08-11T13:19:14.467Z",
        "schritte": {
            "1_aufgabenstellung": title,
            "5_umsetzung": [
                {
                    "originalNorm": original_norm
                    or {
                        "enbez": "§ 21",
                        "jurabk": "EStG",
                        "P": "4",
                        "wording": "",
                    },
                    "amendedNorm": amended_norm
                    or {
                        "enbez": "§ 21",
                        "jurabk": "EStG",
                        "P": "4",
                        "wording": "Neue Freigrenze.",
                    },
                }
            ],
        },
    }
    return json.dumps(payload).encode("utf-8")


def test_upload_regulation_success(test_client):
    """Uploads a valid file and verifies it is saved to the laws table."""
    response = test_client.post(
        "/regulations/upload",
        files={"file": ("test.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["filename"] == "test.txt"
    row = db.get_law_by_filename("test.txt")
    assert row is not None
    assert row["law_text"] == "hello"
    assert row["text_length"] == 5


def test_upload_regulation_empty_file(test_client):
    """Rejects empty file uploads with a 400 response."""
    response = test_client.post(
        "/regulations/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Empty file"


def test_upload_regulation_conflict(test_client):
    """Returns a conflict error when uploading a file that already exists."""
    db.insert_law("exists.txt", "already")

    response = test_client.post(
        "/regulations/upload",
        files={"file": ("exists.txt", b"new", "text/plain")},
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["error"] == "exists"
    assert detail["filename"] == "exists.txt"


def test_import_legisllm_creates_current_and_proposed_laws(test_client):
    response = test_client.post(
        "/regulations/import/legisllm",
        files={"file": ("export.json", _legisllm_payload(), "application/json")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["created"] is True
    assert payload["current_filename"].endswith("_gueltig.legisllm")
    assert payload["proposed_filename"].endswith("_vorschlag.legisllm")
    assert payload["current_filename"].replace("_gueltig.legisllm", "") == payload[
        "proposed_filename"
    ].replace("_vorschlag.legisllm", "")

    current = db.get_law_by_filename(payload["current_filename"])
    proposed = db.get_law_by_filename(payload["proposed_filename"])
    assert current is not None
    assert proposed is not None
    assert "Einführung einer Freigrenze für Einnahmen" in current["law_text"]
    assert "§ 21 Abs. 4 EStG" in current["law_text"]
    assert "Ursprüngliche Fassung" in current["law_text"]
    assert "entfällt" in current["law_text"]
    assert "§ 21 Abs. 4 EStG" in proposed["law_text"]
    assert "Geänderte Fassung" in proposed["law_text"]
    assert "Neue Freigrenze." in proposed["law_text"]


def test_import_legisllm_reuses_existing_import(test_client):
    first = test_client.post(
        "/regulations/import/legisllm",
        files={"file": ("export.json", _legisllm_payload(), "application/json")},
    )
    second = test_client.post(
        "/regulations/import/legisllm",
        files={"file": ("export.json", _legisllm_payload(), "application/json")},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["created"] is False
    assert second.json()["current_document_id"] == first.json()["current_document_id"]
    assert second.json()["proposed_document_id"] == first.json()["proposed_document_id"]


def test_import_legisllm_rejects_same_generated_name_with_different_content(test_client):
    first = test_client.post(
        "/regulations/import/legisllm",
        files={"file": ("export.json", _legisllm_payload(), "application/json")},
    )
    assert first.status_code == 200
    row = db.get_law_by_filename(first.json()["current_filename"])
    assert row is not None
    conn = db.get_conn()
    conn.execute(
        "UPDATE laws SET law_text = ? WHERE document_id = ?",
        ("anderer Inhalt", row["document_id"]),
    )
    conn.commit()
    conn.close()

    second = test_client.post(
        "/regulations/import/legisllm",
        files={"file": ("export.json", _legisllm_payload(), "application/json")},
    )

    assert second.status_code == 409
    assert "anderem Inhalt" in second.json()["detail"]


def test_import_legisllm_is_scoped_per_user(test_client):
    from backend.core import auth as auth_core
    from backend.main import app

    app.dependency_overrides.pop(auth_core.get_current_user, None)
    test_client.post(
        "/auth/login",
        json={"email": "tester@example.com", "password": "password123"},
    )
    first = test_client.post(
        "/regulations/import/legisllm",
        files={"file": ("export.json", _legisllm_payload(), "application/json")},
    )
    assert first.status_code == 200
    test_client.post(
        "/auth/users",
        json={"email": "second@example.com", "password": "secondpass"},
    )
    test_client.post("/auth/logout")
    test_client.post(
        "/auth/login",
        json={"email": "second@example.com", "password": "secondpass"},
    )

    second = test_client.post(
        "/regulations/import/legisllm",
        files={"file": ("export.json", _legisllm_payload(), "application/json")},
    )

    assert second.status_code == 200
    assert second.json()["created"] is True
    assert second.json()["current_filename"] == first.json()["current_filename"]
    assert second.json()["current_document_id"] != first.json()["current_document_id"]


def test_import_legisllm_rejects_missing_implementation(test_client):
    response = test_client.post(
        "/regulations/import/legisllm",
        files={
            "file": (
                "export.json",
                b'{"schritte": {"1_aufgabenstellung": "x"}}',
                "application/json",
            )
        },
    )

    assert response.status_code == 422
    assert "schritte.5_umsetzung" in response.json()["detail"]


def test_import_legisllm_rejects_norm_without_heading(test_client):
    response = test_client.post(
        "/regulations/import/legisllm",
        files={
            "file": (
                "export.json",
                _legisllm_payload(
                    original_norm={"P": "4", "wording": "Alter Text."}
                ),
                "application/json",
            )
        },
    )

    assert response.status_code == 422
    assert "Norm ohne enbez/jurabk" in response.json()["detail"]
