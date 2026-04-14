"""
Schicht 4 / INV-CASE-002.

Spiegel-Identitaet: Nach jedem Sync muessen die gespiegelten Fallzahlen
auf beiden Seiten identisch sein.
"""
import pytest

from backend.core import db
from backend.core.mirror_context import get_deterministic_mirror_case_group_metrics
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS


def _seed_pair(
    session_id: int,
    source_addressee: str,
    target_addressee: str,
    source_addressees: float,
    source_frequency: float,
) -> tuple[int, int]:
    src_proc = db.insert_process(session_id=session_id, process="Sp", description="d", norm_addressee=source_addressee)
    src_cg = db.insert_case_group(session_id=session_id, process_id=src_proc, case_group="Sc", description="d", norm_addressee=source_addressee)
    db.upsert_case_group_metrics_by_addressee(
        session_id=session_id,
        case_group_id=src_cg,
        norm_addressee=source_addressee,
        addressees_current=source_addressees,
        annual_frequency_current=source_frequency,
        cases_current=source_addressees * source_frequency,
        addressees_proposed=source_addressees,
        annual_frequency_proposed=source_frequency,
        cases_proposed=source_addressees * source_frequency,
    )
    tgt_proc = db.insert_process(session_id=session_id, process="Tp", description="d", norm_addressee=target_addressee)
    tgt_cg = db.insert_case_group(session_id=session_id, process_id=tgt_proc, case_group="Tc", description="d", norm_addressee=target_addressee)
    db.upsert_case_group_metrics_by_addressee(
        session_id=session_id,
        case_group_id=tgt_cg,
        norm_addressee=target_addressee,
        addressees_current=1.0,
        annual_frequency_current=1.0,
        cases_current=1.0,
        addressees_proposed=1.0,
        annual_frequency_proposed=1.0,
        cases_proposed=1.0,
    )
    db.replace_mirror_matches(
        session_id,
        [
            {
                "mirror_anchor_key": f"{source_addressee}-{target_addressee}",
                "shared_situation": "spiegel",
                "source_norm_addressee": source_addressee,
                "target_norm_addressee": target_addressee,
                "source_process_id": src_proc,
                "target_process_id": tgt_proc,
                "source_case_group_id": src_cg,
                "target_case_group_id": tgt_cg,
                "relation_type": "antrag_bescheid",
                "sync_addressees": True,
                "sync_frequency": True,
                "sync_cases": True,
                "reason": "test",
            }
        ],
    )
    return src_cg, tgt_cg


@pytest.mark.parametrize(
    "source,target",
    [
        (CITIZENS, ADMINISTRATION),
        (BUSINESS, ADMINISTRATION),
        (CITIZENS, BUSINESS),
        (ADMINISTRATION, BUSINESS),
        (ADMINISTRATION, CITIZENS),
        (BUSINESS, CITIZENS),
    ],
)
def test_deterministic_sync_produces_identical_metrics(session_id, source, target):
    _src_cg, tgt_cg = _seed_pair(session_id, source, target, source_addressees=750.0, source_frequency=4.0)

    overrides = get_deterministic_mirror_case_group_metrics(session_id, target)

    assert tgt_cg in overrides
    metrics = overrides[tgt_cg]
    assert metrics["addressees_current"] == 750.0
    assert metrics["annual_frequency_current"] == 4.0
    assert metrics["addressees_proposed"] == 750.0
    assert metrics["annual_frequency_proposed"] == 4.0
    assert metrics["source_norm_addressee"] == source


def test_edit_on_source_propagates_to_override_on_next_sync_call(session_id):
    """Aendert die Quelle ohne neuen LLM-Aufruf und verifiziert, dass die
    Sync-Logik seiteneffektfrei und immer aktuell ist."""
    src_cg, tgt_cg = _seed_pair(session_id, CITIZENS, ADMINISTRATION, source_addressees=100.0, source_frequency=1.0)

    overrides = get_deterministic_mirror_case_group_metrics(session_id, ADMINISTRATION)
    assert overrides[tgt_cg]["addressees_current"] == 100.0

    db.upsert_case_group_metrics_by_addressee(
        session_id=session_id,
        case_group_id=src_cg,
        norm_addressee=CITIZENS,
        addressees_current=2500.0,
        annual_frequency_current=3.0,
        cases_current=7500.0,
        addressees_proposed=2500.0,
        annual_frequency_proposed=3.0,
        cases_proposed=7500.0,
    )

    overrides = get_deterministic_mirror_case_group_metrics(session_id, ADMINISTRATION)
    assert overrides[tgt_cg]["addressees_current"] == 2500.0
    assert overrides[tgt_cg]["annual_frequency_current"] == 3.0


def test_no_sync_when_sync_cases_flag_is_false(session_id):
    """sync_cases=False darf keine Overrides erzeugen."""
    src_proc = db.insert_process(session_id=session_id, process="Sp", description="d", norm_addressee=CITIZENS)
    src_cg = db.insert_case_group(session_id=session_id, process_id=src_proc, case_group="Sc", description="d", norm_addressee=CITIZENS)
    db.upsert_case_group_metrics_by_addressee(
        session_id=session_id,
        case_group_id=src_cg,
        norm_addressee=CITIZENS,
        addressees_current=500.0,
        annual_frequency_current=2.0,
        cases_current=1000.0,
        addressees_proposed=500.0,
        annual_frequency_proposed=2.0,
        cases_proposed=1000.0,
    )
    tgt_proc = db.insert_process(session_id=session_id, process="Tp", description="d", norm_addressee=ADMINISTRATION)
    tgt_cg = db.insert_case_group(session_id=session_id, process_id=tgt_proc, case_group="Tc", description="d", norm_addressee=ADMINISTRATION)

    db.replace_mirror_matches(
        session_id,
        [
            {
                "mirror_anchor_key": "no-sync",
                "shared_situation": "spiegel",
                "source_norm_addressee": CITIZENS,
                "target_norm_addressee": ADMINISTRATION,
                "source_process_id": src_proc,
                "target_process_id": tgt_proc,
                "source_case_group_id": src_cg,
                "target_case_group_id": tgt_cg,
                "relation_type": "antrag_bescheid",
                "sync_addressees": False,
                "sync_frequency": False,
                "sync_cases": False,
                "reason": "test - no sync",
            }
        ],
    )

    overrides = get_deterministic_mirror_case_group_metrics(session_id, ADMINISTRATION)
    assert tgt_cg not in overrides
