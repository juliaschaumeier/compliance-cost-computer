from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
import threading

from backend.core.config import settings


_WRITE_LOCK = threading.Lock()


def _normalize_session_filter(raw_value: str) -> set[str]:
    return {
        item.strip()
        for item in str(raw_value or "").split(",")
        if item.strip()
    }


def should_audit_session(app_session_id: str | None) -> bool:
    if not settings.prompt_audit_enabled:
        return False
    normalized = str(app_session_id or "").strip()
    if not normalized:
        return False
    session_filter = _normalize_session_filter(settings.prompt_audit_session_ids)
    if not session_filter:
        return True
    return normalized in session_filter


def _sanitize_filename_part(value: str) -> str:
    safe = []
    for char in value:
        if char.isalnum() or char in {"-", "_"}:
            safe.append(char)
        else:
            safe.append("_")
    return "".join(safe).strip("_") or "session"


def _output_path(app_session_id: str) -> Path:
    output_dir = Path(settings.prompt_audit_output_dir)
    safe_session_id = _sanitize_filename_part(app_session_id)
    return output_dir / f"{safe_session_id}_prompt_audit.md"


def append_prompt_audit_entry(
    *,
    app_session_id: str,
    session_id: int,
    prompt_id: str,
    model: str,
    provider: str | None,
    attempt_id: str,
    prompt: str,
    route_method: str | None = None,
    route_path: str | None = None,
) -> Path | None:
    if not should_audit_session(app_session_id):
        return None

    output_path = _output_path(app_session_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%SZ")
    header = (
        f"# Prompt-Audit fuer Session `{app_session_id}`\n\n"
        f"- Session-ID: `{session_id}`\n"
        f"- Audit erstellt durch Laufzeit-Mitschnitt der tatsaechlich gesendeten Prompts\n\n"
    )
    section = (
        f"## {prompt_id}\n\n"
        f"- Timestamp: `{timestamp}`\n"
        f"- Attempt-ID: `{attempt_id}`\n"
        f"- Modell: `{model}`\n"
        f"- Provider: `{provider or ''}`\n"
        f"- Route: `{route_method or ''} {route_path or ''}`\n\n"
        "```text\n"
        f"{prompt.rstrip()}\n"
        "```\n\n"
    )

    with _WRITE_LOCK:
        if not output_path.exists():
            output_path.write_text(header + section, encoding="utf-8")
        else:
            with output_path.open("a", encoding="utf-8") as handle:
                handle.write(section)
    return output_path
