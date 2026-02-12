from __future__ import annotations

from typing import Optional

import httpx
from openai import AsyncOpenAI, NotFoundError

from .auth import ApiKeys
from .config import is_deepinfra_model, is_gemini_model, settings


DEEPINFRA_BASE_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


async def query_llm(
    prompt: str,
    api_keys: ApiKeys,
    model: str,
    provider: Optional[str] = None,
) -> str:
    provider = (provider or "").lower().strip()
    if not provider:
        if is_deepinfra_model(model):
            provider = "deepinfra"
        elif is_gemini_model(model):
            provider = "gemini"
        else:
            provider = "openai"

    if provider == "deepinfra":
        return await query_deepinfra(prompt, api_keys.deepinfra_api_key, model)
    if provider == "gemini":
        return await query_gemini_openai(prompt, api_keys.gemini_api_key, model)
    return await query_openai(prompt, api_keys.openai_api_key, model)


async def query_openai(prompt: str, api_key: str, model: str) -> str:
    if not api_key:
        raise ValueError("Missing OpenAI API key")
    client = AsyncOpenAI(api_key=api_key)
    if model.lower().startswith("gpt-5"):
        return await _query_openai_responses(client, prompt, model)

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if settings.enable_web_search:
        payload["tools"] = [{"type": "web_search"}]
    try:
        response = await client.chat.completions.create(**payload)
        return response.choices[0].message.content or ""
    except NotFoundError as exc:
        if "not a chat model" in str(exc).lower():
            return await _query_openai_responses(client, prompt, model)
        raise
    except Exception:
        if not settings.enable_web_search:
            raise
        payload.pop("tools", None)
        response = await client.chat.completions.create(**payload)
        return response.choices[0].message.content or ""


async def query_gemini_openai(prompt: str, api_key: str, model: str) -> str:
    if not api_key:
        raise ValueError("Missing Gemini API key")
    client = AsyncOpenAI(api_key=api_key, base_url=GEMINI_OPENAI_BASE_URL)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if settings.enable_web_search:
        payload["tools"] = [{"type": "web_search"}]
    try:
        response = await client.chat.completions.create(**payload)
    except Exception:
        if not settings.enable_web_search:
            raise
        payload.pop("tools", None)
        response = await client.chat.completions.create(**payload)
    return response.choices[0].message.content or ""


async def _query_openai_responses(
    client: AsyncOpenAI, prompt: str, model: str
) -> str:
    payload = {"model": model, "input": prompt}
    if settings.enable_web_search:
        payload["tools"] = [{"type": "web_search"}]
    try:
        response = await client.responses.create(**payload)
    except Exception:
        if not settings.enable_web_search:
            raise
        payload.pop("tools", None)
        response = await client.responses.create(**payload)
    return _extract_response_text(response)


def _extract_response_text(response) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return text
    outputs = getattr(response, "output", None) or []
    collected: list[str] = []
    for output in outputs:
        for content in getattr(output, "content", []) or []:
            if isinstance(content, dict):
                if content.get("type") == "output_text" and content.get("text"):
                    collected.append(str(content["text"]))
            else:
                text_value = getattr(content, "text", None)
                if text_value:
                    collected.append(str(text_value))
    return "\n".join(collected).strip()


async def query_deepinfra(prompt: str, api_key: str, model: str) -> str:
    if not api_key:
        raise ValueError("Missing DeepInfra API key")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": settings.deepinfra_temperature,
    }
    if settings.deepinfra_max_tokens > 0:
        payload["max_tokens"] = settings.deepinfra_max_tokens
    timeout = httpx.Timeout(600.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(DEEPINFRA_BASE_URL, headers=headers, json=payload)
        if response.status_code != 200:
            raise RuntimeError(
                f"DeepInfra API error {response.status_code}: {response.text}"
            )
        result = response.json()
        if "choices" not in result or not result["choices"]:
            raise RuntimeError("Unexpected DeepInfra response format")
        return result["choices"][0]["message"]["content"] or ""
