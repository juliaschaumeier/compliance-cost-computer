from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from backend.core import auth as auth_core
from backend.core import db
from backend.core.config import settings


router = APIRouter(prefix="/auth", tags=["auth"])

_MIN_PASSWORD_LENGTH = 8


class LoginRequest(BaseModel):
    email: str
    password: str


class MeResponse(BaseModel):
    user_id: int
    email: str
    is_admin: bool


class UserOut(BaseModel):
    user_id: int
    email: str
    is_admin: bool
    is_active: bool
    created_at: str | None = None


class CreateUserRequest(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: str
    is_admin: bool = False


class UpdateUserRequest(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None
    password: str | None = None


def _user_out(user: dict) -> UserOut:
    return UserOut(
        user_id=int(user["user_id"]),
        email=str(user["email"]),
        is_admin=bool(user.get("is_admin")),
        is_active=bool(user.get("is_active")),
        created_at=user.get("created_at"),
    )


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_token_ttl_minutes * 60,
        path="/",
    )


@router.post("/login", response_model=MeResponse)
async def login(payload: LoginRequest, response: Response) -> MeResponse:
    user = db.get_user_by_email(payload.email)
    if (
        user is None
        or not user.get("is_active")
        or not auth_core.verify_password(payload.password, str(user["password_hash"]))
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = auth_core.create_access_token(int(user["user_id"]))
    _set_auth_cookie(response, token)
    return MeResponse(
        user_id=int(user["user_id"]),
        email=str(user["email"]),
        is_admin=bool(user.get("is_admin")),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> Response:
    response.delete_cookie(settings.auth_cookie_name, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=MeResponse)
async def me(user: auth_core.AuthUser = Depends(auth_core.get_current_user)) -> MeResponse:
    return MeResponse(user_id=user.user_id, email=user.email, is_admin=user.is_admin)


@router.get("/users", response_model=list[UserOut])
async def list_users(
    _admin: auth_core.AuthUser = Depends(auth_core.require_admin),
) -> list[UserOut]:
    return [_user_out(user) for user in db.list_users()]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: CreateUserRequest,
    _admin: auth_core.AuthUser = Depends(auth_core.require_admin),
) -> UserOut:
    if len(payload.password) < _MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {_MIN_PASSWORD_LENGTH} characters",
        )
    if not auth_core.email_is_allowed(payload.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is not in the allowlist",
        )
    try:
        user = db.create_user(
            payload.email,
            auth_core.hash_password(payload.password),
            is_admin=payload.is_admin,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _user_out(user)


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UpdateUserRequest,
    _admin: auth_core.AuthUser = Depends(auth_core.require_admin),
) -> UserOut:
    target = db.get_user_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Guard against locking out the last active admin.
    demotes_admin = (payload.is_active is False) or (payload.is_admin is False)
    if demotes_admin and target.get("is_admin") and db.count_admins() <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the last active admin",
        )
    password_hash = None
    if payload.password is not None:
        if len(payload.password) < _MIN_PASSWORD_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password must be at least {_MIN_PASSWORD_LENGTH} characters",
            )
        password_hash = auth_core.hash_password(payload.password)
    user = db.update_user(
        user_id,
        password_hash=password_hash,
        is_active=payload.is_active,
        is_admin=payload.is_admin,
    )
    assert user is not None
    return _user_out(user)
