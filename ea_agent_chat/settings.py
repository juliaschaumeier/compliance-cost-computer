"""
Centralized settings with separate LLM, backend, and frontend scopes.

Defaults live here. `current_config.py` can stay explicit by calling build_settings(...)
with only the overrides that should be visible.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


ROOT = Path(__file__).resolve().parent
REGULATIONS_ROOT = ROOT.parent / "regulations"
RESULTS_ROOT = ROOT.parent / "results"


@dataclass(frozen=True)
class LLMSettings:
    API_TYPE: str = "openai"
    MODEL_PARAMETERS_REASONING: Any = field(default_factory=lambda: {
        "model": "gpt-5",
        "reasoning_effort": "high",
        "verbosity": "medium",
    })
    MODEL_PARAMETERS_VERIFICATION: Any = field(default_factory=lambda: {
        "model": "gpt-5",
        "reasoning_effort": "low",
        "verbosity": "low",
    })
    CHOOSE_BEST_OF: int = 1
    SAVE_ENTIRE_RESPONSES: bool = False
    TIMEOUT_IN_MINUTES: int = 120
    LOG_LEVEL_CONSOLE: str = "INFO"
    LOG_LEVEL_FILE: str = "INFO"
    REGULATION_1_DESCRIPTOR: Optional[str] = None
    REGULATION_2_DESCRIPTOR: Optional[str] = None
    REGULATION_1_FILENAME: Optional[str] = None
    REGULATION_2_FILENAME: Optional[str] = None
    RESULT_FOLDER: Path = field(
        default_factory=lambda: RESULTS_ROOT / f"chat_{datetime.now():%Y%m%d-%H%M}"
    )
    REGULATION_1_TEXT: Optional[str] = None
    REGULATION_2_TEXT: Optional[str] = None


@dataclass(frozen=True)
class BackendSettings:
    DB_PATH: Path = ROOT / "tiles.db"
    SEED_JSON: Path = ROOT / "mockup_data.json"
    HOST: str = "0.0.0.0"
    PORT: int = 5000
    DEBUG: bool = True


@dataclass(frozen=True)
class FrontendSettings:
    API_BASE_URL: str = "http://localhost:5000"
    DEFAULT_PREREQ_LABEL: str = "generate prerequisites from law"
    DEFAULT_PROCESS_LABEL: str = "generate processes from prerequisites"


@dataclass(frozen=True)
class AppSettings:
    llm: LLMSettings
    backend: BackendSettings
    frontend: FrontendSettings


def _load_reg_text(filename: Optional[str]) -> Optional[str]:
    if not filename:
        return None
    path = REGULATIONS_ROOT / filename
    return path.read_text(encoding="utf-8") if path.exists() else None


def _default_llm_settings(api_type: str) -> LLMSettings:
    api_type = (api_type or "openai").lower()
    if api_type == "gemini":
        return LLMSettings(
            API_TYPE="gemini",
            MODEL_PARAMETERS_REASONING="gemini-2.5-pro",
            MODEL_PARAMETERS_VERIFICATION="gemini-2.5-flash",
        )
    if api_type in ("openai", "openai_with_gemini"):
        return LLMSettings(API_TYPE=api_type)
    raise ValueError(f"Unsupported API_TYPE: {api_type}")


def _apply_llm_derived(llm: LLMSettings, compute_texts: bool) -> LLMSettings:
    if not compute_texts:
        return llm
    reg_1_text = _load_reg_text(llm.REGULATION_1_FILENAME)
    reg_2_text = _load_reg_text(llm.REGULATION_2_FILENAME)
    llm.RESULT_FOLDER.mkdir(parents=True, exist_ok=True)
    return replace(
        llm,
        REGULATION_1_TEXT=reg_1_text,
        REGULATION_2_TEXT=reg_2_text,
    )


def build_settings(
    api_type: str = "openai",
    compute_llm_texts: bool = True,
    **overrides: Dict[str, Any],
) -> AppSettings:
    """
    Build settings with dynamic defaults based on api_type.

    - api_type="openai" or "openai_with_gemini" keeps OpenAI-style model params (dicts)
    - api_type="gemini" uses Gemini model names (strings)
    - compute_llm_texts toggles loading regulation files and creating the results folder
    """
    if "API_TYPE" in overrides:
        api_type = overrides["API_TYPE"]

    llm = _default_llm_settings(api_type)
    backend = BackendSettings()
    frontend = FrontendSettings()

    llm_overrides = {k: v for k, v in overrides.items() if hasattr(llm, k)}
    backend_overrides = {k: v for k, v in overrides.items() if hasattr(backend, k)}
    frontend_overrides = {k: v for k, v in overrides.items() if hasattr(frontend, k)}

    if "RESULT_FOLDER" in llm_overrides and not isinstance(llm_overrides["RESULT_FOLDER"], Path):
        llm_overrides["RESULT_FOLDER"] = Path(llm_overrides["RESULT_FOLDER"])
    if "DB_PATH" in backend_overrides and not isinstance(backend_overrides["DB_PATH"], Path):
        backend_overrides["DB_PATH"] = Path(backend_overrides["DB_PATH"])
    if "SEED_JSON" in backend_overrides and not isinstance(backend_overrides["SEED_JSON"], Path):
        backend_overrides["SEED_JSON"] = Path(backend_overrides["SEED_JSON"])

    llm = LLMSettings(**{**llm.__dict__, **llm_overrides})
    backend = BackendSettings(**{**backend.__dict__, **backend_overrides})
    frontend = FrontendSettings(**{**frontend.__dict__, **frontend_overrides})
    llm = _apply_llm_derived(llm, compute_llm_texts)

    return AppSettings(llm=llm, backend=backend, frontend=frontend)


# Optional singleton for quick imports.
settings = build_settings()
