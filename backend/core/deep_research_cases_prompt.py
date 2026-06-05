from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from backend.core import db
from backend.core.norm_addressees import ALL_NORM_ADDRESSEES
from backend.core.payload_builders import (
    build_case_groups_payload,
    dump_prompt_json,
)


def _resolve_session(*, app_session_id: str | None, session_id: int | None) -> dict[str, Any]:
    if session_id is not None:
        session = db.get_session_by_id(int(session_id))
    elif app_session_id:
        session = db.get_session_by_app_id(app_session_id)
    else:
        raise ValueError("Either app_session_id or session_id is required")
    if session is None:
        identifier = session_id if session_id is not None else app_session_id
        raise ValueError(f"Session not found: {identifier}")
    return session


def _session_context_payload(
    session: dict[str, Any],
    *,
    include_law_texts: bool,
) -> dict[str, Any]:
    session_id = int(session["session_id"])
    norm_addressees: list[dict[str, Any]] = []
    all_regulations = db.list_regulations_for_session(session_id)

    for norm_addressee in ALL_NORM_ADDRESSEES:
        processes = db.list_processes_for_session_and_addressee(
            session_id,
            norm_addressee,
        )
        case_groups = db.list_case_groups_for_session_and_addressee(
            session_id,
            norm_addressee,
        )
        if not processes and not case_groups:
            continue
        regulations = db.list_regulations_for_session_and_addressee(
            session_id,
            norm_addressee,
        )
        norm_addressees.append(
            {
                "normadressat": norm_addressee,
                "prozesse": build_case_groups_payload(
                    processes=processes,
                    case_groups=case_groups,
                    regulations=regulations,
                    norm_addressee=norm_addressee,
                ),
            }
        )

    payload = {
        "session": {
            "session_id": session_id,
            "app_session_id": session.get("app_session_id"),
            "law_diff_title": session.get("law_diff_title"),
            "law_diff_blurb": session.get("law_diff_blurb"),
            "law_diff_summary": session.get("law_diff_summary"),
        },
        "vorgaben_gesamt": all_regulations,
        "normadressaten": norm_addressees,
    }
    if include_law_texts:
        current_law_text, proposed_law_text = db.get_session_law_texts(session_id)
        payload["gesetz_gueltig"] = current_law_text
        payload["gesetz_vorschlag"] = proposed_law_text
    return payload


def build_deep_research_cases_prompt(
    *,
    app_session_id: str | None = None,
    session_id: int | None = None,
    include_law_texts: bool = False,
) -> str:
    """Render a standalone Deep Research prompt for yearly case-number research.

    Intended notebook usage:

    ```
    from backend.core.deep_research_cases_prompt import build_deep_research_cases_prompt
    prompt = build_deep_research_cases_prompt(app_session_id="BI2J3R")
    ```
    """
    session = _resolve_session(app_session_id=app_session_id, session_id=session_id)
    payload = _session_context_payload(
        session,
        include_law_texts=include_law_texts,
    )
    payload_json = dump_prompt_json(payload)
    return _render_prompt(payload_json)


def _render_prompt(session_payload_json: str) -> str:
    return f"""Rechercheauftrag: Ermittlung der jaehrlichen Fallzahlen fuer alle definierten Fallgruppen einer deutschen Gesetzesaenderung.

Sie erhalten unten einen strukturierten Session-Kontext aus einer Fachanwendung. Dieser Kontext enthaelt:

- Informationen zur Session,
- soweit vorhanden den Text des geltenden Rechts und des Gesetzesvorschlags,
- die identifizierten Vorgaben,
- die betroffenen Normadressaten,
- die zugeordneten Verwaltungs-, Wirtschafts- oder Buergerprozesse,
- und die innerhalb dieser Prozesse gebildeten Fallgruppen.

Ihre Aufgabe ist es, fuer alle im Kontext enthaltenen Fallgruppen belastbare quantitative Werte zu recherchieren und herzuleiten. Die Recherche soll nicht nur isolierte Einzelwerte liefern, sondern ein konsistentes Mengenbild ueber alle Normadressaten hinweg entwickeln.

Wichtig:

- Dies ist kein Software- oder Workflow-Task.
- Verwenden Sie nur die fachlichen Informationen aus dem Session-Kontext und externe Quellen fuer die Recherche.
- Formulieren Sie die gesamte Antwort auf Deutsch.
- Liefern Sie konkrete Zahlen, nicht nur qualitative Einordnungen.
- Der Auftrag ist gesetzesagnostisch formuliert: Leiten Sie die fachliche Fragestellung aus dem Session-Kontext ab und vermeiden Sie Annahmen, die dort nicht angelegt sind.
- Betrachten Sie ausschliesslich jaehrlich wiederkehrenden Erfuellungsaufwand: Quantifizieren Sie Fallzahlen nur fuer regelmaessig pro Jahr wiederkehrende Fallgruppen. Einmaligen Umstellungs-/Einfuehrungsaufwand bei Einfuehrung der Regelung nicht als jaehrliche Fallzahl ansetzen.

Ziel der Recherche

Fuer jede Fallgruppe sollen Sie bestimmen:

- wie viele relevante Normadressaten bzw. betroffene Personen, Unternehmen, Organisationen oder Verwaltungseinheiten unter dem geltenden Recht relevant sind,
- wie haeufig ein solcher Normadressat den Vorgang durchschnittlich pro Jahr ausloest oder bearbeitet,
- wie viele relevante Normadressaten bzw. Betroffene unter dem Gesetzesvorschlag relevant sind,
- wie haeufig ein solcher Normadressat den Vorgang unter dem Gesetzesvorschlag durchschnittlich pro Jahr ausloest oder bearbeitet,
- und welche jaehrlichen Fallzahlen sich daraus ergeben.

Die gesuchten Werte sind sowohl fuer das geltende Recht als auch fuer den Gesetzesvorschlag zu ermitteln.

Verbindliche Zielwerte je Fallgruppe

Liefern Sie fuer jede Fallgruppe genau diese vier Eingabewerte:

- `anzahl_betroffene_gueltig`
- `haeufigkeit_pro_jahr_gueltig`
- `anzahl_betroffene_vorschlag`
- `haeufigkeit_pro_jahr_vorschlag`

Ergaenzend sollen Sie rechnerisch ausweisen:

- `fallzahl_gueltig = anzahl_betroffene_gueltig * haeufigkeit_pro_jahr_gueltig`
- `fallzahl_vorschlag = anzahl_betroffene_vorschlag * haeufigkeit_pro_jahr_vorschlag`

Verbindliche Definitionen

- `anzahl_betroffene_gueltig`: Anzahl der unterschiedlichen Normadressaten, Einheiten oder Fallausloeser, die unter geltendem Recht in diese Fallgruppe fallen und im Jahreskontext relevant sind.
- `haeufigkeit_pro_jahr_gueltig`: Durchschnittliche Haeufigkeit pro Jahr, mit der ein solcher Normadressat oder Fallausloeser unter geltendem Recht diesen Vorgang ausloest bzw. bearbeitet.
- `anzahl_betroffene_vorschlag`: Anzahl der unterschiedlichen Normadressaten, Einheiten oder Fallausloeser, die unter dem vorgeschlagenen Recht in diese Fallgruppe fallen und im Jahreskontext relevant sind.
- `haeufigkeit_pro_jahr_vorschlag`: Durchschnittliche Haeufigkeit pro Jahr, mit der ein solcher Normadressat oder Fallausloeser unter dem vorgeschlagenen Recht diesen Vorgang ausloest bzw. bearbeitet.

Interpretation nach Normadressat

- Bei `business` ist die Anzahl Betroffene typischerweise die Zahl der betroffenen Unternehmen, Betriebe, Organisationen oder wirtschaftlichen Einheiten. Die Fallzahl ergibt sich bei periodischen Pflichten aus Bestand mal Periodizitaet und bei anlassbezogenen Pflichten aus den jaehrlich erwarteten Ereignissen.
- Bei `citizens` ist die Anzahl Betroffene typischerweise die Zahl betroffener Personen oder Haushalte. Verwenden Sie keine Gesamtbevoelkerung, wenn nur eine spezifische Teilgruppe betroffen ist.
- Bei `administration` ist die Anzahl Betroffene nicht automatisch die Zahl aller extern Betroffenen. Entscheidend sind die jaehrlich von der Verwaltung zu bearbeitenden Vorgaenge, Antraege, Pruefungen, Bescheide, Kontrollen oder sonstigen Vollzugshandlungen dieser Fallgruppe. Wenn die Verwaltung dieselben Antraege bearbeitet, die Wirtschaft oder Buerger ausloesen, muss die Fallzahl dazu konsistent sein.

Konsistenz ueber Normadressaten hinweg

Pruefen Sie aktiv, ob Fallzahlen zwischen Normadressaten gespiegelt oder gekoppelt sind:

- Wenn Unternehmen Antraege stellen, Anzeigen abgeben oder Nachweise einreichen, pruefen Sie, ob die Verwaltung dieselbe Anzahl an Antraegen, Anzeigen oder Nachweisen bearbeitet.
- Wenn Buergerinnen und Buerger einen Antrag stellen, pruefen Sie, ob eine Verwaltungsfallgruppe dieselbe oder eine sachgerecht verteilte Bearbeitungsmenge abbildet.
- Wenn eine Verwaltungsfallgruppe mehrere wirtschafts- oder buergerseitige Fallgruppen buendelt, erklaeren Sie die Summenbildung.
- Wenn eine wirtschafts- oder buergerseitige Fallgruppe nur einen Teil einer Verwaltungsfallgruppe ausloest, erklaeren Sie die Abgrenzung.
- Vermeiden Sie widerspruechliche Mengenbilder, etwa 500 Antraege auf Seiten der Wirtschaft und 50 Bearbeitungsfaelle auf Seiten der Verwaltung, sofern keine fachliche Begruendung vorliegt.

Erwartete Herleitung

Arbeiten Sie fuer jede wesentliche Mengenannahme mindestens entlang dieser Fragen:

1. Welche externe Grundgesamtheit ist fachlich einschlaegig?
2. Welche Teilmenge faellt tatsaechlich unter die konkrete Vorgabe, den Prozess oder die Fallgruppe?
3. Ist der Vorgang periodisch, anlassbezogen oder bestandsbezogen?
4. Ist die Fallzahl besser ueber Bestand mal Haeufigkeit oder direkt ueber jaehrliche Ereignisse/Antraege/Faelle zu modellieren?
5. Aendert die Gesetzesaenderung nur den Aufwand pro Fall oder auch die Menge der Faelle?
6. Gibt es Nachfrage-, Verhaltens-, Klarstellungs-, Adressatenkreis- oder Vollzugseffekte, die unterschiedliche Werte fuer geltendes Recht und Vorschlag rechtfertigen?
7. Welche Werte anderer Normadressaten muessen damit konsistent sein?

Recherchehinweise

- Fokus ausschliesslich auf Deutschland, sofern der Session-Kontext keine andere Abgrenzung vorgibt.
- Bevorzugen Sie hochwertige und moeglichst primaere Quellen, insbesondere:
  - Gesetzestexte und Gesetzesbegruendungen,
  - Bundestags- oder Ausschussmaterialien,
  - Verwaltungs-, Ministeriums- oder Statistikmaterialien,
  - Destatis, die Webseite des Statistischen Bundesamtes (https://www.destatis.de/DE/Home/_inhalt.html),
  - OnDEA bzw. vorhandene Erfuellungsaufwandsschaetzungen, soweit einschlaegig,
  - amtliche Statistiken,
  - Registerdaten,
  - Verbandsinformationen,
  - wissenschaftliche, juristische oder fachliche Analysen.
- Wenn es keine direkte Statistik gibt, leiten Sie Werte transparent aus Proxys her.
- Unterscheiden Sie sauber zwischen Gesamtbestand, betroffener Teilmenge, jaehrlich aktiven Faellen und Verwaltungsvorgaengen.

Was Sie nicht tun sollen

- Keine qualitativen Platzhalter wie "niedrig", "mittel", "hoch" als Endwert.
- Keine undifferenzierten Gesamtbestandszahlen als direkte Fallzahl verwenden.
- Nicht unterstellen, dass jeder Betroffene jedes Jahr einen Antrag stellt oder eine Pflicht ausloest.
- Nicht automatisch annehmen, dass geltendes Recht exakt 0 Faelle hat.
- Nicht automatisch annehmen, dass der Gesetzesvorschlag sehr hohe Fallzahlen erzeugt.
- Keine Software-, App- oder Datenbankimplementierung beschreiben.
- Keine einmaligen Vorgaenge, die nur bei Einfuehrung der Regelung anfallen (z.B. interne Umstellung, Erstschulung, Einarbeitung), als jaehrliche Fallzahl ansetzen.

Verbindliche Ausgabeanforderungen

Die Antwort soll aus drei Teilen bestehen.

Teil 1: Vollstaendiger Forschungsbericht

Erstellen Sie einen ausfuehrlichen Bericht mit:

1. Management-Zusammenfassung,
2. Methodik,
3. Darstellung der relevanten Quellenlage,
4. Analyse der Mengenannahmen fuer das geltende Recht,
5. Analyse der Mengenannahmen fuer den Gesetzesvorschlag,
6. Konsistenzabgleich ueber alle Normadressaten und Fallgruppen hinweg,
7. Unsicherheiten, Alternativannahmen und plausible Spannbreiten,
8. Quellenliste mit URLs.

Teil 2: Kurze Begruendungszeilen je Fallgruppe und Kennzahl

Fuegen Sie danach fuer jede Fallgruppe genau eine kurze Zeile je Kennzahl ein. Jede Zeile muss einen echten numerischen Wert und einen kurzen Begruendungssatz enthalten.
Der Begruendungssatz soll in sich verstaendlich sein und, soweit die Quelle fuer die Einordnung wichtig ist, die relevante Quelle oder URL direkt in der Zeile nennen.

Format:

- `normadressat=<normadressat>; fallgruppen_id=<id>; anzahl_betroffene_gueltig = <zahl>, weil <kurze Begruendung>`
- `normadressat=<normadressat>; fallgruppen_id=<id>; haeufigkeit_pro_jahr_gueltig = <zahl>, weil <kurze Begruendung>`
- `normadressat=<normadressat>; fallgruppen_id=<id>; anzahl_betroffene_vorschlag = <zahl>, weil <kurze Begruendung>`
- `normadressat=<normadressat>; fallgruppen_id=<id>; haeufigkeit_pro_jahr_vorschlag = <zahl>, weil <kurze Begruendung>`

Teil 3: Tabellarische Kurzfassung und JSON-Block

Fuegen Sie eine kurze Tabelle mit folgenden Spalten hinzu:

- Normadressat
- Prozess-ID
- Fallgruppen-ID
- Kennzahl
- empfohlener Wert
- kurze Begruendung
- Konfidenz (`high`, `medium` oder `low`)

Fuegen Sie am Ende einen maschinenlesbaren JSON-Block genau nach folgendem Schema hinzu. Verwenden Sie echte Zahlen, keine verbalen Platzhalter. Fuehren Sie alle Normadressaten und Fallgruppen aus dem Session-Kontext auf.

```json
{{
  "session": {{
    "session_id": 0,
    "app_session_id": ""
  }},
  "prozesse": [
    {{
      "normadressat": "administration | business | citizens",
      "prozess_id": 0,
      "prozess_bezeichnung": "",
      "fallgruppen": [
        {{
          "fallgruppen_id": 0,
          "fallgruppe_bezeichnung": "",
          "anzahl_betroffene_gueltig": 0,
          "haeufigkeit_pro_jahr_gueltig": 0,
          "fallzahl_gueltig": 0,
          "anzahl_betroffene_vorschlag": 0,
          "haeufigkeit_pro_jahr_vorschlag": 0,
          "fallzahl_vorschlag": 0,
          "erklaerungen": {{
            "anzahl_betroffene_gueltig": "kurze, eigenstaendige Begruendung mit Quellenhinweis/URL, soweit fuer die Einordnung erforderlich",
            "haeufigkeit_pro_jahr_gueltig": "kurze, eigenstaendige Begruendung mit Quellenhinweis/URL, soweit fuer die Einordnung erforderlich",
            "anzahl_betroffene_vorschlag": "kurze, eigenstaendige Begruendung mit Quellenhinweis/URL, soweit fuer die Einordnung erforderlich",
            "haeufigkeit_pro_jahr_vorschlag": "kurze, eigenstaendige Begruendung mit Quellenhinweis/URL, soweit fuer die Einordnung erforderlich"
          }},
          "confidence": {{
            "anzahl_betroffene_gueltig": "high | medium | low",
            "haeufigkeit_pro_jahr_gueltig": "high | medium | low",
            "anzahl_betroffene_vorschlag": "high | medium | low",
            "haeufigkeit_pro_jahr_vorschlag": "high | medium | low"
          }},
          "quellen": [
            {{
              "titel": "",
              "url": "",
              "verwendung": ""
            }}
          ]
        }}
      ]
    }}
  ],
  "konsistenzpruefung": [
    {{
      "beschreibung": "",
      "betroffene_fallgruppen": [
        {{"normadressat": "", "fallgruppen_id": 0}}
      ],
      "bewertung": ""
    }}
  ],
  "notizen": [
    ""
  ]
}}
```

Qualitaetsmassstab

- Liefern Sie konkrete Zahlen fuer jede Fallgruppe und jede der vier verbindlichen Kennzahlen.
- Wenn Sie schaetzen muessen, tun Sie das transparent und begruendet.
- Wenn die Evidenz schwach ist, nennen Sie trotzdem einen bestmoeglichen empfohlenen Zahlenwert und markieren die Konfidenz entsprechend.
- Der Bericht muss fuer eine Person verstaendlich sein, die nur den Session-Kontext und Ihre Antwort liest.
- Der JSON-Block muss vollstaendig sein und die im Session-Kontext enthaltenen IDs unveraendert uebernehmen.
- Die Feldwerte in `erklaerungen` werden spaeter direkt in der App angezeigt. Formulieren Sie sie deshalb knapp, eigenstaendig und mit Quellenhinweis/URL im Text, sofern die Quelle zum Verstaendnis der Zahl erforderlich ist. Die separate `quellen`-Liste bleibt zusaetzliche Audit- und Report-Metadaten.

Session-Kontext

```json
{session_payload_json}
```
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render a standalone Deep Research prompt for case-group numbers.",
    )
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--app-session-id", help="App-facing session id, e.g. BI2J3R")
    selector.add_argument("--session-id", type=int, help="Numeric DB session id")
    parser.add_argument(
        "--include-law-texts",
        action="store_true",
        help="Include raw current/proposed law texts in the rendered session context",
    )
    parser.add_argument("--output", type=Path, help="Optional markdown output path")
    args = parser.parse_args(argv)

    prompt = build_deep_research_cases_prompt(
        app_session_id=args.app_session_id,
        session_id=args.session_id,
        include_law_texts=args.include_law_texts,
    )
    if args.output:
        args.output.write_text(prompt, encoding="utf-8")
    else:
        print(prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
