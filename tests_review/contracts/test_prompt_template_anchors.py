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


class TestInformationspflichtDefinitionAnchor:
    """LF-IP-001: Die inhaltliche NKRG-Definition der Informationspflicht muss
    im REGULATIONS_IDENTIFICATION-Prompt stehen (dort wird das Flag gesetzt),
    und die Step-Analyse muss die Checkliste Teil A an das gesetzte Flag koppeln,
    statt die IP-Eigenschaft neu einzuschaetzen.
    """

    def test_identification_prompt_defines_informationspflicht(self):
        template = PROMPT_TEMPLATES[PromptId.REGULATIONS_IDENTIFICATION]
        assert "NKRG" in template
        assert "verfuegbar zu halten" in template
        assert "uebermitteln" in template

    def test_step_analysis_business_rule_couples_teil_a_to_flag(self):
        rule = PROCESS_STEP_ANALYSIS_ADDRESSEE_RULES[BUSINESS]
        assert "ist_informationspflicht_wirtschaft" in rule
        assert "Teil A" in rule


class TestComplianceExportInformationspflichtBinding:
    """LF-IP-002: Der Compliance-Text-Export-Prompt muss IP-Status und IP-Summe
    deterministisch an die Snapshot-Felder binden, statt sie vom LLM neu
    herleiten zu lassen. Konkret muss das Template den IP-Status an das Flag
    `ist_informationspflicht_wirtschaft` koppeln, die IP-Summe an
    `summen.bureaucracy_cost` binden und die "Keine"-Aussage verschaerfen.
    """

    @pytest.fixture
    def template(self) -> str:
        return PROMPT_TEMPLATES[PromptId.COMPLIANCE_TEXT_EXTRACTION]

    def test_template_binds_ip_status_to_flag(self, template: str):
        # IP-Status muss an das Snapshot-Flag gekoppelt sein.
        assert "ist_informationspflicht_wirtschaft" in template

    def test_template_binds_ip_sum_to_bureaucracy_cost(self, template: str):
        # IP-Summe muss an summen.bureaucracy_cost gebunden sein.
        assert "bureaucracy_cost" in template

    def test_template_tightens_keine_rule(self, template: str):
        # Verschaerfte "Keine"-Regel: "Keine" nur zulaessig, wenn keine
        # Wirtschafts-Vorgabe das IP-Flag traegt. Stabiler Positiv-Marker,
        # der bei harmloser Umformulierung nicht bricht.
        assert "ist nur zulässig, wenn keine" in _compact(template)


class TestComplianceExportVerwaltungLevels:
    """LF-VERW-001: Die Verwaltung wird im Export nicht mehr als reine
    Bundesverwaltung dargestellt, sondern getrennt nach Bundesebene und
    Landesebene (einschliesslich Kommunen), deterministisch gebunden an die
    Snapshot-Felder summen.verwaltung_bundesebene / summen.verwaltung_landesebene
    (StBA-Leitfaden Kap. 8: der Laenderanteil enthaelt die Kommunen).
    """

    @pytest.fixture
    def template(self) -> str:
        return PROMPT_TEMPLATES[PromptId.COMPLIANCE_TEXT_EXTRACTION]

    def test_headings_use_verwaltung_not_bundesverwaltung(self, template: str):
        assert "## E.3 Erfüllungsaufwand der Verwaltung" in template
        assert "## 4.3 Erfüllungsaufwand der Verwaltung" in template
        assert "Bundesverwaltung" not in template

    def test_davon_lines_bound_to_snapshot_fields(self, template: str):
        assert "summen.verwaltung_bundesebene" in template
        assert "summen.verwaltung_landesebene" in template
        assert "Bundesebene" in template
        assert "Landesebene" in template

    def test_kommunen_belong_to_landesebene(self, template: str):
        compact = _compact(template)
        assert (
            "Landesebene (einschließlich Kommunen)" in compact
            or "Länderanteil schließt die Kommunen ein" in compact
        )

    def test_no_bund_only_rule(self, template: str):
        compact = _compact(template)
        assert "ausschließlich den Bund" not in compact
        assert "Stelle keine Beträge für Länder" not in compact


class TestComplianceExportSection4VorgabeTables:
    """LF-EA4-001: Abschnitt 4 der Begruendung stellt je Normadressat genau eine
    konsolidierte, an den Beispieldokumenten ausgerichtete Tabelle dar. Spalten:
    `lfd. Nr.`, `Norm (§§); Bezeichnung der Vorgabe`, `Jährliche Fallzahl und
    Einheit` sowie ein `Jährlicher Aufwand pro Fall`. Die Wirtschaftstabelle (4.2)
    fuehrt eine `IP`-Spalte (`Ja`/leer, gebunden an
    `ist_informationspflicht_wirtschaft`) und eine Summenzeile
    `…davon aus Informationspflichten (IP)` (an `summen.bureaucracy_cost`
    gebunden). Die Verwaltung (4.3) fuehrt Bund/Land nur in den Summenzeilen
    `davon auf Bundesebene`/`davon auf Landesebene (inklusive Kommunen)`. Die
    frueheren Zwischenueberschriften je Vorgabe entfallen.
    """

    @pytest.fixture
    def template(self) -> str:
        return PROMPT_TEMPLATES[PromptId.COMPLIANCE_TEXT_EXTRACTION]

    def test_each_section_table_has_vorgabe_column(self, template: str):
        assert template.count("| Norm (§§); Bezeichnung der Vorgabe |") >= 3

    def test_tables_use_running_number_and_case_count_columns(self, template: str):
        assert "| lfd. Nr. |" in template
        assert "Jährliche Fallzahl und Einheit" in template

    def test_business_table_has_ip_column(self, template: str):
        assert "| Norm (§§); Bezeichnung der Vorgabe | IP |" in _compact(template)

    def test_ip_column_uses_ja_not_symbols(self, template: str):
        assert "In der Spalte `IP` steht `Ja`" in template
        assert "✓" not in template

    def test_business_table_has_ip_sum_row_bound_to_bureaucracy_cost(self, template: str):
        assert "davon aus Informationspflichten (IP)" in template
        assert "bureaucracy_cost" in template

    def test_ip_column_bound_to_flag(self, template: str):
        assert "ist_informationspflicht_wirtschaft" in template

    def test_citizen_table_sum_rows(self, template: str):
        assert "Summe Zeitaufwand (in Stunden)" in template
        assert "Summe Sachaufwand (in Tsd. Euro)" in template

    def test_per_vorgabe_heading_is_gone(self, template: str):
        assert "### Vorgabe [Nummer]" not in template

    def test_result_column_forbids_superscript_footnote_markers(self, template: str):
        assert "keine hochgestellten Fußnotenziffern" in template

    def test_geringfuegig_row_rule_present(self, template: str):
        assert "geringfügig" in template

    def test_administration_split_stays_in_summary_rows(self, template: str):
        assert "davon auf Bundesebene" in template
        assert "davon auf Landesebene (inklusive Kommunen)" in template
        assert "summen.verwaltung_bundesebene" in template
        assert "summen.verwaltung_landesebene" in template

    def test_footnote_format_present(self, template: str):
        assert "**Zu lfd. Nr. X:**" in template


class TestComplianceExportRounding:
    """LF-RUND-001: Euro-Betraege im Export werden auf ganze Euro gerundet.
    Cent-Angaben wie `14 017 746,67 Euro` sind bei Betraegen dieser
    Groessenordnung nicht ueblich und wurden im Review beanstandet.
    """

    @pytest.fixture
    def template(self) -> str:
        return PROMPT_TEMPLATES[PromptId.COMPLIANCE_TEXT_EXTRACTION]

    def test_template_demands_whole_euro_amounts(self, template: str):
        assert "auf ganze Euro gerundet" in _compact(template)

    def test_template_forbids_cent_amounts(self, template: str):
        assert "Cent werden nicht ausgewiesen" in _compact(template)
