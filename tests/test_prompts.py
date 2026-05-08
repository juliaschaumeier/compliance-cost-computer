import re

from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS
from backend.core import prompts
from backend.core.prompts import NORM_ADDRESSEE_PROMPT_OPENINGS, PromptId, render_prompt
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


def _render_prompt_for_contract(prompt_id: str, norm_addressee: str) -> str:
    kwargs = {
        "law_summary": "Kurzfassung",
        "norm_addressee": norm_addressee,
    }
    if prompt_id == PromptId.PROCESS_COMPILATION:
        kwargs["vorgaben_json"] = "[]"
    elif prompt_id == PromptId.CASE_GROUP_DEVELOPMENT:
        kwargs["prozesse_json"] = "[]"
    elif prompt_id in {PromptId.PROCESS_STEP_ANALYSIS, PromptId.CASES_CALCULATION}:
        kwargs["case_groups_json"] = "[]"
    elif prompt_id == PromptId.EFFORT_CALCULATION:
        kwargs["step_analysis_json"] = "[]"
    else:
        raise ValueError(f"Unsupported prompt_id: {prompt_id}")
    return render_prompt(prompt_id, **kwargs)


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


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_effort_prompt_schema_uses_single_json_braces(norm_addressee):
    prompt = _render_effort_prompt(norm_addressee)

    assert "{{" not in prompt
    assert "}}" not in prompt


def test_render_prompt_ignores_contract_field_overrides():
    prompt = render_prompt(
        PromptId.EFFORT_CALCULATION,
        law_summary="Kurzfassung",
        step_analysis_json="[]",
        norm_addressee=BUSINESS,
        norm_addressee_context="BROKEN CONTEXT",
        effort_json_schema='{"normadressat": "citizens"}',
    )

    assert "BROKEN CONTEXT" not in prompt
    assert '"normadressat": "business"' in prompt
    assert '"normadressat": "citizens"' not in prompt


def test_process_compilation_prompt_includes_verbatim_handbook_example():
    prompt = render_prompt(
        PromptId.PROCESS_COMPILATION,
        law_summary="Kurzfassung",
        vorgaben_json="[]",
        norm_addressee=BUSINESS,
    )

    assert (
        "Methodenbeispiel aus dem Leitfaden zur Orientierung; nicht als "
        "Sachverhalt dieses Regelungsvorhabens verwenden"
    ) in prompt
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

    assert (
        "Methodenbeispiel aus dem Leitfaden zur Orientierung; nicht als "
        "Sachverhalt dieses Regelungsvorhabens verwenden"
    ) in prompt
    assert "Fallgruppe 1 Umrüstung bestehender Anlagen (800 Unternehmen)" in prompt
    assert "Fallgruppe 2 Ersatz von Altanlagen durch Neuanlagen (200 Unternehmen)" in prompt


def test_cases_calculation_prompt_includes_verbatim_handbook_examples():
    prompt = render_prompt(
        PromptId.CASES_CALCULATION,
        law_summary="Kurzfassung",
        case_groups_json="[]",
        norm_addressee=CITIZENS,
    )

    assert (
        "Methodenbeispiel aus dem Leitfaden zur Orientierung; nicht als "
        "Sachverhalt dieses Regelungsvorhabens verwenden"
    ) in prompt
    assert (
        "Fallzahlbeispiel aus dem Leitfaden zur Orientierung; nicht als "
        "Sachverhalt dieses Regelungsvorhabens verwenden"
    ) in prompt
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
    assert (
        "Methodenbeispiel aus dem Leitfaden zur Orientierung; nicht als "
        "Sachverhalt dieses Regelungsvorhabens verwenden"
    ) not in prompt


def test_case_group_development_prompt_skips_business_example_for_administration():
    prompt = render_prompt(
        PromptId.CASE_GROUP_DEVELOPMENT,
        law_summary="Kurzfassung",
        prozesse_json="[]",
        norm_addressee=ADMINISTRATION,
    )

    assert "Fallgruppe 1 Umrüstung bestehender Anlagen (800 Unternehmen)" not in prompt
    assert (
        "Methodenbeispiel aus dem Leitfaden zur Orientierung; nicht als "
        "Sachverhalt dieses Regelungsvorhabens verwenden"
    ) not in prompt


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS])
def test_cases_calculation_prompt_skips_citizens_case_example_when_unavailable(
    norm_addressee,
):
    prompt = render_prompt(
        PromptId.CASES_CALCULATION,
        law_summary="Kurzfassung",
        case_groups_json="[]",
        norm_addressee=norm_addressee,
    )

    assert "Aufgrund einer Änderung der Straßenverkehrs-Ordnung (StVO)" not in prompt
    assert (
        "Fallzahlbeispiel aus dem Leitfaden zur Orientierung; nicht als "
        "Sachverhalt dieses Regelungsvorhabens verwenden"
    ) not in prompt
    assert (
        "Methodenbeispiel aus dem Leitfaden zur Orientierung; nicht als "
        "Sachverhalt dieses Regelungsvorhabens verwenden"
    ) in prompt
    assert "- einmal jährlich: Häufigkeit = 1" in prompt


def test_render_prompt_requires_explicit_norm_addressee():
    with pytest.raises(KeyError, match="explicit norm_addressee"):
        render_prompt(
            PromptId.PROCESS_COMPILATION,
            law_summary="Kurzfassung",
            vorgaben_json="[]",
        )



@pytest.mark.parametrize(
    "prompt_id",
    [
        PromptId.PROCESS_COMPILATION,
        PromptId.CASE_GROUP_DEVELOPMENT,
        PromptId.PROCESS_STEP_ANALYSIS,
        PromptId.CASES_CALCULATION,
        PromptId.EFFORT_CALCULATION,
    ],
)
@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_norm_addressee_prompts_end_with_final_json_instruction(prompt_id, norm_addressee):
    prompt = _render_prompt_for_contract(prompt_id, norm_addressee)
    final_instruction = "Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen."

    assert prompt.rstrip().endswith(final_instruction)
    assert prompt.split(final_instruction, 1)[1].strip() == ""
    assert "Zusatz fuer" not in prompt


@pytest.mark.parametrize(
    "prompt_id",
    [
        PromptId.PROCESS_COMPILATION,
        PromptId.CASE_GROUP_DEVELOPMENT,
        PromptId.CASES_CALCULATION,
        PromptId.EFFORT_CALCULATION,
    ],
)
@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_norm_addressee_prompts_integrate_guidance_before_schema(prompt_id, norm_addressee):
    prompt = _render_prompt_for_contract(prompt_id, norm_addressee)
    context_marker = "Dieser Lauf betrifft den Normadressaten"
    schema_marker = "Geben Sie nur und ausschliesslich JSON im folgenden Format zurueck:"

    assert context_marker in prompt
    assert prompt.index(context_marker) < prompt.index(schema_marker)
    assert f'"normadressat": "{norm_addressee}"' in prompt
    assert '"normadressat": "administration | business | citizens"' not in prompt
    assert '"normadressat": "administration | business"' not in prompt


def test_process_step_analysis_prompt_sets_known_norm_addressee_after_context():
    prompt = _render_step_analysis_prompt(BUSINESS)

    assert prompt.index("Sie sind Legist im deutschen Bundestag") < prompt.index(
        "Die wesentlichen Unterschiede der Gesetzesaenderung"
    )
    assert "Dieser Lauf betrifft nur den Normadressaten `business`" in prompt
    assert prompt.index("Die wesentlichen Unterschiede der Gesetzesaenderung") < prompt.index(
        "Dieser Lauf betrifft nur den Normadressaten `business`"
    )
    assert '"normadressat": "business"' in prompt
    assert '"normadressat": "administration | business | citizens"' not in prompt


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_process_step_analysis_prompt_prefills_each_known_norm_addressee(norm_addressee):
    prompt = _render_step_analysis_prompt(norm_addressee)

    assert f"Dieser Lauf betrifft nur den Normadressaten `{norm_addressee}`" in prompt
    assert f'"normadressat": "{norm_addressee}"' in prompt
    assert '"normadressat": "administration | business | citizens"' not in prompt


def test_process_step_analysis_prompt_uses_integrated_step_specific_intro():
    prompt = _render_step_analysis_prompt(BUSINESS)

    assert "In diesem Schritt identifizieren Sie ausschliesslich die fachlich" in prompt
    assert prompt.index("Sie sind Legist im deutschen Bundestag") < prompt.index(
        "In diesem Schritt identifizieren Sie ausschliesslich"
    )


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_process_step_analysis_prompt_has_final_json_instruction_last(norm_addressee):
    prompt = _render_step_analysis_prompt(norm_addressee)
    final_instruction = "Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen."

    assert final_instruction in prompt
    assert prompt.rstrip().endswith(final_instruction)
    trailing_text = prompt.split(final_instruction, 1)[1]
    assert trailing_text.strip() == ""
    assert "Zusatz fuer" not in prompt


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_process_step_analysis_prompt_keeps_general_context_before_step_scope(norm_addressee):
    prompt = _render_step_analysis_prompt(norm_addressee)

    assert "Erfuellungsaufwandsaenderung zu einer geplanten Gesetzesaenderung" in prompt
    assert "Die wesentlichen Unterschiede der Gesetzesaenderung" in prompt
    assert "Schaetzen Sie in diesem Schritt keine Minuten" in prompt
    assert prompt.index(
        "Die wesentlichen Unterschiede der Gesetzesaenderung"
    ) < prompt.index("Schaetzen Sie in diesem Schritt keine Minuten")


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
def test_process_step_analysis_prompt_does_not_set_invented_activity_limits(norm_addressee):
    # "drei bis fuenf" war selbst erfunden und widerspricht dem Leitfaden.
    # "vier bis sechs" stammt aus dem Leitfaden (Kap. 6.2.1 und 7.2.1) und ist
    # fuer Wirtschaft und Verwaltung zulaessig; fuer Buerger gibt der Leitfaden
    # keine Zahl vor, daher dort ebenfalls verboten.
    prompt = _compact(_render_step_analysis_prompt(norm_addressee)).lower()

    forbidden_patterns = [
        r"\b3\s*(?:bis|-)\s*5\b",
        r"\bdrei\s+bis\s+fuenf\b",
        r"\bmaximal\s+\w+\s+taetigkeiten\b",
        r"\bhoechstens\s+\w+\s+taetigkeiten\b",
        r"\bmindestens\s+\w+\s+taetigkeiten\b",
    ]
    assert not any(re.search(pattern, prompt) for pattern in forbidden_patterns)


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS])
def test_process_step_analysis_prompt_cites_handbook_activity_count(norm_addressee):
    # Leitfaden Erfuellungsaufwand (Feb 2026): "lediglich vier bis sechs Taetigkeiten
    # anfallen" steht im Wirtschafts- (Kap. 6.2.1, S. 38) und Verwaltungskapitel
    # (Kap. 7.2.1, S. 49), aber nicht im Buergerkapitel (Kap. 5.2.1).
    prompt = _compact(_render_step_analysis_prompt(norm_addressee)).lower()
    assert re.search(r"\bvier\s+bis\s+sechs\b", prompt)


def test_process_step_analysis_citizens_prompt_has_no_activity_count():
    prompt = _compact(_render_step_analysis_prompt(CITIZENS)).lower()
    assert not re.search(r"\bvier\s+bis\s+sechs\b", prompt)
    assert not re.search(r"\bdrei\s+bis\s+fuenf\b", prompt)


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_process_step_analysis_prompt_uses_clear_bundling_rule(norm_addressee):
    prompt = _compact(_render_step_analysis_prompt(norm_addressee))

    assert "Bei Daueraufgaben oder sehr einfachen Pflichterfuellungen reicht eine einzelne, zusammenfassende Haupttaetigkeit aus" in prompt
    assert "Untergliederung fuer den Vorher-Nachher-Vergleich" in prompt
    assert "Zerlegung fuer die spaetere Aufwandsermittlung" not in prompt


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
                "Zeitaufwand fuer Wegezeiten",
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

    assert "Schaetzen Sie in diesem Schritt keine Minuten, Lohngruppen" in prompt
    assert "Schaetzen Sie in der Schrittanalyse keine Lohngruppen" not in prompt
    assert "Weisen Sie pro Taetigkeit mindestens eine Lohngruppe" not in prompt
    assert "realistischem Zeitaufwand in Minuten" not in prompt
    assert "Null-Zeitaufwaende" not in prompt


def test_business_step_analysis_prompt_does_not_request_it_or_effort_values():
    prompt = _render_step_analysis_prompt(BUSINESS)

    assert "Schaetzen Sie in diesem Schritt keine Minuten, Lohngruppen" in prompt
    assert "Schaetzen Sie in der Schrittanalyse keine Zeitaufwaende" not in prompt
    assert "loesen keinen Zeitaufwand aus" not in prompt
    assert "IT-bezogenen Sach- oder Personalaufwand separat" not in prompt
    assert "Null-Zeitaufwaende" not in prompt


def test_citizens_step_analysis_prompt_matches_schema_without_time_estimate():
    prompt = _render_step_analysis_prompt(CITIZENS)

    assert "Jede Taetigkeit muss eine Handlung der Buergerinnen und Buerger selbst sein" in prompt
    assert "Schaetzen Sie in diesem Schritt keine Minuten, Lohngruppen" in prompt
    assert "Schaetzen Sie in der Schrittanalyse keine Zeit-" not in prompt
    assert "Gesamtzeitaufwand" not in prompt


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_process_step_analysis_prompt_does_not_use_generic_addressee_context(norm_addressee):
    prompt = _render_step_analysis_prompt(norm_addressee)
    generic_context = NORM_ADDRESSEE_PROMPT_OPENINGS[norm_addressee].strip()
    assert generic_context not in prompt
