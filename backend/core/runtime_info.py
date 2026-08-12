from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from pathlib import Path


UNKNOWN_CODE_STATE = "unknown"


@lru_cache(maxsize=1)
def app_code_state() -> str:
    """Return a compact label for the code currently serving this request."""
    explicit = _clean(os.environ.get("CCC_APP_CODE_STATE"))
    if explicit:
        return explicit

    branch = _clean(os.environ.get("CCC_APP_GIT_BRANCH"))
    sha = _clean(os.environ.get("CCC_APP_GIT_SHA"))
    dirty = _env_bool(os.environ.get("CCC_APP_GIT_DIRTY"))
    if branch and sha:
        return format_app_code_state(branch=branch, sha=sha, dirty=dirty)

    state = _git_code_state()
    return state or UNKNOWN_CODE_STATE


def format_app_code_state(*, branch: str, sha: str, dirty: bool = False) -> str:
    branch = _clean(branch) or "unknown"
    sha = _clean(sha) or "unknown"
    suffix = "-dirty" if dirty else ""
    return f"{branch}@{sha}{suffix}"


def _git_code_state() -> str | None:
    repo_root = Path(__file__).resolve().parents[2]
    sha = _git(["rev-parse", "--short", "HEAD"], cwd=repo_root)
    if not sha:
        return None
    branch = _git(["branch", "--show-current"], cwd=repo_root)
    if not branch:
        branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root)
    if not branch or branch == "HEAD":
        branch = "detached"
    dirty = _git_dirty(cwd=repo_root)
    return format_app_code_state(branch=branch, sha=sha, dirty=dirty)


def _git(args: list[str], *, cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return _clean(result.stdout)


def _git_dirty(*, cwd: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if result.returncode != 0:
        return False
    return bool(result.stdout.strip())


def _env_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "dirty"}


def _clean(value: str | None) -> str:
    return str(value or "").strip()
