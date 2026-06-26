"""
Regression-Guard fuer Review-Befund Block 3.1 (Buerokratiekosten).

Hintergrund: Vor Commit 2cb0b80 verlangte costs.py, dass ALLE an einen
Schritt gekoppelten Vorgaben Informationspflichten sein muessen, damit
Buerokratiekosten verbucht werden. Gemischt verknuepfte Schritte wurden
mit 0 verbucht und ein Test in tests/test_costs_flow.py zementierte
dieses Fehlverhalten.

Seit 2cb0b80 ("fix(costs): Buerokratiekosten proportional statt pauschal
allokieren") berechnet _compute_step_bureaucracy_fractions den Anteil als
info_count / total_regulations. Damit greifen anteilige Buerokratiekosten
auch fuer gemischt verknuepfte Schritte.

Diese Tests beweisen:
  - Schritt mit ausschliesslich Infopflicht-Vorgaben -> fraction = 1.0
  - Schritt mit zwei Vorgaben, davon eine Infopflicht -> fraction = 0.5
  - Schritt mit ausschliesslich Nicht-Infopflicht-Vorgaben -> nicht enthalten
  - Schritt mit drei Vorgaben, einer Infopflicht -> fraction = 1/3

Der Test greift auf die private Funktion _compute_step_bureaucracy_fractions
direkt zu. Rechtfertigung: Wir testen hier eine Leitfaden-Anforderung, die
als dedizierte Mathematik-Einheit implementiert ist. Ein End-to-End-Test
ueber die costs-Route existiert in tests/test_costs_flow.py; dieser Guard
schuetzt ausschliesslich die Kern-Allokationsformel gegen Regression.
"""
import pytest

from backend.core import db
from backend.core.norm_addressees import BUSINESS
from backend.core.cost_aggregation import _compute_step_bureaucracy_fractions


def _seed_business_step_with_regulations(
    session_id: int,
    info_count: int,
    other_count: int,
) -> int:
    process_id = db.insert_process(
        session_id=session_id,
        process="Wirtschaftsprozess",
        description="d",
        norm_addressee=BUSINESS,
    )
    case_group_id = db.insert_case_group(
        session_id=session_id,
        process_id=process_id,
        case_group="CG",
        description="d",
        norm_addressee=BUSINESS,
    )
    step_id = db.insert_process_step(
        session_id=session_id,
        case_group_id=case_group_id,
        step="Schritt",
        description="d",
        norm_addressee=BUSINESS,
    )

    regulation_ids: list[int] = []
    for i in range(info_count):
        rid = db.insert_regulation(
            session_id=session_id,
            legal_citation=f"§ info-{i}",
            description=f"Infopflicht {i}",
            process_id=process_id,
            applies_to_administration=False,
            applies_to_business=True,
            is_business_information_obligation=True,
        )
        regulation_ids.append(rid)
    for i in range(other_count):
        rid = db.insert_regulation(
            session_id=session_id,
            legal_citation=f"§ other-{i}",
            description=f"Materielle Vorgabe {i}",
            process_id=process_id,
            applies_to_administration=False,
            applies_to_business=True,
            is_business_information_obligation=False,
        )
        regulation_ids.append(rid)

    db.replace_process_step_regulation_links(
        session_id=session_id,
        step_id=step_id,
        norm_addressee=BUSINESS,
        regulation_ids=regulation_ids,
    )
    return step_id


def test_pure_information_duty_step_gets_full_fraction(session_id):
    step_id = _seed_business_step_with_regulations(session_id, info_count=2, other_count=0)

    fractions = _compute_step_bureaucracy_fractions(session_id, BUSINESS)

    assert fractions.get(step_id) == pytest.approx(1.0)


def test_mixed_step_gets_proportional_fraction_half(session_id):
    """Kernbefund 3.1: Ein Schritt mit einer Infopflicht und einer
    materiellen Vorgabe muss 0.5 als Anteil bekommen, nicht 0."""
    step_id = _seed_business_step_with_regulations(session_id, info_count=1, other_count=1)

    fractions = _compute_step_bureaucracy_fractions(session_id, BUSINESS)

    assert fractions.get(step_id) == pytest.approx(0.5)


def test_mixed_step_with_one_of_three_info_gets_one_third(session_id):
    step_id = _seed_business_step_with_regulations(session_id, info_count=1, other_count=2)

    fractions = _compute_step_bureaucracy_fractions(session_id, BUSINESS)

    assert fractions.get(step_id) == pytest.approx(1.0 / 3.0)


def test_pure_material_step_is_not_in_fractions(session_id):
    step_id = _seed_business_step_with_regulations(session_id, info_count=0, other_count=2)

    fractions = _compute_step_bureaucracy_fractions(session_id, BUSINESS)

    assert step_id not in fractions


def test_step_without_information_duties_in_session_returns_empty_dict(session_id):
    """Wenn die Session gar keine Infopflichten enthaelt, returnt die
    Funktion fruehzeitig und liefert ein leeres Dict."""
    _seed_business_step_with_regulations(session_id, info_count=0, other_count=3)

    fractions = _compute_step_bureaucracy_fractions(session_id, BUSINESS)

    assert fractions == {}
