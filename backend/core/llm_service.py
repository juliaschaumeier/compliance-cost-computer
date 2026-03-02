from __future__ import annotations

"""
LLM provider access + token/cost normalization.

Billing overview:
- Each provider call returns token usage metadata in slightly different shapes.
- We normalize these into `LlmResult` fields (`input_tokens`, `output_tokens`,
  `hidden_thinking_tokens`, `estimated_cost_usd`).
- `estimated_cost_usd` is resolved as:
  1) provider-reported cost (if present),
  2) otherwise fallback estimate from token counts + static price map.

DB integration:
- This module does not write to DB directly.
- Routers pass `LlmResult` to `backend/core/llm_attempts.py`, which persists into
  `llm_answers` via `backend/core/db.py`.
"""

import asyncio
from dataclasses import dataclass
import json
from typing import Any, Optional

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    NotFoundError,
    RateLimitError,
)

from .auth import ApiKeys
from .config import is_deepinfra_model, is_gemini_model, settings


DEEPINFRA_BASE_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


@dataclass
class LlmResult:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    hidden_thinking_tokens: int | None = None
    estimated_cost_usd: float | None = None
    provider_response_json: dict[str, Any] | list[Any] | None = None


class LlmQueryError(RuntimeError):
    """Normalized provider query failure with machine-readable reason."""

    def __init__(
        self,
        *,
        provider: str,
        model: str,
        reason: str,
        message: str,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.reason = reason
        self.status_code = status_code
        self.details = details

    def __str__(self) -> str:
        prefix = f"{self.provider}:{self.reason}"
        if self.status_code is not None:
            prefix = f"{prefix}:{self.status_code}"
        return f"{prefix} - {self.args[0]}"


@dataclass
class _UsageStats:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


async def query_llm(
    prompt: str,
    api_keys: ApiKeys,
    model: str,
    provider: Optional[str] = None,
) -> LlmResult:
    """Route one prompt to the selected provider and return normalized usage/cost."""
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


async def query_openai(prompt: str, api_key: str, model: str) -> LlmResult:
    if not api_key:
        raise ValueError("Missing OpenAI API key")
    client = AsyncOpenAI(api_key=api_key)
    if model.lower().startswith("gpt-5"):
        return await _query_openai_responses(client, prompt, model)

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if settings.openai_max_tokens > 0:
        payload["max_tokens"] = settings.openai_max_tokens
    if settings.enable_web_search:
        payload["tools"] = [{"type": "web_search"}]
    try:
        response = await client.chat.completions.create(**payload)
    except NotFoundError as exc:
        if "not a chat model" in str(exc).lower():
            return await _query_openai_responses(client, prompt, model)
        raise
    except Exception as exc:
        if not settings.enable_web_search:
            raise _normalize_llm_exception(
                provider="openai",
                model=model,
                exc=exc,
            ) from exc
        payload.pop("tools", None)
        try:
            response = await client.chat.completions.create(**payload)
        except Exception as retry_exc:
            raise _normalize_llm_exception(
                provider="openai",
                model=model,
                exc=retry_exc,
            ) from retry_exc
    text = response.choices[0].message.content or ""
    usage = _extract_chat_usage(response)
    response_json = _to_jsonable_response(response)
    hidden_thinking_tokens = _extract_hidden_thinking_tokens(
        provider="openai",
        response_json=response_json,
    )
    provider_reported_cost_usd = _extract_provider_reported_cost_usd(response_json)
    billable_output_tokens = _resolve_billable_output_tokens(
        provider="openai",
        output_tokens=usage.output_tokens,
        response_json=response_json,
        hidden_thinking_tokens=hidden_thinking_tokens,
    )
    return LlmResult(
        text=text,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        hidden_thinking_tokens=hidden_thinking_tokens,
        estimated_cost_usd=_resolve_estimated_cost_usd(
            provider="openai",
            model=model,
            input_tokens=usage.input_tokens,
            output_tokens=billable_output_tokens,
            provider_reported_cost_usd=provider_reported_cost_usd,
        ),
        provider_response_json=response_json,
    )


async def query_gemini_openai(prompt: str, api_key: str, model: str) -> LlmResult:
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
    except Exception as exc:
        if not settings.enable_web_search:
            raise _normalize_llm_exception(
                provider="gemini",
                model=model,
                exc=exc,
            ) from exc
        payload.pop("tools", None)
        try:
            response = await client.chat.completions.create(**payload)
        except Exception as retry_exc:
            raise _normalize_llm_exception(
                provider="gemini",
                model=model,
                exc=retry_exc,
            ) from retry_exc
    text = response.choices[0].message.content or ""
    usage = _extract_chat_usage(response)
    response_json = _to_jsonable_response(response)
    hidden_thinking_tokens = _extract_hidden_thinking_tokens(
        provider="gemini",
        response_json=response_json,
    )
    provider_reported_cost_usd = _extract_provider_reported_cost_usd(response_json)
    billable_output_tokens = _resolve_billable_output_tokens(
        provider="gemini",
        output_tokens=usage.output_tokens,
        response_json=response_json,
        hidden_thinking_tokens=hidden_thinking_tokens,
    )
    return LlmResult(
        text=text,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        hidden_thinking_tokens=hidden_thinking_tokens,
        estimated_cost_usd=_resolve_estimated_cost_usd(
            provider="gemini",
            model=model,
            input_tokens=usage.input_tokens,
            output_tokens=billable_output_tokens,
            provider_reported_cost_usd=provider_reported_cost_usd,
        ),
        provider_response_json=response_json,
    )


async def _query_openai_responses(
    client: AsyncOpenAI, prompt: str, model: str
) -> LlmResult:
    payload = {"model": model, "input": prompt}
    if settings.openai_max_tokens > 0:
        payload["max_output_tokens"] = settings.openai_max_tokens
    if settings.enable_web_search:
        payload["tools"] = [{"type": "web_search"}]
    try:
        response = await client.responses.create(**payload)
    except Exception as exc:
        if not settings.enable_web_search:
            raise _normalize_llm_exception(
                provider="openai",
                model=model,
                exc=exc,
            ) from exc
        payload.pop("tools", None)
        try:
            response = await client.responses.create(**payload)
        except Exception as retry_exc:
            raise _normalize_llm_exception(
                provider="openai",
                model=model,
                exc=retry_exc,
            ) from retry_exc
    usage = _extract_responses_usage(response)
    response_json = _to_jsonable_response(response)
    hidden_thinking_tokens = _extract_hidden_thinking_tokens(
        provider="openai",
        response_json=response_json,
    )
    provider_reported_cost_usd = _extract_provider_reported_cost_usd(response_json)
    billable_output_tokens = _resolve_billable_output_tokens(
        provider="openai",
        output_tokens=usage.output_tokens,
        response_json=response_json,
        hidden_thinking_tokens=hidden_thinking_tokens,
    )
    return LlmResult(
        text=_extract_response_text(response),
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        hidden_thinking_tokens=hidden_thinking_tokens,
        estimated_cost_usd=_resolve_estimated_cost_usd(
            provider="openai",
            model=model,
            input_tokens=usage.input_tokens,
            output_tokens=billable_output_tokens,
            provider_reported_cost_usd=provider_reported_cost_usd,
        ),
        provider_response_json=response_json,
    )


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


async def query_deepinfra(prompt: str, api_key: str, model: str) -> LlmResult:
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
        try:
            response = await client.post(
                DEEPINFRA_BASE_URL,
                headers=headers,
                json=payload,
            )
        except Exception as exc:
            raise _normalize_llm_exception(
                provider="deepinfra",
                model=model,
                exc=exc,
            ) from exc
        if response.status_code != 200:
            response_json: dict[str, Any] | list[Any] | None = None
            try:
                response_json = response.json()
            except Exception:
                response_json = None
            raise LlmQueryError(
                provider="deepinfra",
                model=model,
                reason=(
                    "rate_limit"
                    if response.status_code == 429
                    else "provider_timeout"
                    if response.status_code in {408, 504}
                    else "provider_http_error"
                ),
                status_code=response.status_code,
                message=response.text or "DeepInfra API error",
                details={
                    "http_status": response.status_code,
                    "response_headers": dict(response.headers or {}),
                    "response_json": response_json,
                    "response_text": response.text or "",
                },
            )
        result = response.json()
        if "choices" not in result or not result["choices"]:
            raise RuntimeError("Unexpected DeepInfra response format")
        usage = _extract_deepinfra_usage(result)
        hidden_thinking_tokens = _extract_hidden_thinking_tokens(
            provider="deepinfra",
            response_json=result,
        )
        provider_reported_cost_usd = _extract_provider_reported_cost_usd(result)
        billable_output_tokens = _resolve_billable_output_tokens(
            provider="deepinfra",
            output_tokens=usage.output_tokens,
            response_json=result,
            hidden_thinking_tokens=hidden_thinking_tokens,
        )
        return LlmResult(
            text=result["choices"][0]["message"]["content"] or "",
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            hidden_thinking_tokens=hidden_thinking_tokens,
            estimated_cost_usd=_resolve_estimated_cost_usd(
                provider="deepinfra",
                model=model,
                input_tokens=usage.input_tokens,
                output_tokens=billable_output_tokens,
                provider_reported_cost_usd=provider_reported_cost_usd,
            ),
            provider_response_json=result,
        )


def coerce_llm_result(result: str | LlmResult) -> LlmResult:
    if isinstance(result, LlmResult):
        return result
    return LlmResult(text=str(result))


def _extract_chat_usage(response) -> _UsageStats:
    usage = getattr(response, "usage", None)
    if usage is None:
        return _UsageStats()
    input_tokens = _as_int(getattr(usage, "prompt_tokens", None))
    output_tokens = _as_int(getattr(usage, "completion_tokens", None))
    total_tokens = _as_int(getattr(usage, "total_tokens", None))
    return _UsageStats(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def _extract_responses_usage(response) -> _UsageStats:
    usage = getattr(response, "usage", None)
    if usage is None:
        return _UsageStats()
    input_tokens = _as_int(getattr(usage, "input_tokens", None))
    output_tokens = _as_int(getattr(usage, "output_tokens", None))
    total_tokens = _as_int(getattr(usage, "total_tokens", None))
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    return _UsageStats(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def _extract_deepinfra_usage(result: dict) -> _UsageStats:
    usage = result.get("usage")
    if not isinstance(usage, dict):
        return _UsageStats()
    input_tokens = _as_int(usage.get("prompt_tokens"))
    output_tokens = _as_int(usage.get("completion_tokens"))
    total_tokens = _as_int(usage.get("total_tokens"))
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    return _UsageStats(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def _as_int(value) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_llm_exception(
    provider: str,
    model: str,
    exc: Exception,
) -> LlmQueryError:
    if isinstance(exc, LlmQueryError):
        return exc

    reason = "provider_error"
    status_code: int | None = None
    details: dict[str, Any] = {
        "exception_type": exc.__class__.__name__,
    }
    if isinstance(exc, (APITimeoutError, httpx.TimeoutException, asyncio.TimeoutError, TimeoutError)):
        reason = "provider_timeout"
    elif isinstance(exc, RateLimitError):
        reason = "rate_limit"
        status_code = 429
    elif isinstance(exc, APIConnectionError):
        reason = "provider_connection_error"
    elif isinstance(exc, APIStatusError):
        status_code = int(exc.status_code) if exc.status_code is not None else None
        response = getattr(exc, "response", None)
        response_body = getattr(exc, "body", None)
        if response is not None:
            details["response_status_code"] = getattr(response, "status_code", None)
            details["response_headers"] = dict(getattr(response, "headers", {}) or {})
            request = getattr(response, "request", None)
            if request is not None:
                details["request_url"] = str(getattr(request, "url", ""))
                details["request_method"] = getattr(request, "method", None)
        if response_body is not None:
            details["response_body"] = response_body
        if status_code == 429:
            reason = "rate_limit"
        elif status_code in {408, 504}:
            reason = "provider_timeout"
        else:
            reason = "provider_http_error"
    elif isinstance(
        exc,
        (
            httpx.ConnectError,
            httpx.ReadError,
            httpx.RemoteProtocolError,
            httpx.NetworkError,
            httpx.ProtocolError,
            httpx.HTTPError,
        ),
    ):
        reason = "provider_connection_error"

    return LlmQueryError(
        provider=provider,
        model=model,
        reason=reason,
        status_code=status_code,
        message=str(exc),
        details=details,
    )


def _extract_nested(data: Any, path: list[str]) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _first_int(data: Any, paths: list[list[str]]) -> int | None:
    for path in paths:
        value = _extract_nested(data, path)
        parsed = _as_int(value)
        if parsed is not None:
            return parsed
    return None


def _first_float(data: Any, paths: list[list[str]]) -> float | None:
    for path in paths:
        value = _extract_nested(data, path)
        parsed = _as_float(value)
        if parsed is not None:
            return parsed
    return None


def _extract_hidden_thinking_tokens(
    provider: str,
    response_json: dict[str, Any] | list[Any] | None,
) -> int | None:
    """
    Extract provider-specific hidden reasoning/thought token counts.

    These tokens are useful for observability and may be billable depending on
    provider rules/model family.
    """
    if not isinstance(response_json, dict):
        return None

    common_reasoning = _first_int(
        response_json,
        [
            ["usage", "output_tokens_details", "reasoning_tokens"],
            ["usage", "completion_tokens_details", "reasoning_tokens"],
            ["usage", "outputTokensDetails", "reasoningTokens"],
            ["usage", "completionTokensDetails", "reasoningTokens"],
        ],
    )
    if provider == "openai":
        return common_reasoning

    if provider == "gemini":
        gemini_thoughts = _first_int(
            response_json,
            [
                ["usageMetadata", "thoughtsTokenCount"],
                ["usage_metadata", "thoughts_token_count"],
                ["usage", "thoughtsTokenCount"],
                ["usage", "thoughts_tokens"],
            ],
        )
        if gemini_thoughts is not None:
            return gemini_thoughts
        return common_reasoning

    return common_reasoning


def _resolve_billable_output_tokens(
    provider: str,
    output_tokens: int | None,
    response_json: dict[str, Any] | list[Any] | None,
    hidden_thinking_tokens: int | None = None,
) -> int | None:
    """
    Resolve output tokens used for fallback cost estimation.

    For Gemini, thoughts can be reported separately; we include them without
    double-counting if completion/output totals already contain them.
    """
    if provider != "gemini":
        return output_tokens
    if not isinstance(response_json, dict):
        return output_tokens

    candidates_tokens = _first_int(
        response_json,
        [
            ["usageMetadata", "candidatesTokenCount"],
            ["usage_metadata", "candidates_token_count"],
        ],
    )
    thoughts_tokens = _extract_hidden_thinking_tokens(
        provider="gemini",
        response_json=response_json,
    )
    if thoughts_tokens is None:
        thoughts_tokens = hidden_thinking_tokens

    combined: int | None = None
    if candidates_tokens is not None or thoughts_tokens is not None:
        combined = (candidates_tokens or 0) + (thoughts_tokens or 0)

    if combined is None:
        return output_tokens
    if output_tokens is None:
        return combined
    # Avoid double-counting when completion_tokens already includes thinking.
    return max(output_tokens, combined)


def _extract_provider_reported_cost_usd(
    response_json: dict[str, Any] | list[Any] | None,
) -> float | None:
    """Read provider-reported request cost when exposed by the API payload."""
    if not isinstance(response_json, dict):
        return None
    return _first_float(
        response_json,
        [
            ["usage", "estimated_cost"],
            ["usage", "estimatedCost"],
            ["usage", "estimated_cost_usd"],
        ],
    )


def _resolve_estimated_cost_usd(
    provider: str,
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
    provider_reported_cost_usd: float | None = None,
) -> float | None:
    """
    Final per-call cost value persisted to DB.

    Preference order:
    1) provider-reported USD cost (more precise for provider-side pricing details),
    2) fallback estimate from local token/rate map.
    """
    if provider_reported_cost_usd is not None:
        return round(provider_reported_cost_usd, 8)
    return _estimate_cost_usd(
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _estimate_cost_usd(
    provider: str,
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
) -> float | None:
    if input_tokens is None and output_tokens is None:
        return None

    # Standard API pricing, USD per 1M tokens.
    # Sources (checked on 2026-02-27):
    # - https://openai.com/api/pricing
    # - https://ai.google.dev/gemini-api/docs/pricing
    pricing_per_million: dict[str, dict[str, tuple[float, float]]] = {
        "openai": {
            "gpt-5.2-pro": (21.00, 168.00),
            "gpt-5.2": (1.75, 14.00),
            "gpt-5-pro": (15.00, 120.00),
            "gpt-5.1": (1.25, 10.00),
            "gpt-5-mini": (0.25, 2.00),
            "gpt-5-nano": (0.05, 0.40),
            "gpt-5": (1.25, 10.00),
            "gpt-4.1-mini": (0.40, 1.60),
            "gpt-4.1-nano": (0.10, 0.40),
            "gpt-4.1": (2.00, 8.00),
            "gpt-4o-mini": (0.15, 0.60),
            "gpt-4o": (2.50, 10.00),
        },
        "gemini": {
            "gemini-2.5-pro": (1.25, 10.00),
            "gemini-2.5-flash-lite": (0.10, 0.40),
            "gemini-2.5-flash": (0.30, 2.50),
        },
    }
    provider_pricing = pricing_per_million.get(provider.lower(), {})
    model_lc = model.lower()
    matched: tuple[float, float] | None = None
    # Prefer the most specific prefix first (e.g., gpt-5.2-pro before gpt-5.2).
    for name in sorted(provider_pricing.keys(), key=len, reverse=True):
        if model_lc == name or model_lc.startswith(name):
            matched = provider_pricing[name]
            break
    if matched is None:
        return None

    input_price_per_million, output_price_per_million = matched
    in_cost = ((input_tokens or 0) / 1_000_000.0) * input_price_per_million
    out_cost = ((output_tokens or 0) / 1_000_000.0) * output_price_per_million
    return round(in_cost + out_cost, 8)


def _to_jsonable_response(response: Any) -> dict[str, Any] | list[Any] | None:
    if response is None:
        return None
    if isinstance(response, (dict, list)):
        return response

    model_dump_json = getattr(response, "model_dump_json", None)
    if callable(model_dump_json):
        try:
            dumped = model_dump_json()
            loaded = json.loads(dumped)
            if isinstance(loaded, (dict, list)):
                return loaded
        except Exception:
            pass

    model_dump = getattr(response, "model_dump", None)
    if callable(model_dump):
        try:
            dumped = model_dump()
            if isinstance(dumped, (dict, list)):
                return dumped
        except Exception:
            pass

    try:
        serialized = json.dumps(response, default=str, ensure_ascii=False)
        loaded = json.loads(serialized)
        if isinstance(loaded, (dict, list)):
            return loaded
    except Exception:
        pass

    return {"raw": str(response)}
