"""
Regression-Test fuer Review-Befund Block 3 (Buerokratiekosten-Bug).

Behauptung (Soll): Wenn ein Schritt an mehrere Vorgaben gekoppelt ist und
mindestens eine davon eine Informationspflicht der Wirtschaft ist, muss der
Buerokratiekosten-Anteil dieses Schritts > 0 sein. Aktuell verlangt die
Logik in costs.py, dass *alle* gekoppelten Vorgaben Informationspflichten
sein muessen.
"""
import pytest


@pytest.mark.xfail(
    reason=(
        "Bekannter Bug aus Review-Befund Block 3.1: costs.py verlangt, "
        "dass ALLE Vorgaben eines Schritts Informationspflichten sind, damit "
        "Buerokratiekosten verbucht werden. Test beschreibt das gewuenschte "
        "Verhalten und soll xpassen, sobald der Fix da ist."
    ),
    strict=True,
)
def test_step_with_mixed_regulations_still_reports_bureaucracy_cost():
    raise AssertionError(
        "Test noch nicht implementiert - dokumentiert geforderten Fix fuer "
        "costs.py _list_business_information_step_ids."
    )
