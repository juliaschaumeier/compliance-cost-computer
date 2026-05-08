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
    CITIZENS_PROMPT_RULES,
    EFFORT_METHOD_GUIDANCE,
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


class TestEffortGuidanceAddresseeAnchors:
    """LF-K7-001 / LF-K8-001: Pro Adressat muessen die richtigen
    Zeitwert- und Lohnkostentabellen und Lohngruppen referenziert sein.
    """

    def test_administration_references_lohngruppen_a_to_d(self):
        text = EFFORT_METHOD_GUIDANCE[ADMINISTRATION]
        assert "A=Einfacher und mittlerer Dienst" in text
        assert "B=Gehobener Dienst" in text
        assert "C=Hoeherer Dienst" in text
        assert "D=Durchschnitt" in text

    def test_administration_references_zeitwerttabelle_verwaltung(self):
        text = EFFORT_METHOD_GUIDANCE[ADMINISTRATION]
        assert "Zeitwerttabelle Verwaltung" in text

    def test_business_references_zeitwerttabelle_wirtschaft_anhang_4(self):
        """Befund Block 2.4: Anhang 4 muss explizit benannt sein."""
        text = EFFORT_METHOD_GUIDANCE[BUSINESS]
        assert "Zeitwerttabelle Wirtschaft" in text
        assert "Anhang 4" in text

    def test_business_references_lohngruppen_niedrig_to_durchschnitt(self):
        text = EFFORT_METHOD_GUIDANCE[BUSINESS]
        assert "A=Niedrig" in text
        assert "B=Mittel" in text
        assert "C=Hoch" in text
        assert "D=Durchschnitt" in text

    def test_business_marks_bureaucracy_costs_as_separate(self):
        text = EFFORT_METHOD_GUIDANCE[BUSINESS]
        assert "Buerokratiekosten" in text
        assert "getrennt" in text

    def test_citizens_explicitly_forbids_roles_and_wages(self):
        """LF-K8-001 fuer Citizens: Keine Monetarisierung, keine Rollen,
        keine Lohngruppen, keine Stundenloehne."""
        text = EFFORT_METHOD_GUIDANCE[CITIZENS]
        assert "keine Rollen" in text
        assert "keine Lohngruppen" in text or "Lohngruppen" in text
        assert "keine Stundenloehne" in text or "Stundenloehne" in text
        assert "Monetarisieren Sie den Zeitaufwand nicht" in text

    def test_citizens_references_zeitwerttabelle_buerger(self):
        text = EFFORT_METHOD_GUIDANCE[CITIZENS]
        assert "Buergerinnen und Buerger" in text

    def test_citizens_defines_sachaufwand_explicitly(self):
        text = EFFORT_METHOD_GUIDANCE[CITIZENS]
        assert "Sachaufwand" in text
        assert "Gebuehren" in text


class TestCitizensPromptRulesExist:
    """Pro mehrstufigem Prompt muss eine Citizens-spezifische Zusatzregel
    hinterlegt sein, sonst greift die Adressaten-Klausel nicht."""

    @pytest.mark.parametrize(
        "prompt_id",
        [
            PromptId.PROCESS_COMPILATION,
            PromptId.CASE_GROUP_DEVELOPMENT,
            PromptId.CASES_CALCULATION,
        ],
    )
    def test_citizens_addendum_exists_for_prompt(self, prompt_id):
        assert prompt_id in CITIZENS_PROMPT_RULES
        assert CITIZENS_PROMPT_RULES[prompt_id].strip()
        assert "buerger" in CITIZENS_PROMPT_RULES[prompt_id].lower()

    def test_citizens_step_analysis_rule_exists_in_integrated_rules(self):
        text = PROCESS_STEP_ANALYSIS_ADDRESSEE_RULES[CITIZENS]

        assert text.strip()
        assert "Buerger" in text


class TestCasesCalculationSowiesoMention:
    """Befund Block 2.3 (offen): Sowieso-Anteile sollten in der
    Fallzahlermittlung explizit erwaehnt sein. Aktuell nur fuer Citizens
    formuliert. Dieser Test sichert wenigstens die Citizens-Formulierung.
    Ein zusaetzlicher Test fuer Business/Administration kommt, wenn die
    Regel dort ergaenzt ist (Befund 2.3).
    """

    def test_citizens_cases_rule_mentions_sowieso(self):
        text = CITIZENS_PROMPT_RULES[PromptId.CASES_CALCULATION]
        assert "Sowieso" in text


class TestProcessStepAnalysisContract:
    """Issue #26: Schrittanalyse bleibt Taetigkeitsanalyse.

    Der Prompt darf die spaetere Aufwandsermittlung vorbereiten, aber nicht
    selbst Minuten, Lohngruppen, Stundenloehne, Sachaufwand oder Kosten
    anfordern.
    """

    @pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
    def test_step_analysis_renders_known_norm_addressee(self, norm_addressee):
        text = render_prompt(
            PromptId.PROCESS_STEP_ANALYSIS,
            law_summary="Kurzfassung",
            case_groups_json="[]",
            norm_addressee=norm_addressee,
        )

        assert f"Dieser Lauf betrifft nur den Normadressaten `{norm_addressee}`" in text
        assert f'"normadressat": "{norm_addressee}"' in text

    @pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
    def test_step_analysis_final_json_instruction_is_last(self, norm_addressee):
        text = render_prompt(
            PromptId.PROCESS_STEP_ANALYSIS,
            law_summary="Kurzfassung",
            case_groups_json="[]",
            norm_addressee=norm_addressee,
        )
        final_instruction = "Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen."

        assert text.rstrip().endswith(final_instruction)
        assert "Zusatz fuer" not in text

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
            "Zeitaufwand fuer Wegezeiten",
        ]
        assert all(phrase not in text for phrase in forbidden)
        assert "Schaetzen Sie in diesem Schritt keine Minuten" in text

    @pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
    def test_step_analysis_uses_flexible_activity_count(self, norm_addressee):
        text = render_prompt(
            PromptId.PROCESS_STEP_ANALYSIS,
            law_summary="Kurzfassung",
            case_groups_json="[]",
            norm_addressee=norm_addressee,
        )

        assert "wenige, fachlich klare Haupttaetigkeiten" in text
        assert "drei bis fuenf" not in text
        assert "vier bis sechs" not in text
