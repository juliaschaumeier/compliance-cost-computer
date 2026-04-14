from backend.core import db
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


def test_process_compilation_prompt_includes_structured_mirror_context_from_session():
    session_id, _ = db.upsert_session("PROMPT-MIRROR-PROCESS", "test-model")
    business_regulation_id = db.insert_regulation(
        session_id,
        "§ 52 Abs. 2 Nr. 21 AO",
        "E-Sport-Vereine koennen den Zweck geltend machen.",
        applies_to_administration=False,
        applies_to_business=True,
        mirror_applies_to_administration=True,
        mirror_description="Korrespondierender Pruefaufwand bei der Verwaltung.",
        mirror_anchor_key="gemeinnuetzigkeit-esport",
    )
    admin_regulation_id = db.insert_regulation(
        session_id,
        "§ 52 Abs. 2 Nr. 21 AO",
        "Die Finanzverwaltung prueft die Anerkennung.",
        applies_to_administration=True,
        applies_to_business=False,
        mirror_applies_to_business=True,
        mirror_description="Korrespondierender Aufwand bei den Koerperschaften.",
        mirror_anchor_key="gemeinnuetzigkeit-esport",
    )
    admin_process_id = db.insert_process(
        session_id,
        "Pruefung der Gemeinnuetzigkeit",
        "Verwaltungsprozess",
        norm_addressee=ADMINISTRATION,
    )
    db.update_regulation_process(
        regulation_id=admin_regulation_id,
        process_id=admin_process_id,
        norm_addressee=ADMINISTRATION,
    )
    db.replace_mirror_matches(
        session_id,
        [
            {
                "mirror_anchor_key": "gemeinnuetzigkeit-esport",
                "shared_situation": "Ein Antrag fuehrt zu korrespondierender Bearbeitung.",
                "source_norm_addressee": ADMINISTRATION,
                "target_norm_addressee": BUSINESS,
                "source_process_id": admin_process_id,
                "target_process_id": None,
                "source_case_group_id": None,
                "target_case_group_id": None,
                "relation_type": "one_to_one",
                "sync_addressees": True,
                "sync_frequency": True,
                "sync_cases": True,
                "reason": "Gleicher Lebenssachverhalt.",
            }
        ],
    )

    prompt = render_prompt(
        PromptId.PROCESS_COMPILATION,
        session_id=session_id,
        law_summary="Kurzfassung",
        vorgaben_json=(
            '[{"vorgaben_id": %d, "normzitat": "§ 52 Abs. 2 Nr. 21 AO", '
            '"beschreibung": "E-Sport-Vereine koennen den Zweck geltend machen."}]'
            % business_regulation_id
        ),
        norm_addressee=BUSINESS,
    )

    assert "Zusaetzlicher strukturierter Spiegelkontext" in prompt
    assert '"mirror_anchor_key": "gemeinnuetzigkeit-esport"' in prompt
    assert '"mirror_matches"' in prompt
    assert '"source_norm_addressee": "business"' in prompt
    assert '"prozess_bezeichnung": "Pruefung der Gemeinnuetzigkeit"' in prompt


def test_render_prompt_requires_explicit_norm_addressee():
    with pytest.raises(KeyError, match="explicit norm_addressee"):
        render_prompt(
            PromptId.PROCESS_COMPILATION,
            law_summary="Kurzfassung",
            vorgaben_json="[]",
        )
