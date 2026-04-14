from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from backend.core import db
from backend.core.norm_addressees import SUPPORTED_NORM_ADDRESSEES
from backend.core.prompts import PromptId


@dataclass(frozen=True)
class WorkflowStep:
    key: str
    label: str
    status_flag: str


WORKFLOW_STEPS: tuple[WorkflowStep, ...] = (
    WorkflowStep("total_cost", "Gesamtkosten berechnen", "total_cost_ready"),
    WorkflowStep("effort", "Aufwand berechnen", "effort_ready"),
    WorkflowStep("process_steps", "Prozessschritte bestimmen", "process_steps_ready"),
    WorkflowStep("case_groups", "Fallgruppen entwickeln", "case_groups_ready"),
    WorkflowStep("processes", "Prozesse bündeln", "processes_ready"),
    WorkflowStep("regulations", "Vorgaben bestimmen", "regulations_ready"),
    WorkflowStep("summary", "CCC starten", "summary_ready"),
)


def get_last_completed_step(status: dict) -> WorkflowStep | None:
    for step in WORKFLOW_STEPS:
        if bool(status.get(step.status_flag)):
            return step
    return None


def _undo_total_cost(session_id: int) -> None:
    for addressee in SUPPORTED_NORM_ADDRESSEES:
        db.clear_costs(session_id, norm_addressee=addressee)


def _undo_effort(session_id: int) -> None:
    for addressee in SUPPORTED_NORM_ADDRESSEES:
        db.clear_effort_metrics(session_id, norm_addressee=addressee)
    db.invalidate_llm_answers(
        session_id,
        [PromptId.CASES_CALCULATION, PromptId.EFFORT_CALCULATION],
        reason="session_reverted",
    )


def _undo_process_steps(session_id: int) -> None:
    db.delete_process_steps_for_session(session_id)
    db.invalidate_llm_answers(
        session_id,
        [PromptId.PROCESS_STEP_ANALYSIS],
        reason="session_reverted",
    )


def _undo_case_groups(session_id: int) -> None:
    db.delete_case_groups_for_session(session_id)
    db.invalidate_llm_answers(
        session_id,
        [PromptId.CASE_GROUP_DEVELOPMENT],
        reason="session_reverted",
    )


def _undo_processes(session_id: int) -> None:
    db.delete_processes_for_session(session_id)
    db.invalidate_llm_answers(
        session_id,
        [PromptId.PROCESS_COMPILATION],
        reason="session_reverted",
    )


def _undo_regulations(session_id: int) -> None:
    db.delete_regulations_for_session(session_id)
    db.invalidate_llm_answers(
        session_id,
        [PromptId.REGULATIONS_IDENTIFICATION],
        reason="session_reverted",
    )


def _undo_summary(session_id: int) -> None:
    db.clear_session_summary(session_id)
    db.invalidate_llm_answers(
        session_id,
        [PromptId.LAW_SUMMARY],
        reason="session_reverted",
    )


_UNDO_HANDLERS: dict[str, Callable[[int], None]] = {
    "total_cost": _undo_total_cost,
    "effort": _undo_effort,
    "process_steps": _undo_process_steps,
    "case_groups": _undo_case_groups,
    "processes": _undo_processes,
    "regulations": _undo_regulations,
    "summary": _undo_summary,
}


def undo_step(session_id: int, step_key: str) -> None:
    handler = _UNDO_HANDLERS.get(step_key)
    if handler is None:
        raise ValueError(f"Unknown workflow step: {step_key}")
    handler(session_id)
