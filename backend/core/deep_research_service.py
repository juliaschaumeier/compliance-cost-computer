from __future__ import annotations

import asyncio
from dataclasses import dataclass
import threading
import time
from typing import Any, Callable

from google import genai
from google.genai import types

from backend.core.auth import ApiKeys
from backend.core.config import settings
from backend.core.llm_service import _resolve_estimated_cost_usd


class DeepResearchError(RuntimeError):
    pass


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class DeepResearchResult:
    agent: str
    interaction_id: str
    report_text: str
    response_json: dict[str, Any] | list[Any] | None
    input_tokens: int | None = None
    output_tokens: int | None = None
    thought_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None


def _to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return _to_jsonable(value.model_dump())
    if hasattr(value, "to_dict"):
        return _to_jsonable(value.to_dict())
    if hasattr(value, "__dict__"):
        return _to_jsonable(value.__dict__)
    return str(value)


def _extract_text_from_interaction(interaction: Any) -> str:
    outputs = getattr(interaction, "outputs", None)
    if outputs:
        last = outputs[-1]
        text = getattr(last, "text", None)
        if isinstance(text, str) and text.strip():
            return text

    steps = getattr(interaction, "steps", None) or []
    for step in reversed(steps):
        if getattr(step, "type", None) != "model_output":
            continue
        content = getattr(step, "content", None) or []
        pieces: list[str] = []
        for item in content:
            text = getattr(item, "text", None)
            if isinstance(text, str) and text:
                pieces.append(text)
        if pieces:
            return "\n".join(pieces)
    return ""


def _extract_usage(interaction_json: dict[str, Any] | list[Any] | None) -> dict[str, int | None]:
    if not isinstance(interaction_json, dict):
        return {
            "input_tokens": None,
            "output_tokens": None,
            "thought_tokens": None,
            "total_tokens": None,
        }
    usage = interaction_json.get("usage")
    if not isinstance(usage, dict):
        return {
            "input_tokens": None,
            "output_tokens": None,
            "thought_tokens": None,
            "total_tokens": None,
        }
    return {
        "input_tokens": _as_int(usage.get("total_input_tokens")),
        "output_tokens": _as_int(usage.get("total_output_tokens")),
        "thought_tokens": _as_int(usage.get("total_thought_tokens")),
        "total_tokens": _as_int(usage.get("total_tokens")),
    }


def _billable_output_tokens_for_cost(
    *,
    input_tokens: int | None,
    output_tokens: int | None,
    thought_tokens: int | None,
    total_tokens: int | None,
) -> int | None:
    if total_tokens is not None and input_tokens is not None:
        return max(total_tokens - input_tokens, 0)
    if output_tokens is None and thought_tokens is None:
        return None
    return (output_tokens or 0) + (thought_tokens or 0)


def _run_interaction_sync(
    *,
    api_key: str,
    prompt: str,
    agent: str,
    poll_interval_seconds: float,
    max_poll_seconds: float = 1800.0,
    request_timeout_seconds: float = 30.0,
    stop_event: threading.Event | None = None,
    on_interaction_started: Callable[[str, str], None] | None = None,
) -> DeepResearchResult:
    if not api_key:
        raise DeepResearchError("Gemini API key is required for Deep Research")
    timeout_ms = (
        int(request_timeout_seconds * 1000)
        if request_timeout_seconds and request_timeout_seconds > 0
        else None
    )
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=timeout_ms),
    )
    interaction = client.interactions.create(
        agent=agent,
        input=prompt,
        agent_config={
            "type": "deep-research",
            "thinking_summaries": "auto",
            "collaborative_planning": False,
        },
        background=True,
    )
    interaction_id = str(getattr(interaction, "id", "") or "")
    if not interaction_id:
        raise DeepResearchError("Gemini did not return a Deep Research interaction id")
    if on_interaction_started:
        on_interaction_started(agent, interaction_id)

    started = time.monotonic()
    while True:
        if stop_event is not None and stop_event.is_set():
            raise DeepResearchError("Gemini Deep Research polling was cancelled")
        if max_poll_seconds > 0 and time.monotonic() - started >= max_poll_seconds:
            raise DeepResearchError(
                f"Gemini Deep Research timed out after {int(max_poll_seconds)} seconds"
            )
        result = client.interactions.get(id=interaction_id)
        status = str(getattr(result, "status", "") or "").lower()
        if status == "completed":
            response_json = _to_jsonable(result)
            report_text = _extract_text_from_interaction(result)
            if not report_text.strip():
                raise DeepResearchError("Gemini Deep Research completed without report text")
            usage = _extract_usage(response_json)
            billable_output_tokens = _billable_output_tokens_for_cost(
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                thought_tokens=usage["thought_tokens"],
                total_tokens=usage["total_tokens"],
            )
            return DeepResearchResult(
                agent=agent,
                interaction_id=interaction_id,
                report_text=report_text,
                response_json=response_json,
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                thought_tokens=usage["thought_tokens"],
                total_tokens=usage["total_tokens"],
                estimated_cost_usd=_resolve_estimated_cost_usd(
                    provider="gemini",
                    model=agent,
                    input_tokens=usage["input_tokens"],
                    output_tokens=billable_output_tokens,
                ),
            )
        if status == "failed":
            error = getattr(result, "error", None)
            raise DeepResearchError(f"Gemini Deep Research failed: {error or 'unknown error'}")
        if status in {"cancelled", "canceled"}:
            raise DeepResearchError("Gemini Deep Research was cancelled")

        if stop_event is not None:
            stop_event.wait(poll_interval_seconds)
        else:
            time.sleep(poll_interval_seconds)


def _poll_interaction_sync(
    *,
    api_key: str,
    interaction_id: str,
    agent: str,
    poll_interval_seconds: float,
    max_poll_seconds: float = 1800.0,
    request_timeout_seconds: float = 30.0,
) -> DeepResearchResult:
    if not api_key:
        raise DeepResearchError("Gemini API key is required for Deep Research")
    if not interaction_id:
        raise DeepResearchError("Gemini Deep Research interaction id is required")
    timeout_ms = (
        int(request_timeout_seconds * 1000)
        if request_timeout_seconds and request_timeout_seconds > 0
        else None
    )
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=timeout_ms),
    )
    started = time.monotonic()
    while True:
        if max_poll_seconds > 0 and time.monotonic() - started >= max_poll_seconds:
            raise DeepResearchError(
                f"Gemini Deep Research harvest timed out after {int(max_poll_seconds)} seconds"
            )
        result = client.interactions.get(id=interaction_id)
        status = str(getattr(result, "status", "") or "").lower()
        if status == "completed":
            response_json = _to_jsonable(result)
            report_text = _extract_text_from_interaction(result)
            if not report_text.strip():
                raise DeepResearchError("Gemini Deep Research completed without report text")
            usage = _extract_usage(response_json)
            billable_output_tokens = _billable_output_tokens_for_cost(
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                thought_tokens=usage["thought_tokens"],
                total_tokens=usage["total_tokens"],
            )
            return DeepResearchResult(
                agent=agent,
                interaction_id=interaction_id,
                report_text=report_text,
                response_json=response_json,
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                thought_tokens=usage["thought_tokens"],
                total_tokens=usage["total_tokens"],
                estimated_cost_usd=_resolve_estimated_cost_usd(
                    provider="gemini",
                    model=agent,
                    input_tokens=usage["input_tokens"],
                    output_tokens=billable_output_tokens,
                ),
            )
        if status == "failed":
            error = getattr(result, "error", None)
            raise DeepResearchError(f"Gemini Deep Research failed: {error or 'unknown error'}")
        if status in {"cancelled", "canceled"}:
            raise DeepResearchError("Gemini Deep Research was cancelled")
        time.sleep(poll_interval_seconds)


async def run_deep_research(
    *,
    prompt: str,
    api_keys: ApiKeys,
    agent: str | None = None,
    on_interaction_started: Callable[[str, str], None] | None = None,
) -> DeepResearchResult:
    primary_agent = agent or settings.deep_research_primary_agent
    fallback_agent = settings.deep_research_fallback_agent
    poll_interval = max(float(settings.deep_research_poll_interval_seconds), 1.0)
    max_poll_seconds = max(float(settings.deep_research_max_poll_seconds), 1.0)
    request_timeout_seconds = max(float(settings.deep_research_request_timeout_seconds), 1.0)
    stop_event = threading.Event()
    try:
        return await asyncio.to_thread(
            _run_interaction_sync,
            api_key=api_keys.gemini_api_key,
            prompt=prompt,
            agent=primary_agent,
            poll_interval_seconds=poll_interval,
            max_poll_seconds=max_poll_seconds,
            request_timeout_seconds=request_timeout_seconds,
            stop_event=stop_event,
            on_interaction_started=on_interaction_started,
        )
    except asyncio.CancelledError:
        stop_event.set()
        raise
    except Exception as exc:
        message = str(exc)
        if fallback_agent and fallback_agent != primary_agent and "agent" in message.lower():
            fallback_stop_event = threading.Event()
            try:
                return await asyncio.to_thread(
                    _run_interaction_sync,
                    api_key=api_keys.gemini_api_key,
                    prompt=prompt,
                    agent=fallback_agent,
                    poll_interval_seconds=poll_interval,
                    max_poll_seconds=max_poll_seconds,
                    request_timeout_seconds=request_timeout_seconds,
                    stop_event=fallback_stop_event,
                    on_interaction_started=on_interaction_started,
                )
            except asyncio.CancelledError:
                fallback_stop_event.set()
                raise
            except Exception as fallback_exc:
                raise DeepResearchError(
                    "Gemini Deep Research failed with primary and fallback agents: "
                    f"primary={primary_agent}: {exc}; fallback={fallback_agent}: {fallback_exc}"
                ) from fallback_exc
        raise DeepResearchError(
            f"Gemini Deep Research failed for agent={primary_agent}: {exc}"
        ) from exc


async def harvest_deep_research_interaction(
    *,
    interaction_id: str,
    api_keys: ApiKeys,
    agent: str,
) -> DeepResearchResult:
    poll_interval = max(float(settings.deep_research_poll_interval_seconds), 1.0)
    max_poll_seconds = max(float(settings.deep_research_max_poll_seconds), 1.0)
    request_timeout_seconds = max(float(settings.deep_research_request_timeout_seconds), 1.0)
    try:
        return await asyncio.to_thread(
            _poll_interaction_sync,
            api_key=api_keys.gemini_api_key,
            interaction_id=interaction_id,
            agent=agent,
            poll_interval_seconds=poll_interval,
            max_poll_seconds=max_poll_seconds,
            request_timeout_seconds=request_timeout_seconds,
        )
    except Exception as exc:
        raise DeepResearchError(
            f"Gemini Deep Research harvest failed for interaction={interaction_id}: {exc}"
        ) from exc
