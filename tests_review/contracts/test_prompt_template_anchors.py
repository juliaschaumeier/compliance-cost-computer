"""
Schicht 2.3 / Regression-Guard fuer Befund Block 2.2 und verwandte
Leitfaden-Anker in den Prompt-Templates.

Zweck: Schuetzt zentrale Leitfaden-Regeln gegen unbemerktes Verschwinden
oder Abschwaechung beim Refactoring der Prompts. Jede Behauptung ist eine
inhaltliche Pflichtformulierung, deren Loeschung eine Verletzung des
Leitfadens StBA 2026 waere.

Die Anchors sind bewusst tolerant gegenueber Wortumstellungen formuliert,
aber spezifisch genug, dass eine versehentliche Entfernung der
Kernaussage anschlaegt.
"""
import pytest

from backend.core.prompts import (
    PROCESS_STEP_ANALYSIS_ADDRESSEE_CONTEXTS,
    PROCESS_STEP_ANALYSIS_ADDRESSEE_RULES,
    PROMPT_TEMPLATES,
    PromptId,
    render_prompt,
)
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS


def _compact(text: str) -> str:
    return " ".join(text.split())


# ---------------------------------------------------------------------------
# BLOCK 2.2 — Union/National-Buendelungsregel im PROCESS_COMPILATION-Prompt
# ---------------------------------------------------------------------------


class TestProcessCompilationUnionNationalRule:
    """LF-K10-001: Vorgaben aus Unionsrecht und aus nationalem Recht
    duerfen nie in denselben Prozess gebuendelt werden. Die Regel muss
    explizit im PROCESS_COMPILATION-Prompt stehen.
    """

    @pytest.fixture
    def template(self) -> str:
        return PROMPT_TEMPLATES[PromptId.PROCESS_COMPILATION]

    def test_template_mentions_unionsrecht(self, template: str):
        assert "Unionsrecht" in template

    def test_template_mentions_nationales_recht(self, template: str):
        assert "nationalem Recht" in template

    def test_template_forbids_bundling_explicitly(self, template: str):
        # "niemals" + "denselben Prozess" -> klare Verbotsformulierung
        assert "niemals" in template.lower()
        assert "denselben Prozess" in template

    def test_template_demands_separate_processes(self, template: str):
        # "getrennte Prozesse" -> klare Anweisung zur Trennung
        assert "getrennte Prozesse" in template

    def test_template_explains_eu_attribution_motivation(self, template: str):
        # Begruendung muss erhalten bleiben, damit der LLM versteht warum
        assert "EU-bedingten" in template or "EU-bedingt" in template


# ---------------------------------------------------------------------------
# Weitere Leitfaden-Anker, parallel abgesichert
# ---------------------------------------------------------------------------


class TestProcessStepAnalysisContract:
    """Issue #26: Schrittanalyse bleibt Taetigkeitsanalyse.

    Der Prompt darf die spaetere Aufwandsermittlung vorbereiten, aber nicht
    selbst Minuten, Lohngruppen, Stundenloehne, Sachaufwand oder Kosten
    anfordern.
    """

    @pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
    def test_step_analysis_renders_integrated_addressee_context_and_rule(self, norm_addressee):
        text = render_prompt(
            PromptId.PROCESS_STEP_ANALYSIS,
            law_summary="Kurzfassung",
            case_groups_json="[]",
            norm_addressee=norm_addressee,
        )
        context = PROCESS_STEP_ANALYSIS_ADDRESSEE_CONTEXTS[norm_addressee]
        rule = PROCESS_STEP_ANALYSIS_ADDRESSEE_RULES[norm_addressee]

        assert context.strip()
        assert rule.strip()
        assert context in text
        assert rule in text

    @pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
    def test_step_analysis_excludes_effort_calculation_instructions(self, norm_addressee):
        text = render_prompt(
            PromptId.PROCESS_STEP_ANALYSIS,
            law_summary="Kurzfassung",
            case_groups_json="[]",
            norm_addressee=norm_addressee,
        )

        forbidden = [
            "Weisen Sie pro Taetigkeit mindestens eine Lohngruppe",
            "realistischem Zeitaufwand in Minuten",
            "IT-bezogenen Sach- oder Personalaufwand separat",
            "Null-Zeitaufwaende",
            "Gesamtzeitaufwand",
        ]
        assert all(phrase not in text for phrase in forbidden)
        assert "Schaetzen Sie in diesem Schritt keine Minuten" in text

    @pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
    def test_step_analysis_does_not_use_invented_activity_count(self, norm_addressee):
        text = render_prompt(
            PromptId.PROCESS_STEP_ANALYSIS,
            law_summary="Kurzfassung",
            case_groups_json="[]",
            norm_addressee=norm_addressee,
        )

        assert "wenige, fachlich klare Haupttaetigkeiten" in text
        assert "drei bis fuenf" not in text
