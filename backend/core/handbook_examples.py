from __future__ import annotations

"""Handbook examples injected into prompts.

The examples are based on the official handbook, with light formatting cleanup
for prompt readability:

Statistisches Bundesamt, "Leitfaden zur Ermittlung und Darstellung des
Erfüllungsaufwands in Regelungsvorhaben der Bundesregierung", Februar 2026.
"""


CASES_CALCULATION_FREQUENCY_EXAMPLE = """
Beispiele für jährliche Häufigkeit bei periodisch zu erfüllenden Vorgaben:

Vorgabe ist periodisch zu erfüllen

- einmal jährlich: Häufigkeit = 1
- halbjährlich: Häufigkeit = 2
- monatlich: Häufigkeit = 12
- alle 5 Jahre: Häufigkeit = 0,2
""".strip()


CASES_CALCULATION_CASE_EXAMPLE = """
Beispiel zur Ermittlung der Fallzahl:

- Aufgrund einer Änderung der Straßenverkehrs-Ordnung (StVO) darf ein Kraftfahrzeug (Kfz) bei Glatteis, Schneeglätte, Schneematsch, Eis- oder Reifglätte nach Inkrafttreten nur gefahren werden, wenn die Reifen bestimmte Eigenschaften (M+S-Reifen) erfüllen. Aus dieser neuen Vorgabe entsteht den Halterinnen und Haltern von privaten Kfz unmittelbar Erfüllungsaufwand: Die Kfz sind - soweit sie bei den oben angegebenen Witterungsverhältnissen betrieben werden sollten - mit M+S-Reifen auszurüsten (Anschaffungs- und Montagekosten). Im Falle der Vorgabe, bei entsprechenden Witterungsverhältnissen Winterreifen zu benutzen, entspricht es der Lebenswirklichkeit, dass Kfz-Halterinnen und Halter nicht nur einmal auf Winterreifen umrüsten, sondern im Frühjahr wieder zurück auf Sommerreifen wechseln. Auch der Aufwand für diesen zweiten Wechsel steht in unmittelbarem Zusammenhang mit der Vorgabe und ist daher bei der Ermittlung und Darstellung des Erfüllungsaufwands zu berücksichtigen.
- Von insgesamt 66,9 Millionen zugelassenen Kfz (Quelle: Kraftfahrt-Bundesamt) würden nach Einschätzung von Verbänden 70 Prozent (46,8 Millionen Kfz) im Herbst und im Frühjahr jeweils umgerüstet. Weitere 20 Prozent (13,4 Millionen Kfz) würden ganzjährig mit Allwetterreifen fahren oder bei winterlichen Straßenverhältnissen gar nicht. Berechnungsgrundlage sind also die verbleibenden 10 Prozent und somit 6,7 Millionen Kfz der Halterinnen und Halter, die nur Sommerreifen nutzen würden. Diese müssen erstmals M+S-Reifen beschaffen und in den Folgejahren regelmäßig wechseln (Häufigkeit = 2, Zahl der Kfz: 6,7 Millionen, Fallzahl 13,4 Millionen Kfz).
- Dabei wird angenommen, dass die Fallzahl von 6,7 Millionen Kfz sich ausschließlich auf Privat-Kfz bezieht, weil Kfz der Wirtschaft und der Verwaltung bereits überwiegend mit Winterreifen ausgestattet sind.
""".strip()
