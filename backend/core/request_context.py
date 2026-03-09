from __future__ import annotations

from contextvars import ContextVar, Token


_REQUEST_CONTEXT: ContextVar[dict[str, str | None]] = ContextVar(
    "request_context",
    default={},
)


def bind_request_context(
    *,
    request_id: str,
    route_method: str,
    route_path: str,
    app_session_id: str | None = None,
) -> Token[dict[str, str | None]]:
    return _REQUEST_CONTEXT.set(
        {
            "request_id": request_id,
            "route_method": route_method,
            "route_path": route_path,
            "app_session_id": app_session_id,
        }
    )


def reset_request_context(token: Token[dict[str, str | None]]) -> None:
    _REQUEST_CONTEXT.reset(token)


def get_request_context() -> dict[str, str | None]:
    value = _REQUEST_CONTEXT.get()
    if not isinstance(value, dict):
        return {}
    return {
        "request_id": value.get("request_id"),
        "route_method": value.get("route_method"),
        "route_path": value.get("route_path"),
        "app_session_id": value.get("app_session_id"),
    }
