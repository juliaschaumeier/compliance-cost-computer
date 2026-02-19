from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.core.auth import ApiKeys, get_api_keys
from backend.core.config import (
    DEEPINFRA_RECOMMENDED,
    GEMINI_RECOMMENDED,
    OPENAI_RECOMMENDED,
    get_deepinfra_models,
    get_gemini_models,
    get_openai_models,
    settings,
)
from backend.core.models import (
    ModelInfo,
    OrganizedModels,
    OrganizedModelsResponse,
    ProviderModels,
)


router = APIRouter(prefix="/models", tags=["models"])


def format_model_name(model_id: str, provider: str) -> str:
    if provider == "OpenAI":
        return (
            model_id.replace("-", " ")
            .replace("gpt", "GPT")
            .replace("o1", "O1")
            .replace("o3", "O3")
            .replace("o4", "O4")
        )
    if provider == "Gemini":
        return model_id.replace("-", " ").replace("gemini", "Gemini")
    name_parts = model_id.split("/")[-1]
    return name_parts.replace("-", " ").replace("_", " ")


def _as_model_info(models: list[str], provider: str) -> list[ModelInfo]:
    return [
        ModelInfo(id=model, name=format_model_name(model, provider), provider=provider)
        for model in models
    ]


@router.get("/organized", response_model=OrganizedModelsResponse)
async def get_organized_models(api_keys: ApiKeys = Depends(get_api_keys)) -> OrganizedModelsResponse:
    openai_models = get_openai_models(api_keys.openai_api_key)
    deepinfra_models = get_deepinfra_models(api_keys.deepinfra_api_key)
    gemini_models = get_gemini_models(api_keys.gemini_api_key)

    openai = ProviderModels(
        recommended=_as_model_info([m for m in OPENAI_RECOMMENDED if m in openai_models], "OpenAI"),
        additional=_as_model_info(sorted([m for m in openai_models if m not in OPENAI_RECOMMENDED]), "OpenAI"),
    )
    deepinfra = ProviderModels(
        recommended=_as_model_info([m for m in DEEPINFRA_RECOMMENDED if m in deepinfra_models], "DeepInfra"),
        additional=_as_model_info(
            sorted([m for m in deepinfra_models if m not in DEEPINFRA_RECOMMENDED]),
            "DeepInfra",
        ),
    )
    gemini = ProviderModels(
        recommended=_as_model_info([m for m in GEMINI_RECOMMENDED if m in gemini_models], "Gemini"),
        additional=_as_model_info(sorted([m for m in gemini_models if m not in GEMINI_RECOMMENDED]), "Gemini"),
    )

    organized = OrganizedModels(openai=openai, deepinfra=deepinfra, gemini=gemini)
    return OrganizedModelsResponse(organized=organized, default=settings.default_model)
