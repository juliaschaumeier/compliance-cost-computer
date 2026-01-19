from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List

import httpx
import logging
from pydantic_settings import BaseSettings


logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BASE_DIR / "backend" / "legacy" / "tiles.db"
DEFAULT_SEED_JSON = BASE_DIR / "backend" / "legacy" / "mockup_data.json"


class Settings(BaseSettings):
    openai_api_key: str = ""
    deepinfra_api_key: str = ""
    gemini_api_key: str = ""
    default_model: str = "gpt-4o"
    db_path: Path = DEFAULT_DB_PATH
    seed_json: Path = DEFAULT_SEED_JSON

    class Config:
        env_file = ".env"


settings = Settings()

OPENAI_RECOMMENDED = [
    "o1",
    "o3",
    "o1-mini",
    "o3-mini",
    "o4-mini",
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
]

DEEPINFRA_RECOMMENDED = [
    "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
    "meta-llama/Llama-4-Scout-17B-16E-Instruct",
    "deepseek-ai/DeepSeek-R1-Turbo",
    "deepseek-ai/DeepSeek-R1",
    "deepseek-ai/DeepSeek-V3-0324",
]

GEMINI_RECOMMENDED = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]


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

        logger.warning("OpenAI API returned status %s, using hardcoded models", response.status_code)
    except Exception as exc:
        logger.error("Failed to fetch OpenAI models: %s", exc)

    return hardcoded_models


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

        logger.warning("DeepInfra API returned status %s, using hardcoded models", response.status_code)
    except Exception as exc:
        logger.error("Failed to fetch DeepInfra models: %s", exc)

    return hardcoded_models


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
                text_models = [model for model in models if model.startswith("gemini-")]
                if text_models:
                    logger.info("Fetched %s Gemini models", len(text_models))
                    return text_models

        logger.warning("Gemini API returned status %s, using hardcoded models", response.status_code)
    except Exception as exc:
        logger.error("Failed to fetch Gemini models: %s", exc)

    return hardcoded_models


def is_deepinfra_model(model: str) -> bool:
    model_lower = model.lower()
    return any(token in model_lower for token in ["deepseek", "llama", "mixtral", "mistral", "qwen", "phi", "/"])


def is_gemini_model(model: str) -> bool:
    return model.startswith("gemini-") or model in GEMINI_RECOMMENDED


def get_all_available_models(api_key_map: Dict[str, str] | None = None) -> Dict[str, List[str]]:
    api_key_map = api_key_map or {}
    return {
        "openai": get_openai_models(api_key_map.get("openai")),
        "deepinfra": get_deepinfra_models(api_key_map.get("deepinfra")),
        "gemini": get_gemini_models(api_key_map.get("gemini")),
    }


def get_organized_models(api_key_map: Dict[str, str] | None = None) -> Dict[str, Dict[str, List[str]]]:
    api_key_map = api_key_map or {}
    all_openai = get_openai_models(api_key_map.get("openai"))
    all_deepinfra = get_deepinfra_models(api_key_map.get("deepinfra"))
    all_gemini = get_gemini_models(api_key_map.get("gemini"))

    return {
        "openai": {
            "recommended": [model for model in OPENAI_RECOMMENDED if model in all_openai],
            "additional": sorted([model for model in all_openai if model not in OPENAI_RECOMMENDED]),
        },
        "deepinfra": {
            "recommended": [model for model in DEEPINFRA_RECOMMENDED if model in all_deepinfra],
            "additional": sorted([model for model in all_deepinfra if model not in DEEPINFRA_RECOMMENDED]),
        },
        "gemini": {
            "recommended": [model for model in GEMINI_RECOMMENDED if model in all_gemini],
            "additional": sorted([model for model in all_gemini if model not in GEMINI_RECOMMENDED]),
        },
    }
