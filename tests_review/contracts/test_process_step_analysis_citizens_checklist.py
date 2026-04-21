"""
Regression-Guard fuer Review-Befund "Admin-Regeln im PROCESS_STEP_ANALYSIS
fuer alle NAs sichtbar".

Der Leitfaden Erfuellungsaufwand (Feb 2026) gibt je Normadressat eine
eigene Checkliste vor:
  - Verwaltung: Kap. 7.2.1, S. 49 (mit "Bescheid erstellen", Eingangs-
    bestaetigung, Ueberwachungs-/Aufsichtsmassnahmen, Risikoklassifizierung).
  - Wirtschaft: Kap. 6.2.1 Teil A + Teil B, S. 37-38 (Einarbeitung in IP,
    Mitwirkung bei Pruefung, Lagerhaltung/Warenwirtschaft/Produktion etc.).
  - Buergerinnen und Buerger: Kap. 5 enthaelt keine Checkliste im
    klassischen Sinn; stattdessen liefert CITIZENS_PROMPT_RULES die
    fachspezifischen Hinweise.

Vorher wurde die Verwaltungs-Checkliste auch fuer Wirtschaft ausgeliefert,
was laut Leitfaden nicht vorgesehen ist. Jetzt rendert das Template je NA
die jeweils passende Checkliste; fuer Citizens bleibt der Platzhalter leer.
"""
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS
from backend.core.prompts import PromptId, render_prompt


_ADMIN_CHECKLIST_MARKER = "Bescheid erstellen"
_BUSINESS_CHECKLIST_MARKER = "Lagerhaltung, Warenwirtschaft, Produktion"
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
    assert _BUSINESS_CHECKLIST_MARKER not in prompt


def test_business_run_sees_business_checklist():
    prompt = _render(BUSINESS)
    assert _BUSINESS_CHECKLIST_MARKER in prompt
    # Die Verwaltungs-Checkliste (z. B. "Bescheid erstellen") darf bei
    # Wirtschaft nicht auftauchen – sie ist laut Leitfaden Kap. 7
    # ausschliesslich fuer die Verwaltung vorgesehen.
    assert _ADMIN_CHECKLIST_MARKER not in prompt


def test_citizens_run_does_not_see_admin_checklist():
    prompt = _render(CITIZENS)
    assert _ADMIN_CHECKLIST_MARKER not in prompt
    assert _BUSINESS_CHECKLIST_MARKER not in prompt


def test_citizens_run_gets_citizens_specific_rule():
    prompt = _render(CITIZENS)
    assert _CITIZENS_RULE_MARKER in prompt


def test_admin_run_does_not_get_citizens_rule():
    prompt = _render(ADMINISTRATION)
    assert _CITIZENS_RULE_MARKER not in prompt
