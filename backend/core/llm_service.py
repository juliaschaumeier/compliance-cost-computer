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
import re
from typing import Any, Awaitable, Callable, Optional

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
OPENAI_SAFE_MAX_OUTPUT_TOKENS = 100_000


def _openai_chat_token_limit_key(model: str) -> str:
    model_name = _openai_model_name(model)
    if model_name.startswith(("o1", "o3", "o4")):
        return "max_completion_tokens"
    return "max_tokens"


def _openai_model_name(model: str) -> str:
    return model.lower().strip().rsplit("/", 1)[-1].replace("_", "-").replace(" ", "-")


def _openai_chat_max_tokens(model: str, configured_max_tokens: int) -> int:
    if configured_max_tokens <= 0:
        return configured_max_tokens
    model_name = _openai_model_name(model)
    if model_name.startswith("o4-mini"):
        return min(configured_max_tokens, OPENAI_SAFE_MAX_OUTPUT_TOKENS)
    return configured_max_tokens


def _openai_safe_max_tokens(configured_max_tokens: int) -> int:
    if configured_max_tokens <= 0:
        return configured_max_tokens
    return min(configured_max_tokens, OPENAI_SAFE_MAX_OUTPUT_TOKENS)


def _openai_chat_payload_token_limit_key(payload: dict[str, Any]) -> str | None:
    if "max_tokens" in payload:
        return "max_tokens"
    if "max_completion_tokens" in payload:
        return "max_completion_tokens"
    return None


def _openai_chat_retry_payload_for_token_error(
    payload: dict[str, Any],
    exc: Exception,
) -> dict[str, Any] | None:
    message = str(exc)
    lowered = message.lower()
    current_key = _openai_chat_payload_token_limit_key(payload)
    if current_key == "max_tokens" and (
        "unsupported parameter" in lowered and "max_tokens" in lowered
    ):
        retry_payload = dict(payload)
        retry_payload["max_completion_tokens"] = retry_payload.pop("max_tokens")
        return retry_payload

    if current_key is None:
        return None

    match = re.search(r"supports at most\s+([0-9][0-9,_.]*)\s+completion tokens", lowered)
    if not match:
        return None
    raw_limit = match.group(1).replace(",", "").replace("_", "").replace(".", "")
    try:
        provider_limit = int(raw_limit)
    except ValueError:
        return None
    current_value = payload.get(current_key)
    if not isinstance(current_value, int) or current_value <= provider_limit:
        return None
    retry_payload = dict(payload)
    retry_payload[current_key] = provider_limit
    return retry_payload


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


StreamEventHandler = Callable[[dict[str, Any]], Awaitable[None] | None]


async def _emit_stream_event(
    on_event: StreamEventHandler | None,
    payload: dict[str, Any],
) -> None:
    if on_event is None:
        return
    maybe_awaitable = on_event(payload)
    if asyncio.iscoroutine(maybe_awaitable):
        await maybe_awaitable


async def query_llm(
    prompt: str,
    api_keys: ApiKeys,
    model: str,
    provider: Optional[str] = None,
    stream: bool = False,
    on_event: StreamEventHandler | None = None,
    response_format: dict[str, Any] | None = None,
) -> LlmResult:
    """Route one prompt to the selected provider and return normalized usage/cost.

    `response_format` erzwingt (wo der Provider/das Modell es unterstuetzt) die
    JSON-Ausgabe bereits am Generierungszeitpunkt. Lehnt der Provider den
    Parameter ab (Bad Request), wird der Call einmal ohne Erzwingung wiederholt,
    sodass der Workflow nicht an fehlender Provider-Unterstuetzung scheitert.
    """
    provider = (provider or "").lower().strip()
    if not provider:
        if is_deepinfra_model(model):
            provider = "deepinfra"
        elif is_gemini_model(model):
            provider = "gemini"
        else:
            provider = "openai"

    async def _dispatch(active_response_format: dict[str, Any] | None) -> LlmResult:
        if provider == "deepinfra":
            return await query_deepinfra(
                prompt,
                api_keys.deepinfra_api_key,
                model,
                stream=stream,
                on_event=on_event,
                response_format=active_response_format,
            )
        if provider == "gemini":
            return await query_gemini_openai(
                prompt,
                api_keys.gemini_api_key,
                model,
                stream=stream,
                on_event=on_event,
                response_format=active_response_format,
            )
        return await query_openai(
            prompt,
            api_keys.openai_api_key,
            model,
            stream=stream,
            on_event=on_event,
            response_format=active_response_format,
        )

    if response_format is None:
        return await _dispatch(None)
    try:
        return await _dispatch(response_format)
    except LlmQueryError as exc:
        # Graceful fallback: Provider/Modell lehnt response_format ab (Bad
        # Request) -> einmal ohne strukturierte JSON-Erzwingung wiederholen,
        # statt den Workflow-Schritt scheitern zu lassen.
        if exc.status_code == 400:
            return await _dispatch(None)
        raise


def _is_stream_unsupported_error(exc: Exception) -> bool:
    message = str(exc).lower()
    if "stream" not in message:
        return False
    keywords = [
        "unsupported",
        "not support",
        "unknown parameter",
        "invalid parameter",
        "not available",
    ]
    if any(keyword in message for keyword in keywords):
        return True
    status_code = getattr(exc, "status_code", None)
    return status_code in {400, 404, 422}


def _extract_stream_delta_text(chunk_json: dict[str, Any] | None) -> str:
    if not isinstance(chunk_json, dict):
        return ""
    choices = chunk_json.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    choice0 = choices[0]
    if not isinstance(choice0, dict):
        return ""
    delta = choice0.get("delta")
    if not isinstance(delta, dict):
        return ""
    content = delta.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        pieces: list[str] = []
        for part in content:
            if isinstance(part, str):
                pieces.append(part)
            elif isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str) and text:
                    pieces.append(text)
        return "".join(pieces)
    return ""


async def _query_chat_completions_once(
    *,
    provider: str,
    client: AsyncOpenAI,
    payload: dict[str, Any],
    model: str,
) -> LlmResult:
    response = await client.chat.completions.create(**payload)
    text = response.choices[0].message.content or ""
    usage = _extract_chat_usage(response)
    response_json = _to_jsonable_response(response)
    hidden_thinking_tokens = _extract_hidden_thinking_tokens(
        provider=provider,
        response_json=response_json,
    )
    provider_reported_cost_usd = _extract_provider_reported_cost_usd(response_json)
    billable_output_tokens = _resolve_billable_output_tokens(
        provider=provider,
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
            provider=provider,
            model=model,
            input_tokens=usage.input_tokens,
            output_tokens=billable_output_tokens,
            provider_reported_cost_usd=provider_reported_cost_usd,
        ),
        provider_response_json=response_json,
    )


async def _query_chat_completions_stream(
    *,
    provider: str,
    client: AsyncOpenAI,
    payload: dict[str, Any],
    model: str,
    on_event: StreamEventHandler | None,
) -> LlmResult:
    stream_payload = {**payload, "stream": True}
    stream_payload.setdefault("stream_options", {"include_usage": True})
    await _emit_stream_event(
        on_event,
        {
            "event_type": "llm_stream_started",
            "stream_mode": "provider_stream",
        },
    )

    chunk_index = 0
    collected: list[str] = []
    cumulative_chars = 0
    usage = _UsageStats()
    last_chunk_json: dict[str, Any] | None = None

    try:
        stream_handle = await client.chat.completions.create(**stream_payload)
        async for chunk in stream_handle:
            chunk_index += 1
            chunk_json_raw = _to_jsonable_response(chunk)
            chunk_json = chunk_json_raw if isinstance(chunk_json_raw, dict) else None
            if chunk_json is not None:
                last_chunk_json = chunk_json
            delta_text = _extract_stream_delta_text(chunk_json)
            if delta_text:
                collected.append(delta_text)
                cumulative_chars += len(delta_text)
                await _emit_stream_event(
                    on_event,
                    {
                        "event_type": "llm_stream_delta",
                        "chunk_index": chunk_index,
                        "delta_text": delta_text,
                        "delta_chars": len(delta_text),
                        "cumulative_chars": cumulative_chars,
                    },
                )

            chunk_usage = _extract_chat_usage(chunk)
            if any(
                value is not None
                for value in [
                    chunk_usage.input_tokens,
                    chunk_usage.output_tokens,
                    chunk_usage.total_tokens,
                ]
            ):
                usage = chunk_usage
    except Exception as exc:
        await _emit_stream_event(
            on_event,
            {
                "event_type": "llm_stream_failed",
                "error": str(exc),
            },
        )
        raise

    text = "".join(collected)
    response_json: dict[str, Any] = {
        "streamed": True,
        "chunk_count": chunk_index,
        "final_chunk": last_chunk_json,
    }
    hidden_thinking_tokens = _extract_hidden_thinking_tokens(
        provider=provider,
        response_json=response_json,
    )
    provider_reported_cost_usd = _extract_provider_reported_cost_usd(response_json)
    billable_output_tokens = _resolve_billable_output_tokens(
        provider=provider,
        output_tokens=usage.output_tokens,
        response_json=response_json,
        hidden_thinking_tokens=hidden_thinking_tokens,
    )
    estimated_cost_usd = _resolve_estimated_cost_usd(
        provider=provider,
        model=model,
        input_tokens=usage.input_tokens,
        output_tokens=billable_output_tokens,
        provider_reported_cost_usd=provider_reported_cost_usd,
    )
    await _emit_stream_event(
        on_event,
        {
            "event_type": "llm_stream_completed",
            "chunk_count": chunk_index,
            "output_chars": len(text),
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "hidden_thinking_tokens": hidden_thinking_tokens,
            "estimated_cost_usd": estimated_cost_usd,
        },
    )
    return LlmResult(
        text=text,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        hidden_thinking_tokens=hidden_thinking_tokens,
        estimated_cost_usd=estimated_cost_usd,
        provider_response_json=response_json,
    )


async def query_openai(
    prompt: str,
    api_key: str,
    model: str,
    *,
    stream: bool = False,
    on_event: StreamEventHandler | None = None,
    response_format: dict[str, Any] | None = None,
) -> LlmResult:
    if not api_key:
        raise ValueError("Missing OpenAI API key")
    client = AsyncOpenAI(api_key=api_key)
    if model.lower().startswith("gpt-5"):
        if stream:
            try:
                return await _query_openai_responses_stream(
                    client=client,
                    prompt=prompt,
                    model=model,
                    on_event=on_event,
                    response_format=response_format,
                )
            except Exception as exc:
                if _is_stream_unsupported_error(exc):
                    await _emit_stream_event(
                        on_event,
                        {
                            "event_type": "llm_stream_fallback",
                            "stream_mode": "fallback_non_stream",
                            "reason": "provider_rejected_stream",
                            "error": str(exc),
                        },
                    )
                    return await _query_openai_responses(client, prompt, model, response_format=response_format)
                raise _normalize_llm_exception(
                    provider="openai",
                    model=model,
                    exc=exc,
                ) from exc
        return await _query_openai_responses(client, prompt, model, response_format=response_format)

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if response_format is not None:
        payload["response_format"] = response_format
    if settings.openai_max_tokens > 0:
        payload[_openai_chat_token_limit_key(model)] = _openai_chat_max_tokens(
            model,
            settings.openai_max_tokens,
        )
    if settings.enable_web_search:
        payload["tools"] = [{"type": "web_search"}]
    async def _run_once(local_payload: dict[str, Any], *, use_stream: bool) -> LlmResult:
        if use_stream:
            return await _query_chat_completions_stream(
                provider="openai",
                client=client,
                payload=local_payload,
                model=model,
                on_event=on_event,
            )
        return await _query_chat_completions_once(
            provider="openai",
            client=client,
            payload=local_payload,
            model=model,
        )

    async def _run_with_token_retry(
        local_payload: dict[str, Any],
        *,
        use_stream: bool,
    ) -> LlmResult:
        current_payload = local_payload
        for attempt_index in range(3):
            try:
                return await _run_once(current_payload, use_stream=use_stream)
            except Exception as exc:
                retry_payload = _openai_chat_retry_payload_for_token_error(
                    current_payload,
                    exc,
                )
                if (
                    retry_payload is None
                    or retry_payload == current_payload
                    or attempt_index == 2
                ):
                    raise
                current_payload = retry_payload
        raise RuntimeError("unreachable OpenAI token retry state")

    try:
        return await _run_with_token_retry(payload, use_stream=stream)
    except NotFoundError as exc:
        if "not a chat model" in str(exc).lower():
            if stream:
                await _emit_stream_event(
                    on_event,
                    {
                        "event_type": "llm_stream_fallback",
                        "stream_mode": "fallback_non_stream",
                        "reason": "chat_api_not_supported",
                    },
                )
            return await _query_openai_responses(client, prompt, model, response_format=response_format)
        raise
    except Exception as exc:
        if not settings.enable_web_search:
            if stream and _is_stream_unsupported_error(exc):
                await _emit_stream_event(
                    on_event,
                    {
                        "event_type": "llm_stream_fallback",
                        "stream_mode": "fallback_non_stream",
                        "reason": "provider_rejected_stream",
                        "error": str(exc),
                    },
                )
                try:
                    return await _run_with_token_retry(payload, use_stream=False)
                except Exception as fallback_exc:
                    raise _normalize_llm_exception(
                        provider="openai",
                        model=model,
                        exc=fallback_exc,
                    ) from fallback_exc
            raise _normalize_llm_exception(provider="openai", model=model, exc=exc) from exc
        payload.pop("tools", None)
        try:
            return await _run_with_token_retry(payload, use_stream=stream)
        except Exception as retry_exc:
            if stream and _is_stream_unsupported_error(retry_exc):
                await _emit_stream_event(
                    on_event,
                    {
                        "event_type": "llm_stream_fallback",
                        "stream_mode": "fallback_non_stream",
                        "reason": "provider_rejected_stream",
                        "error": str(retry_exc),
                    },
                )
                try:
                    return await _run_with_token_retry(payload, use_stream=False)
                except Exception as fallback_exc:
                    raise _normalize_llm_exception(
                        provider="openai",
                        model=model,
                        exc=fallback_exc,
                    ) from fallback_exc
            raise _normalize_llm_exception(
                provider="openai",
                model=model,
                exc=retry_exc,
            ) from retry_exc


async def query_gemini_openai(
    prompt: str,
    api_key: str,
    model: str,
    *,
    stream: bool = False,
    on_event: StreamEventHandler | None = None,
    response_format: dict[str, Any] | None = None,
) -> LlmResult:
    if not api_key:
        raise ValueError("Missing Gemini API key")
    client = AsyncOpenAI(api_key=api_key, base_url=GEMINI_OPENAI_BASE_URL)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if response_format is not None:
        payload["response_format"] = response_format
    if settings.enable_web_search:
        payload["tools"] = [{"type": "web_search"}]
    async def _run_once(local_payload: dict[str, Any]) -> LlmResult:
        if stream:
            return await _query_chat_completions_stream(
                provider="gemini",
                client=client,
                payload=local_payload,
                model=model,
                on_event=on_event,
            )
        return await _query_chat_completions_once(
            provider="gemini",
            client=client,
            payload=local_payload,
            model=model,
        )
    try:
        return await _run_once(payload)
    except Exception as exc:
        if not settings.enable_web_search:
            if stream and _is_stream_unsupported_error(exc):
                await _emit_stream_event(
                    on_event,
                    {
                        "event_type": "llm_stream_fallback",
                        "stream_mode": "fallback_non_stream",
                        "reason": "provider_rejected_stream",
                        "error": str(exc),
                    },
                )
                try:
                    return await _query_chat_completions_once(
                        provider="gemini",
                        client=client,
                        payload=payload,
                        model=model,
                    )
                except Exception as fallback_exc:
                    raise _normalize_llm_exception(
                        provider="gemini",
                        model=model,
                        exc=fallback_exc,
                    ) from fallback_exc
            raise _normalize_llm_exception(
                provider="gemini",
                model=model,
                exc=exc,
            ) from exc
        payload.pop("tools", None)
        try:
            return await _run_once(payload)
        except Exception as retry_exc:
            if stream and _is_stream_unsupported_error(retry_exc):
                await _emit_stream_event(
                    on_event,
                    {
                        "event_type": "llm_stream_fallback",
                        "stream_mode": "fallback_non_stream",
                        "reason": "provider_rejected_stream",
                        "error": str(retry_exc),
                    },
                )
                try:
                    return await _query_chat_completions_once(
                        provider="gemini",
                        client=client,
                        payload=payload,
                        model=model,
                    )
                except Exception as fallback_exc:
                    raise _normalize_llm_exception(
                        provider="gemini",
                        model=model,
                        exc=fallback_exc,
                    ) from fallback_exc
            raise _normalize_llm_exception(
                provider="gemini",
                model=model,
                exc=retry_exc,
            ) from retry_exc


async def _query_openai_responses(
    client: AsyncOpenAI,
    prompt: str,
    model: str,
    *,
    response_format: dict[str, Any] | None = None,
) -> LlmResult:
    payload = {"model": model, "input": prompt}
    if response_format is not None:
        payload["text"] = {"format": response_format}
    if settings.openai_max_tokens > 0:
        payload["max_output_tokens"] = _openai_safe_max_tokens(
            settings.openai_max_tokens
        )
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


def _extract_openai_responses_stream_event_type(
    event: Any,
    event_json: dict[str, Any] | None,
) -> str:
    if isinstance(event_json, dict):
        event_type = event_json.get("type")
        if isinstance(event_type, str):
            return event_type
    event_type = getattr(event, "type", None)
    if isinstance(event_type, str):
        return event_type
    return ""


def _extract_openai_responses_stream_delta_text(
    event: Any,
    event_json: dict[str, Any] | None,
) -> str:
    if _extract_openai_responses_stream_event_type(event, event_json) != "response.output_text.delta":
        return ""

    delta = getattr(event, "delta", None)
    if isinstance(delta, str):
        return delta

    if isinstance(event_json, dict):
        payload_delta = event_json.get("delta")
        if isinstance(payload_delta, str):
            return payload_delta
        if isinstance(payload_delta, dict):
            text = payload_delta.get("text")
            if isinstance(text, str):
                return text
    return ""


def _extract_openai_responses_stream_error(
    event: Any,
    event_json: dict[str, Any] | None,
) -> str | None:
    event_type = _extract_openai_responses_stream_event_type(event, event_json)
    if event_type not in {"error", "response.failed"}:
        return None

    if isinstance(event_json, dict):
        error_data = event_json.get("error")
        if error_data:
            return f"OpenAI responses stream error: {error_data}"
        response_data = event_json.get("response")
        if isinstance(response_data, dict):
            response_error = response_data.get("error")
            if response_error:
                return f"OpenAI responses stream error: {response_error}"

    event_error = getattr(event, "error", None)
    if event_error:
        return f"OpenAI responses stream error: {event_error}"
    return f"OpenAI responses stream error event: {event_type}"


async def _query_openai_responses_stream_once(
    *,
    client: AsyncOpenAI,
    payload: dict[str, Any],
    model: str,
    on_event: StreamEventHandler | None,
) -> LlmResult:
    await _emit_stream_event(
        on_event,
        {
            "event_type": "llm_stream_started",
            "stream_mode": "provider_stream",
        },
    )

    collected: list[str] = []
    delta_count = 0
    event_count = 0
    cumulative_chars = 0
    last_event_json: dict[str, Any] | None = None
    final_response: Any = None

    try:
        async with client.responses.stream(**payload) as stream:
            async for event in stream:
                event_count += 1
                event_json_raw = _to_jsonable_response(event)
                event_json = event_json_raw if isinstance(event_json_raw, dict) else None
                if event_json is not None:
                    last_event_json = event_json
                stream_error = _extract_openai_responses_stream_error(event, event_json)
                if stream_error:
                    raise RuntimeError(stream_error)
                delta_text = _extract_openai_responses_stream_delta_text(event, event_json)
                if not delta_text:
                    continue
                collected.append(delta_text)
                delta_count += 1
                cumulative_chars += len(delta_text)
                await _emit_stream_event(
                    on_event,
                    {
                        "event_type": "llm_stream_delta",
                        "chunk_index": delta_count,
                        "delta_text": delta_text,
                        "delta_chars": len(delta_text),
                        "cumulative_chars": cumulative_chars,
                    },
                )
            final_response = await stream.get_final_response()
    except Exception as exc:
        await _emit_stream_event(
            on_event,
            {
                "event_type": "llm_stream_failed",
                "error": str(exc),
            },
        )
        raise

    if final_response is None:
        raise RuntimeError("OpenAI responses stream finished without final response")

    usage = _extract_responses_usage(final_response)
    final_response_json = _to_jsonable_response(final_response)
    if isinstance(final_response_json, dict):
        response_json = dict(final_response_json)
        response_json["_stream"] = {
            "event_count": event_count,
            "delta_count": delta_count,
            "last_event": last_event_json,
        }
    else:
        response_json = {
            "streamed": True,
            "event_count": event_count,
            "delta_count": delta_count,
            "last_event": last_event_json,
            "final_response": final_response_json,
        }
    text = "".join(collected)
    if not text:
        text = _extract_response_text(final_response)
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
    estimated_cost_usd = _resolve_estimated_cost_usd(
        provider="openai",
        model=model,
        input_tokens=usage.input_tokens,
        output_tokens=billable_output_tokens,
        provider_reported_cost_usd=provider_reported_cost_usd,
    )
    await _emit_stream_event(
        on_event,
        {
            "event_type": "llm_stream_completed",
            "chunk_count": delta_count,
            "output_chars": len(text),
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "hidden_thinking_tokens": hidden_thinking_tokens,
            "estimated_cost_usd": estimated_cost_usd,
        },
    )
    return LlmResult(
        text=text,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        hidden_thinking_tokens=hidden_thinking_tokens,
        estimated_cost_usd=estimated_cost_usd,
        provider_response_json=response_json,
    )


async def _query_openai_responses_stream(
    *,
    client: AsyncOpenAI,
    prompt: str,
    model: str,
    on_event: StreamEventHandler | None,
    response_format: dict[str, Any] | None = None,
) -> LlmResult:
    payload = {"model": model, "input": prompt}
    if response_format is not None:
        payload["text"] = {"format": response_format}
    if settings.openai_max_tokens > 0:
        payload["max_output_tokens"] = _openai_safe_max_tokens(
            settings.openai_max_tokens
        )
    if settings.enable_web_search:
        payload["tools"] = [{"type": "web_search"}]
    try:
        return await _query_openai_responses_stream_once(
            client=client,
            payload=payload,
            model=model,
            on_event=on_event,
        )
    except Exception:
        if not settings.enable_web_search:
            raise
        payload.pop("tools", None)
        return await _query_openai_responses_stream_once(
            client=client,
            payload=payload,
            model=model,
            on_event=on_event,
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


def _extract_deepinfra_delta_text(result: dict[str, Any]) -> str:
    choices = result.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    delta = first.get("delta")
    if not isinstance(delta, dict):
        return ""
    content = delta.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        pieces: list[str] = []
        for part in content:
            if isinstance(part, str):
                pieces.append(part)
            elif isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str) and text:
                    pieces.append(text)
        return "".join(pieces)
    return ""


def _raise_deepinfra_http_error(
    *,
    model: str,
    response: httpx.Response,
) -> None:
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


async def _query_deepinfra_non_stream(
    *,
    prompt: str,
    api_key: str,
    model: str,
    response_format: dict[str, Any] | None = None,
) -> LlmResult:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": settings.deepinfra_temperature,
    }
    if response_format is not None:
        payload["response_format"] = response_format
    if settings.deepinfra_max_tokens > 0:
        payload["max_tokens"] = settings.deepinfra_max_tokens
    timeout = httpx.Timeout(600.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            DEEPINFRA_BASE_URL,
            headers=headers,
            json=payload,
        )
        if response.status_code != 200:
            _raise_deepinfra_http_error(model=model, response=response)
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


async def _query_deepinfra_stream(
    *,
    prompt: str,
    api_key: str,
    model: str,
    on_event: StreamEventHandler | None,
    response_format: dict[str, Any] | None = None,
) -> LlmResult:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": settings.deepinfra_temperature,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if response_format is not None:
        payload["response_format"] = response_format
    if settings.deepinfra_max_tokens > 0:
        payload["max_tokens"] = settings.deepinfra_max_tokens
    timeout = httpx.Timeout(600.0)
    await _emit_stream_event(
        on_event,
        {
            "event_type": "llm_stream_started",
            "stream_mode": "provider_stream",
        },
    )
    text_parts: list[str] = []
    chunk_count = 0
    usage = _UsageStats()
    last_chunk: dict[str, Any] | None = None
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                DEEPINFRA_BASE_URL,
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    raw_text = await response.aread()
                    text = raw_text.decode("utf-8", errors="replace")
                    fake_response = httpx.Response(
                        status_code=response.status_code,
                        headers=response.headers,
                        text=text,
                    )
                    _raise_deepinfra_http_error(model=model, response=fake_response)

                cumulative_chars = 0
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    trimmed = line.strip()
                    if not trimmed.startswith("data:"):
                        continue
                    data = trimmed[5:].strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        chunk_json = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(chunk_json, dict):
                        continue
                    chunk_count += 1
                    last_chunk = chunk_json
                    delta_text = _extract_deepinfra_delta_text(chunk_json)
                    if delta_text:
                        text_parts.append(delta_text)
                        cumulative_chars += len(delta_text)
                        await _emit_stream_event(
                            on_event,
                            {
                                "event_type": "llm_stream_delta",
                                "chunk_index": chunk_count,
                                "delta_text": delta_text,
                                "delta_chars": len(delta_text),
                                "cumulative_chars": cumulative_chars,
                            },
                        )
                    chunk_usage = _extract_deepinfra_usage(chunk_json)
                    if any(
                        value is not None
                        for value in [
                            chunk_usage.input_tokens,
                            chunk_usage.output_tokens,
                            chunk_usage.total_tokens,
                        ]
                    ):
                        usage = chunk_usage
    except Exception as exc:
        await _emit_stream_event(
            on_event,
            {
                "event_type": "llm_stream_failed",
                "error": str(exc),
            },
        )
        raise

    full_text = "".join(text_parts)
    response_json: dict[str, Any] = {
        "streamed": True,
        "chunk_count": chunk_count,
        "final_chunk": last_chunk,
    }
    hidden_thinking_tokens = _extract_hidden_thinking_tokens(
        provider="deepinfra",
        response_json=response_json,
    )
    provider_reported_cost_usd = _extract_provider_reported_cost_usd(response_json)
    billable_output_tokens = _resolve_billable_output_tokens(
        provider="deepinfra",
        output_tokens=usage.output_tokens,
        response_json=response_json,
        hidden_thinking_tokens=hidden_thinking_tokens,
    )
    estimated_cost_usd = _resolve_estimated_cost_usd(
        provider="deepinfra",
        model=model,
        input_tokens=usage.input_tokens,
        output_tokens=billable_output_tokens,
        provider_reported_cost_usd=provider_reported_cost_usd,
    )
    await _emit_stream_event(
        on_event,
        {
            "event_type": "llm_stream_completed",
            "chunk_count": chunk_count,
            "output_chars": len(full_text),
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "hidden_thinking_tokens": hidden_thinking_tokens,
            "estimated_cost_usd": estimated_cost_usd,
        },
    )
    return LlmResult(
        text=full_text,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        hidden_thinking_tokens=hidden_thinking_tokens,
        estimated_cost_usd=estimated_cost_usd,
        provider_response_json=response_json,
    )


async def query_deepinfra(
    prompt: str,
    api_key: str,
    model: str,
    *,
    stream: bool = False,
    on_event: StreamEventHandler | None = None,
    response_format: dict[str, Any] | None = None,
) -> LlmResult:
    if not api_key:
        raise ValueError("Missing DeepInfra API key")
    if not stream:
        try:
            return await _query_deepinfra_non_stream(
                prompt=prompt,
                api_key=api_key,
                model=model,
                response_format=response_format,
            )
        except Exception as exc:
            raise _normalize_llm_exception(
                provider="deepinfra",
                model=model,
                exc=exc,
            ) from exc
    try:
        return await _query_deepinfra_stream(
            prompt=prompt,
            api_key=api_key,
            model=model,
            on_event=on_event,
            response_format=response_format,
        )
    except Exception as exc:
        if _is_stream_unsupported_error(exc):
            await _emit_stream_event(
                on_event,
                {
                    "event_type": "llm_stream_fallback",
                    "stream_mode": "fallback_non_stream",
                    "reason": "provider_rejected_stream",
                    "error": str(exc),
                },
            )
            try:
                return await _query_deepinfra_non_stream(
                    prompt=prompt,
                    api_key=api_key,
                    model=model,
                    response_format=response_format,
                )
            except Exception as fallback_exc:
                raise _normalize_llm_exception(
                    provider="deepinfra",
                    model=model,
                    exc=fallback_exc,
                ) from fallback_exc
        raise _normalize_llm_exception(
            provider="deepinfra",
            model=model,
            exc=exc,
        ) from exc


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
    # Sources (checked on 2026-06-01):
    # - https://openai.com/api/pricing
    # - https://ai.google.dev/gemini-api/docs/pricing
    pricing_per_million: dict[str, dict[str, tuple[float, float]]] = {
        "openai": {
            "gpt-5.5": (5.00, 30.00),
            "gpt-5.4-mini": (0.75, 4.50),
            "gpt-5.4-nano": (0.20, 1.25),
            "gpt-5.4": (2.50, 15.00),
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
            "deep-research-pro-preview": (2.00, 12.00),
            "deep-research-preview": (2.00, 12.00),
            "gemini-3.5-flash": (1.50, 9.00),
            "gemini-3.1-pro-preview": (2.00, 12.00),
            "gemini-3.1-flash-lite": (0.25, 1.50),
            "gemini-3-pro-preview": (2.00, 12.00),
            "gemini-3-flash-preview": (0.50, 3.00),
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
            dumped = model_dump_json(warnings=False)
            loaded = json.loads(dumped)
            if isinstance(loaded, (dict, list)):
                return loaded
        except Exception:
            pass

    model_dump = getattr(response, "model_dump", None)
    if callable(model_dump):
        try:
            dumped = model_dump(mode="json", warnings=False)
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
