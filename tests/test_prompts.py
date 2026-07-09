import re

from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS
from backend.core import prompts
from backend.core.payload_builders import (
    build_case_groups_payload,
    build_step_analysis_output_skeleton,
    dump_prompt_json,
)
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

    assert "Dieser Lauf betrifft nur den Normadressaten Wirtschaft." in prompt
    assert "`niedrig`, `mittel`, `hoch` oder `durchschnitt`" in prompt
    assert '"personalaufwand_gueltig"' in prompt
    assert '"stundenlohn"' not in prompt
    assert "Anhang Wirtschaft:" in prompt
    assert "Zeitwerttabelle Wirtschaft" in prompt
    assert "Anhang 4" in prompt
    assert "Anhang 8" in prompt
    assert "Standardkostenmodell" in prompt
    assert "Lohnkostentabelle Wirtschaft" in prompt
    assert "Zeitwerttabelle Verwaltung" not in prompt
    assert "Lohnkostentabelle Verwaltung" not in prompt
    assert "Einfacher und mittlerer Dienst" not in prompt


def test_effort_prompt_for_citizens_uses_simplified_schema_without_wages():
    prompt = _render_effort_prompt(CITIZENS)

    assert "Dieser Lauf betrifft nur den Normadressaten Buergerinnen und Buerger." in prompt
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

    assert "Dieser Lauf betrifft nur den Normadressaten Verwaltung." in prompt
    assert (
        "`einfacher_und_mittlerer_dienst`, `gehobener_dienst`, "
        "`hoeherer_dienst` oder `durchschnitt`"
    ) in prompt
    assert '"personalaufwand_gueltig"' in prompt
    assert '"stundenlohn"' not in prompt
    assert "Anhang Verwaltung:" in prompt
    assert "Zeitwerttabelle Verwaltung" in prompt
    assert "Lohnkostentabelle Verwaltung" in prompt
    assert "Zeitwerttabelle Wirtschaft" not in prompt
    assert "Lohnkostentabelle Wirtschaft" not in prompt


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS])
def test_effort_prompt_uses_row_based_personnel_effort_contract(norm_addressee):
    prompt = _render_effort_prompt(norm_addressee)

    # New row-based contract: qualifikation + lohnquelle + zeitaufwand per row.
    assert '"personalaufwand_gueltig"' in prompt
    assert '"personalaufwand_vorschlag"' in prompt
    assert '"qualifikation"' in prompt
    assert '"lohnquelle"' in prompt
    # Legacy role/wage fields are gone; the LLM no longer outputs wages.
    assert '"rollen_gueltig"' not in prompt
    assert '"rollen_vorschlag"' not in prompt
    assert '"lohngruppe"' not in prompt
    assert '"stundenlohn"' not in prompt
    # Aggregation + backend-resolves-wage rules are stated.
    assert "zu genau einem Eintrag zusammen" in prompt
    assert "Backend-Anwendung ermittelt den Stundenlohn" in prompt


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_effort_prompt_schema_uses_single_json_braces(norm_addressee):
    prompt = _render_effort_prompt(norm_addressee)

    assert "{{" not in prompt
    assert "}}" not in prompt


def test_render_prompt_effort_default_skeleton_echoes_run_addressee():
    # #64 (Schritt 6): ohne Router-Skelett faellt render_prompt auf ein leeres
    # Default-Skelett zurueck, das den Lauf-Normadressaten fest echot; ein
    # Kontext-Override (norm_addressee_prompt_opening) wird weiterhin ignoriert.
    prompt = render_prompt(
        PromptId.EFFORT_CALCULATION,
        law_summary="Kurzfassung",
        step_analysis_json="[]",
        norm_addressee=BUSINESS,
        norm_addressee_prompt_opening="BROKEN CONTEXT",
    )

    assert "BROKEN CONTEXT" not in prompt
    assert '"normadressat": "business"' in prompt
    assert '"normadressat": "citizens"' not in prompt


def test_process_compilation_prompt_omits_handbook_example():
    # #13/#25: Das Leitfaden-Prozessbeispiel (Solarien/Betriebsbeauftragte) mischte
    # einmalige und wiederkehrende Posten und verleitete im recurring-only-Modus zu
    # Einmal-Prozessen. Es wird daher nicht mehr eingespeist - auch nicht fuer
    # business. Die Buendelungsmethode steht weiterhin in der BUSINESS-Regel.
    prompt = render_prompt(
        PromptId.PROCESS_COMPILATION,
        law_summary="Kurzfassung",
        vorgaben_json="[]",
        norm_addressee=BUSINESS,
    )

    assert (
        "Methodenbeispiel aus dem Leitfaden zur Orientierung; nicht als "
        "Sachverhalt dieses Regelungsvorhabens verwenden"
    ) not in prompt
    assert "Durchführung von Beratungsgesprächen" not in prompt
    assert "Beteiligung der Beauftragten an Prozessen im Unternehmen" not in prompt
    # Die Buendelungsmethode bleibt ueber die BUSINESS-Regel erhalten.
    assert "Buendeln Sie Vorgaben zu Prozessen entlang des operativen Ablaufs" in prompt


def test_process_compilation_prompt_does_not_require_placeholder_for_no_own_action():
    prompt = render_prompt(
        PromptId.PROCESS_COMPILATION,
        law_summary="Kurzfassung",
        vorgaben_json='[{"vorgaben_id": 12, "normzitat": "§ 1", "beschreibung": "Test"}]',
        norm_addressee=CITIZENS,
    )

    assert "statt `prozesse` leer zu lassen" not in prompt
    assert "Platzhalter-Prozess" not in prompt
    assert "Keine eigenstaendige Buergerpflicht oder Handlung" not in prompt
    assert "Verknuepfen Sie darin die betroffene `vorgaben_id`" not in prompt


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_process_compilation_prompt_demands_recurring_only_for_all_addressees(norm_addressee):
    # #13/#25: Die "nur wiederkehrend"-Regel muss in der Prozessbildung fuer ALLE
    # Normadressaten erscheinen (frueher nur im business-only-Beispielheading).
    prompt = render_prompt(
        PromptId.PROCESS_COMPILATION,
        law_summary="Kurzfassung",
        vorgaben_json="[]",
        norm_addressee=norm_addressee,
    )

    assert "Nur jaehrlich wiederkehrender Erfuellungsaufwand" in prompt
    assert "Nicht zulaessig als Prozess" in prompt


def test_case_group_development_prompt_omits_handbook_example():
    # Das Leitfaden-Fallgruppenbeispiel (Umruestung/Ersatz von Anlagen) ist rein
    # einmalig und wird im recurring-only-Modus bewusst nicht mehr eingespeist
    # (#13/#25) - auch nicht fuer business.
    prompt = render_prompt(
        PromptId.CASE_GROUP_DEVELOPMENT,
        law_summary="Kurzfassung",
        prozesse_json="[]",
        norm_addressee=BUSINESS,
    )

    assert "Fallgruppe 1 Umrüstung bestehender Anlagen (800 Unternehmen)" not in prompt
    assert "Fallgruppe 2 Ersatz von Altanlagen durch Neuanlagen (200 Unternehmen)" not in prompt
    assert (
        "Methodenbeispiel aus dem Leitfaden zur Orientierung; nicht als "
        "Sachverhalt dieses Regelungsvorhabens verwenden"
    ) not in prompt


def test_business_investment_axes_are_recurring_qualified():
    # #13/#25 (Revier-Agent Medium): Die wirtschaftsseitigen Investitionsachsen
    # in Prozessbildung und Fallgruppenentwicklung duerfen nicht mehr zu einmaligem
    # Investitions-/Umstellungsaufwand steuern, sondern nur zu jaehrlich
    # wiederkehrendem Aufwand.
    case_group = _compact(
        _render_prompt_for_contract(PromptId.CASE_GROUP_DEVELOPMENT, BUSINESS)
    )
    assert "Neuanschaffung versus" not in case_group
    assert (
        "wiederkehrende Ersatzbeschaffung versus Umruestung bestehender Anlagen, "
        "jeweils nur soweit der Aufwand jaehrlich wiederkehrt"
    ) in case_group

    process = _compact(
        _render_prompt_for_contract(PromptId.PROCESS_COMPILATION, BUSINESS)
    )
    assert "(iv) Beschaffung oder Umruestung von Anlagen, Waren oder Material" not in process
    assert (
        "laufend wiederkehrende Beschaffung oder Umruestung von Anlagen, Waren oder "
        "Material, soweit der Aufwand jaehrlich erneut anfaellt"
    ) in process


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


def test_cases_calculation_prompt_requests_case_metric_evidence():
    prompt = render_prompt(
        PromptId.CASES_CALCULATION,
        law_summary="Kurzfassung",
        case_groups_json="[]",
        norm_addressee=BUSINESS,
    )

    assert '"erklaerungen"' in prompt
    assert '"confidence"' in prompt
    assert "high | medium | low" in prompt
    assert "auf welcher Grundlage der jeweilige Wert hergeleitet wurde" in prompt
    assert "wie belastbar die jeweilige Schaetzung ist" in prompt
    for key in (
        "anzahl_betroffene_gueltig",
        "haeufigkeit_pro_jahr_gueltig",
        "anzahl_betroffene_vorschlag",
        "haeufigkeit_pro_jahr_vorschlag",
    ):
        assert key in prompt


def test_compliance_text_prompt_protects_user_edited_values_from_deep_research_evidence():
    prompt = render_prompt(
        PromptId.COMPLIANCE_TEXT_EXTRACTION,
        law_summary="Kurzfassung",
        consolidated_session_json="{}",
        optional_deep_research_part_1_2="Kein Deep-Research-Bericht vorhanden.",
        beispiel_1="",
        beispiel_2="",
        beispiel_3="",
    )

    assert 'value_source: "user_edited"' in prompt
    assert 'value_source: "derived_from_user_edited"' in prompt
    assert "nicht als Begründung oder Konfidenzquelle" in prompt
    assert "Deep Research Report" in prompt


def test_compliance_text_prompt_avoids_repeated_general_scope_warnings():
    prompt = render_prompt(
        PromptId.COMPLIANCE_TEXT_EXTRACTION,
        law_summary="Kurzfassung",
        consolidated_session_json="{}",
        optional_deep_research_part_1_2="Kein Deep-Research-Bericht vorhanden.",
        beispiel_1="",
        beispiel_2="",
        beispiel_3="",
    )

    assert (
        "[Prüfbedarf: Einmaliger Erfüllungsaufwand ist nicht Gegenstand der "
        "vorliegenden Analyse.]"
    ) not in prompt
    assert (
        "[Prüfbedarf: Angaben zu Ländern oder Kommunen sind nicht Gegenstand "
        "der vorliegenden Analyse.]"
    ) not in prompt


def test_compliance_text_prompt_keeps_detailed_labels_out_of_headings():
    prompt = render_prompt(
        PromptId.COMPLIANCE_TEXT_EXTRACTION,
        law_summary="Kurzfassung",
        consolidated_session_json="{}",
        optional_deep_research_part_1_2="Kein Deep-Research-Bericht vorhanden.",
        beispiel_1="",
        beispiel_2="",
        beispiel_3="",
    )

    assert "Überschriften müssen kurz bleiben" in prompt
    assert "Fallgruppen- oder Tätigkeitsbezeichnungen gehören in den Fließtext" in prompt
    assert "### Vorgabe [Nummer]: [kurzes Stichwort]; [Norm]" in prompt
    assert "Fallgruppen dürfen nicht als eigene Markdown-Überschriften" in prompt
    assert "- Erstanerkennungsverfahren (Fallgruppe 1): ..." in prompt
    assert "steht bereits in der PDF-Infobox" in prompt


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
    context_marker = "Dieser Lauf betrifft nur den Normadressaten"
    schema_marker = "Geben Sie nur und ausschliesslich JSON"

    assert context_marker in prompt
    assert prompt.index(context_marker) < prompt.index(schema_marker)
    assert f'"normadressat": "{norm_addressee}"' in prompt
    assert '"normadressat": "administration | business | citizens"' not in prompt
    assert '"normadressat": "administration | business"' not in prompt


def test_process_step_analysis_prompt_sets_known_norm_addressee_after_context():
    prompt = _render_step_analysis_prompt(BUSINESS)

    assert prompt.index("Sie sind Legist und unterstuetzen die fachliche Pruefung") < prompt.index(
        "Das Gesetz bzw. die Gesetzesaenderung ist wie folgt"
    )
    assert "Dieser Lauf betrifft nur den Normadressaten Wirtschaft" in prompt
    assert prompt.index("Das Gesetz bzw. die Gesetzesaenderung ist wie folgt") < prompt.index(
        "Dieser Lauf betrifft nur den Normadressaten Wirtschaft"
    )
    assert '"normadressat": "business"' in prompt
    assert '"normadressat": "administration | business | citizens"' not in prompt


_ADDRESSEE_GERMAN = {
    ADMINISTRATION: "Verwaltung",
    BUSINESS: "Wirtschaft",
    CITIZENS: "Buergerinnen und Buerger",
}


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_process_step_analysis_prompt_prefills_each_known_norm_addressee(norm_addressee):
    prompt = _render_step_analysis_prompt(norm_addressee)

    assert f"Dieser Lauf betrifft nur den Normadressaten {_ADDRESSEE_GERMAN[norm_addressee]}" in prompt
    assert f'"normadressat": "{norm_addressee}"' in prompt
    assert '"normadressat": "administration | business | citizens"' not in prompt


def test_process_step_analysis_prompt_uses_integrated_step_specific_intro():
    prompt = _render_step_analysis_prompt(BUSINESS)

    assert "Ihre Aufgabe ist es, die wesentlichen anfallenden Taetigkeiten" in prompt
    assert prompt.index("Sie sind Legist und unterstuetzen die fachliche Pruefung") < prompt.index(
        "Ihre Aufgabe ist es, die wesentlichen anfallenden Taetigkeiten"
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
    assert "Das Gesetz bzw. die Gesetzesaenderung ist wie folgt" in prompt
    assert "Schaetzen Sie in diesem Schritt keine Minuten" in prompt
    assert prompt.index(
        "Das Gesetz bzw. die Gesetzesaenderung ist wie folgt"
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
def test_process_step_analysis_prompt_frames_checklist_recurring_only(norm_addressee):
    prompt = render_prompt(
        PromptId.PROCESS_STEP_ANALYSIS,
        law_summary="Kurzfassung",
        case_groups_json="[]",
        norm_addressee=norm_addressee,
    )

    assert (
        "Waehlen Sie aus der folgenden Checkliste nur wiederkehrende Taetigkeiten aus"
        in prompt
    )


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_process_step_analysis_prompt_demands_unique_fallgruppen(norm_addressee):
    # #64 (Option 4): flaches Schema - jede fallgruppen_id genau einmal, kein
    # Zusammenfuehren/Aufteilen (der fruehere Prozess-Bezug entfaellt flach).
    prompt = render_prompt(
        PromptId.PROCESS_STEP_ANALYSIS,
        law_summary="Kurzfassung",
        case_groups_json="[]",
        norm_addressee=norm_addressee,
    )

    assert "Geben Sie jede vorgegebene `fallgruppen_id` genau einmal aus" in prompt
    assert "keine `fallgruppen_id` mehrfach vorkommt" in prompt
    assert "Fuehren Sie Fallgruppen nicht zusammen, teilen Sie sie nicht auf" in prompt
    assert "unter ihrem vorgegebenen Prozess" not in prompt
    assert "unter einem fremden Prozess" not in prompt


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_process_step_analysis_prompt_injects_flat_output_skeleton(norm_addressee):
    # #64 (Option 4): Statt eines nested Schemas zeigt der Prompt ein aus
    # case_groups_json vorbefuelltes FLACHES Skelett (nur fallgruppen_id,
    # taetigkeiten leer, keine Prozess-Ebene); das Modell fuellt nur taetigkeiten.
    processes = [
        {"process_id": 312, "process": "Prozess 312", "description": "d", "change_status": "geaendert"},
        {"process_id": 313, "process": "Prozess 313", "description": "d", "change_status": "geaendert"},
    ]
    case_groups = [
        {"case_group_id": 491, "process_id": 312, "case_group": "F491", "description": "d", "change_status": "geaendert"},
        {"case_group_id": 492, "process_id": 313, "case_group": "F492", "description": "d", "change_status": "geaendert"},
    ]
    payload_groups = build_case_groups_payload(
        processes=processes,
        case_groups=case_groups,
        norm_addressee=norm_addressee,
    )
    prompt = render_prompt(
        PromptId.PROCESS_STEP_ANALYSIS,
        law_summary="Kurzfassung",
        case_groups_json=dump_prompt_json(payload_groups),
        output_skeleton_json=dump_prompt_json(
            build_step_analysis_output_skeleton(payload_groups, norm_addressee=norm_addressee)
        ),
        norm_addressee=norm_addressee,
    )

    output_section = prompt.split("vorbefuellten Skelett", 1)[1]
    assert "Fuellen Sie ausschliesslich das Feld `taetigkeiten`" in prompt
    assert (
        "Fuegen Sie keine Fallgruppen-Objekte hinzu, entfernen, "
        "verschieben oder duplizieren Sie keine" in prompt
    )
    assert '"fallgruppen_id": 491' in prompt
    assert '"fallgruppen_id": 492' in prompt
    assert '"taetigkeiten": []' in prompt
    assert '"fallgruppen_id": ""' not in prompt
    assert '"prozess_id"' not in output_section


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_cases_calculation_prompt_demands_unique_fallgruppen(norm_addressee):
    # #13/#25: jede fallgruppen_id genau einmal in den Kennzahlen, damit Schritt 6
    # doppelte Fallgruppen nicht still ueberschreibt (last-write-wins).
    prompt = _render_prompt_for_contract(PromptId.CASES_CALCULATION, norm_addressee)

    assert "zu jeder vorgegebenen `fallgruppen_id` genau eine Kennzahlenmenge" in prompt
    assert "keine `fallgruppen_id` mehrfach vorkommt" in prompt


@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_effort_calculation_prompt_demands_unique_taetigkeiten(norm_addressee):
    # #13/#25: jede taetigkeiten_id genau einmal, keine auslassen (Nullwerte statt
    # Weglassen), keine Duplikate.
    prompt = _render_prompt_for_contract(PromptId.EFFORT_CALCULATION, norm_addressee)

    assert "zu jeder vorgegebenen `taetigkeiten_id` genau ein Ergebnisobjekt" in prompt
    assert "keine `taetigkeiten_id` mehrfach vorkommt" in prompt


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
                "Checkliste (Verwaltung):",
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
                "Checkliste (Verwaltung):",
                "Checkliste (Buergerinnen und Buerger",
            ],
        ),
        (
            CITIZENS,
            [
                "Checkliste (Buergerinnen und Buerger):",
                "Formulare ausfuellen",
                "Zeitaufwand fuer Wegezeiten",
            ],
            [
                "Checkliste (Verwaltung):",
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


def test_effort_prompt_includes_lohnquelle_field_for_administration():
    prompt = _render_effort_prompt(ADMINISTRATION)

    assert '"lohnquelle"' in prompt


def test_effort_prompt_includes_lohnquelle_field_for_business():
    prompt = _render_effort_prompt(BUSINESS)

    assert '"lohnquelle"' in prompt


def test_effort_prompt_excludes_lohnquelle_field_for_citizens():
    prompt = _render_effort_prompt(CITIZENS)

    assert '"lohnquelle"' not in prompt


def test_effort_prompt_administration_guidance_names_verwaltungsebenen():
    prompt = _render_effort_prompt(ADMINISTRATION)

    assert "verwaltungsebene" in prompt.lower() or "bund" in prompt.lower()
    assert "laender" in prompt.lower() or "länder" in prompt.lower()
    assert "kommunen" in prompt.lower()
    assert "sozialversicherung" in prompt.lower()
    assert "durchschnitt" in prompt.lower()


def test_effort_prompt_business_guidance_names_wirtschaftsabschnitt():
    prompt = _render_effort_prompt(BUSINESS)

    assert "wirtschaftsabschnitt" in prompt.lower() or "lohnquelle" in prompt.lower()
    assert "gesamtwirtschaft" in prompt.lower()
