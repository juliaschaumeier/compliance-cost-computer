from __future__ import annotations

from typing import Dict


class PromptId:
    LAW_SUMMARY = "law_summary"
    REGULATIONS_IDENTIFICATION = "regulations_identification"
    PROCESS_COMPILATION = "process_compilation"
    CASE_GROUP_DEVELOPMENT = "case_group_development"
    PROCESS_STEP_ANALYSIS = "process_step_analysis"
    CASES_CALCULATION = "cases_calculation"
    EFFORT_CALCULATION = "effort_calculation"


PROMPT_TEMPLATES: Dict[str, str] = {
    PromptId.LAW_SUMMARY: (
        "Vergleiche den derzeit gueltigen Gesetzestext mit dem vorgeschlagenen "
        "Gesetzesvorschlag. Leite daraus ab, was der Gesetzgeber erreichen moechte. "
        "Gib strikt JSON zurueck im Format: {{\"title\": \"...\", \"blurb\": \"...\"}}. "
        "Die 'title' soll ein kurzer Titel sein (max. 12 Woerter). "
        "Die 'blurb' soll genau ein Satz sein.\n\n"
        "Geltendes Gesetz:\n{gesetz_gueltig}\n\n"
        "Gesetzesvorschlag:\n{gesetz_vorschlag}"
    ),
    # TODO: Also ask for the vorgaben type, i.e. added, deleted or changed during the law migration, add field in json and db.
    # TODO: Maybe add the title/text-body of the law tile to give the llm more up-front context on what the change is about?
    PromptId.REGULATIONS_IDENTIFICATION: (
        """ 
        Du bist Legist im deutschen Bundestag und damit betraut, den Erfüllungsaufwand zu einer geplanten Gesetzesänderung zu berechnen.

        Folgendes ist das konsolidierte, geltende Gesetz: {gesetz_gueltig}
        Folgendes konsolidiertes Gesetz wird vorgeschlagen: {gesetz_vorschlag}

        Deine Aufgabe ist, ausgehend, von den konsolidierten Versionen die Gesetzesänderungen herauszuarbeiten und 
        alle darin enthaltenen Vorgaben (Einzelregelungen) im nachfolgendem Sinne zu identifizieren. 
        Wichtig: Jede Gesetzesänderung kann keine, eine oder mehrere Vorgaben enthalten. Identifiziere alle für die Verwaltung zu beachtenden Vorgaben.

        Verwaltung sind alle die mit der Wahrnehmung von Verwaltungsaufgaben betrauten Verwaltungsträger (rechtsfähige Körperschaften, Anstalten und Stiftungen 
        des öffentlichen Rechts einschließlich Beliehene im Rahmen der ihnen übertragenen hoheitlichen Kompetenzen). Soweit Körperschaften/Anstalten des 
        öffentlichen Rechts privatwirtschaftlich tätig sind und in Wettbewerb stehen (z. B. kostenpflichtige Schulungen der Kammern; Universitäten bei 
        Forschungsförderungen) sind diese als Wirtschaft zu behandeln. Soweit Unternehmen hoheitliche Aufgaben wahrnehmen (z. B. Beliehene wie Prüfingenieure, 
        Bezirksschornsteinfegermeister, Tierärzte bei Fleischbeschau), sind diese als Verwaltung zu behandeln. Soweit öffentliche Unternehmen, die Aufgaben der 
        Daseinsvorsorge im staatlichen Auftrag erfüllen (z. B. Wasserkraftwerke in öffentlicher Hand) sind diese als Verwaltung zu behandeln. Die Rechtsform 
        bietet nur Anhaltspunkte; maßgeblich ist die vorgeschriebene Tätigkeit.

        Definition von Vorgaben:
        * Vorgaben sind Einzelregelungen, die unmittelbar zu Änderungen von Kosten oder Zeitaufwand bei den Normadressaten führen.
        * Sie beruhen auf bundesrechtlichen Regelungen und verpflichten Normadressaten, bestimmte Ziele zu erreichen, Vorgaben einzuhalten oder Handlungen 
          vorzunehmen bzw. zu unterlassen.
        * Dazu gehören auch Verpflichtungen zu Kooperation, Überwachung, Kontrolle sowie Informationspflichten (als Teilmenge).

        Unmittelbarkeit bedeutet, dass der Kosten- oder Zeitaufwand direkt aus der Befolgung der Vorgabe entsteht. Normadressaten müssen die Vorgaben einhalten, 
        um Rechtsverstöße oder den Verlust von Ansprüchen zu vermeiden. Auch Regelungen, die nur Ziele, Grenzwerte oder förderbedingte Verhaltensänderungen 
        vorgeben, gelten als Vorgaben, wenn sie direkt Aufwand auslösen.

        Gib nur und ausschließlich JSON im folgenden Format zurück:

        {{
          "vorgaben": [
            {{
              "normzitat": "",
              "beschreibung": ""
            }}
          ]
        }}

        Verwende keine ein- oder ausleitenden Texte und keine sonstigen Zeichen.
        """
    ),
    PromptId.PROCESS_COMPILATION: (
        """
        Du bist Legist im deutschen Bundestag und damit betraut, den Erfüllungsaufwand zu einer geplanten Gesetzesänderung zu berechnen.
        
        Die Gesetzesänderung führt zu folgenden Einzelvorgaben für die Verwaltung: {vorgaben_json}

        Deine Aufgabe ist, die enthaltenen Vorgaben (Einzelregelungen), welche in der Praxis in einem Zusammenhang erfüllt werden, können zu gemeinsamen 
        Prozessen zu bündeln. Soweit eine Bündelung von Vorgaben in Prozesse nicht möglich oder sinnvoll ist, ist die betreffende Einzelvorgabe identisch 
        einem eigenen Prozess zu behandeln. Ein solcher Prozess besteht daher ausschließlich aus einer Vorgabe.

        Gib mir nur und ausschließlich JSON zurück, das zwingend wie folgt formatiert ist:

        {{
        "prozesse": [
            {{
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "vorgaben": [
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                }}
            ]
            }},
            {{
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "vorgaben": [
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                }},
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                }}
            ]
            }}
        ]
        }}

        Verwende keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 
        """
    ),
    PromptId.CASE_GROUP_DEVELOPMENT: (
        """
        Du bist Legist im deutschen Bundestag und damit betraut, den Erfüllungsaufwand zu einer geplanten Gesetzesänderung zu berechnen.
        
        Die Gesetzesänderung führt zu folgenden, Erfüllungsaufwand auslösenden Prozessen für die Verwaltung: {prozesse_json}

        Wenn damit zu rechnen ist, dass die Verwaltung die jeweiligen Prozesse auf unterschiedlichen Wegen erfüllt, sind dafür sogenannte Fallgruppen zu bilden. 
        Dies jedoch nur, soweit durch die verschiedenen Wege wesentliche Unterschiede zu erwarten sind. Für jede Fallgruppe ist der Erfüllungsaufwand separat zu 
        ermitteln und darzustellen. Dabei ist es unerheblich, ob die Differenzierung erfolgt, weil die Normadressaten verschiedene Gestaltungsmöglichkeiten nutzen 
        oder weil sich die zugrunde liegenden Sachverhalte unterscheiden.

        Soweit eine Bildung von Fallgruppen aus dem jeweiligem Prozess nicht möglich oder sinnvoll ist, hat der betreffende Prozess nur eine einzige Fallgruppe. 
        Ein solcher Prozess besteht daher ausschließlich aus einer Fallgruppe.

        Gib mir nur und ausschließlich eine JSON-Datei zurück, die zwingend wie folgt formatiert ist:

        {{
        "prozesse": [
            {{
            "prozess_id": "",
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "vorgaben": [
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                }}
            ], 
            "fallgruppen": [
                {{
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": ""
                }},
                {{
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": ""
                }}
            ]
            }},
            {{
            "prozess_id": "",
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "vorgaben": [
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                }},
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                }}
            ], 
            "fallgruppen": [
                {{
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": ""
                }}
            ]
            }}
        ]
        }}
        Verwende keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 
        """
    ),
    # TODO: ausfuehrung_pro_einzelfall bereits hier abfragen und nicht erst in effort_calculation??
    PromptId.PROCESS_STEP_ANALYSIS: (
        """
        Du bist Legist im deutschen Bundestag und damit betraut, den Erfüllungsaufwand zu einer geplanten Gesetzesänderung zu berechnen.
        
        Die Gesetzesänderung führt zu folgenden, Erfüllungsaufwand auslösenden Prozessen für die Verwaltung, welche durch folgende Fallgruppen 
        differenziert werden: {case_groups_json}

        Deine Aufgabe ist es, die wesentlichen anfallenden Tätigkeiten der Verwaltungsträger zur Erfüllung eines Prozesses pro Fallgruppe 
        zu identifizieren. Auf dieser Grundlage werden später der anfallende Personal- und ggf. Sachaufwand bestimmt. 

        Als Hilfsmittel für die Identifizierung der zu erwartenden Tätigkeiten kann die Checkliste mit den möglichen Tätigkeiten der Verwaltung zur Erfüllung 
        von Vorgaben oder Prozessen herangezogen werden. Es kann sich in einzelnen Fällen anbieten, die Checkliste um spezielle Tätigkeiten zu erweitern.

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
        gezeigt, dass bei den meisten Informationspflichten lediglich vier bis sechs Tätigkeiten anfallen.
        
        Bei Daueraufgaben oder wenn gesicherte Erfahrungswerte (z. B. aus Organisationsuntersuchungen, Vergleichsringen etc.) vorliegen, kann es zweckmäßig 
        sein, den Zeitaufwand ohne vorherige Zerlegung in Einzeltätigkeiten zu  ermitteln, entsprechend wird lediglich eine Tätigkeit in dieser Fallgruppe 
        befüllt.
        
        Gib nur und ausschließlich JSON im folgenden Format zurück:
        
        {{
        "prozesse": [
            {{
            "prozess_id": "",
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "fallgruppen": [
                {{
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "taetigkeiten": [ 
                        {{
                            "taetigkeit": "",
                            "beschreibung": ""
                        }},
                        {{
                            "taetigkeit": "",
                            "beschreibung": ""
                        }}
                    ]
                }},
                {{
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "taetigkeiten": [ 
                        {{
                            "taetigkeit": "",
                            "beschreibung": ""
                        }}
                    ]
                }}
            ]
            }},
            {{
            "prozess_id": "",
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "fallgruppen": [
                {{
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "taetigkeiten": [ 
                        {{
                            "taetigkeit": "",
                            "beschreibung": ""
                        }},
                        {{
                            "taetigkeit": "",
                            "beschreibung": ""
                        }}
                    ]
                }}
            ]
            }}
        ]
        }}
        Verwende keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 

        """
    ),
    PromptId.CASES_CALCULATION: (
        """
        Du bist Legist im deutschen Bundestag und damit betraut, den Erfüllungsaufwand zu einer geplanten Gesetzesänderung zu berechnen.
        
        Die Gesetzesänderung führt zu folgenden, Erfüllungsaufwand auslösenden Prozessen für die Verwaltung, welche durch folgende Fallgruppen 
        differenziert werden: {case_groups_json}

        Deine Aufgabe ist es, die Fallzahlen jeder dieser Fallgruppen zu bestimmen. 

        Allgemein gilt: Bei periodisch zu erfüllenden Vorgaben oder Prozessen ergibt sich die Fallzahl aus der Multiplikation der Häufigkeit mit der Anzahl 
        der Betroffenen. Die Häufigkeit gibt an, wie oft pro Jahr eine Vorgabe oder ein Prozess erledigt wird bzw. wie häufig der damit einhergehende 
        Aufwand entsteht. Bei Vorgaben oder Prozessen, die aufgrund der Bearbeitung von Anträgen anlassbezogen erfüllt werden, sollte die Zahl der 
        jährlich zu erwartenden Anträge als Fallzahl zugrunde  gelegt werden. Bei Schwankungen ist ein sachgerechter Mittelwert zu verwenden. Die Fallzahl 
        für Überwachungs- und Kontrollmaßnahmen ist in der Regel wesentlich geringer.
        Aufwand, der aufgrund der Anpassung an das neue Regelungsvorhaben nur ein Mal innerhalb einer Einrichtung der Verwaltung anfällt, wird als 
        einmaliger Erfüllungsaufwand bezeichnet und ist gesondert auszuweisen.

        Soweit bestehende Regelungen geändert werden, können Fallzahlen unter Umständen auch aus bereits vorliegenden Aufwandsschätzungen und 
        Gesetzesbegründungen oder der OnDEA-Datenbank des StBA (https://www.ondea.de/) übernommen werden. Bevor solche Angaben verwendet werden, sollten 
        sie ggf. aktualisiert werden.

        Gib nur und ausschließlich JSON im folgenden Format zurück:        
        {{
        "prozesse": [
            {{
            "prozess_id": "",
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "vorgaben": [
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": ""
                }}
            ], 
            "fallgruppen": [
                {{
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "anzahl_betroffene": "",
                    "haeufigkeit_pro_jahr": ""
                }},
                {{
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "anzahl_betroffene": "",
                    "haeufigkeit_pro_jahr": ""
                }}
            ]
            }},
            {{
            "prozess_id": "",
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "vorgaben": [
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": ""
                }},
                {{
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": ""
                }}
            ], 
            "fallgruppen": [
                {{
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "anzahl_betroffene": "",
                    "haeufigkeit_pro_jahr": ""
                }}
            ]
            }}
        ]
        }}
        Verwende keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 
        """
    ),
    # TODO: How to add this? Die Bereitstellung und Wartung von Informationstechnologie aufgrund der Änderung von 
    #                        Vorgaben kann jedoch zusätzlichen Sach- und Personalaufwand erzeugen.
    PromptId.EFFORT_CALCULATION: (
        """
        Du bist Legist im deutschen Bundestag und damit betraut, den Erfüllungsaufwand zu einer geplanten Gesetzesänderung zu berechnen.
        
        Die Gesetzesänderung führt zu folgenden, Erfüllungsaufwand auslösenden Prozessen für die Verwaltung, welche durch folgende Fallgruppen und 
        Prozessschritte differenziert werden: {step_analysis_json}

        Deine Aufgabe ist es, den anfallenden Personal- und ggf. Sachaufwand der anfallenden Tätigkeiten der Verwaltungsträger pro Einzelfall zu identifizieren.

        Eine Reihe von Tätigkeiten läuft bei Nutzung entsprechender Informationstechnologie automatisch ab. Aus automatisch ablaufenden Prozessen resultiert 
        zunächst kein Zeitaufwand.
        Sofern keine spezifischen Daten über den Zeitaufwand für die Erfüllung der Vorgaben zu ermitteln sind, kann die Zeitwerttabelle Verwaltung 
        herangezogen werden (siehe Anhang 7: Zeitwerttabelle Verwaltung). Zudem findet sich im Anhang eine Tabelle mit Pauschalen zu Wegezeiten 
        (siehe Anhang 5: Wegezeiten und -sachkosten, Seite 62). Zur Ermittlung des Personalaufwands für die Verwaltung werden zunächst die zu erwartenden 
        Bearbeitungszeiten dargestellt. Dabei zählen Gemeinkosten nicht zum Erfüllungsaufwand.

        Personalaufwand wird grundsätzlich über die zu erwartende Arbeitszeit pro Tätigkeit (in Minuten) und Fall dargestellt und mit den laufbahnspezifischen 
        Lohnsätzen der mit der Bearbeitung zu  betrauenden Mitarbeiterinnen und Mitarbeitern multipliziert. Die zu erwartende Arbeitszeit pro Fall 
        (Zeitaufwand) kann z. B. anhand von Erfahrungswerten, Organisationsuntersuchungen oder Daten der Kosten- und Leistungsrechnung ermittelt werden.
        Die laufbahnspezifischen Lohnsätze ergeben sich aus der Lohnkostentabelle des StBA (siehe Anhang 8: Lohnkostentabelle Verwaltung). Es sind hierbei jeweils 
        nur die Lohnsatz/Zeitaufwand Paare anzugeben, welche tatsächlich bei der Erfüllung der Tätigkeit relevant sind.

        Wenn der zu erfüllende Prozess nicht in Einzeltätigkeiten (oder lediglich eine Einzeltätigkeit) zerlegt wurde, etwa bei Daueraufgaben oder wenn 
        gesicherte Erfahrungswerte (z. B. aus Organisationsuntersuchungen, Vergleichsringen etc.) vorliegen, ermittelt man Zeitaufwand in  Personentagen oder 
        Personenmonaten und rechnet ihn dann um. Den Berechnungen ist dann die Minutenzahl pro Jahr zugrunde zu legen, die  durchschnittlich der tatsächlichen 
        Leistungserbringung je Behörde zugerechnet werden kann.  
        Für die Beschäftigten im öffentlichen Dienst sind Richtwerte bei einer 40-Stunden-Woche:  
        • 1 Personentag: 8 Stunden (zu je 60 min),  
        • 1 Personenmonat: 134 Stunden,  
        • 1 Personenjahr: 200 Arbeitstage.

        Unter Sachaufwand fällt der Betriebs-, Unterhaltungs- und Investitionsaufwand, der zur Erfüllung einer Vorgabe oder eines Prozesses zu erwarten ist. 
        Gemeinkosten zählen hingegen nicht zum Erfüllungsaufwand. Darüber hinaus notwendige Investitionsaufwendungen für die Verwaltung sollten bei der  
        Aufwandsermittlung ebenfalls konkret aufgeschlüsselt werden. Hierzu zählen beispielsweise:  
        • Aufwand für die Inanspruchnahme Dritter (z. B. Handwerkerleistungen),  
        • Aufwand für die Beschaffung von spezieller Informations- und Kommunikationstechnik,  
        • Aufwand für die Nachrüstung von Anlagen,  
        • Sachaufwand für Wege zu anderen Behörden oder Stellen (siehe Anhang 5: Wegezeiten und -sachkosten).

        Außerdem soll angegeben werden, ob die Tätigkeit pro Einzelfall (=1) oder lediglich einmal pro gesamte Fallgruppe (z.B. Einarbeitung in die Vorgabe) ausgeführt wird (=0).

        Anhang:

        {Wegezeiten_Wegesachkosten}

        {Zeitwerttabelle_Verwaltung}

        {Lohnkostentabelle_Verwaltung}

        Gib nur und ausschließlich JSON im folgenden Format zurück:
        
        {{
        "prozesse": [
            {{
            "prozess_id": "",
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "fallgruppen": [
                {{
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "taetigkeiten": [ 
                        {{
                            "taetigkeiten_id": "",
                            "taetigkeit": "",
                            "beschreibung": "",
                            "stundenlohn_satz_a": "",
                            "stundenlohn_satz_b": "",
                            "stundenlohn_satz_c": "",
                            "stundenlohn_satz_d": "",
                            "stundenlohn_satz_e": "",
                            "zeitaufwand_in_min_a": "",
                            "zeitaufwand_in_min_b": "",
                            "zeitaufwand_in_min_c": "",
                            "zeitaufwand_in_min_d": "",
                            "zeitaufwand_in_min_e": "",
                            "sachaufwand": "",
                            "ausfuehrung_pro_einzelfall": ""
                        }},
                        {{
                            "taetigkeiten_id": "",
                            "taetigkeit": "",
                            "beschreibung": "",
                            "stundenlohn_satz_a": "",
                            "stundenlohn_satz_b": "",
                            "stundenlohn_satz_c": "",
                            "stundenlohn_satz_d": "",
                            "stundenlohn_satz_e": "",
                            "zeitaufwand_in_min_a": "",
                            "zeitaufwand_in_min_b": "",
                            "zeitaufwand_in_min_c": "",
                            "zeitaufwand_in_min_d": "",
                            "zeitaufwand_in_min_e": "",
                            "sachaufwand": "",
                            "ausfuehrung_pro_einzelfall": ""
                        }}
                    ]
                }},
                {{
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "taetigkeiten": [ 
                        {{
                            "taetigkeiten_id": "",
                            "taetigkeit": "",
                            "beschreibung": "",
                            "stundenlohn_satz_a": "",
                            "stundenlohn_satz_b": "",
                            "stundenlohn_satz_c": "",
                            "stundenlohn_satz_d": "",
                            "stundenlohn_satz_e": "",
                            "zeitaufwand_in_min_a": "",
                            "zeitaufwand_in_min_b": "",
                            "zeitaufwand_in_min_c": "",
                            "zeitaufwand_in_min_d": "",
                            "zeitaufwand_in_min_e": "",
                            "sachaufwand": "",
                            "ausfuehrung_pro_einzelfall": ""
                        }}
                    ]
                }}
            ]
            }},
            {{
            "prozess_id": "",
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "fallgruppen": [
                {{
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "taetigkeiten": [ 
                        {{
                            "taetigkeiten_id": "",
                            "taetigkeit": "",
                            "beschreibung": "",
                            "stundenlohn_satz_a": "",
                            "stundenlohn_satz_b": "",
                            "stundenlohn_satz_c": "",
                            "stundenlohn_satz_d": "",
                            "stundenlohn_satz_e": "",
                            "zeitaufwand_in_min_a": "",
                            "zeitaufwand_in_min_b": "",
                            "zeitaufwand_in_min_c": "",
                            "zeitaufwand_in_min_d": "",
                            "zeitaufwand_in_min_e": "",
                            "sachaufwand": "",
                            "ausfuehrung_pro_einzelfall": ""
                        }},
                        {{
                            "taetigkeiten_id": "",
                            "taetigkeit": "",
                            "beschreibung": "",
                            "stundenlohn_satz_a": "",
                            "stundenlohn_satz_b": "",
                            "stundenlohn_satz_c": "",
                            "stundenlohn_satz_d": "",
                            "stundenlohn_satz_e": "",
                            "zeitaufwand_in_min_a": "",
                            "zeitaufwand_in_min_b": "",
                            "zeitaufwand_in_min_c": "",
                            "zeitaufwand_in_min_d": "",
                            "zeitaufwand_in_min_e": "",
                            "sachaufwand": "",
                            "ausfuehrung_pro_einzelfall": ""
                        }}
                    ]
                }}
            ]
            }}
        ]
        }}
        Verwende keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 
        """
    ),
}


def render_prompt(prompt_id: str, **kwargs: str) -> str:
    template = PROMPT_TEMPLATES[prompt_id]
    appendix_values = {
        name: value
        for name, value in Appendix.__dict__.items()
        if not name.startswith("_") and isinstance(value, str)
    }
    return template.format(**appendix_values, **kwargs)


class Appendix:
    """ This class lists the appendices of the LEITFADEN """
    Wegezeiten_Wegesachkosten = (
        "### Anhang 5: Wegezeiten und -sachkosten\n\n"
        "Wegezeiten umfassen den Zeitaufwand des Normadressaten, um von seinem Wohnort bzw. "
        "Sitz zur zuständigen Behörde zu gelangen. Die Wegesachkosten beschreiben den "
        "Sachaufwand, um diesen Weg zurückzulegen und beinhalten beispielsweise Fahrkarten "
        "für den ÖPNV oder Kraftstoff für das eigene Fahrzeug.\n\n"
        "Wegezeiten und Wegesachkosten werden bei der Ermittlung des Erfüllungsaufwands "
        "berücksichtigt, wenn die jeweilige Regelung ein persönliches Erscheinen in einer "
        "Behörde oder Stelle vorschreibt und keine Alternativen wie den Postweg oder "
        "Online-Verfahren erlaubt. "
        "Gleiches gilt, wenn Behördenvertreterinnen und -vertreter verpflichtet sind, "
        "beispielsweise im Rahmen von Gremiensitzungen persönlich andere Ämter oder "
        "Stellen aufzusuchen.\n\n"
        "Die folgende Tabelle zeigt pauschale Wegezeiten und -sachkosten in Abhängigkeit "
        "der zuständigen Verwaltungsebene. Gibt es belastbare Anhaltspunkte dafür, dass "
        "der nach der Tabelle ermittelte Wert aller Wahrscheinlichkeit nach über- oder "
        "unterzeichnet ist, sollte der aus Fachsicht realistischere Wert für die "
        "Ermittlung genutzt werden.\n\n"
        "*Wegezeiten und -sachkosten nach Verwaltungsebene*\n\n"
        "| Verwaltungsebene | Wegezeiten (Min.) | Wegesachkosten (Euro) |\n"
        "| --- | --- | --- |\n"
        "| Gemeinde | 15 | 1,10 |\n"
        "| Kreis | 22 | 3,10 |\n"
        "| Regierungsbezirk/Land | 59 | 13,20 |\n"
        "| Durchschnitt | 20 | 2,60 |\n"
    )
    Zeitwerttabelle_Verwaltung = (
        "### Anhang 7: Zeitwerttabelle Verwaltung\n\n"
        "Liegen noch keine vergleichbaren Daten für den Zeitaufwand einzelner Tätigkeiten "
        "vor, kann auf die sogenannte Zeitwerttabelle Verwaltung zurückgegriffen werden. "
        "Die Zeitwerttabelle weist für einen großen Teil der auf Seite 46 angegebenen "
        "Standardaktivitäten Minutenwerte aus. Die Standardaktivitäten sind nach dem Grad "
        "der Schwierigkeit in einfach, mittel und hoch gestaffelt.\n\n"
        "Der nach der Zeitwerttabelle ermittelte Zeitwert (das heißt der Zeitaufwand für "
        "eine Tätigkeit) sollte immer anhand begründbarer Einschätzungen aus fachlicher "
        "Sicht überprüft werden. Gibt es belastbare Anhaltspunkte dafür, dass der nach der "
        "Tabelle ermittelte Wert aller Wahrscheinlichkeit nach zu hoch oder zu niedrig "
        "angesetzt ist, sollte der aus Fachsicht realistischere Wert für die Ermittlung "
        "genutzt werden.\n\n"
        "*Zeitwerttabelle Verwaltung*\n\n"
        "| Nr. | Standardaktivität | Einfache Komplexität (Min.) | Mittlere Komplexität (Min.) | Hohe Komplexität (Min.) | Erläuterung |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| 1 | Einarbeiten in die Vorgabe | 2 | 13 | 413 | Welcher Aufwand entsteht regelmäßig, um sich mit der gesetzlichen Verpflichtung vertraut zu machen? |\n"
        "| 2 | Beraten, Vorgespräche führen | 3 | 30 | 460 (1 PT) | Welcher Aufwand fällt zur Beantwortung von Fragen durch Bürgerinnen und Bürger oder Unternehmen und der Klärung von Sachverhalten an? |\n"
        "| 3 | Formelle Prüfung, Daten sichten | 5 | 30 | 110 | Welcher Aufwand entsteht durch Kontrolle auf Vollständigkeit und Richtigkeit von vorhandenen Informationen wie z. B. Nachweisen? |\n"
        "| 4 | Eingang bestätigen oder Einholen fehlender Daten | 5 | 10 | 22 | Welcher Aufwand entsteht durch Eingangsbestätigungen oder die Nachforderung fehlender Daten? |\n"
        "| 5 | Inhaltliche Prüfung, Daten erfassen | 8 | 60 | 480 (1 PT) | Welcher Aufwand fällt durch die Prüfung von Formularen, Belegen und Berechnungen sowie durch das elektronische Erfassen an? |\n"
        "| 6 | Berechnungen durchführen | 9 | 120 | X[^7] | Welcher Aufwand fällt für Berechnungen, Bewertungen und Zählungen an? |\n"
        "| 7 | Ergebnisse/Berechnungen überprüfen und ggf. korrigieren | 4 | 30 | 1 170 (3,7 PT) | Welcher Aufwand entsteht durch die Prüfung von Ergebnissen z. B. durch das Vieraugenprinzip oder Mitzeichnungen? |\n"
        "| 8 | Interne Sitzungen | 2 | 60 | 2 120 (4,4 PT) | Welcher Aufwand entsteht durch notwendige interne Sitzungen? |\n"
        "| 9 | Externe Sitzungen | 5 | 80 | 2 640 (5,5 PT) | Welcher Aufwand entsteht durch notwendige externe Sitzungen z. B. mit externen Sachverständigen oder anderen Behörden? |\n"
        "| 10 | Daten übermitteln oder veröffentlichen | 1 | 10 | 60 | Welcher Aufwand fällt an, um Informationen zu veröffentlichen oder an andere öffentliche Stellen weiterzugeben? |\n"
        "| 11 | Abschließende Informationen aufbereiten, Bescheid erstellen | 5 | 60 | 480 (1 PT) | Welcher Aufwand entsteht z. B. durch das Erstellen von Bescheiden oder Vermerken? |\n"
        "| 12 | Zahlungen anweisen, annehmen oder überwachen | 1 | 5 | 18 | Welcher Aufwand fällt für Überweisungen oder die Prüfung von Zahlungsein- und -ausgängen an? |\n"
        "| 13 | Korrektur bzw. weitere Informationen bei Rückfragen vorlegen | 30 | 60 | 120 | Welcher Aufwand entsteht durch Rückfragen nach Bescheiderhalt und ggf. Fehlerkorrekturen? |\n"
        "| 14 | Kopieren, archivieren, verteilen | 2 | 10 | 20 | Welcher Aufwand entsteht durch Kopier- oder Archivierungstätigkeiten und das Verteilen von Informationen innerhalb der Behörde? |\n"
        "| 15 | Fortbildungen und Schulungen | 1 | 3 | 2 640 (5,5 PT) | Welcher Aufwand entsteht dadurch, dass die Erfüllung einer Vorgabe eine Schulung voraussetzt? |\n"
        "| 16 | Überwachungs- und Aufsichtsmaßnahmen | 8 | 156 | 25 000 (52,1 PT) | Welcher Aufwand fällt durch Begehungen in Betrieben oder Besuchen bei Bürgerinnen und Bürgern an? |\n"
        "| 17 | Anpassen von internen Prozessen | 12 | 4 080 (8,5 PT) | 67 200 (140 PT) | Welcher Aufwand entsteht, wenn interne Prozesse verändert oder angepasst werden müssen? |\n\n"
        "[^7]: Aufgrund methodischer Unterschiede wurde hier auf die Darstellung von „hoch“ verzichtet.\n\n"
        "PT: Persontag(e)\n"
        "Stand: Januar 2025; Quelle: StBA\n"
    )
    Lohnkostentabelle_Verwaltung = (
        "### Anhang 8: Lohnkostentabelle Verwaltung\n\n"
        "In Anlehnung an die Lohnkostentabelle für Informationspflichten der Wirtschaft "
        "nach dem Standardkosten-Modell wurde für die Verwaltung vom StBA eine eigene "
        "Tariflohntabelle entwickelt. Analog zum Bereich Wirtschaft werden die "
        "Standardlohnsätze der Verwaltung getrennt nach Hierarchieebene und "
        "Qualifikationsniveau in Euro ausgewiesen.\n\n"
        "*Lohnkosten pro Stunde in Euro*\n\n"
        "| Verwaltungsebene | Einfacher und mittlerer Dienst | Gehobener Dienst | Höherer Dienst | Durchschnitt |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| Bund | 33,80 | 40,40 | 67,60 | 44,40 |\n"
        "| Länder | 30,50 | 43,20 | 69,30 | 46,70 |\n"
        "| Kommunen | 25,50 | 42,20 | 70,40 | 40,70 |\n"
        "| Sozialversicherung | 30,30 | 46,30 | 73,20 | 48,10 |\n"
        "| Durchschnitt Öffentliche Verwaltung, Verteidigung, Sozialversicherung | 27,30 | 42,90 | 69,30 | 44,40 |\n\n"
        "Stand: 2025; Quelle: StBA\n\n"
        "*Lohnkosten pro Mitarbeiterkapazität (MAK) in Euro*\n\n"
        "| Verwaltungsebene | Einfacher und mittlerer Dienst | Gehobener Dienst | Höherer Dienst | Durchschnitt |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| Bund | 54 080 | 64 640 | 108 160 | 71 040 |\n"
        "| Länder | 48 800 | 69 120 | 110 880 | 74 720 |\n"
        "| Kommunen | 40 800 | 67 520 | 112 640 | 65 120 |\n"
        "| Sozialversicherung | 48 480 | 74 080 | 117 120 | 76 960 |\n"
        "| Durchschnitt Öffentliche Verwaltung, Verteidigung, Sozialversicherung | 43 680 | 68 640 | 110 880 | 71 040 |\n\n"
        "Stand: 2025; Quelle: StBA\n"
        "1 MAK = 1 Personenjahr à 200 Arbeitstage mit je 8 Stunden\n"
    )
    # TODO: Insert glossary items into prompts?
    Begriffsdefinitionen_Erlaeuterungen = (
        "### Anhang 9: Begriffsdefinitionen und Erläuterungen\n\n"
        "**Erfüllungsaufwand**\n\n"
        "Der Erfüllungsaufwand umfasst den gesamten messbaren Zeitaufwand und die Kosten, "
        "die durch die Befolgung einer bundesrechtlichen Vorschrift bei Bürgerinnen und "
        "Bürgern, Wirtschaft sowie der öffentlichen Verwaltung entstehen. Teil des "
        "Erfüllungsaufwands sind Bürokratiekosten, die durch die Erfüllung von "
        "Informationspflichten verursacht werden. Diese sind beim Normadressaten Wirtschaft "
        "gesondert auszuweisen.\n\n Bei Bürgerinnen und Bürgern sowie der Verwaltung ist eine "
        "Unterscheidung zwischen Informationspflichten und anderen Vorgaben entbehrlich.\n\n"
        "Zum Erfüllungsaufwand der Verwaltung gehört der Vollzugsaufwand. Auch das "
        "fiskalische Handeln der Verwaltung als Normadressat (z. B. als Halter von Kfz oder "
        "als Bauherr) ist dem Erfüllungsaufwand zuzurechnen. Erfüllungsaufwand entsteht der "
        "Verwaltung insbesondere durch die Bearbeitung von Anträgen oder durch "
        "Überwachungsaufgaben sowie durch die Bereitstellung von Informationen und "
        "Materialien (z. B. Antragsformulare) für Bürgerinnen und Bürger oder für die "
        "Wirtschaft oder für andere Teile der Verwaltung.\n\n"
        "Einnahmen und Ausgaben, die bei Gesetzentwürfen unter Buchstabe D des Vorblattes "
        "ausgewiesen werden, bleiben beim Erfüllungsaufwand unberücksichtigt (z. B. "
        "Steuermehr-/ -mindereinnahmen, Aufwendungen gem. Artikel 104a Absatz3 und 4 GG).\n\n"
        "Beim Erfüllungsaufwand wird lediglich die Kostenseite betrachtet. Es findet keine "
        "Saldierung mit dem Nutzen einer Regelung statt.\n\n"
        "**Normadressaten**\n\n"
        "Bürgerinnen und Bürger, Wirtschaft sowie die öffentliche Verwaltung stellen die "
        "möglichen Normadressaten dar.\n\n"
        "Zum Normadressaten Wirtschaft zählt jede Einheit, die eine wirtschaftliche Tätigkeit "
        "ausübt, die zum Bruttoinlandsprodukt beiträgt und dem Privatsektor zugerechnet wird. "
        "Der Privatsektor umfasst auch karitative Organisationen und den ehrenamtlichen "
        "Sektor; nicht darunter fallen öffentliche Verwaltung, private Haushalte und "
        "exterritoriale Körperschaften und Organisationen.\n\n"
        "Als öffentliche Verwaltung gelten die mit der Wahrnehmung von Verwaltungsaufgaben "
        "betrauten Verwaltungsträger (rechtsfähige Körperschaften, Anstalten und Stiftungen "
        "des öffentlichen Rechts einschließlich Beliehene im Rahmen der ihnen übertragenen "
        "hoheitlichen Kompetenzen).\n\n"
        "Alle Vorgaben, die sich an natürliche Personen richten, sind Vorgaben für "
        "Bürgerinnen und Bürger. Führt eine natürliche Person ein Unternehmen, dann zählen "
        "diejenigen Vorgaben, die sich an die Person aufgrund ihrer Eigenschaft als "
        "Unternehmerinnen und Unternehmer richten, als Vorgaben für die Wirtschaft.\n\n"
        "Vorgaben können mehrere Normadressaten gleichzeitig betreffen.\n\n"
        "**Prozess**\n\n"
        "Mehrere Vorgaben, die in der Praxis in einem Zusammenhang erfüllt werden, können "
        "zu einem Prozess gebündelt werden.\n\n"
        "**Regelungsvorhaben**\n\n"
        "Bei Regelungsvorhaben handelt es sich um alle Entwürfe von Rechts- und "
        "Verwaltungsvorschriften, die nach den §§ 43, 44, 62 Absatz 2 und § 70 Absatz 1 der "
        "GGO mit einer Gesetzesfolgenabschätzung zu versehen sind.\n\n"
        "**Vorgaben**\n\n"
        "Vorgaben sind Einzelregelungen, die bei den Normadressaten unmittelbar zur Änderung "
        "von Kosten, Zeitaufwand oder beidem führen. Sie ergeben sich aus bundesrechtlichen "
        "Regelungen. Sie veranlassen die Normadressaten, bestimmte Ziele oder Anordnungen zu "
        "erfüllen oder auch bestimmte Handlungen zu unterlassen. Dazu zählen auch "
        "Verpflichtungen zur Kooperation mit Dritten sowie zur Überwachung und Kontrolle "
        "von Zuständen, Handlungen, numerischen Werten oder Verhaltensweisen. "
        "Informationspflichten bilden eine Teilmenge der Vorgaben.\n\n"
        "„Unmittelbar“ bedeutet hierbei, dass die Änderung von Kosten oder Zeitaufwand in "
        "direkter Verbindung mit der Befolgung der jeweiligen Vorgabe steht. Ein Merkmal "
        "von Vorgaben ist, dass Bürgerinnen und Bürger, Wirtschaft sowie öffentliche "
        "Verwaltung ihnen Folge leisten müssen, um nicht gegen Rechtsvorschriften zu "
        "verstoßen oder etwaige Ansprüche auf staatliche Leistungen zu verlieren "
        "(z. B. Anträge).\n\n"
        "Bei der Identifizierung von Vorgaben ist zu beachten, dass der Gesetzgeber zum "
        "Teil neben Ge- oder Verboten lediglich Ziele oder Grenzwerte festgelegt oder "
        "z. B. durch staatliche Förderungen Verhaltensänderungen erreichen will. Auch "
        "solche Einzelregelungen sind als Vorgaben zu verstehen, weil sie unmittelbar zur "
        "Änderung von Kosten bzw. Zeitaufwand bei den Normadressaten führen.\n"
    )


    
