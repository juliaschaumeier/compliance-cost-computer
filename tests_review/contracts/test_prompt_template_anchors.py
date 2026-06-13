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
    EFFORT_JSON_SCHEMA_BY_ADDRESSEE,
    EFFORT_JSON_SCHEMA_DEFAULT,
    NORM_ADDRESSEE_PROMPT_OPENINGS,
    NORM_ADDRESSEE_RULES_ADMINISTRATION,
    NORM_ADDRESSEE_RULES_BUSINESS,
    NORM_ADDRESSEE_RULES_CITIZENS,
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

    def test_template_requires_one_process_per_vorgabe(self, template: str):
        # Issue #13: jede vorgaben_id nur in einem Prozess; Selbstcheck vor Ausgabe.
        assert "genau einem Prozess" in template
        assert "in mehreren Prozessen vorkommt" in template
        assert "im selben Prozess" in template


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
        context = NORM_ADDRESSEE_PROMPT_OPENINGS[norm_addressee].strip()
        rule = PROCESS_STEP_ANALYSIS_ADDRESSEE_RULES[norm_addressee]

        assert context
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


class TestRecurringOnlyContract:
    """Issues #13/#25: Die Pipeline erzeugt/berechnet ausschliesslich jaehrlich
    wiederkehrenden Erfuellungsaufwand. Einmaliger Umstellungs-/Einfuehrungs-/
    Einarbeitungsaufwand wird nicht ausgegeben, quantifiziert oder bewertet.

    Diese Anker sichern die positive "nur wiederkehrend"-Pflichtregel in den vier
    Bodies sowie die Abwesenheit der entfernten einmalig-Logik gegen Rueckkehr.
    """

    def test_case_group_development_demands_recurring_only(self):
        t = PROMPT_TEMPLATES[PromptId.CASE_GROUP_DEVELOPMENT]
        assert "Nur jaehrlich wiederkehrender Erfuellungsaufwand" in t
        assert "Nicht zulaessig als Fallgruppe" in t

    def test_process_compilation_demands_recurring_only(self):
        t = PROMPT_TEMPLATES[PromptId.PROCESS_COMPILATION]
        assert "Nur jaehrlich wiederkehrender Erfuellungsaufwand" in t
        assert "Nicht zulaessig als Prozess" in t
        # Status-Klarstellung: ein neu eingefuehrter, aber wiederkehrender Prozess bleibt zulaessig.
        assert "ist hingegen zulaessig" in t

    def test_process_step_analysis_demands_recurring_only(self):
        t = PROMPT_TEMPLATES[PromptId.PROCESS_STEP_ANALYSIS]
        assert "Nur jaehrlich wiederkehrender Erfuellungsaufwand" in t

    def test_cases_calculation_demands_recurring_only(self):
        t = PROMPT_TEMPLATES[PromptId.CASES_CALCULATION]
        assert (
            "Quantifizieren Sie Fallzahlen ausschliesslich fuer regelmaessig pro Jahr "
            "wiederkehrende Fallgruppen" in t
        )

    def test_effort_calculation_demands_recurring_only(self):
        t = PROMPT_TEMPLATES[PromptId.EFFORT_CALCULATION]
        assert "regelmaessig wiederkehrenden Aufwand pro Einzelfall und Jahr" in t

    def test_addressee_rules_have_no_one_time_axes(self):
        # Die entfernten einmalig-Achsen duerfen nicht zurueckkehren.
        for rules in (
            NORM_ADDRESSEE_RULES_ADMINISTRATION,
            NORM_ADDRESSEE_RULES_BUSINESS,
            NORM_ADDRESSEE_RULES_CITIZENS,
        ):
            for text in rules.values():
                assert "einmalig" not in text.lower()

    def test_effort_schema_has_no_per_case_execution_field(self):
        assert "ausfuehrung_pro_einzelfall" not in EFFORT_JSON_SCHEMA_DEFAULT
        for schema in EFFORT_JSON_SCHEMA_BY_ADDRESSEE.values():
            assert "ausfuehrung_pro_einzelfall" not in schema

    def test_one_off_lists_avoid_status_ambiguous_einfuehrung(self):
        # "Einfuehrung" als nacktes Listenbeispiel kollidiert mit dem aenderungsstatus
        # "eingefuehrt"; die Negativlisten beginnen daher mit "Implementierung".
        for pid in (
            PromptId.PROCESS_COMPILATION,
            PromptId.CASE_GROUP_DEVELOPMENT,
            PromptId.PROCESS_STEP_ANALYSIS,
        ):
            assert "z.B. Einfuehrung, Implementierung" not in PROMPT_TEMPLATES[pid]
