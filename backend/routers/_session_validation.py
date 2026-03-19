from __future__ import annotations

from typing import Annotated

from fastapi import Query
from pydantic import StringConstraints


AppSessionId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$",
    ),
]


APP_SESSION_ID_QUERY_VALIDATION = Query(
    ...,
    min_length=1,
    max_length=64,
    pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$",
)
