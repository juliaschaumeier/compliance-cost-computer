from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, Request, status

from . import db
from .config import settings


@dataclass(frozen=True)
class ApiKeys:
    openai_api_key: str = ""
    deepinfra_api_key: str = ""
    gemini_api_key: str = ""


def get_api_keys(
    x_openai_key: Optional[str] = Header(default=None, alias="x-openai-key"),
    x_deepinfra_key: Optional[str] = Header(default=None, alias="x-deepinfra-key"),
    x_gemini_key: Optional[str] = Header(default=None, alias="x-gemini-key"),
) -> ApiKeys:
    return ApiKeys(
        openai_api_key=x_openai_key or settings.openai_api_key,
        deepinfra_api_key=x_deepinfra_key or settings.deepinfra_api_key,
        gemini_api_key=x_gemini_key or settings.gemini_api_key,
    )


# ---------------------------------------------------------------------------
# Accounts / authentication
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthUser:
    user_id: int
    email: str
    is_admin: bool


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _require_secret() -> str:
    secret = (settings.auth_secret_key or "").strip()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AUTH_SECRET_KEY is not configured",
        )
    return secret


def create_access_token(user_id: int) -> str:
    secret = _require_secret()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(int(user_id)),
        "iat": now,
        "exp": now + timedelta(minutes=settings.auth_token_ttl_minutes),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _decode_user_id(token: str) -> int | None:
    try:
        payload = jwt.decode(token, _require_secret(), algorithms=["HS256"])
    except HTTPException:
        raise
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    try:
        return int(sub)
    except (TypeError, ValueError):
        return None


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


def get_current_user(request: Request) -> AuthUser:
    """FastAPI dependency: resolve the authenticated user from the auth cookie."""
    # Surfaces a clear 500 when the deployment forgot to set AUTH_SECRET_KEY.
    _require_secret()
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise _unauthorized()
    user_id = _decode_user_id(token)
    if user_id is None:
        raise _unauthorized()
    user = db.get_user_by_id(user_id)
    if user is None or not user.get("is_active"):
        raise _unauthorized()
    return AuthUser(
        user_id=int(user["user_id"]),
        email=str(user["email"]),
        is_admin=bool(user.get("is_admin")),
    )


def require_admin(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


def email_is_allowed(email: str) -> bool:
    """Whether an admin may provision this email, per AUTH_ALLOWED_EMAILS.

    Empty allowlist = no extra restriction (accounts are still admin-provisioned;
    there is no public self-signup). Entries may be full emails or `@domain`.
    """
    entries = [e.strip().lower() for e in (settings.auth_allowed_emails or "").split(",") if e.strip()]
    if not entries:
        return True
    email_l = str(email).strip().lower()
    for entry in entries:
        if entry.startswith("@") and email_l.endswith(entry):
            return True
        if entry == email_l:
            return True
    return False


def ensure_bootstrap_admin() -> None:
    """Seed the configured bootstrap admin only for an empty admin set."""
    email = (settings.admin_bootstrap_email or "").strip()
    password = settings.admin_bootstrap_password or ""
    if not email or not password:
        return
    if db.count_admins() > 0:
        return
    if db.get_user_by_email(email) is not None:
        return
    db.create_user(email, hash_password(password), is_admin=True, is_active=True)
