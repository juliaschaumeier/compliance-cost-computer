from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import time
from dataclasses import dataclass, field, fields, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Literal

import httpx


DEFAULT_MODELS: tuple[tuple[str, str], ...] = (
    ("gemini", "gemini-3.1-pro-preview"),
    ("gemini", "gemini-3.5-flash"),
)
DEFAULT_OUTPUT_DIR = Path("batch_runs")
DEFAULT_BUILT_IN_LAWS_DIR = Path("resources/built_in_laws")
DEFAULT_ENV_PATH = Path(".env")
DEEP_RESEARCH_PROMPT_ID = "deep_research_case_group_metrics"


@dataclass(frozen=True)
class LawPair:
    name: str
    current_filename: str
    proposed_filename: str


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str


@dataclass(frozen=True)
class Scenario:
    law_pair: LawPair
    model_spec: ModelSpec
    deep_research: bool
    repetition: int

    @property
    def scenario_id(self) -> str:
        dr = "dr" if self.deep_research else "no-dr"
        model = self.model_spec.model.replace("/", "_")
        return f"{self.law_pair.name}__{model}__{dr}__{self.repetition:02d}"


@dataclass(frozen=True)
class BatchConfig:
    base_url: str = "http://localhost:5000"
    email: str = ""
    password: str = ""
    law_pairs: tuple[str, ...] = ()
    models: tuple[ModelSpec, ...] = tuple(
        ModelSpec(provider=provider, model=model) for provider, model in DEFAULT_MODELS
    )
    deep_research_modes: tuple[bool, ...] = (True, False)
    repetitions: int = 10
    concurrency: int = 4
    resume_completed: bool = True
    max_run_attempts: int = 5
    max_deep_research_attempts: int = 1
    max_stuck_minutes: float = 60.0
    poll_seconds: float = 5.0
    output_dir: Path = DEFAULT_OUTPUT_DIR
    batch_id: str = ""
    built_in_laws_dir: Path = DEFAULT_BUILT_IN_LAWS_DIR
    user_edit_policy: Literal["reject_if_user_edits", "use_user_edits"] = (
        "reject_if_user_edits"
    )
    limit_scenarios: int | None = None
    scenario_ids: tuple[str, ...] = ()
    download_pdfs: bool = True
    openai_api_key: str = ""
    deepinfra_api_key: str = ""
    gemini_api_key: str = ""


@dataclass
class ScenarioResult:
    status: str
    law_pair: str
    model: str
    deep_research: bool
    repetition: int
    scenario_id: str = ""
    scenario_index: int | None = None
    scenario_total: int | None = None
    app_session_id: str | None = None
    duration_min: float | None = None
    run_attempts: int = 0
    export_status: str | None = None
    estimated_llm_cost_usd: float | None = None
    estimated_dr_cost_usd: float | None = None
    estimated_total_cost_usd: float | None = None
    missing_cost_estimates: int = 0
    error: str | None = None
    step_failed: str | None = None
    export_file: str | None = None
    batch_id: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    retry_reasons: list[str] = field(default_factory=list)
    llm_calls_total: int = 0
    llm_calls_failed: int = 0

    def to_row(self, *, include_diagnostics: bool = False) -> dict[str, Any]:
        row: dict[str, Any] = {
            "status": self.status,
            "scenario_id": self.scenario_id,
            "law_pair": self.law_pair,
            "model": self.model,
            "deep_research": self.deep_research,
            "repetition": self.repetition,
            "app_session_id": self.app_session_id,
            "duration_min": self.duration_min,
            "run_attempts": self.run_attempts,
            "export_status": self.export_status,
            "estimated_llm_cost_usd": self.estimated_llm_cost_usd,
            "estimated_dr_cost_usd": self.estimated_dr_cost_usd,
            "estimated_total_cost_usd": self.estimated_total_cost_usd,
            "missing_cost_estimates": self.missing_cost_estimates,
            "error": self.error,
        }
        if include_diagnostics:
            row.update(
                {
                    "batch_id": self.batch_id,
                    "scenario_index": self.scenario_index,
                    "scenario_total": self.scenario_total,
                    "step_failed": self.step_failed,
                    "export_file": self.export_file,
                    "started_at": self.started_at,
                    "finished_at": self.finished_at,
                    "retry_reasons": "; ".join(self.retry_reasons),
                    "llm_calls_total": self.llm_calls_total,
                    "llm_calls_failed": self.llm_calls_failed,
                }
            )
        return row


@dataclass
class BatchResult:
    results: list[ScenarioResult]
    output_dir: Path

    def to_dataframe(self, *, include_diagnostics: bool = False):
        import pandas as pd

        return pd.DataFrame(
            [result.to_row(include_diagnostics=include_diagnostics) for result in self.results]
        )

    def to_summary_dataframe(self):
        import pandas as pd

        df = self.to_dataframe()
        if df.empty:
            return pd.DataFrame()
        value_columns = [
            "estimated_llm_cost_usd",
            "estimated_dr_cost_usd",
            "estimated_total_cost_usd",
            "missing_cost_estimates",
            "duration_min",
            "run_attempts",
        ]
        for column in value_columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

        def _std(series: pd.Series, digits: int) -> float:
            value = series.std(ddof=0)
            if pd.isna(value):
                value = 0.0
            return round(float(value), digits)

        def _aggregate(group: pd.DataFrame, label: str) -> dict[str, Any]:
            success = group["status"] == "success"
            return {
                "group": label,
                "runs": len(group),
                "success": int(success.sum()),
                "failed": int((~success).sum()),
                "success_rate": round(float(success.mean()) if len(group) else 0.0, 3),
                "total_cost_usd": round(float(group["estimated_total_cost_usd"].sum()), 4),
                "avg_cost_usd": round(float(group["estimated_total_cost_usd"].mean()), 4),
                "std_cost_usd": _std(group["estimated_total_cost_usd"], 4),
                "avg_llm_cost_usd": round(float(group["estimated_llm_cost_usd"].mean()), 4),
                "std_llm_cost_usd": _std(group["estimated_llm_cost_usd"], 4),
                "avg_dr_cost_usd": round(float(group["estimated_dr_cost_usd"].mean()), 4),
                "std_dr_cost_usd": _std(group["estimated_dr_cost_usd"], 4),
                "avg_duration_min": round(float(group["duration_min"].mean()), 2),
                "std_duration_min": _std(group["duration_min"], 2),
                "avg_attempts": round(float(group["run_attempts"].mean()), 2),
                "std_attempts": _std(group["run_attempts"], 2),
                "missing_cost_estimates": int(group["missing_cost_estimates"].sum()),
            }

        rows = [_aggregate(df, "gesamt")]
        rows.extend(
            _aggregate(group, f"model={model}")
            for model, group in df.groupby("model", dropna=False, sort=True)
        )
        rows.extend(
            _aggregate(group, f"deep_research={bool(deep_research)}")
            for deep_research, group in df.groupby("deep_research", dropna=False, sort=True)
        )
        rows.extend(
            _aggregate(group, f"model={model} | deep_research={bool(deep_research)}")
            for (model, deep_research), group in df.groupby(
                ["model", "deep_research"], dropna=False, sort=True
            )
        )
        return pd.DataFrame(rows)


def load_batch_result(batch_dir: Path) -> BatchResult:
    jsonl_path = batch_dir / "runs.jsonl"
    if not jsonl_path.exists():
        raise FileNotFoundError(f"No runs.jsonl found in {batch_dir}")

    scenario_result_fields = {item.name for item in fields(ScenarioResult)}
    results: list[ScenarioResult] = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            continue
        payload = {key: value for key, value in row.items() if key in scenario_result_fields}
        retry_reasons = payload.get("retry_reasons")
        if isinstance(retry_reasons, str):
            payload["retry_reasons"] = [
                item.strip() for item in retry_reasons.split(";") if item.strip()
            ]
        results.append(ScenarioResult(**payload))
    return BatchResult(results=results, output_dir=batch_dir)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def default_batch_id() -> str:
    return "batch_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_batch_output_dir(config: BatchConfig) -> Path:
    batch_id = config.batch_id.strip() or default_batch_id()
    return config.output_dir / batch_id


def discover_law_pairs(laws_dir: Path = DEFAULT_BUILT_IN_LAWS_DIR) -> list[LawPair]:
    candidates: dict[str, dict[str, str]] = {}
    for path in sorted(laws_dir.glob("*.txt")):
        name = path.name
        if name.endswith("_gueltig.txt"):
            stem = name[: -len("_gueltig.txt")]
            candidates.setdefault(stem, {})["current"] = name
        elif name.endswith("_vorschlag.txt"):
            stem = name[: -len("_vorschlag.txt")]
            candidates.setdefault(stem, {})["proposed"] = name

    pairs = [
        LawPair(
            name=stem,
            current_filename=parts["current"],
            proposed_filename=parts["proposed"],
        )
        for stem, parts in sorted(candidates.items())
        if "current" in parts and "proposed" in parts
    ]
    return pairs


def build_scenarios(
    law_pairs: Iterable[LawPair],
    models: Iterable[ModelSpec],
    deep_research_modes: Iterable[bool],
    repetitions: int,
    *,
    limit: int | None = None,
) -> list[Scenario]:
    if repetitions < 1:
        raise ValueError("repetitions must be at least 1")
    scenarios = [
        Scenario(
            law_pair=pair,
            model_spec=model_spec,
            deep_research=deep_research,
            repetition=repetition,
        )
        for pair in law_pairs
        for model_spec in models
        for deep_research in deep_research_modes
        for repetition in range(1, repetitions + 1)
    ]
    return scenarios[:limit] if limit is not None else scenarios


def select_scenarios(
    law_pairs: Iterable[LawPair],
    models: Iterable[ModelSpec],
    deep_research_modes: Iterable[bool],
    repetitions: int,
    *,
    scenario_ids: Iterable[str] = (),
    limit: int | None = None,
) -> list[Scenario]:
    scenarios = build_scenarios(
        law_pairs,
        models,
        deep_research_modes,
        repetitions,
    )
    requested_ids = {scenario_id.strip() for scenario_id in scenario_ids if scenario_id.strip()}
    if requested_ids:
        scenarios_by_id = {scenario.scenario_id: scenario for scenario in scenarios}
        missing = sorted(requested_ids - set(scenarios_by_id))
        if missing:
            raise RuntimeError(
                "No matching scenario(s) found: "
                + ", ".join(missing)
            )
        scenarios = [scenario for scenario in scenarios if scenario.scenario_id in requested_ids]
    return scenarios[:limit] if limit is not None else scenarios


def validate_config(config: BatchConfig) -> None:
    if config.concurrency < 1:
        raise ValueError("concurrency must be at least 1")
    if config.max_run_attempts < 1:
        raise ValueError("max_run_attempts must be at least 1")
    if config.max_deep_research_attempts < 1:
        raise ValueError("max_deep_research_attempts must be at least 1")
    if config.max_stuck_minutes < 0:
        raise ValueError("max_stuck_minutes must not be negative")
    if config.poll_seconds < 0:
        raise ValueError("poll_seconds must not be negative")


def load_dotenv_if_available(env_path: Path = DEFAULT_ENV_PATH) -> bool:
    if not env_path.exists():
        return False
    try:
        from dotenv import load_dotenv
    except ImportError:
        return _load_dotenv_fallback(env_path)
    return bool(load_dotenv(env_path, override=False))


def _load_dotenv_fallback(env_path: Path) -> bool:
    loaded = False
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = _clean_env_value(value)
        loaded = True
    return loaded


def _clean_env_value(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        return cleaned[1:-1]
    return cleaned


def api_key_headers(config: BatchConfig) -> dict[str, str]:
    values = {
        "x-openai-key": config.openai_api_key or os.environ.get("OPENAI_API_KEY", ""),
        "x-deepinfra-key": config.deepinfra_api_key
        or os.environ.get("DEEPINFRA_API_KEY", ""),
        "x-gemini-key": config.gemini_api_key or os.environ.get("GEMINI_API_KEY", ""),
    }
    return {key: value.strip() for key, value in values.items() if value.strip()}


def redacted_config(config: BatchConfig) -> dict[str, Any]:
    batch_id = config.batch_id.strip()
    return {
        "created_at": utc_now(),
        "base_url": config.base_url,
        "law_pairs": list(config.law_pairs),
        "models": [
            {"provider": model.provider, "model": model.model}
            for model in config.models
        ],
        "deep_research_modes": list(config.deep_research_modes),
        "repetitions": config.repetitions,
        "concurrency": config.concurrency,
        "resume_completed": config.resume_completed,
        "max_run_attempts": config.max_run_attempts,
        "max_deep_research_attempts": config.max_deep_research_attempts,
        "max_stuck_minutes": config.max_stuck_minutes,
        "poll_seconds": config.poll_seconds,
        "output_dir": str(config.output_dir),
        "batch_id": batch_id,
        "effective_output_dir": str(config.output_dir / batch_id) if batch_id else "",
        "built_in_laws_dir": str(config.built_in_laws_dir),
        "user_edit_policy": config.user_edit_policy,
        "limit_scenarios": config.limit_scenarios,
        "scenario_ids": list(config.scenario_ids),
        "download_pdfs": config.download_pdfs,
        "email": config.email,
        "password": "<redacted>" if config.password else "",
        "openai_api_key_present": bool(
            config.openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        ),
        "deepinfra_api_key_present": bool(
            config.deepinfra_api_key or os.environ.get("DEEPINFRA_API_KEY", "")
        ),
        "gemini_api_key_present": bool(
            config.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        ),
    }


def load_config_from_env(**overrides: Any) -> BatchConfig:
    load_dotenv_if_available()
    values = {
        "email": os.environ.get("CCC_BATCH_EMAIL", ""),
        "password": os.environ.get("CCC_BATCH_PASSWORD", ""),
    }
    values.update({key: value for key, value in overrides.items() if value is not None})
    return BatchConfig(**values)


async def _request_json(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    expected: tuple[int, ...] = (200,),
    **kwargs: Any,
) -> dict[str, Any]:
    response = await client.request(method, path, **kwargs)
    if response.status_code not in expected:
        raise RuntimeError(f"{method} {path} failed: {response.status_code} {response.text}")
    return response.json()


async def login(client: httpx.AsyncClient, config: BatchConfig) -> None:
    if not config.email or not config.password:
        raise ValueError("CCC_BATCH_EMAIL and CCC_BATCH_PASSWORD are required")
    await _request_json(
        client,
        "POST",
        "/auth/login",
        json={"email": config.email, "password": config.password},
    )


async def validate_law_pairs(
    client: httpx.AsyncClient,
    pairs: list[LawPair],
) -> list[LawPair]:
    payload = await _request_json(client, "GET", "/regulations")
    visible = set(payload.get("files") or [])
    missing = [
        filename
        for pair in pairs
        for filename in (pair.current_filename, pair.proposed_filename)
        if filename not in visible
    ]
    if missing:
        raise RuntimeError(
            "Built-in law files are not available through the API: "
            + ", ".join(sorted(missing))
        )
    return pairs


async def create_session(client: httpx.AsyncClient, scenario: Scenario) -> str:
    payload = await _request_json(
        client,
        "POST",
        "/sessions",
        json={"llm_model": scenario.model_spec.model},
    )
    return str(payload["app_session_id"])


async def set_deep_research(
    client: httpx.AsyncClient,
    app_session_id: str,
    enabled: bool,
    headers: dict[str, str],
) -> None:
    await _request_json(
        client,
        "POST",
        "/sessions/case-group-research",
        json={"app_session_id": app_session_id, "enabled": enabled},
        headers=headers,
    )


def _progress_signature(status: dict[str, Any]) -> tuple[Any, ...]:
    steps = status.get("steps") or []
    return (
        status.get("status"),
        status.get("current_step"),
        status.get("current_norm_addressee"),
        status.get("last_error"),
        tuple((step.get("key"), step.get("status")) for step in steps if isinstance(step, dict)),
    )


def _failed_step(status: dict[str, Any]) -> str | None:
    steps = status.get("steps") or []
    for step in reversed(steps):
        if isinstance(step, dict) and step.get("status") == "failed":
            return str(step.get("key") or "") or None
    return None


async def _wait_for_run(
    client: httpx.AsyncClient,
    run_id: str,
    config: BatchConfig,
) -> dict[str, Any]:
    last_progress_at = time.monotonic()
    last_signature: tuple[Any, ...] | None = None
    stuck_seconds = config.max_stuck_minutes * 60 if config.max_stuck_minutes else None

    while True:
        status = await _request_json(client, "GET", f"/sessions/run-all/{run_id}")
        if status.get("status") in {"completed", "failed", "cancelled"}:
            return status

        signature = _progress_signature(status)
        if signature != last_signature:
            last_signature = signature
            last_progress_at = time.monotonic()
        elif stuck_seconds is not None and time.monotonic() - last_progress_at > stuck_seconds:
            raise TimeoutError(
                f"run {run_id} made no observable progress for "
                f"{config.max_stuck_minutes:g} minutes"
            )
        await asyncio.sleep(config.poll_seconds)


def _is_deep_research_failure(status: dict[str, Any], message: str) -> bool:
    final_status = status.get("final_status")
    if isinstance(final_status, dict):
        if final_status.get("case_group_research_status") == "failed":
            return True
        failed_message = str(final_status.get("last_failed_message") or "")
        if "deep_research" in failed_message or "Deep Research" in failed_message:
            return True
    return "deep_research" in message or "Deep Research" in message


async def _cancel_run(client: httpx.AsyncClient, run_id: str) -> None:
    try:
        await _request_json(
            client,
            "POST",
            f"/sessions/run-all/{run_id}/cancel",
            expected=(200,),
        )
    except Exception:
        return


async def run_workflow_with_retries(
    client: httpx.AsyncClient,
    scenario: Scenario,
    app_session_id: str,
    config: BatchConfig,
    headers: dict[str, str],
) -> tuple[dict[str, Any], int, list[str]]:
    retry_reasons: list[str] = []
    last_status: dict[str, Any] = {}
    deep_research_attempts = 0

    for attempt in range(1, config.max_run_attempts + 1):
        started = await _request_json(
            client,
            "POST",
            "/sessions/run-all/start",
            json={
                "app_session_id": app_session_id,
                "current_filename": scenario.law_pair.current_filename,
                "proposed_filename": scenario.law_pair.proposed_filename,
                "model": scenario.model_spec.model,
                "provider": scenario.model_spec.provider,
            },
            headers=headers,
        )
        run_id = str(started["run_id"])
        try:
            last_status = await _wait_for_run(client, run_id, config)
        except TimeoutError as exc:
            retry_reasons.append(str(exc))
            await _cancel_run(client, run_id)
            continue

        if last_status.get("status") == "completed" and last_status.get("ok") is True:
            return last_status, attempt, retry_reasons

        message = str(last_status.get("last_error") or last_status.get("status") or "failed")
        retry_reasons.append(message)
        if scenario.deep_research and _is_deep_research_failure(last_status, message):
            deep_research_attempts += 1
            if deep_research_attempts >= config.max_deep_research_attempts:
                retry_reasons.append(
                    "Deep Research retry cap reached "
                    f"({config.max_deep_research_attempts})"
                )
                return last_status, attempt, retry_reasons

    return last_status, config.max_run_attempts, retry_reasons


async def export_compliance_text(
    client: httpx.AsyncClient,
    scenario: Scenario,
    app_session_id: str,
    config: BatchConfig,
    headers: dict[str, str],
    output_dir: Path,
) -> tuple[str, str | None]:
    response = await client.post(
        "/sessions/compliance-text-export",
        json={
            "app_session_id": app_session_id,
            "model": scenario.model_spec.model,
            "provider": scenario.model_spec.provider,
            "user_edit_policy": config.user_edit_policy,
        },
        headers=headers,
    )
    if response.status_code != 200:
        return "failed", response.text
    if not config.download_pdfs:
        return "success", None
    pdf_dir = output_dir / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    filename = pdf_dir / f"{scenario.scenario_id}__{app_session_id}.pdf"
    filename.write_bytes(response.content)
    return "success", str(filename)


async def load_cost_summary(
    client: httpx.AsyncClient,
    app_session_id: str,
) -> tuple[float | None, float | None, float | None, int, int, int]:
    response = await client.get(
        "/sessions/llm-monitor",
        params={"app_session_id": app_session_id, "limit": 500},
    )
    if response.status_code != 200:
        return None, None, None, 0, 0, 0
    payload = response.json()
    rows = list(payload.get("recent") or [])
    llm_total = 0.0
    dr_total = 0.0
    missing = 0
    failed = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("estimated_cost_usd") is None:
            missing += 1
        else:
            cost = float(row.get("estimated_cost_usd") or 0)
            if row.get("prompt_id") == DEEP_RESEARCH_PROMPT_ID:
                dr_total += cost
            else:
                llm_total += cost
        if row.get("answer_state") == "invalid":
            failed += 1
    return llm_total, dr_total, llm_total + dr_total, missing, len(rows), failed


async def _fill_cost_summary(
    client: httpx.AsyncClient,
    result: ScenarioResult,
) -> None:
    if not result.app_session_id:
        return
    llm_cost, dr_cost, total_cost, missing, calls_total, calls_failed = await load_cost_summary(
        client, result.app_session_id
    )
    result.estimated_llm_cost_usd = llm_cost
    result.estimated_dr_cost_usd = dr_cost
    result.estimated_total_cost_usd = total_cost
    result.missing_cost_estimates = missing
    result.llm_calls_total = calls_total
    result.llm_calls_failed = calls_failed


async def run_scenario(
    client: httpx.AsyncClient,
    scenario: Scenario,
    config: BatchConfig,
    headers: dict[str, str],
    output_dir: Path,
    *,
    scenario_index: int | None = None,
    scenario_total: int | None = None,
) -> ScenarioResult:
    started_monotonic = time.monotonic()
    started_at = utc_now()
    result = ScenarioResult(
        status="failed",
        scenario_id=scenario.scenario_id,
        law_pair=scenario.law_pair.name,
        model=scenario.model_spec.model,
        deep_research=scenario.deep_research,
        repetition=scenario.repetition,
        scenario_index=scenario_index,
        scenario_total=scenario_total,
        batch_id=output_dir.name,
        started_at=started_at,
    )
    try:
        app_session_id = await create_session(client, scenario)
        result.app_session_id = app_session_id
        if scenario_index is not None and scenario_total is not None:
            print(
                f"[{scenario_index}/{scenario_total}] started {scenario.scenario_id} "
                f"session={app_session_id}",
                flush=True,
            )
        await set_deep_research(client, app_session_id, scenario.deep_research, headers)
        final_status, attempts, retry_reasons = await run_workflow_with_retries(
            client,
            scenario,
            app_session_id,
            config,
            headers,
        )
        result.run_attempts = attempts
        result.retry_reasons = retry_reasons
        result.step_failed = _failed_step(final_status)
        if final_status.get("status") != "completed" or final_status.get("ok") is not True:
            result.error = str(final_status.get("last_error") or "run-all failed")
            await _fill_cost_summary(client, result)
            return result

        export_status, export_file_or_error = await export_compliance_text(
            client,
            scenario,
            app_session_id,
            config,
            headers,
            output_dir,
        )
        result.export_status = export_status
        if export_status == "success":
            result.export_file = export_file_or_error
            result.status = "success"
        else:
            result.status = "export_failed"
            result.error = export_file_or_error

        await _fill_cost_summary(client, result)
        return result
    except Exception as exc:
        result.error = str(exc)
        try:
            await _fill_cost_summary(client, result)
        except Exception:
            pass
        return result
    finally:
        result.finished_at = utc_now()
        result.duration_min = round((time.monotonic() - started_monotonic) / 60, 2)


class BatchLogger:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.output_dir / "runs.jsonl"
        self.csv_path = self.output_dir / "summary.csv"
        self.config_path = self.output_dir / "config.json"
        self._csv_fieldnames: list[str] | None = None

    def write_config(self, config: BatchConfig) -> None:
        self.config_path.write_text(
            json.dumps(redacted_config(config), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def write_result(self, result: ScenarioResult) -> None:
        diagnostic_row = result.to_row(include_diagnostics=True)
        with self.jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(diagnostic_row, ensure_ascii=False) + "\n")

        if self._csv_fieldnames is None:
            self._csv_fieldnames = list(diagnostic_row)
            write_header = not self.csv_path.exists()
        else:
            write_header = False
        with self.csv_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self._csv_fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow(diagnostic_row)

    def completed_scenario_ids(self) -> set[str]:
        if not self.jsonl_path.exists():
            return set()
        completed: set[str] = set()
        with self.jsonl_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("status") == "success" and row.get("scenario_id"):
                    completed.add(str(row["scenario_id"]))
        return completed


async def run_batch(
    config: BatchConfig,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> BatchResult:
    validate_config(config)
    output_dir = resolve_batch_output_dir(config)
    effective_config = config if config.batch_id.strip() else replace(config, batch_id=output_dir.name)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = BatchLogger(output_dir)
    logger.write_config(effective_config)
    headers = api_key_headers(config)

    async with httpx.AsyncClient(
        base_url=config.base_url.rstrip("/"),
        timeout=httpx.Timeout(60.0, read=None),
        transport=transport,
    ) as client:
        await login(client, config)
        pairs = discover_law_pairs(config.built_in_laws_dir)
        if config.law_pairs:
            selected = set(config.law_pairs)
            pairs = [pair for pair in pairs if pair.name in selected]
        if not pairs:
            raise RuntimeError("No matching built-in law pairs found")
        await validate_law_pairs(client, pairs)

        scenarios = select_scenarios(
            pairs,
            config.models,
            config.deep_research_modes,
            config.repetitions,
            scenario_ids=config.scenario_ids,
            limit=config.limit_scenarios,
        )
        if config.resume_completed:
            completed_ids = logger.completed_scenario_ids()
            if completed_ids:
                original_count = len(scenarios)
                scenarios = [
                    scenario
                    for scenario in scenarios
                    if scenario.scenario_id not in completed_ids
                ]
                skipped = original_count - len(scenarios)
                print(
                    f"Resuming {output_dir.name}: skipped {skipped} completed scenario(s), "
                    f"{len(scenarios)} remaining.",
                    flush=True,
                )

        semaphore = asyncio.Semaphore(config.concurrency)
        results: list[ScenarioResult] = []

        async def _run_and_log(index: int, scenario: Scenario) -> ScenarioResult:
            async with semaphore:
                print(
                    f"[{index}/{len(scenarios)}] queued {scenario.scenario_id} "
                    f"batch={output_dir.name}",
                    flush=True,
                )
                result = await run_scenario(
                    client,
                    scenario,
                    config,
                    headers,
                    output_dir,
                    scenario_index=index,
                    scenario_total=len(scenarios),
                )
                logger.write_result(result)
                print(
                    f"[{index}/{len(scenarios)}] {result.status} {scenario.scenario_id} "
                    f"session={result.app_session_id or '-'} "
                    f"duration={result.duration_min}min "
                    f"cost={result.estimated_total_cost_usd}",
                    flush=True,
                )
                return result

        for result in await asyncio.gather(
            *[_run_and_log(index, scenario) for index, scenario in enumerate(scenarios, start=1)]
        ):
            results.append(result)

    return BatchResult(results=results, output_dir=output_dir)


def parse_model_specs(values: list[str] | None) -> tuple[ModelSpec, ...]:
    if not values:
        return tuple(ModelSpec(provider=provider, model=model) for provider, model in DEFAULT_MODELS)
    specs = []
    for value in values:
        if ":" not in value:
            raise ValueError("models must use provider:model format")
        provider, model = value.split(":", 1)
        specs.append(ModelSpec(provider=provider.strip(), model=model.strip()))
    return tuple(specs)


def parse_deep_research_modes(value: str) -> tuple[bool, ...]:
    normalized = value.strip().lower()
    if normalized in {"both", "all"}:
        return (True, False)
    if normalized in {"on", "true", "yes", "mit"}:
        return (True,)
    if normalized in {"off", "false", "no", "ohne"}:
        return (False,)
    raise ValueError("--deep-research must be one of: both, on, off")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run CCC batch workflows and exports.")
    parser.add_argument("--base-url", default="http://localhost:5000")
    parser.add_argument("--email", default=os.environ.get("CCC_BATCH_EMAIL", ""))
    parser.add_argument("--password", default=os.environ.get("CCC_BATCH_PASSWORD", ""))
    parser.add_argument("--pair", action="append", dest="law_pairs")
    parser.add_argument("--model", action="append", dest="models", help="provider:model")
    parser.add_argument("--deep-research", default="both", choices=["both", "on", "off"])
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Do not skip previously successful scenarios in the same batch folder.",
    )
    parser.add_argument("--max-run-attempts", type=int, default=5)
    parser.add_argument("--max-deep-research-attempts", type=int, default=1)
    parser.add_argument(
        "--max-stuck-minutes",
        type=float,
        default=60.0,
        help="Retry a run after this many minutes without observable progress. Use 0 to disable.",
    )
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--limit-scenarios", type=int)
    parser.add_argument(
        "--scenario-id",
        action="append",
        dest="scenario_ids",
        help="Run only the selected stable scenario id. Repeat to select multiple.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--batch-id",
        default="",
        help="Optional log folder name under --output-dir. Defaults to a UTC timestamp.",
    )
    parser.add_argument("--built-in-laws-dir", type=Path, default=DEFAULT_BUILT_IN_LAWS_DIR)
    parser.add_argument("--no-download-pdfs", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


async def async_main(argv: list[str] | None = None) -> int:
    load_dotenv_if_available()
    args = build_arg_parser().parse_args(argv)
    config = BatchConfig(
        base_url=args.base_url,
        email=args.email,
        password=args.password,
        law_pairs=tuple(args.law_pairs or ()),
        models=parse_model_specs(args.models),
        deep_research_modes=parse_deep_research_modes(args.deep_research),
        repetitions=args.repetitions,
        concurrency=args.concurrency,
        resume_completed=not args.no_resume,
        max_run_attempts=args.max_run_attempts,
        max_deep_research_attempts=args.max_deep_research_attempts,
        max_stuck_minutes=args.max_stuck_minutes,
        poll_seconds=args.poll_seconds,
        output_dir=args.output_dir,
        batch_id=args.batch_id,
        built_in_laws_dir=args.built_in_laws_dir,
        limit_scenarios=args.limit_scenarios,
        scenario_ids=tuple(args.scenario_ids or ()),
        download_pdfs=not args.no_download_pdfs,
    )
    validate_config(config)

    pairs = discover_law_pairs(config.built_in_laws_dir)
    if config.law_pairs:
        selected = set(config.law_pairs)
        pairs = [pair for pair in pairs if pair.name in selected]
    scenarios = select_scenarios(
        pairs,
        config.models,
        config.deep_research_modes,
        config.repetitions,
        scenario_ids=config.scenario_ids,
        limit=config.limit_scenarios,
    )
    if args.dry_run:
        for scenario in scenarios:
            print(scenario.scenario_id)
        print(f"{len(scenarios)} scenario(s)")
        return 0

    result = await run_batch(config)
    print(result.to_dataframe())
    return 0


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
