from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS
from backend.core.prompts import PromptId, render_prompt


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
