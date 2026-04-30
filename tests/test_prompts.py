import re

from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS
from backend.core.prompts import PromptId, render_prompt
import pytest


def _render_effort_prompt(norm_addressee: str) -> str:
    return render_prompt(
        PromptId.EFFORT_CALCULATION,
        law_summary="Kurzfassung",
        step_analysis_json="[]",
        norm_addressee=norm_addressee,
    )


def _render_step_analysis_prompt(norm_addressee: str) -> str:
    return render_prompt(
        PromptId.PROCESS_STEP_ANALYSIS,
        law_summary="Kurzfassung",
        case_groups_json="[]",
        norm_addressee=norm_addressee,
    )


def _compact(text: str) -> str:
    return " ".join(text.split())


def test_effort_prompt_for_business_uses_only_business_tables_and_guidance():
    prompt = _render_effort_prompt(BUSINESS)

    assert "Dieser Lauf betrifft den Normadressaten Wirtschaft." in prompt
    assert "A=Niedrig, B=Mittel, C=Hoch, D=Durchschnitt" in prompt
    assert "Anhang Wirtschaft:" in prompt
    assert "Zeitwerttabelle Wirtschaft" in prompt
    assert "Anhang 4" in prompt
    assert "Anhang 8" in prompt
    assert "Standardkostenmodell" in prompt
    assert "Lohnkostentabelle Wirtschaft" in prompt
    assert "Zeitwerttabelle Verwaltung" not in prompt
    assert "Lohnkostentabelle Verwaltung" not in prompt
    assert "Einfacher und mittlerer Dienst" not in prompt
    assert "Buergerinnen und Buerger" not in prompt


def test_effort_prompt_for_citizens_uses_simplified_schema_without_wages():
    prompt = _render_effort_prompt(CITIZENS)

    assert "Dieser Lauf betrifft den Normadressaten Buergerinnen und Buerger." in prompt
    assert "Monetarisieren Sie den Zeitaufwand nicht." in prompt
    assert "Anhang Buergerinnen und Buerger:" in prompt
    assert "Zeitwerttabelle Buergerinnen und Buerger" in prompt
    assert '"zeitaufwand_in_min_gueltig": ""' in prompt
    assert '"rollen_gueltig"' not in prompt
    assert '"lohngruppe"' not in prompt
    assert '"stundenlohn"' not in prompt
    assert "Lohnkostentabelle Verwaltung" not in prompt
    assert "Lohnkostentabelle Wirtschaft" not in prompt


def test_effort_prompt_for_administration_keeps_administration_specific_tables():
    prompt = _render_effort_prompt(ADMINISTRATION)

    assert "Dieser Lauf betrifft den Normadressaten Verwaltung." in prompt
    assert "A=Einfacher und mittlerer Dienst, B=Gehobener Dienst, C=Hoeherer Dienst" in prompt
    assert "Anhang Verwaltung:" in prompt
    assert "Zeitwerttabelle Verwaltung" in prompt
    assert "Lohnkostentabelle Verwaltung" in prompt
    assert "Zeitwerttabelle Wirtschaft" not in prompt
    assert "Lohnkostentabelle Wirtschaft" not in prompt


def test_process_compilation_prompt_includes_verbatim_handbook_example():
    prompt = render_prompt(
        PromptId.PROCESS_COMPILATION,
        law_summary="Kurzfassung",
        vorgaben_json="[]",
        norm_addressee=BUSINESS,
    )

    assert "Offizielles Methodenbeispiel aus dem Leitfaden" in prompt
    assert "Nachrüstung/Austausch von alten Bestrahlungsgeräten" in prompt
    assert "Beteiligung der Beauftragten an Prozessen im Unternehmen" in prompt
    assert "Buendeln Sie Vorgaben aus Unionsrecht und aus nationalem Recht niemals in denselben Prozess." in prompt


def test_case_group_development_prompt_includes_verbatim_handbook_example():
    prompt = render_prompt(
        PromptId.CASE_GROUP_DEVELOPMENT,
        law_summary="Kurzfassung",
        prozesse_json="[]",
        norm_addressee=BUSINESS,
    )

    assert "Offizielles Methodenbeispiel aus dem Leitfaden" in prompt
    assert "Fallgruppe 1 Umrüstung bestehender Anlagen (800 Unternehmen)" in prompt
    assert "Fallgruppe 2 Ersatz von Altanlagen durch Neuanlagen (200 Unternehmen)" in prompt


def test_cases_calculation_prompt_includes_verbatim_handbook_examples():
    prompt = render_prompt(
        PromptId.CASES_CALCULATION,
        law_summary="Kurzfassung",
        case_groups_json="[]",
        norm_addressee=CITIZENS,
    )

    assert "Offizielles Methodenbeispiel aus dem Leitfaden" in prompt
    assert "- einmal jährlich: Häufigkeit = 1" in prompt
    assert "Aufgrund einer Änderung der Straßenverkehrs-Ordnung (StVO)" in prompt


def test_process_compilation_prompt_skips_business_example_for_administration():
    prompt = render_prompt(
        PromptId.PROCESS_COMPILATION,
        law_summary="Kurzfassung",
        vorgaben_json="[]",
        norm_addressee=ADMINISTRATION,
    )

    assert "Nachrüstung/Austausch von alten Bestrahlungsgeräten" not in prompt


def test_cases_calculation_prompt_skips_citizens_case_example_for_administration():
    prompt = render_prompt(
        PromptId.CASES_CALCULATION,
        law_summary="Kurzfassung",
        case_groups_json="[]",
        norm_addressee=ADMINISTRATION,
    )

    assert "- einmal jährlich: Häufigkeit = 1" in prompt
    assert "Aufgrund einer Änderung der Straßenverkehrs-Ordnung (StVO)" not in prompt


def test_render_prompt_requires_explicit_norm_addressee():
    with pytest.raises(KeyError, match="explicit norm_addressee"):
        render_prompt(
            PromptId.PROCESS_COMPILATION,
            law_summary="Kurzfassung",
            vorgaben_json="[]",
        )


def test_process_step_analysis_prompt_sets_known_norm_addressee_early():
    prompt = _render_step_analysis_prompt(BUSINESS)
    first_lines = "\n".join(prompt.splitlines()[:15])

    assert "Dieser Lauf analysiert ausschliesslich den Normadressaten `business`." in first_lines
    assert '"normadressat": "business"' in prompt
    assert '"normadressat": "administration | business | citizens"' not in prompt


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_process_step_analysis_prompt_prefills_each_known_norm_addressee(norm_addressee):
    prompt = _render_step_analysis_prompt(norm_addressee)
    first_lines = "\n".join(prompt.splitlines()[:15])

    assert f"Dieser Lauf analysiert ausschliesslich den Normadressaten `{norm_addressee}`." in first_lines
    assert f'"normadressat": "{norm_addressee}"' in prompt
    assert '"normadressat": "administration | business | citizens"' not in prompt


def test_process_step_analysis_prompt_uses_step_specific_opening():
    prompt = _render_step_analysis_prompt(BUSINESS)

    assert "In diesem Schritt geht es ausschliesslich um die fachlich relevanten" in prompt
    assert "Zeit-, Personal- sowie Sachaufwands ermittelt" not in prompt


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_process_step_analysis_prompt_does_not_use_general_effort_opening(norm_addressee):
    prompt = _render_step_analysis_prompt(norm_addressee)

    assert "Erfuellungsaufwandsaenderung zu einer geplanten Gesetzesaenderung zu berechnen" not in prompt
    assert "Fuer diese Taetigkeiten werden die zu erwartenden Aenderungen des" not in prompt
    assert "Zeit-, Personal- sowie Sachaufwands ermittelt" not in prompt


def test_process_step_analysis_prompt_keeps_vorgaben_ids_as_technical_link():
    prompt = _render_step_analysis_prompt(BUSINESS)
    compact_prompt = _compact(prompt)

    assert "`vorgaben_ids`" in prompt
    assert "technische Rueckbindung" in prompt
    assert "nur `vorgaben_id`-Werte aus den Vorgaben dieses Prozesses" in compact_prompt
    assert "Wenn im Prozess nur genau eine Vorgabe enthalten ist" in prompt


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_process_step_analysis_prompt_vorgaben_ids_contract_is_list_scoped_to_process(
    norm_addressee,
):
    prompt = _render_step_analysis_prompt(norm_addressee)
    compact_prompt = _compact(prompt)

    assert '"vorgaben_ids": [""]' in prompt
    assert '"vorgaben_id": [""]' not in prompt
    assert "Wenn im Prozess nur genau eine Vorgabe enthalten ist" in prompt
    assert "geben Sie mehrere passende IDs an" in compact_prompt


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_process_step_analysis_prompt_excludes_effort_schema_fields(norm_addressee):
    prompt = _render_step_analysis_prompt(norm_addressee)

    forbidden_schema_fields = [
        '"rollen_gueltig"',
        '"rollen_vorschlag"',
        '"lohngruppe"',
        '"stundenlohn"',
        '"zeitaufwand_in_min"',
        '"zeitaufwand_in_min_gueltig"',
        '"zeitaufwand_in_min_vorschlag"',
        '"sachaufwand_gueltig"',
        '"sachaufwand_vorschlag"',
        '"ausfuehrung_pro_einzelfall"',
    ]
    assert all(field not in prompt for field in forbidden_schema_fields)


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_process_step_analysis_prompt_does_not_set_numeric_activity_limits(norm_addressee):
    prompt = _compact(_render_step_analysis_prompt(norm_addressee)).lower()

    forbidden_patterns = [
        r"\b3\s*(?:bis|-)\s*5\b",
        r"\b4\s*(?:bis|-)\s*6\b",
        r"\bdrei\s+bis\s+fuenf\b",
        r"\bvier\s+bis\s+sechs\b",
        r"\bmaximal\s+\w+\s+taetigkeiten\b",
        r"\bhoechstens\s+\w+\s+taetigkeiten\b",
        r"\bmindestens\s+\w+\s+taetigkeiten\b",
    ]
    assert not any(re.search(pattern, prompt) for pattern in forbidden_patterns)


@pytest.mark.parametrize(
    ("norm_addressee", "expected", "forbidden"),
    [
        (
            ADMINISTRATION,
            [
                "Checkliste (Verwaltung, Leitfaden Erfuellungsaufwand",
                "Bescheid erstellen",
                "Zahlungen anweisen",
            ],
            [
                "Checkliste Teil A",
                "Checkliste (Buergerinnen und Buerger",
            ],
        ),
        (
            BUSINESS,
            [
                "Checkliste Teil A",
                "Checkliste Teil B",
                "Taetigkeiten zur Erfuellung von Informationspflichten der Wirtschaft",
            ],
            [
                "Checkliste (Verwaltung, Leitfaden Erfuellungsaufwand",
                "Checkliste (Buergerinnen und Buerger",
            ],
        ),
        (
            CITIZENS,
            [
                "Checkliste (Buergerinnen und Buerger, Leitfaden Erfuellungsaufwand",
                "Formulare ausfuellen",
                "Wege zu zustaendigen Stellen",
            ],
            [
                "Checkliste (Verwaltung, Leitfaden Erfuellungsaufwand",
                "Checkliste Teil A",
                "Checkliste Teil B",
            ],
        ),
    ],
)
def test_process_step_analysis_prompt_uses_only_addressee_specific_checklist(
    norm_addressee,
    expected,
    forbidden,
):
    prompt = _render_step_analysis_prompt(norm_addressee)

    for phrase in expected:
        assert phrase in prompt
    for phrase in forbidden:
        assert phrase not in prompt


def test_administration_step_analysis_prompt_does_not_request_effort_values():
    prompt = _render_step_analysis_prompt(ADMINISTRATION)

    assert "Schaetzen Sie in der Schrittanalyse keine Lohngruppen" in prompt
    assert "Weisen Sie pro Taetigkeit mindestens eine Lohngruppe" not in prompt
    assert "realistischem Zeitaufwand in Minuten" not in prompt
    assert "Null-Zeitaufwaende" not in prompt


def test_business_step_analysis_prompt_does_not_request_it_or_effort_values():
    prompt = _render_step_analysis_prompt(BUSINESS)

    assert "Schaetzen Sie in der Schrittanalyse keine Zeitaufwaende" in prompt
    assert "loesen keinen Zeitaufwand aus" not in prompt
    assert "IT-bezogenen Sach- oder Personalaufwand separat" not in prompt
    assert "Null-Zeitaufwaende" not in prompt


def test_citizens_step_analysis_prompt_matches_schema_without_time_estimate():
    prompt = _render_step_analysis_prompt(CITIZENS)

    assert "Jede Taetigkeit muss eine Handlung der Buergerinnen und Buerger selbst sein" in prompt
    assert "Schaetzen Sie in der Schrittanalyse keine Zeit-" in prompt
    assert "Gesamtzeitaufwand" not in prompt
    assert "Zeitaufwand fuer Wegezeiten" not in prompt
