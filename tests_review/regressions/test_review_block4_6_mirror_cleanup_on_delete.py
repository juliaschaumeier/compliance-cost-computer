"""
Regression-Guard fuer Review-Befund Block 4.6.

Hintergrund: Die Review behauptete urspruenglich, dass
`delete_mirror_matches_for_session` nirgends aufgerufen werde und Waisen-
Matches nach Loeschung von Fallgruppen/Prozessen/Vorgaben in der DB
zurueckblieben.

Tatsaechlicher Stand: Drei Funktionen fuehren bereits einen Eager Cleanup
von mirror_matches durch, wenn die referenzierten Tabellen geleert werden:

  - db.delete_case_groups_for_session (db.py:4344-4347)
  - db.delete_processes_for_session   (db.py:4368-4371)
  - db.delete_regulations_for_session (db.py:4383-4386)

Plus Lazy Cleanup ueber `_mirror_matches_are_current` in
`ensure_mirror_matching` und Safeguard via `_assert_required_mirror_case_group_sync`.

Diese Tests zementieren das Eager-Cleanup-Verhalten gegen Regression. Wenn
jemand das `DELETE FROM mirror_matches` versehentlich aus einer der drei
delete-Funktionen entfernt, schlagen diese Tests an.
"""
import pytest

from backend.core import db
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS


def _seed_minimal_mirror_setup(session_id: int) -> tuple[int, int]:
    """Legt zwei Adressaten-Seiten an und schreibt einen Mirror-Match
    zwischen ihnen. Liefert (source_case_group_id, target_case_group_id)."""
    src_proc = db.insert_process(
        session_id=session_id,
        process="Antrag",
        description="d",
        norm_addressee=CITIZENS,
    )
    src_cg = db.insert_case_group(
        session_id=session_id,
        process_id=src_proc,
        case_group="Antragsfaelle",
        description="d",
        norm_addressee=CITIZENS,
    )
    tgt_proc = db.insert_process(
        session_id=session_id,
        process="Bescheid",
        description="d",
        norm_addressee=ADMINISTRATION,
    )
    tgt_cg = db.insert_case_group(
        session_id=session_id,
        process_id=tgt_proc,
        case_group="Bescheidfaelle",
        description="d",
        norm_addressee=ADMINISTRATION,
    )
    db.replace_mirror_matches(
        session_id,
        [
            {
                "mirror_anchor_key": "antrag",
                "shared_situation": "Antrag und Bescheid",
                "source_norm_addressee": CITIZENS,
                "target_norm_addressee": ADMINISTRATION,
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
    assert db.list_mirror_matches(session_id), "Setup-Voraussetzung verletzt"
    return src_cg, tgt_cg


def test_delete_case_groups_clears_mirror_matches(session_id):
    _seed_minimal_mirror_setup(session_id)
    db.delete_case_groups_for_session(session_id)
    assert db.list_mirror_matches(session_id) == []


def test_delete_processes_clears_mirror_matches(session_id):
    _seed_minimal_mirror_setup(session_id)
    db.delete_processes_for_session(session_id)
    assert db.list_mirror_matches(session_id) == []


def test_delete_regulations_clears_mirror_matches(session_id):
    _seed_minimal_mirror_setup(session_id)
    db.delete_regulations_for_session(session_id)
    assert db.list_mirror_matches(session_id) == []


def test_delete_case_groups_for_specific_addressee_also_clears_matches(session_id):
    """Auch wenn nur eine Adressaten-Seite geloescht wird, muessen alle
    Matches der Session entfernt werden - andernfalls wuerden Matches auf
    die geloeschte Seite verweisen, was die Sync-Logik bricht."""
    _seed_minimal_mirror_setup(session_id)
    db.delete_case_groups_for_session(session_id, norm_addressee=CITIZENS)
    assert db.list_mirror_matches(session_id) == []


def test_delete_processes_for_specific_addressee_also_clears_matches(session_id):
    _seed_minimal_mirror_setup(session_id)
    db.delete_processes_for_session(session_id, norm_addressee=ADMINISTRATION)
    assert db.list_mirror_matches(session_id) == []


def test_delete_mirror_matches_for_session_is_idempotent(session_id):
    """Der niedrigste-Level-Helper darf mehrfach aufgerufen werden, ohne
    zu failen - relevant fuer Lazy-Cleanup im ensure_mirror_matching-Flow."""
    _seed_minimal_mirror_setup(session_id)
    db.delete_mirror_matches_for_session(session_id)
    db.delete_mirror_matches_for_session(session_id)
    assert db.list_mirror_matches(session_id) == []
