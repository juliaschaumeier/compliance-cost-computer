from __future__ import annotations

from typing import Optional

import httpx
from openai import AsyncOpenAI

from .auth import ApiKeys
from .config import is_deepinfra_model, is_gemini_model


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
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


async def query_gemini_openai(prompt: str, api_key: str, model: str) -> str:
    if not api_key:
        raise ValueError("Missing Gemini API key")
    client = AsyncOpenAI(api_key=api_key, base_url=GEMINI_OPENAI_BASE_URL)
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


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
        "temperature": 0.7,
        "max_tokens": 2048,
    }
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
