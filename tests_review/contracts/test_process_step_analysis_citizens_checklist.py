"""
Regression-Guard fuer Review-Befund "Admin-Regeln im PROCESS_STEP_ANALYSIS
fuer alle NAs sichtbar".

Der Basisprompt fuer PROCESS_STEP_ANALYSIS enthielt eine Checkliste mit
stark verwaltungsinternen Taetigkeiten (Bescheid erstellen, Anhoerung,
Risikoklassifizierung, Aufsichtsmassnahmen etc.). Diese Liste wurde
bisher allen Normadressaten mitgegeben - auch Buergerinnen und Buergern,
deren LLM-Output dadurch verwaltungsnah verwaessert werden konnte.

Jetzt: Die Checkliste ist ein Template-Placeholder. Bei Citizens wird sie
auf leeren String gesetzt; die buergerbezogene Checkliste kommt
stattdessen aus CITIZENS_PROMPT_RULES[PROCESS_STEP_ANALYSIS].
"""
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS
from backend.core.prompts import PromptId, render_prompt


_ADMIN_CHECKLIST_MARKER = "Bescheid erstellen"
_CITIZENS_RULE_MARKER = "Buergerinnen und Buerger bei der Schrittanalyse"


def _render(norm_addressee: str) -> str:
    return render_prompt(
        PromptId.PROCESS_STEP_ANALYSIS,
        case_groups_json="[]",
        law_summary="dummy",
        norm_addressee=norm_addressee,
    )


def test_admin_run_sees_admin_checklist():
    prompt = _render(ADMINISTRATION)
    assert _ADMIN_CHECKLIST_MARKER in prompt


def test_business_run_sees_admin_business_checklist():
    # Die Leitfaden-Checkliste ist fuer admin UND Wirtschaft konzipiert.
    prompt = _render(BUSINESS)
    assert _ADMIN_CHECKLIST_MARKER in prompt


def test_citizens_run_does_not_see_admin_checklist():
    prompt = _render(CITIZENS)
    assert _ADMIN_CHECKLIST_MARKER not in prompt


def test_citizens_run_gets_citizens_specific_rule():
    prompt = _render(CITIZENS)
    assert _CITIZENS_RULE_MARKER in prompt


def test_admin_run_does_not_get_citizens_rule():
    prompt = _render(ADMINISTRATION)
    assert _CITIZENS_RULE_MARKER not in prompt
