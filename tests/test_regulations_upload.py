from pathlib import Path

from backend.core import db


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
