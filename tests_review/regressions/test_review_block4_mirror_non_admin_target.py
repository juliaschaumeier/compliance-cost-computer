"""
Regression-Guard fuer Review-Befund Block 4.1.

Behauptung: get_deterministic_mirror_case_group_metrics liefert auch dann
korrekte Overrides, wenn target_norm_addressee == 'administration'.
"""
import pytest

from backend.core import db
from backend.core.mirror_context import get_deterministic_mirror_case_group_metrics
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS


def _seed_case_group(session_id: int, addressee: str, *, addressees: float, frequency: float) -> int:
    process_id = db.insert_process(
        session_id=session_id,
        process="P",
        description="d",
        norm_addressee=addressee,
    )
    cg_id = db.insert_case_group(
        session_id=session_id,
        process_id=process_id,
        case_group="CG",
        description="d",
        norm_addressee=addressee,
    )
    db.upsert_case_group_metrics_by_addressee(
        session_id=session_id,
        case_group_id=cg_id,
        norm_addressee=addressee,
        addressees_current=addressees,
        annual_frequency_current=frequency,
        cases_current=addressees * frequency,
        addressees_proposed=addressees,
        annual_frequency_proposed=frequency,
        cases_proposed=addressees * frequency,
    )
    return cg_id


@pytest.mark.parametrize(
    "source_addressee,target_addressee",
    [
        (CITIZENS, ADMINISTRATION),
        (BUSINESS, ADMINISTRATION),
        (ADMINISTRATION, BUSINESS),
        (ADMINISTRATION, CITIZENS),
        (CITIZENS, BUSINESS),
        (BUSINESS, CITIZENS),
    ],
)
def test_mirror_sync_works_for_every_addressee_pair(session_id, source_addressee, target_addressee):
    source_cg = _seed_case_group(session_id, source_addressee, addressees=500.0, frequency=2.0)
    target_cg = _seed_case_group(session_id, target_addressee, addressees=1.0, frequency=1.0)

    db.replace_mirror_matches(
        session_id,
        [
            {
                "mirror_anchor_key": "anchor-1",
                "shared_situation": "Antrag und Bescheid",
                "source_norm_addressee": source_addressee,
                "target_norm_addressee": target_addressee,
                "source_process_id": None,
                "target_process_id": None,
                "source_case_group_id": source_cg,
                "target_case_group_id": target_cg,
                "relation_type": "antrag_bescheid",
                "sync_addressees": True,
                "sync_frequency": True,
                "sync_cases": True,
                "reason": "test",
            }
        ],
    )

    overrides = get_deterministic_mirror_case_group_metrics(session_id, target_addressee)

    assert target_cg in overrides, (
        f"Mirror sync must produce an override for {source_addressee} -> {target_addressee}"
    )
    metrics = overrides[target_cg]
    assert metrics["addressees_current"] == 500.0
    assert metrics["annual_frequency_current"] == 2.0
    assert metrics["source_norm_addressee"] == source_addressee
