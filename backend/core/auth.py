from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Header

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
