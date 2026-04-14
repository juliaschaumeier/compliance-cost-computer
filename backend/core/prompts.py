from __future__ import annotations

from typing import Any, Dict

from backend.core.handbook_examples import (
    CASE_GROUP_DEVELOPMENT_EXAMPLE,
    CASES_CALCULATION_CASE_EXAMPLE,
    CASES_CALCULATION_FREQUENCY_EXAMPLE,
    PROCESS_COMPILATION_EXAMPLE,
)
from backend.core.handbook_tables import Appendix
from backend.core.mirror_context import render_mirror_prompt_context
from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS


class PromptId:
    LAW_SUMMARY = "law_summary"
    REGULATIONS_IDENTIFICATION = "regulations_identification"
    PROCESS_COMPILATION = "process_compilation"
    CASE_GROUP_DEVELOPMENT = "case_group_development"
    MIRROR_MATCHING = "mirror_matching"
    PROCESS_STEP_ANALYSIS = "process_step_analysis"
    CASES_CALCULATION = "cases_calculation"
    EFFORT_CALCULATION = "effort_calculation"


LEGIST_PROMPT_OPENING = (
    """
    Sie sind Legist im deutschen Bundestag und damit betraut, die 
    Erfüllungsaufwandsänderung zu einer geplanten Gesetzesänderung zu berechnen.

    Insbesondere werden zur Ermittlung der zu erwartenden Änderung des Aufwands 
    pro Fall die wesentlichen Tätigkeiten identifiziert, die zur Erfüllung 
    einer Vorgabe oder eines Prozesses im Einzelfall zu erwarten sind. Diese 
    schließen Tätigkeiten ein, welche neu hinzukommen, welche sich ändern und 
    welche wegfallen. Für diese Tätigkeiten werden die zu erwartenden Änderungen des 
    Zeit-, Personal- sowie Sachaufwands ermittelt.

    Die wesentlichen Unterschiede der Gesetzesänderung sind wie folgt 
    zusammengefasst: {law_summary}

    """
)


NORM_ADDRESSEE_PROMPT_OPENINGS: Dict[str, str] = {
    ADMINISTRATION: (
        """
        Dieser Lauf betrifft den Normadressaten Verwaltung.

        Beruecksichtigen Sie ausschliesslich den Erfuellungsaufwand der Verwaltung. Dazu
        gehoeren insbesondere Vollzugsaufwand sowie sonstige verwaltungsinterne oder
        verwaltungsseitig ausgeloeste Taetigkeiten. Uebernehmen Sie keine wirtschaftlichen
        oder buergerbezogenen Prozesse, Fallgruppen, Taetigkeiten, Fallzahlen oder Werte,
        sofern diese nicht ausdruecklich als Spiegelwirkung der Verwaltung zuzurechnen sind.
        """
    ),
    BUSINESS: (
        """
        Dieser Lauf betrifft den Normadressaten Wirtschaft.

        Beruecksichtigen Sie ausschliesslich den Erfuellungsaufwand der Wirtschaft.
        Analysieren Sie nur wirtschaftsbezogene Prozesse, Fallgruppen, Taetigkeiten,
        Fallzahlen und Werte. Uebernehmen Sie keine Verwaltungslogik, Verwaltungswerte
        oder buergerbezogenen Inhalte, sofern diese nicht ausdruecklich als Spiegelwirkung
        oder wirtschaftsrelevante Folge der Vorgabe begruendet sind. Informationspflichten
        der Wirtschaft, Spiegelsituationen, interne Umstellungen, externe Dienstleistungen
        sowie wirtschaftsspezifische Pruef-, Melde-, Nachweis- und Dokumentationspflichten
        sind mitzudenken.
        """
    ),
    CITIZENS: (
        """
        Dieser Lauf betrifft den Normadressaten Buergerinnen und Buerger.

        Beruecksichtigen Sie ausschliesslich den Erfuellungsaufwand von Buergerinnen und
        Buergern. Analysieren Sie nur buergerbezogene Prozesse, Fallgruppen, Taetigkeiten,
        Fallzahlen und Werte. Uebernehmen Sie keine Verwaltungs- oder Unternehmenslogik,
        sofern diese nicht ausdruecklich als Spiegelwirkung oder unmittelbare Folge fuer
        Buergerinnen und Buerger begruendet sind. Fuer Buergerinnen und Buerger stehen
        Zeitaufwand und privater Sachaufwand im Vordergrund; eine generelle Monetarisierung
        des Zeitaufwands findet nicht statt. Achten Sie besonders auf alltagsnahe
        Pflichterfuellung, persoenliches Erscheinen, Beschaffung von Nachweisen oder Material,
        Einschaltung Dritter, Gebuehren, Porto- und Fahrtkosten sowie auf einmalige
        Einfuehrungsaufwaende im privaten Bereich. Beschreiben Sie niemals interne
        Verwaltungspruefungen, verwaltungsinterne Abstimmungen, Bearbeitungsschritte der
        Behoerde, Unternehmensorganisation oder fachliche Schritte Dritter als Taetigkeiten
        der Buergerinnen und Buerger. Wenn eine Handlung von einer Behoerde, einem
        Unternehmen oder einem Sachverstaendigen vorgenommen wird, gehoert fuer
        Buergerinnen und Buerger nur der eigene ausgeloeste Aufwand dazu, etwa Termin
        vereinbaren, Unterlagen vorbereiten, erscheinen, bezahlen, mitwirken oder beauftragen.
        """
    ),
}


PROMPT_IDS_WITH_NORM_ADDRESSEE_CLAUSE = {
    PromptId.PROCESS_COMPILATION,
    PromptId.CASE_GROUP_DEVELOPMENT,
    PromptId.PROCESS_STEP_ANALYSIS,
    PromptId.CASES_CALCULATION,
    PromptId.EFFORT_CALCULATION,
}


CITIZENS_PROMPT_RULES: Dict[str, str] = {
    PromptId.PROCESS_COMPILATION: (
        "Zusatz fuer Buergerinnen und Buerger bei der Prozessbildung: "
        "Bilden Sie Prozesse aus Sicht der privaten Lebensfuehrung. Ein Buergerprozess "
        "ist die praktisch wahrnehmbare Erfuellung einer gesetzlichen Pflicht, etwa "
        "Beantragen, Nachweisen, Melden, Bezahlen, Beschaffen, Vorlegen, Mitwirken "
        "bei Pruefungen oder persoenliches Erscheinen. Bilden Sie keine internen "
        "Behoerdenablaeufe als Buergerprozess. Wenn die Vorgabe fuer Buergerinnen und "
        "Buerger nur dazu fuehrt, Unterlagen zu beschaffen oder Daten zu uebermitteln, "
        "soll genau dieser Handlungskern den Prozess bestimmen. Geben Sie nur solche "
        "Prozesse aus, die Buergerinnen und Buerger tatsaechlich selbst wahrnehmen. "
        "Erfinden Sie keine Sammelprozesse, die mehrere voneinander unabhaengige "
        "Alltagshandlungen kuenstlich zusammenziehen."
    ),
    PromptId.CASE_GROUP_DEVELOPMENT: (
        "Zusatz fuer Buergerinnen und Buerger bei der Fallgruppenbildung: "
        "Typische buergerbezogene Fallgruppen koennen sich insbesondere unterscheiden "
        "nach erstmaliger Erfuellung versus wiederkehrender Erfuellung, digitalem "
        "Verfahren versus Postweg oder persoenlichem Erscheinen, einfacher Standardlage "
        "versus zusaetzlichem Nachweis- oder Beratungsbedarf, eigener Vornahme versus "
        "Beauftragung Dritter sowie nach einmaligem Einfuehrungsaufwand versus "
        "laufendem Aufwand. Bilden Sie solche Fallgruppen aber nur, wenn daraus "
        "wesentlich unterschiedliche Zeit- oder Sachaufwaende folgen. Bilden Sie keine "
        "Fallgruppen nur deshalb, weil unterschiedliche Behoerden oder Drittstellen "
        "beteiligt sind, sofern sich der buergerseitige Aufwand dadurch nicht merklich "
        "aendert. Verwenden Sie moeglichst wenige, fachlich trennscharfe Fallgruppen."
    ),
    PromptId.PROCESS_STEP_ANALYSIS: (
        "Zusatz fuer Buergerinnen und Buerger bei der Schrittanalyse: "
        "Orientieren Sie die Taetigkeiten moeglichst eng an der buergerbezogenen "
        "Checkliste: sich mit der Vorgabe vertraut machen, Beratung in Anspruch nehmen, "
        "Daten und Informationen sammeln, Informationen aufbereiten, Formulare "
        "ausfuellen, Schriftstuecke aufsetzen, Daten uebermitteln, bezahlen, "
        "Unterlagen abspeichern, bei Pruefungen mitwirken, Material beschaffen, "
        "Leistung selbst erbringen oder Dritte beauftragen, Umsetzung pruefen und "
        "Wegezeiten. Waehlen Sie nur die fuer den Vorher-Nachher-Vergleich wirklich "
        "erforderlichen Hauptschritte. Wenn der Gesamtzeitaufwand fuer eine einfache "
        "Pflichterfuellung belastbar direkt schaetzbar ist, darf die Fallgruppe auch "
        "nur eine einzige zusammenfassende Taetigkeit enthalten. Jede ausgegebene "
        "Taetigkeit muss eine Handlung der Buergerinnen und Buerger selbst sein. "
        "Unzulaessig sind insbesondere verwaltungsinterne Pruefungen, Bescheiderstellung, "
        "interne Ruecksprachen oder Unternehmensablaeufe. Geben Sie nur die minimale, "
        "aber vollstaendige Menge an buergerseitigen Hauptschritten aus."
    ),
    PromptId.CASES_CALCULATION: (
        "Zusatz fuer Buergerinnen und Buerger bei der Fallzahlermittlung: "
        "Bei periodisch zu erfuellenden privaten Pflichten ergibt sich die Fallzahl "
        "grundsaetzlich aus der Multiplikation von Betroffenen und Haeufigkeit pro Jahr. "
        "Bei anlassbezogenen Pflichten ist die jaehrlich zu erwartende Zahl der Faelle "
        "zugrunde zu legen. Einmaliger Erfuellungsaufwand im privaten Bereich ist "
        "gesondert auszuweisen und nicht mit laufenden jaehrlichen Faellen zu "
        "vermischen. Beruecksichtigen Sie plausible Sowieso-Anteile, wenn ein Teil der "
        "Betroffenen die Handlung auch ohne die Gesetzesaenderung vorgenommen haette. "
        "Veraendern Sie Fallzahlen nicht kuenstlich, wenn sich tatsaechlich nur der "
        "Zeit- oder Sachaufwand pro Fall aendert."
    ),
}


EFFORT_METHOD_GUIDANCE: Dict[str, str] = {
    ADMINISTRATION: (
        "Eine Reihe von Taetigkeiten laeuft bei Nutzung entsprechender "
        "Informationstechnologie automatisch ab. Aus automatisch ablaufenden Prozessen "
        "resultiert zunaechst kein Zeitaufwand. Sofern keine spezifischen Daten ueber "
        "den Zeitaufwand vorliegen, kann die Zeitwerttabelle Verwaltung herangezogen "
        "werden. Zudem kann die Tabelle zu Wegezeiten und -sachkosten genutzt werden, "
        "wenn persoenliche Termine bei anderen Stellen oder Behoerden erforderlich sind. "
        "Zur Ermittlung des Personalaufwands werden die Bearbeitungszeiten mit den "
        "laufbahnspezifischen Lohnsaetzen der Verwaltung verknuepft. Die festen "
        "Lohngruppen sind A=Einfacher und mittlerer Dienst, B=Gehobener Dienst, "
        "C=Hoeherer Dienst, D=Durchschnitt. Ordnen Sie jede benoetigte "
        "Bearbeitungsstufe genau einer dieser Gruppen zu. Eine einzige Lohngruppe ist "
        "der Regelfall; mehrere Lohngruppen sind nur bei klar getrennten "
        "Bearbeitungsstufen zulaessig, etwa Bearbeitung und anschliessende Freigabe. "
        "Vermeiden Sie schematische Mehrfachbefuellung. Wenn der zu erfuellende Prozess "
        "nicht in Einzeltätigkeiten zerlegt wurde, koennen gesicherte Erfahrungswerte "
        "in Personentagen oder Personenmonaten genutzt und anschliessend umgerechnet "
        "werden. Fuer die Beschaeftigten im oeffentlichen Dienst gelten bei einer "
        "40-Stunden-Woche als Richtwerte 1 Personentag = 8 Stunden, 1 Personenmonat = "
        "134 Stunden und 1 Personenjahr = 200 Arbeitstage."
    ),
    BUSINESS: (
        "Eine Reihe von Taetigkeiten laeuft bei Nutzung entsprechender "
        "Informationstechnologie automatisch ab. Aus automatisch ablaufenden Prozessen "
        "resultiert zunaechst kein Zeitaufwand. Sofern keine spezifischen Daten ueber "
        "den Zeitaufwand vorliegen, kann die Zeitwerttabelle Wirtschaft herangezogen "
        "werden. Die Tabelle zu Wegezeiten und -sachkosten kann genutzt werden, wenn "
        "persoenliche Termine bei anderen Stellen oder Behoerden erforderlich sind. "
        "Zur Ermittlung des Personalaufwands werden die Bearbeitungszeiten mit den "
        "einschlaegigen Lohnsaetzen der Wirtschaft verknuepft. Die festen Lohngruppen "
        "sind A=Niedrig, B=Mittel, C=Hoch, D=Durchschnitt. Ordnen Sie jede benoetigte "
        "Bearbeitungsstufe genau einer dieser Gruppen zu. Eine einzige Lohngruppe ist "
        "der Regelfall; mehrere Lohngruppen sind nur bei klar getrennten "
        "Bearbeitungsstufen zulaessig, etwa operative Bearbeitung und anschliessende "
        "Freigabe. Vermeiden Sie schematische Mehrfachbefuellung. Buerokratiekosten der "
        "Wirtschaft sind spaeter getrennt auszuweisen. Ersatzinvestitionen sind nur zur "
        "Haelfte als Erfuellungsaufwand anzusetzen, soweit kein anderer Anteil fachlich "
        "begruendet ist."
    ),
    CITIZENS: (
        "Eine Reihe von Taetigkeiten laeuft bei Nutzung entsprechender "
        "Informationstechnologie automatisch ab. Aus automatisch ablaufenden Prozessen "
        "resultiert zunaechst kein Zeitaufwand. Ermitteln Sie fuer jede Taetigkeit "
        "ausschliesslich den Zeitaufwand in Minuten sowie den Sachaufwand in Euro. "
        "Monetarisieren Sie den Zeitaufwand nicht. Verwenden Sie keine Rollen, keine "
        "Lohngruppen und keine Stundenloehne. Orientieren Sie sich bei Zeitwerten an "
        "der Zeitwerttabelle fuer Buergerinnen und Buerger und pruefen Sie deren "
        "Plausibilitaet fuer den konkreten Fall. Die Tabelle zu Wegezeiten und "
        "-sachkosten kann genutzt werden, wenn persoenliches Erscheinen erforderlich "
        "ist. Sachaufwand umfasst insbesondere Gebuehren, Anschaffungen, Porto- und "
        "Fahrtkosten, Materialkosten sowie zwingend ausgeloeste Kosten fuer Dritte wie "
        "Notare oder Sachverstaendige. Geben Sie den Zeit- und Sachaufwand jeweils fuer "
        "gueltige und vorgeschlagene Rechtslage getrennt an. Wenn fuer eine Taetigkeit "
        "kein Sachaufwand anfaellt, verwenden Sie 0. Wenn fuer eine Taetigkeit kein "
        "Zeitaufwand anfaellt, verwenden Sie 0. Erfinden Sie keine verdeckten "
        "Verwaltungs- oder Unternehmenskosten als buergerseitigen Sachaufwand. Weisen "
        "Sie Sachaufwand nur aus, wenn er fuer Buergerinnen und Buerger selbst "
        "unmittelbar anfaellt."
    ),
}


EFFORT_APPENDICES: Dict[str, str] = {
    ADMINISTRATION: (
        "Anhang Verwaltung:\n\n"
        "{Wegezeiten_Wegesachkosten}\n\n"
        "{Zeitwerttabelle_Verwaltung}\n\n"
        "{Lohnkostentabelle_Verwaltung}"
    ),
    BUSINESS: (
        "Anhang Wirtschaft:\n\n"
        "{Wegezeiten_Wegesachkosten}\n\n"
        "{Zeitwerttabelle_Wirtschaft}\n\n"
        "{Lohnkostentabelle_Wirtschaft}"
    ),
    CITIZENS: (
        "Anhang Buergerinnen und Buerger:\n\n"
        "{Wegezeiten_Wegesachkosten}\n\n"
        "{Zeitwerttabelle_Buerger}"
    ),
}


EFFORT_JSON_SCHEMA_DEFAULT = """
{{
"prozesse": [
    {{
    "prozess_id": "",
    "prozess_bezeichnung": "",
    "prozess_beschreibung": "",
    "aenderungsstatus": "",
    "vorgaben": [
        {{
            "vorgaben_id": "",
            "normzitat": "",
            "beschreibung": "",
            "aenderungsstatus": ""
        }}
    ],
    "fallgruppen": [
        {{
            "fallgruppen_id": "",
            "fallgruppe_bezeichnung": "",
            "fallgruppe_beschreibung": "",
            "aenderungsstatus": "",
            "taetigkeiten": [
                {{
                    "taetigkeiten_id": "",
                    "taetigkeit": "",
                    "beschreibung": "",
                    "aenderungsstatus": "",
                    "rollen_gueltig": [
                        {{
                            "rolle": "",
                            "lohngruppe": "A | B | C | D",
                            "schwierigkeitsgrad": "",
                            "stundenlohn": "",
                            "zeitaufwand_in_min": ""
                        }}
                    ],
                    "sachaufwand_gueltig": "",
                    "rollen_vorschlag": [
                        {{
                            "rolle": "",
                            "lohngruppe": "A | B | C | D",
                            "schwierigkeitsgrad": "",
                            "stundenlohn": "",
                            "zeitaufwand_in_min": ""
                        }}
                    ],
                    "sachaufwand_vorschlag": "",
                    "ausfuehrung_pro_einzelfall": "0 | 1"
                }}
            ]
        }}
    ]
    }}
]
}}
"""


EFFORT_JSON_SCHEMA_BY_ADDRESSEE: Dict[str, str] = {
    CITIZENS: """
{{
"prozesse": [
    {{
    "prozess_id": "",
    "prozess_bezeichnung": "",
    "prozess_beschreibung": "",
    "aenderungsstatus": "",
    "vorgaben": [
        {{
            "vorgaben_id": "",
            "normzitat": "",
            "beschreibung": "",
            "aenderungsstatus": ""
        }}
    ],
    "fallgruppen": [
        {{
            "fallgruppen_id": "",
            "fallgruppe_bezeichnung": "",
            "fallgruppe_beschreibung": "",
            "aenderungsstatus": "",
            "taetigkeiten": [
                {{
                    "taetigkeiten_id": "",
                    "taetigkeit": "",
                    "beschreibung": "",
                    "aenderungsstatus": "",
                    "zeitaufwand_in_min_gueltig": "",
                    "sachaufwand_gueltig": "",
                    "zeitaufwand_in_min_vorschlag": "",
                    "sachaufwand_vorschlag": "",
                    "ausfuehrung_pro_einzelfall": "0 | 1"
                }}
            ]
        }}
    ]
    }}
]
}}
"""
}


PROMPT_TEMPLATES: Dict[str, str] = {
    # Input contract:
    # - gesetz_gueltig: str
    # - gesetz_vorschlag: str
    PromptId.LAW_SUMMARY: (
        """
        Sie sind Legist im deutschen Bundestag. 

        Vergleichen Sie den derzeit gueltigen Gesetzestext mit dem vorgeschlagenen 
        Gesetzesvorschlag. Leiten Sie daraus ab, was der Gesetzgeber erreichen möchte. 
        Geben Sie strikt JSON zurueck im Format: {{\"title\": \"...\", \"blurb\": \"...\", \"summary\": \"...\"}}.

        Der 'title' soll ein kurzer Titel sein (max. 12 Wörter), der 'blurb' soll genau ein Satz sein. Für die 'summary' geben Sie bitte eine 
        ausführliche Zusammenfassung an, mit Hilfe derer man die Ziele und wesentlichen Unterschiede der Gesetzesänderung verstehen kann ohne 
        die zwei Gesetzestexte vorliegen zu haben.

        Geltendes Gesetz: {gesetz_gueltig}

        Gesetzesvorschlag: {gesetz_vorschlag}
        """
    ),
    # Input contract:
    # - gesetz_gueltig: str
    # - gesetz_vorschlag: str
    PromptId.REGULATIONS_IDENTIFICATION: (
        LEGIST_PROMPT_OPENING
        + """ 
        Folgendes ist das konsolidierte, geltende Gesetz: {gesetz_gueltig}

        Folgendes konsolidiertes Gesetz wird vorgeschlagen: {gesetz_vorschlag}

        Ihre Aufgabe ist, ausgehend von den konsolidierten Versionen die Gesetzesänderungen herauszuarbeiten und alle darin enthaltenen Vorgaben 
        (Einzelregelungen) im nachfolgenden Sinne zu identifizieren. 
        Wichtig: Jede Gesetzesänderung kann keine, eine oder mehrere Vorgaben enthalten. Identifizieren Sie alle relevanten Vorgaben und geben Sie den Status an, 
        also ob es sich um entweder eine Einführung, eine Änderung, oder eine Streichung/Löschung handelt.
        Berücksichtigen Sie dabei auch implizite Änderungen von Vorgaben, bei denen bisher Betroffene wegfallen, weil sie künftig stattdessen einem neuen
        Prozess unterliegen; solche Fälle sind ebenfalls als eigene relevante Vorgaben mit passendem Änderungsstatus auszuweisen.

        Bestimmen Sie fuer jede Vorgabe ausserdem:
        * welche Normadressaten betroffen sind: administration, business, citizens,
        * ob es sich um eine Informationspflicht der Wirtschaft handelt,
        * ob eine Spiegelsituation vorliegt, also ob die Befolgung der Vorgabe unmittelbar Aufwand bei einem anderen Normadressaten ausloest,
        * und falls ja, fuer welche weiteren Normadressaten diese Spiegelwirkung auftritt.

        Wenn eine Spiegelsituation vorliegt, vergeben Sie zusaetzlich einen kurzen,
        stabilen `mirror_anchor_key`, der den gemeinsamen zugrunde liegenden
        Lebenssachverhalt beschreibt. Verwenden Sie dafuer eine kurze,
        kleingeschriebene, bindestrichgetrennte Kennung, zum Beispiel
        `antrag-gemeinnuetzigkeit` oder `nachweis-vorlage`.

        Zum Normadressaten Verwaltung zählen alle mit der Wahrnehmung von Verwaltungsaufgaben betrauten Verwaltungsträger (rechtsfähige Körperschaften, Anstalten und Stiftungen 
        des öffentlichen Rechts einschließlich Beliehene im Rahmen der ihnen übertragenen hoheitlichen Kompetenzen). Soweit Körperschaften/Anstalten des 
        öffentlichen Rechts privatwirtschaftlich tätig sind und in Wettbewerb stehen (z. B. kostenpflichtige Schulungen der Kammern; Universitäten bei 
        Forschungsförderungen) sind diese als Wirtschaft zu behandeln. Soweit Unternehmen hoheitliche Aufgaben wahrnehmen (z. B. Beliehene wie Prüfingenieure, 
        Bezirksschornsteinfegermeister, Tierärzte bei Fleischbeschau), sind diese als Verwaltung zu behandeln. Soweit öffentliche Unternehmen, die Aufgaben der 
        Daseinsvorsorge im staatlichen Auftrag erfüllen (z. B. Wasserkraftwerke in öffentlicher Hand) sind diese als Verwaltung zu behandeln. Die Rechtsform 
        bietet nur Anhaltspunkte; maßgeblich ist die vorgeschriebene Tätigkeit.

        Der Normadressat Wirtschaft umfasst alle Akteure, die eine wirtschaftliche Tätigkeit am Markt ausüben, wobei die Rechtsform oder eine Gewinnerzielungsabsicht
        nicht ausschlaggebend sind. Hierzu zählen primär private Unternehmen jeder Größe (einschließlich KMU), Selbstständige sowie Freiberufler. Zur Wirtschaft gehören
        im Sinne des Erfüllungsaufwands auch gemeinnützige Organisationen wie Vereine, Verbände oder Stiftungen, sofern sie als Arbeitgeber agieren oder Dienstleistungen
        im Wettbewerb anbieten. In Abgrenzung zur Verwaltung sind zudem öffentliche Institutionen (wie Universitäten oder Kammern) der Wirtschaft zuzurechnen,
        wenn sie privatwirtschaftlich tätig werden und in Konkurrenz zu privaten Anbietern treten.

        Der Normadressat Bürgerinnen und Bürger definiert sich durch natürliche Personen, die von einer gesetzlichen Regelung in ihrer Rolle als Privatperson betroffen sind.
        Der Aufwand wird dieser Gruppe immer dann zugeordnet, wenn die Tätigkeit der privaten Lebensführung dient und nicht im Rahmen einer beruflichen, gewerblichen
        oder hoheitlichen Aufgabe erfolgt. Ein typisches Beispiel ist die Erfüllung von Verhaltenspflichten im Alltag, wie etwa die Einhaltung der M+S-Reifenpflicht
        bei privaten Kraftfahrzeugen. Im Gegensatz zur Wirtschaft und Verwaltung wird bei den Bürgerinnen und Bürgern primär der Zeitaufwand für Tätigkeiten
        (z. B. Informationsbeschaffung oder das Ausfüllen von Formularen) sowie der private Sachaufwand ermittelt, ohne dass eine generelle Monetarisierung der Zeit erfolgt.

        Definition von Vorgaben:
        * Vorgaben sind Einzelregelungen, die unmittelbar zu Änderungen von Kosten oder Zeitaufwand bei den Normadressaten führen.
        * Sie beruhen auf bundesrechtlichen Regelungen und verpflichten Normadressaten, bestimmte Ziele zu erreichen, Vorgaben einzuhalten oder Handlungen 
          vorzunehmen bzw. zu unterlassen.
        * Dazu zählen auch Verpflichtungen zur Kooperation mit Dritten sowie zur Überwachung und Kontrolle von Zuständen, Handlungen, numerischen Werten oder 
          Verhaltensweisen. Informationspflichten bilden eine Teilmenge der Vorgaben.

        "Unmittelbar" bedeutet, dass der Kosten- oder Zeitaufwand direkt aus der Befolgung der Vorgabe entsteht. Normadressaten müssen die Vorgaben einhalten, 
        um Rechtsverstöße oder den Verlust von Ansprüchen zu vermeiden. Auch Regelungen, die nur Ziele, Grenzwerte oder förderbedingte Verhaltensänderungen 
        vorgeben, gelten als Vorgaben, wenn sie direkt Aufwand auslösen.

        Bei der Identifizierung von Vorgaben ist zu beachten, dass der Gesetzgeber zum Teil neben  Ge- oder Verboten lediglich Ziele oder Grenzwerte festlegt 
        oder zum Beispiel durch staatliche Förderungen Verhaltensänderungen erreichen will. Auch solche Einzelregelungen sind  als Vorgaben zu verstehen, weil 
        sie unmittelbar zur Änderung von Kosten bzw. Zeitaufwand  bei den Normadressaten führen.

        Geben Sie nur und ausschließlich JSON im folgenden Format zurück: 

        {{
          "vorgaben": [
            {{
              "normzitat": "",
              "beschreibung": "",
              "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft",
              "normadressaten": ["administration | business | citizens"],
              "ist_informationspflicht_wirtschaft": "0 | 1",
              "spiegelsituation": {{
                "liegt_vor": "0 | 1",
                "normadressaten": ["administration | business | citizens"],
                "beschreibung": "",
                "mirror_anchor_key": ""
              }}
            }}
          ]
        }}

        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen.
        """
    ),
    # Input contract:
    # - gesetz_gueltig: str
    # - gesetz_vorschlag: str
    # - vorgaben_json: JSON string of list[VorgabePayload]
    PromptId.PROCESS_COMPILATION: (
        LEGIST_PROMPT_OPENING
        + """
        Die Gesetzesänderung führt zu folgenden Einzelvorgaben für den betroffenen Normadressaten: {vorgaben_json}
        {mirror_process_context}

        Ihre Aufgabe ist, die enthaltenen Vorgaben (Einzelregelungen), welche in der Praxis in einem Zusammenhang erfüllt werden, zu gemeinsamen 
        Prozessen zu bündeln. Soweit eine Bündelung von Vorgaben in Prozesse nicht möglich oder sinnvoll ist, ist die betreffende Einzelvorgabe identisch 
        einem eigenen Prozess zu behandeln. Ein solcher Prozess besteht daher ausschließlich aus einer Vorgabe. Geben Sie außerdem den Status an, 
        also ob es sich um entweder eine Einführung, eine Änderung, oder eine Streichung/Löschung des Prozesses handelt. Orientieren Sie sich dazu an den 
        Statusangaben der Vorgaben.

        Wenn Vorgaben als Spiegelsituation gekennzeichnet sind, beziehen sie sich auf denselben zugrunde liegenden Lebenssachverhalt wie beim anderen
        Normadressaten. Bilden Sie solche Vorgaben daher nicht als fachlich losgelöste Sonderprozesse, sondern strukturieren Sie sie so, dass die
        Spiegelbeziehung nachvollziehbar bleibt. Unterschiede zwischen Normadressaten sollen sich aus der jeweiligen Perspektive und den jeweiligen
        Tätigkeiten ergeben, nicht aus einer widersprüchlichen Beschreibung des zugrunde liegenden Fallgeschehens.

        Wenn zusaetzlicher strukturierter Spiegelkontext mit bereits bekannten Zuordnungen oder Gegenstrukturen vorliegt, behandeln Sie diesen als
        verbindlichen fachlichen Konsistenzrahmen. Passen Sie Ihre Prozessbildung daran an, statt parallele konkurrierende Spiegelstrukturen zu erzeugen.

        Offizielles Methodenbeispiel aus dem Leitfaden (woertlich uebernommen):
        {handbook_process_example}

        Geben Sie nur und ausschließlich JSON im folgenden Format zurück: 

        {{
        "prozesse": [
            {{
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft",
            "vorgaben": [
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                }}
            ]
            }},
            {{
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft",
            "vorgaben": [
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                }},
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                }}
            ]
            }}
        ]
        }}

        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 
        """
    ),
    # Input contract:
    # - gesetz_gueltig: str
    # - gesetz_vorschlag: str
    # - prozesse_json: JSON string of list[ProzessWithVorgabenPayload]
    PromptId.CASE_GROUP_DEVELOPMENT: (
        LEGIST_PROMPT_OPENING
        + """
        Die Gesetzesänderung führt zu folgenden, Erfüllungsaufwand auslösenden Prozessen für den betroffenen Normadressaten: {prozesse_json}
        {mirror_case_group_context}

        Wenn damit zu rechnen ist, dass der betroffene Normadressat die jeweiligen Prozesse auf unterschiedlichen Wegen erfüllt, sind dafür sogenannte Fallgruppen zu bilden. 
        Dies jedoch nur, soweit durch die verschiedenen Wege wesentliche Unterschiede zu erwarten sind. Für jede Fallgruppe ist der Erfüllungsaufwand separat zu 
        ermitteln und darzustellen. Dabei ist es unerheblich, ob die Differenzierung erfolgt, weil unterschiedliche Gestaltungsmöglichkeiten genutzt werden 
        oder weil sich die zugrunde liegenden Sachverhalte unterscheiden. Geben Sie außerdem den Status an, also ob es sich um entweder eine Einführung, 
        eine Änderung, oder eine Streichung/Löschung der Fallgruppe handelt.

        Bei Spiegelsituationen ist auf strukturelle Konsistenz mit dem anderen Normadressaten zu achten: Wenn auf beiden Seiten derselbe zugrunde liegende
        Fall betrachtet wird, sollen die Fallgruppen logisch zueinander passen. Unterschiede sind nur dort auszuweisen, wo sie sich aus unterschiedlichen
        Verfahrenswegen, unterschiedlichen Betroffenheiten oder unterschiedlichen Rollen des jeweiligen Normadressaten ergeben. Erfinden Sie keine
        voneinander losgeloesten Fallgruppen fuer denselben Spiegel-Sachverhalt.

        Wenn strukturierter Spiegelkontext mit bereits bekannten Gegenstrukturen oder Matches vorliegt, nutzen Sie diesen als bindenden Abgleichsrahmen.
        Erfinden Sie keine abweichenden Fallgruppen, wenn der gemeinsame Spiegel-Sachverhalt dort bereits hinreichend konkretisiert ist.

        Soweit eine Bildung von Fallgruppen aus dem jeweiligen Prozess nicht möglich oder sinnvoll ist, hat der betreffende Prozess nur eine einzige Fallgruppe. 
        Ein solcher Prozess besteht daher ausschließlich aus einer Fallgruppe.

        Offizielles Methodenbeispiel aus dem Leitfaden (woertlich uebernommen):
        {handbook_case_group_example}

        Geben Sie nur und ausschließlich JSON im folgenden Format zurück: 

        {{
        "prozesse": [
            {{
            "prozess_id": "",
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "aenderungsstatus": "",
            "vorgaben": [
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                }}
            ], 
            "fallgruppen": [
                {{
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft"
                }},
                {{
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft"
                }}
            ]
            }},
            {{
            "prozess_id": "",
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "aenderungsstatus": "",
            "vorgaben": [
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                }},
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                }}
            ], 
            "fallgruppen": [
                {{
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft"
                }}
            ]
            }}
        ]
        }}
        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 
        """
    ),
    PromptId.MIRROR_MATCHING: (
        LEGIST_PROMPT_OPENING
        + """
        Fuer die folgende Gesetzesaenderung liegen bereits Prozesse und Fallgruppen
        mehrerer Normadressaten vor, die ueber Spiegelsituationen miteinander
        verknuepft sein koennen: {mirror_clusters_json}

        Ihre Aufgabe ist zweistufig:
        1. Analysieren Sie pro Spiegelanker zuerst den gemeinsamen realen Sachverhalt.
        2. Ordnen Sie danach nur bereits vorhandene Strukturen ueber diesen
           gemeinsamen Sachverhalt hinweg zu.

        Ihre Aufgabe ist nicht, neue Prozesse oder Fallgruppen zu erzeugen.
        Formulieren Sie fuer jeden Spiegelanker zuerst kurz die
        `shared_situation`. Diese beschreibt in einem Satz, was der gemeinsame
        reale Kernfall ueber alle Normadressaten hinweg ist.

        Ordnen Sie anschliessend nur solche Fallgruppen einander zu, die diesen
        gemeinsamen Kernfall beschreiben. Unterschiede in Perspektive und
        Benennung sind zulaessig. Unzulaessig ist eine Zuordnung, wenn die
        Fallgruppen fachlich verschiedene Sachverhalte betreffen.

        Entscheiden Sie fuer jede Zuordnung ausserdem gesondert:
        - ob die Zahl der Betroffenen synchronisiert werden soll
        - ob die Haeufigkeit synchronisiert werden soll
        - ob die gesamte Fallzahl direkt synchronisiert werden soll

        Verwenden Sie diese Felder streng fachlich:
        - `sync_addressees = 1`, wenn dieselbe Menge Betroffener auf beiden Seiten zugrunde liegt
        - `sync_frequency = 1`, wenn dieselbe Haeufigkeit pro Jahr zugrunde liegt
        - `sync_cases = 1`, wenn die resultierende Fallzahl als Ganzes direkt uebernommen werden soll

        Beziehen Sie bei der Analyse alle vorliegenden Informationen gemeinsam
        ein: Vorgaben, Spiegelbeschreibung, Prozessbeschreibungen,
        Fallgruppenbeschreibungen und eventuell bereits bekannte Fallzahlen.

        Geben Sie nur solche Zuordnungen aus, die fachlich belastbar sind. Wenn
        keine verlaessliche Zuordnung moeglich ist, lassen Sie die betreffende
        Fallgruppe ungemappt.

        Verwenden Sie fuer `relation_type` nur:
        - `one_to_one`
        - `one_to_many`
        - `many_to_one`
        - `loosely_coupled`

        Geben Sie nur und ausschliesslich JSON im folgenden Format zurueck:

        {{
          "analyses": [
            {{
              "mirror_anchor_key": "",
              "shared_situation": "",
              "matches": [
                {{
                  "source_norm_addressee": "administration | business | citizens",
                  "target_norm_addressee": "administration | business | citizens",
                  "source_process_id": "",
                  "target_process_id": "",
                  "source_case_group_id": "",
                  "target_case_group_id": "",
                  "relation_type": "one_to_one | one_to_many | many_to_one | loosely_coupled",
                  "sync_addressees": "0 | 1",
                  "sync_frequency": "0 | 1",
                  "sync_cases": "0 | 1",
                  "reason": ""
                }}
              ]
            }}
          ]
        }}

        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen.
        """
    ),
    # TODO: ausfuehrung_pro_einzelfall bereits hier abfragen und nicht erst in effort_calculation??
    # Input contract:
    # - gesetz_gueltig: str
    # - gesetz_vorschlag: str
    # - case_groups_json: JSON string of list[ProzessWithFallgruppenPayload]
    PromptId.PROCESS_STEP_ANALYSIS: (
        LEGIST_PROMPT_OPENING
        + """
        Die Gesetzesänderung führt zu folgenden, positiven oder negativen Erfüllungsaufwand auslösenden Prozessen für den betroffenen Normadressaten, welche durch folgende 
        Fallgruppen differenziert werden: {case_groups_json}
        {mirror_step_context}

        Ihre Aufgabe ist es, die wesentlichen anfallenden Tätigkeiten zur Erfüllung eines Prozesses pro Fallgruppe 
        zu identifizieren. Auf dieser Grundlage werden später der anfallende Personal- und ggf. Sachaufwand bestimmt. Die einzelnen Tätigkeiten können vor und nach
        der Gesetzesänderung unterschiedlich sein, hinzukommen oder wegfallen, einige Tätigkeiten des Prozess können beibehalten bleiben. Geben Sie diesen 
        Änderungsstatus an, orientieren Sie sich dabei wenn nötig an den vorhandenen Statusangaben in den Fallgruppen und Prozessen.

        Entscheidend ist die Aenderung des Erfuellungsaufwands, nicht die abstrakte Vollbeschreibung des gesamten Verfahrens. Beschreiben Sie daher nur solche
        Taetigkeiten, die fuer die Ermittlung des Unterschieds zwischen geltender Rechtslage und Vorschlag erforderlich sind. Uebernehmen Sie unveraenderte
        Standardschritte nur dann, wenn sie fuer den Vorher-Nachher-Vergleich wirklich benoetigt werden; erfinden Sie keine vollstaendige Verfahrenskette neu,
        wenn sich tatsaechlich nur einzelne Schritte aendern.

        Bei Spiegelsituationen sollen die Prozessschritte die Perspektive des betroffenen Normadressaten abbilden, aber dennoch denselben zugrunde liegenden
        Fall erkennbar spiegeln. Das bedeutet: unterschiedliche Schritte sind zulaessig, wenn sie sich aus der Rolle des Normadressaten ergeben; unzulaessig
        ist jedoch eine voellig andere, nicht mehr wiedererkennbare Struktur fuer denselben Spiegel-Sachverhalt.

        Wenn bereits strukturierte Spiegel-Matches oder Gegenstrukturen vorliegen, behandeln Sie diese als verbindliche Orientierung fuer die Zuordnung der
        Taetigkeiten zu demselben gemeinsamen Fall. Erfinden Sie keine fachlich abweichende Schrittlogik fuer bereits gematchte Spiegel-Fallgruppen.

        Als Hilfsmittel für die Identifizierung der zu erwartenden Tätigkeiten kann die nachfolgende Checkliste mit möglichen Tätigkeiten zur Erfüllung 
        von Vorgaben oder Prozessen herangezogen werden. Es kann sich in einzelnen Fällen anbieten, die Checkliste um spezielle Tätigkeiten zu erweitern.

        Orientieren Sie die Bildung der Tätigkeiten eng an dieser Checkliste, damit die Prozessschritte zwischen verschiedenen Regelungsvorhaben nachvollziehbar
        und vergleichbar bleiben. Bilden Sie keine künstlich kleinteiligen Einzelschritte, sondern wenige, in sich sinnvolle Hauptschritte. Im Regelfall sollten
        pro Fallgruppe etwa drei bis fünf Tätigkeiten ausreichen; nur wenn der Sachverhalt es fachlich wirklich erfordert, sollten es ausnahmsweise sechs sein.
        Fassen Sie eng zusammenhängende Unterhandlungen zu einem gemeinsamen Prozessschritt zusammen, statt sie separat auszuweisen.

        Checkliste:
        • Mit der Vorgabe vertraut machen 
        • Beratung, Führen von Vorgesprächen mit Antragstellerinnen und Antragstellern 
        • Formelle Prüfung, Daten und Informationen sichten und zusammenstellen, Vollständigkeitsprüfung 
        • Eingangsbestätigung oder fehlende Daten/Informationen einholen 
        • Inhaltliche Prüfung, Berechnungen und Bewertungen durchführen 
        • Interne oder externe Besprechungen (z. B. Anhörungen) 
        • Formulare ausfüllen bzw. vervollständigen, Daten erfassen, Kennzeichnungen vornehmen 
        • Ergebnisse/Berechnungen prüfen und ggf. korrigieren 
        • Datenübermittlung und Veröffentlichung 
        • Zahlungen anweisen 
        • Korrektur (z. B. aufgrund von Beteiligungsverfahren) bzw. weitere Informationen bei Rückfragen vorlegen 
        • Informationen abschließend aufbereiten 
        • Bescheid erstellen 
        • Kopieren, verteilen, archivieren, dokumentieren 
        • Überwachungs- und Aufsichtsmaßnahmen, Risikoklassifizierung 
        • Beschaffen von Waren, Dienstleistungen und/oder zusätzlichem Personal 
        • Anpassen von internen Prozessabläufen 
        • Teilnahme an Fortbildungen und Schulungen 
        • Wege zu anderen Behörden, Organisationen oder Unternehmen 

        In der Praxis sind selten alle oben aufgeführten Tätigkeiten relevant. In der Bestandsmessung der Bürokratiekosten der Wirtschaft hatte sich z. B. 
        gezeigt, dass bei den meisten Informationspflichten lediglich vier bis sechs Tätigkeiten anfallen. Auch hier gilt: lieber eine kleine Zahl klar
        abgegrenzter und gut begründbarer Hauptschritte als eine lange Liste kleinteiliger Einzeltätigkeiten.
        
        Bei Daueraufgaben oder wenn gesicherte Erfahrungswerte (z. B. aus Organisationsuntersuchungen, Vergleichsringen etc.) vorliegen, kann es zweckmäßig 
        sein, den Zeitaufwand ohne vorherige Zerlegung in Einzeltätigkeiten zu ermitteln, entsprechend wird lediglich eine Tätigkeit in dieser Fallgruppe 
        befüllt.
        
        Geben Sie nur und ausschließlich JSON im folgenden Format zurück: 
        
        {{
        "prozesse": [
            {{
            "prozess_id": "",
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "aenderungsstatus": "",
            "vorgaben": [
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                }}
            ],
            "fallgruppen": [
                {{
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "",
                    "taetigkeiten": [ 
                        {{
                            "taetigkeit": "",
                            "beschreibung": "",
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert"
                        }},
                        {{
                            "taetigkeit": "",
                            "beschreibung": "",
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert"
                        }}
                    ]
                }},
                {{
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "",
                    "taetigkeiten": [ 
                        {{
                            "taetigkeit": "",
                            "beschreibung": "",
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert"
                        }}
                    ]
                }}
            ]
            }},
            {{
            "prozess_id": "",
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "aenderungsstatus": "",
            "vorgaben": [
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                }},
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                }}
            ],
            "fallgruppen": [
                {{
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "",
                    "taetigkeiten": [ 
                        {{
                            "taetigkeit": "",
                            "beschreibung": "",
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert"
                        }},
                        {{
                            "taetigkeit": "",
                            "beschreibung": "",
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert"
                        }}
                    ]
                }}
            ]
            }}
        ]
        }}
        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 

        """
    ),
    # Input contract:
    # - gesetz_gueltig: str
    # - gesetz_vorschlag: str
    # - case_groups_json: JSON string of list[ProzessWithFallgruppenPayload]
    PromptId.CASES_CALCULATION: (
        LEGIST_PROMPT_OPENING
        + """
        Die Gesetzesänderung führt zu folgenden, Erfüllungsaufwand auslösenden Prozessen für den betroffenen Normadressaten, welche durch folgende Fallgruppen 
        differenziert werden: {case_groups_json}
        {mirror_case_context}

        Ihre Aufgabe ist es, die Änderung der Fallzahlen jeder dieser Fallgruppen zu bestimmen. Hierzu werden die Häufigkeit und die Anzahl der Betroffenen 
        vor (_gueltig) und nach (_vorschlag) der geplanten Gesetzesänderung betrachtet. Bei der Einführung einer Fallgruppe werden typischerweise nur die 
        _vorschlag-Werte angegeben, bei der Löschung nur die _gueltig-Werte und bei einer Änderung beide.

        Massgeblich ist auch hier die Aenderung des Erfuellungsaufwands. Schaetzen Sie deshalb nicht losgeloest einen abstrakten Gesamtbestand an Faellen,
        sondern die fuer die geltende und die vorgeschlagene Rechtslage jeweils sachgerechte Fallzahl derselben Fallgruppe. Wenn sich die Fallzahl durch die
        Gesetzesaenderung nicht aendert, sind identische Werte fuer _gueltig und _vorschlag plausibel. Wenn sich nur der Aufwand pro Fall aendert, duerfen
        die Fallzahlen nicht kuenstlich mitveraendert werden.

        Bei Spiegelsituationen gilt: Wenn aus einem anderen Normadressaten bereits spiegelnde Fallzahlen vorliegen und der zugrunde liegende Sachverhalt
        logisch 1:1 gekoppelt ist, sind dieselben Mengen zu übernehmen statt sie erneut unabhängig zu schätzen. Beispiel: Wenn 500 neue Vereine gegründet
        werden und deshalb 500 Anträge bei der Verwaltung zu bearbeiten sind, muss dieselbe Fallzahl auf beiden Seiten zugrunde gelegt werden; unterschiedlich
        sind dann nur die Tätigkeiten und Kosten, nicht die Zahl der Fälle.

        Wenn strukturierte Spiegel-Matches mit `sync_cases = 1`, `sync_addressees = 1` oder `sync_frequency = 1` vorliegen, befolgen Sie diese Vorgaben
        vorrangig. Solche Matches sind als autoritative Synchronisierungshinweise zu behandeln und nicht erneut frei zu ueberschreiben.

        Offizielles Methodenbeispiel aus dem Leitfaden (woertlich uebernommen):
        {handbook_cases_frequency_example}

        Offizielles Fallzahlbeispiel aus dem Leitfaden (woertlich uebernommen):
        {handbook_cases_case_example}

        Allgemein gilt: Bei periodisch zu erfüllenden Vorgaben oder Prozessen ergibt sich die Fallzahl aus der Multiplikation der Häufigkeit mit der Anzahl 
        der Betroffenen. Die Häufigkeit gibt an, wie oft pro Jahr eine Vorgabe oder ein Prozess erledigt wird bzw. wie häufig der damit einhergehende 
        Aufwand entsteht. Bei Vorgaben oder Prozessen, die aufgrund der Bearbeitung von Anträgen anlassbezogen erfüllt werden, sollte die Zahl der 
        jährlich zu erwartenden Anträge als Fallzahl zugrunde gelegt werden. Bei Schwankungen ist ein sachgerechter Mittelwert zu verwenden. Die Fallzahl 
        für Überwachungs- und Kontrollmaßnahmen ist in der Regel wesentlich geringer.
        Aufwand, der aufgrund der Anpassung an das neue Regelungsvorhaben nur einmal innerhalb einer Organisationseinheit des betroffenen Normadressaten anfällt, wird als 
        einmaliger Erfüllungsaufwand bzw. Umstellungsaufwannd bezeichnet und ist gesondert auszuweisen.

        Soweit bestehende Regelungen geändert werden, können Fallzahlen unter Umständen auch aus bereits vorliegenden Aufwandsschätzungen und 
        Gesetzesbegründungen oder der OnDEA-Datenbank des StBA (https://www.ondea.de/) übernommen werden. Bevor solche Angaben verwendet werden, sollten 
        sie ggf. aktualisiert werden.

        Geben Sie nur und ausschließlich JSON im folgenden Format zurück: 
        
        {{
        "prozesse": [
            {{
            "prozess_id": "",
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "aenderungsstatus": "",
            "vorgaben": [
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                }}
            ], 
            "fallgruppen": [
                {{
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "",
                    "anzahl_betroffene_gueltig": "",
                    "haeufigkeit_pro_jahr_gueltig": "",
                    "anzahl_betroffene_vorschlag": "",
                    "haeufigkeit_pro_jahr_vorschlag": ""
                }},
                {{
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "",
                    "anzahl_betroffene_gueltig": "",
                    "haeufigkeit_pro_jahr_gueltig": "",
                    "anzahl_betroffene_vorschlag": "",
                    "haeufigkeit_pro_jahr_vorschlag": ""
                }}
            ]
            }},
            {{
            "prozess_id": "",
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "aenderungsstatus": "",
            "vorgaben": [
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                }},
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                }}
            ], 
            "fallgruppen": [
                {{
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "",
                    "anzahl_betroffene_gueltig": "",
                    "haeufigkeit_pro_jahr_gueltig": "",
                    "anzahl_betroffene_vorschlag": "",
                    "haeufigkeit_pro_jahr_vorschlag": ""
                }}
            ]
            }}
        ]
        }}
        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 
        """
    ),
    # TODO: How to add this? Die Bereitstellung und Wartung von Informationstechnologie aufgrund der Änderung von 
    #                        Vorgaben kann jedoch zusätzlichen Sach- und Personalaufwand erzeugen.
    # Input contract:
    # - gesetz_gueltig: str
    # - gesetz_vorschlag: str
    # - step_analysis_json: JSON string of list[ProzessStepAnalysisPayload]
    PromptId.EFFORT_CALCULATION: (
        LEGIST_PROMPT_OPENING
        + """
        Die Gesetzesänderung führt zu folgenden, Erfüllungsaufwand auslösenden Prozessen für den betroffenen Normadressaten, welche durch folgende Fallgruppen und 
        Prozessschritte differenziert werden: {step_analysis_json}

        Ihre Aufgabe ist es, den anfallenden Personal- und ggf. Sachaufwand der anfallenden Tätigkeiten pro Einzelfall zu identifizieren. 
        Hierzu werden die Stundenlöhne, Zeit- und Sachaufwände vor (_gueltig) und nach (_vorschlag) der geplanten Gesetzesänderung betrachtet. Bei der Einführung
        eines Prozessschrittes werden typischerweise nur die _vorschlag-Werte angegeben, bei der Löschung nur die _gueltig-Werte und bei einer Änderung beide.

        Entscheidend ist die Aenderung des Erfuellungsaufwands je Fall. Schaetzen Sie daher nicht den gesamten denkbaren Bearbeitungsaufwand eines Verfahrens
        neu, sondern den fuer die geltende und die vorgeschlagene Rechtslage jeweils relevanten Aufwand derselben Taetigkeit. Wenn sich nur ein Teilaspekt
        aendert, darf nicht automatisch der gesamte Schritt neu und vollumfaenglich angesetzt werden. Unveraenderte Aufwaende sollten in _gueltig und
        _vorschlag gleich bleiben; nur geaenderte Mehr- oder Minderaufwaende sind abweichend auszuweisen.

        {effort_method_guidance}

        Unter Sachaufwand fällt der Betriebs-, Unterhaltungs- und Investitionsaufwand, der zur Erfüllung einer Vorgabe oder eines Prozesses zu erwarten ist. 
        Gemeinkosten zählen hingegen nicht zum Erfüllungsaufwand. Darüber hinaus notwendige Investitionsaufwendungen des betroffenen Normadressaten sollten bei der 
        Aufwandsermittlung ebenfalls konkret aufgeschlüsselt werden. Hierzu zählen beispielsweise: 
        • Aufwand für die Inanspruchnahme Dritter (z. B. Handwerkerleistungen), 
        • Aufwand für die Beschaffung von spezieller Informations- und Kommunikationstechnik, 
        • Aufwand für die Nachrüstung von Anlagen, 
        • Sachaufwand für Wege zu anderen Behörden oder Stellen (siehe Anhang 5: Wegezeiten und -sachkosten).

        Außerdem soll angegeben werden, ob die Tätigkeit pro Einzelfall (=1) oder lediglich einmal pro gesamte Fallgruppe (z.B. Einarbeitung in die Vorgabe) ausgeführt wird (=0).
        Waehlen Sie =0 immer dann, wenn es sich um einmaligen Umstellungs-, Einfuehrungs-, Abstimmungs- oder Einarbeitungsaufwand handelt, der nicht fuer jeden
        einzelnen Fall erneut anfaellt.

        {effort_appendix}

        Geben Sie nur und ausschließlich JSON im folgenden Format zurück: 

        {effort_json_schema}
        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 
        """
    )
}


def _resolve_session_id(kwargs: dict[str, Any]) -> int | None:
    raw_session_id = kwargs.get("session_id")
    if raw_session_id is not None:
        try:
            return int(raw_session_id)
        except (TypeError, ValueError):
            return None

    app_session_id = kwargs.get("app_session_id")
    if not app_session_id:
        return None
    from backend.core import db

    return db.get_session_id_by_app_id(str(app_session_id))


def render_prompt(prompt_id: str, **kwargs: Any) -> str:
    template = PROMPT_TEMPLATES[prompt_id]
    appendix_values = {
        name: value
        for name, value in Appendix.__dict__.items()
        if not name.startswith("_") and isinstance(value, str)
    }
    render_values = dict(kwargs)
    render_values.setdefault("mirror_process_context", "")
    render_values.setdefault("mirror_case_group_context", "")
    render_values.setdefault("mirror_step_context", "")
    render_values.setdefault("mirror_case_context", "")
    render_values.setdefault("mirror_clusters_json", "[]")
    norm_addressee = str(render_values.get("norm_addressee") or ADMINISTRATION)
    render_values.setdefault(
        "handbook_process_example",
        _render_handbook_process_example(norm_addressee),
    )
    render_values.setdefault(
        "handbook_case_group_example",
        _render_handbook_case_group_example(norm_addressee),
    )
    render_values.setdefault(
        "handbook_cases_frequency_example",
        CASES_CALCULATION_FREQUENCY_EXAMPLE,
    )
    render_values.setdefault(
        "handbook_cases_case_example",
        _render_handbook_cases_case_example(norm_addressee),
    )
    if prompt_id == PromptId.EFFORT_CALCULATION:
        render_values.setdefault(
            "effort_method_guidance",
            _render_effort_method_guidance(norm_addressee),
        )
        render_values.setdefault(
            "effort_appendix",
            _render_effort_appendix(norm_addressee),
        )
        render_values.setdefault(
            "effort_json_schema",
            _render_effort_json_schema(norm_addressee),
        )

    needs_law_summary = "{law_summary}" in template and not render_values.get("law_summary")
    needs_regulation_laws = (
        prompt_id == PromptId.REGULATIONS_IDENTIFICATION
        and (
            ("{gesetz_gueltig}" in template and not render_values.get("gesetz_gueltig"))
            or ("{gesetz_vorschlag}" in template and not render_values.get("gesetz_vorschlag"))
        )
    )

    if needs_law_summary or needs_regulation_laws:
        session_id = _resolve_session_id(render_values)
        if session_id is not None:
            from backend.core import db

            if needs_law_summary:
                session = db.get_session_by_id(session_id) or {}
                law_summary = (
                    str(session.get("law_diff_summary") or "").strip()
                    or str(session.get("law_diff_blurb") or "").strip()
                    or str(session.get("law_diff_title") or "").strip()
                )
                render_values.setdefault("law_summary", law_summary)

            if needs_regulation_laws:
                current_text, proposed_text = db.get_session_law_texts(session_id)
                render_values.setdefault("gesetz_gueltig", current_text)
                render_values.setdefault("gesetz_vorschlag", proposed_text)
    else:
        session_id = _resolve_session_id(render_values)

    if session_id is not None and norm_addressee:
        _populate_mirror_prompt_contexts(
            prompt_id=prompt_id,
            render_values=render_values,
            session_id=session_id,
            norm_addressee=norm_addressee,
        )

    prompt = template.format(**appendix_values, **render_values)
    norm_addressee = render_values.get("norm_addressee")
    return _apply_norm_addressee_prompt_rules(prompt_id, prompt, norm_addressee)


def _apply_norm_addressee_prompt_rules(
    prompt_id: str,
    prompt: str,
    norm_addressee: str | None,
) -> str:
    if not norm_addressee:
        return prompt

    if prompt_id in PROMPT_IDS_WITH_NORM_ADDRESSEE_CLAUSE:
        prompt = _append_prompt_section(prompt, NORM_ADDRESSEE_PROMPT_OPENINGS.get(norm_addressee))

    citizens_rule = CITIZENS_PROMPT_RULES.get(prompt_id) if norm_addressee == CITIZENS else None
    prompt = _append_prompt_section(prompt, citizens_rule)

    return prompt


def _append_prompt_section(prompt: str, section: str | None) -> str:
    if not section:
        return prompt
    return prompt + "\n\n" + section.strip()


def _render_handbook_process_example(norm_addressee: str | None) -> str:
    if norm_addressee == BUSINESS:
        return PROCESS_COMPILATION_EXAMPLE
    return ""


def _render_handbook_case_group_example(norm_addressee: str | None) -> str:
    if norm_addressee == BUSINESS:
        return CASE_GROUP_DEVELOPMENT_EXAMPLE
    return ""


def _render_handbook_cases_case_example(norm_addressee: str | None) -> str:
    if norm_addressee == CITIZENS:
        return CASES_CALCULATION_CASE_EXAMPLE
    return ""


def _render_effort_appendix(norm_addressee: str | None) -> str:
    if not norm_addressee:
        return ""
    appendix_template = EFFORT_APPENDICES.get(norm_addressee)
    if not appendix_template:
        return ""
    return appendix_template.format(
        Wegezeiten_Wegesachkosten=Appendix.Wegezeiten_Wegesachkosten,
        Zeitwerttabelle_Verwaltung=Appendix.Zeitwerttabelle_Verwaltung,
        Lohnkostentabelle_Verwaltung=Appendix.Lohnkostentabelle_Verwaltung,
        Zeitwerttabelle_Buerger=Appendix.Zeitwerttabelle_Buerger,
        Zeitwerttabelle_Wirtschaft=Appendix.Zeitwerttabelle_Wirtschaft,
        Lohnkostentabelle_Wirtschaft=Appendix.Lohnkostentabelle_Wirtschaft,
    )


def _render_effort_method_guidance(norm_addressee: str | None) -> str:
    if not norm_addressee:
        norm_addressee = ADMINISTRATION
    return EFFORT_METHOD_GUIDANCE.get(norm_addressee, EFFORT_METHOD_GUIDANCE[ADMINISTRATION])


def _render_effort_json_schema(norm_addressee: str | None) -> str:
    if not norm_addressee:
        norm_addressee = ADMINISTRATION
    return EFFORT_JSON_SCHEMA_BY_ADDRESSEE.get(norm_addressee, EFFORT_JSON_SCHEMA_DEFAULT).strip()


def _populate_mirror_prompt_contexts(
    prompt_id: str,
    render_values: dict[str, Any],
    session_id: int,
    norm_addressee: str,
) -> None:
    if prompt_id == PromptId.PROCESS_COMPILATION:
        render_values["mirror_process_context"] = render_values.get(
            "mirror_process_context"
        ) or render_mirror_prompt_context(
            session_id=session_id,
            norm_addressee=norm_addressee,
            stage="processes",
        )
    elif prompt_id == PromptId.CASE_GROUP_DEVELOPMENT:
        render_values["mirror_case_group_context"] = render_values.get(
            "mirror_case_group_context"
        ) or render_mirror_prompt_context(
            session_id=session_id,
            norm_addressee=norm_addressee,
            stage="case_groups",
        )
    elif prompt_id == PromptId.PROCESS_STEP_ANALYSIS:
        render_values["mirror_step_context"] = render_values.get(
            "mirror_step_context"
        ) or render_mirror_prompt_context(
            session_id=session_id,
            norm_addressee=norm_addressee,
            stage="steps",
        )
    elif prompt_id == PromptId.CASES_CALCULATION:
        render_values["mirror_case_context"] = render_values.get(
            "mirror_case_context"
        ) or render_mirror_prompt_context(
            session_id=session_id,
            norm_addressee=norm_addressee,
            stage="cases",
        )
