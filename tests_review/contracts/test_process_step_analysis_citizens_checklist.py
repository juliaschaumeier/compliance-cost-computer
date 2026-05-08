"""
Regression-Guard fuer Review-Befund "Admin-Regeln im PROCESS_STEP_ANALYSIS
fuer alle NAs sichtbar".

Der Leitfaden Erfuellungsaufwand (Feb 2026) gibt je Normadressat eigene
Taetigkeitsanker vor:
  - Verwaltung: Kap. 7.2.1, S. 49 (mit "Bescheid erstellen", Eingangs-
    bestaetigung, Ueberwachungs-/Aufsichtsmassnahmen, Risikoklassifizierung).
  - Wirtschaft: Kap. 6.2.1 Teil A + Teil B, S. 37-38 (Einarbeitung in IP,
    Mitwirkung bei Pruefung, Lagerhaltung/Warenwirtschaft/Produktion etc.).
  - Buergerinnen und Buerger: Kap. 5.2.1, S. 27 (Informationen beschaffen,
    Zeitaufwand fuer Wegezeiten, Formulare ausfuellen etc.).

Checklisten-Isolation (welcher NA bekommt welche Checkliste) ist in
tests/test_prompts.py abgedeckt. Dieser Guard schuetzt ausschliesslich die
Gegenrichtung: dass die Citizens-Handlungsregel nicht in den Admin-Prompt
einfliesst.
"""
from backend.core.norm_addressees import ADMINISTRATION
from backend.core.prompts import PromptId, render_prompt


_CITIZENS_RULE_MARKER = "Jede Taetigkeit muss eine Handlung der Buergerinnen und Buerger selbst sein"


def _render(norm_addressee: str) -> str:
    return render_prompt(
        PromptId.PROCESS_STEP_ANALYSIS,
        case_groups_json="[]",
        law_summary="dummy",
        norm_addressee=norm_addressee,
    )


def test_admin_run_does_not_get_citizens_rule():
    prompt = _render(ADMINISTRATION)
    assert _CITIZENS_RULE_MARKER not in prompt
