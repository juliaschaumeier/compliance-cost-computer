from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

import httpx
import logging
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BASE_DIR / "backend" / "ccc.db"
DEFAULT_REGULATIONS_PATH = BASE_DIR / "regulations"


class Settings(BaseSettings):
    openai_api_key: str = ""
    deepinfra_api_key: str = ""
    gemini_api_key: str = ""
    default_model: str = "gpt-4o"
    enable_web_search: bool = True
    openai_max_tokens: int = 100000
    deepinfra_max_tokens: int = 0
    deepinfra_temperature: float = 0.4
    llm_stream_debug_enabled: bool = True
    llm_console_enabled: bool = True
    prompt_audit_enabled: bool = False
    prompt_audit_output_dir: Path = BASE_DIR / "prompt_audits"
    prompt_audit_session_ids: str = ""
    deep_research_primary_agent: str = "deep-research-preview-04-2026"
    deep_research_fallback_agent: str = "deep-research-pro-preview-12-2025"
    deep_research_poll_interval_seconds: float = 5.0
    # 2026-06-10: Gemini docs state Deep Research has a 60-minute server-side max
    # and most tasks should complete within 20 minutes; keep the local poll cap
    # explicit so stuck interactions cannot run forever.
    deep_research_max_poll_seconds: float = 1800.0
    deep_research_request_timeout_seconds: float = 30.0
    db_path: Path = DEFAULT_DB_PATH
    regulations_path: Path = DEFAULT_REGULATIONS_PATH

    model_config = ConfigDict(env_file=".env")


settings = Settings()

OPENAI_RECOMMENDED = [
    "gpt-5.4",
    "gpt-5.4-mini",
]

DEEPINFRA_RECOMMENDED = [
    "anthropic/claude-sonnet-4-6",
    "deepseek-ai/DeepSeek-V3.2",
]

GEMINI_RECOMMENDED = [
    "gemini-3.1-pro-preview",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
]

GEMINI_EXCLUDED_MODEL_TOKENS = (
    "preview",
    "exp",
    "image",
    "audio",
    "embedding",
    "imagen",
    "veo",
    "lyria",
    "aqa",
    "nano-banana",
    "robotics",
    "computer-use",
    "deep-research",
)


def _is_supported_gemini_text_model(model: str) -> bool:
    if model in GEMINI_RECOMMENDED:
        return True
    model_lower = model.lower()
    return model.startswith("gemini-") and not any(
        token in model_lower for token in GEMINI_EXCLUDED_MODEL_TOKENS
    )


@lru_cache(maxsize=1)
def get_openai_models(api_key: str | None = None) -> List[str]:
    hardcoded_models = list(OPENAI_RECOMMENDED)

    api_key = api_key or settings.openai_api_key
    if not api_key:
        logger.warning("No OpenAI API key provided, using hardcoded models")
        return hardcoded_models

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=10.0) as client:
            response = client.get("https://api.openai.com/v1/models", headers=headers)

        if response.status_code == 200:
            data = response.json()
            if isinstance(data.get("data"), list):
                models = [model["id"] for model in data["data"] if "id" in model]
                text_models = [
                    model
                    for model in models
                    if any(keyword in model.lower() for keyword in [
                        "gpt",
                        "o1",
                        "o3",
                        "o4",
                        "davinci",
                        "curie",
                        "babbage",
                        "ada",
                    ])
                    and not any(exclude in model.lower() for exclude in [
                        "embed",
                        "tts",
                        "whisper",
                        "dall-e",
                        "audio",
                        "stt",
                    ])
                ]
                if text_models:
                    logger.info("Fetched %s OpenAI models", len(text_models))
                    return text_models

        logger.warning(
            "OpenAI API returned status %s, no OpenAI models available",
            response.status_code,
        )
    except Exception as exc:
        logger.error("Failed to fetch OpenAI models: %s", exc)

    return []


@lru_cache(maxsize=1)
def get_deepinfra_models(api_key: str | None = None) -> List[str]:
    hardcoded_models = list(DEEPINFRA_RECOMMENDED)

    api_key = api_key or settings.deepinfra_api_key
    if not api_key:
        logger.warning("No DeepInfra API key provided, using hardcoded models")
        return hardcoded_models

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=10.0) as client:
            response = client.get("https://api.deepinfra.com/v1/openai/models", headers=headers)

        if response.status_code == 200:
            data = response.json()
            if isinstance(data.get("data"), list):
                models = [model["id"] for model in data["data"] if "id" in model]
                text_models = [
                    model
                    for model in models
                    if any(keyword in model.lower() for keyword in [
                        "llama",
                        "anthropic",
                        "claude",
                        "deepseek",
                        "qwen",
                        "mixtral",
                        "phi",
                        "gemma",
                        "mistral",
                        "codellama",
                        "vicuna",
                        "alpaca",
                        "openchat",
                    ])
                ]
                if text_models:
                    logger.info("Fetched %s DeepInfra models", len(text_models))
                    return text_models

        logger.warning(
            "DeepInfra API returned status %s, no DeepInfra models available",
            response.status_code,
        )
    except Exception as exc:
        logger.error("Failed to fetch DeepInfra models: %s", exc)

    return []


@lru_cache(maxsize=1)
def get_gemini_models(api_key: str | None = None) -> List[str]:
    hardcoded_models = list(GEMINI_RECOMMENDED)

    api_key = api_key or settings.gemini_api_key
    if not api_key:
        logger.warning("No Gemini API key provided, using hardcoded models")
        return hardcoded_models

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                "https://generativelanguage.googleapis.com/v1beta/openai/models",
                headers=headers,
            )

        if response.status_code == 200:
            data = response.json()
            if isinstance(data.get("data"), list):
                models = [model["id"] for model in data["data"] if "id" in model]
                normalized = [
                    model.split("/", 1)[1] if model.startswith("models/") else model
                    for model in models
                ]
                text_models = [
                    model
                    for model in normalized
                    if _is_supported_gemini_text_model(model)
                ]
                if text_models:
                    logger.info("Fetched %s Gemini models", len(text_models))
                    return text_models

        logger.warning(
            "Gemini API returned status %s, no Gemini models available",
            response.status_code,
        )
    except Exception as exc:
        logger.error("Failed to fetch Gemini models: %s", exc)

    return []


def is_deepinfra_model(model: str) -> bool:
    model_lower = model.lower()
    return any(token in model_lower for token in ["deepseek", "llama", "mixtral", "mistral", "qwen", "phi", "/"])


def is_gemini_model(model: str) -> bool:
    return model.startswith("gemini-") or model in GEMINI_RECOMMENDED
