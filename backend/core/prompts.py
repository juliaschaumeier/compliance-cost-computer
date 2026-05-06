from __future__ import annotations

from typing import Any, Dict

from backend.core.handbook_examples import (
    CASE_GROUP_DEVELOPMENT_EXAMPLE,
    CASES_CALCULATION_CASE_EXAMPLE,
    CASES_CALCULATION_FREQUENCY_EXAMPLE,
    PROCESS_COMPILATION_EXAMPLE,
)
from backend.core.handbook_tables import Appendix
from backend.core.norm_addressees import (
    ADMINISTRATION,
    BUSINESS,
    CITIZENS,
    SUPPORTED_NORM_ADDRESSEES,
)


class PromptId:
    LAW_SUMMARY = "law_summary"
    REGULATIONS_IDENTIFICATION = "regulations_identification"
    PROCESS_COMPILATION = "process_compilation"
    CASE_GROUP_DEVELOPMENT = "case_group_development"
    PROCESS_STEP_ANALYSIS = "process_step_analysis"
    CASES_CALCULATION = "cases_calculation"
    EFFORT_CALCULATION = "effort_calculation"


PROMPTS_REQUIRING_NORM_ADDRESSEE = {
    PromptId.PROCESS_COMPILATION,
    PromptId.CASE_GROUP_DEVELOPMENT,
    PromptId.PROCESS_STEP_ANALYSIS,
    PromptId.CASES_CALCULATION,
    PromptId.EFFORT_CALCULATION,
}

LEGIST_PROMPT_OPENING = (
    """
    Sie sind Legist im deutschen Bundestag und damit betraut, die 
    Erfuellungsaufwandsaenderung zu einer geplanten Gesetzesaenderung zu berechnen.

    Insbesondere werden zur Ermittlung der zu erwartenden Aenderung des Aufwands 
    pro Fall die wesentlichen Taetigkeiten identifiziert, die zur Erfuellung 
    einer Vorgabe oder eines Prozesses im Einzelfall zu erwarten sind. Diese 
    schliessen Taetigkeiten ein, welche neu hinzukommen, welche sich aendern und 
    welche wegfallen. Fuer diese Taetigkeiten werden die zu erwartenden Aenderungen des 
    Zeit-, Personal- sowie Sachaufwands ermittelt.

    Die wesentlichen Unterschiede der Gesetzesaenderung sind wie folgt 
    zusammengefasst: {law_summary}

    """
)


NORM_ADDRESSEE_PROMPT_OPENINGS: Dict[str, str] = {
    ADMINISTRATION: (
        """
        Dieser Lauf betrifft den Normadressaten Verwaltung.

        Ein Verwaltungsprozess ist die durch die Regelung ausgeloeste Bearbeitungs-
        oder Vollzugshandlung einer zustaendigen Behoerde bei einem konkreten
        Vorgang. Typische Auspraegungen sind Antragsbearbeitung und Bescheidung,
        Anerkennung/Genehmigung/Registrierung, turnusmaessige oder anlassbezogene
        Pruefung und Aufsicht, Erstattungs- und Auszahlungsverfahren, Register- und
        Aktenfuehrung, Rechtsbehelfs- und Widerspruchsbearbeitung sowie einmalige
        Umstellungsaufwaende (Schulung, IT-Anpassung, Formular- und Merkblatt-
        pflege). Der verwaltungsseitige Erfuellungsaufwand entsteht dort, wo die
        Behoerde tatsaechlich taetig wird.

        Beruecksichtigen Sie ausschliesslich den Erfuellungsaufwand der Verwaltung.
        Uebernehmen Sie keine wirtschaftlichen oder buergerbezogenen Prozesse,
        Fallgruppen, Taetigkeiten, Fallzahlen oder Werte. Vermeiden Sie zugleich,
        aus Vorsicht ganze Vollzugsstraenge wegzulassen: wenn eine Regelung die
        Verwaltung zur Pruefung, Bescheidung oder Aufsicht verpflichtet, ist dieser
        Vollzugsaufwand auszuweisen, auch wenn er aus einem wirtschafts- oder
        buergerseitigen Antrag ausgeloest wird.
        """
    ),
    BUSINESS: (
        """
        Dieser Lauf betrifft den Normadressaten Wirtschaft.

        Beruecksichtigen Sie ausschliesslich den Erfuellungsaufwand der Wirtschaft.
        Analysieren Sie nur wirtschaftsbezogene Prozesse, Fallgruppen, Taetigkeiten,
        Fallzahlen und Werte. Uebernehmen Sie keine Verwaltungslogik, Verwaltungswerte
        oder buergerbezogenen Inhalte. Informationspflichten der Wirtschaft, interne
        Umstellungen, externe Dienstleistungen sowie wirtschaftsspezifische Pruef-,
        Melde-, Nachweis- und Dokumentationspflichten sind mitzudenken.
        """
    ),
    CITIZENS: (
        """
        Dieser Lauf betrifft den Normadressaten Buergerinnen und Buerger.

        Beruecksichtigen Sie ausschliesslich den Erfuellungsaufwand von Buergerinnen und
        Buergern. Analysieren Sie nur buergerbezogene Prozesse, Fallgruppen, Taetigkeiten,
        Fallzahlen und Werte. Uebernehmen Sie keine Verwaltungs- oder Unternehmenslogik.
        Fuer Buergerinnen und Buerger stehen
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


PROCESS_STEP_ANALYSIS_ADDRESSEE_CONTEXTS: Dict[str, str] = {
    ADMINISTRATION: (
        "Dieser Lauf betrifft nur den Normadressaten `administration` "
        "(Verwaltung). Verwaltungstaetigkeiten sind Bearbeitungs- oder "
        "Vollzugshandlungen der zustaendigen Behoerde, z.B. Pruefung, "
        "Bescheidung, Aufsicht, Register- oder Aktenfuehrung."
    ),
    BUSINESS: (
        "Dieser Lauf betrifft nur den Normadressaten `business` "
        "(Wirtschaft). Unternehmenstaetigkeiten sind Handlungen von Unternehmen "
        "zur Erfuellung der Vorgabe, z.B. Melden, Nachweisen, Dokumentieren, "
        "interne Ablaeufe anpassen oder bei behoerdlichen Pruefungen mitwirken."
    ),
    CITIZENS: (
        "Dieser Lauf betrifft nur den Normadressaten `citizens` "
        "(Buergerinnen und Buerger). Buergerseitige Taetigkeiten sind "
        "Handlungen der privaten Pflichterfuellung, z.B. informieren, "
        "Unterlagen beschaffen, Formulare ausfuellen, erscheinen, bezahlen "
        "oder Dritte beauftragen."
    ),
}


PROCESS_STEP_ANALYSIS_ADDRESSEE_RULES: Dict[str, str] = {
    ADMINISTRATION: (
        "Jede Taetigkeit beschreibt eine Bearbeitungshandlung der Verwaltung "
        "pro einzelnem Vorgang (z.B. Unterlagen sichten, Zweckzuordnung "
        "pruefen, Bescheid erstellen). Geben Sie nur fachlich relevante "
        "Haupttaetigkeiten aus, die fuer den Vorher-Nachher-Vergleich der "
        "Fallgruppe benoetigt werden. Uebernehmen Sie keine Handlungen der "
        "Wirtschaft und keine privaten Handlungen von Buergerinnen und "
        "Buergern als Verwaltungstaetigkeit. Schaetzen Sie in der "
        "Schrittanalyse keine Lohngruppen, Stundenloehne, Zeitaufwaende, "
        "Sachaufwaende oder Kosten."
    ),
    BUSINESS: (
        "Jede Taetigkeit beschreibt eine Handlung des Unternehmens zur "
        "Erfuellung der Vorgabe (z.B. Daten beschaffen, Meldung erstellen, "
        "Betriebspruefung begleiten, interne Prozesse anpassen). Orientieren "
        "Sie sich bei Informationspflichten an Teil A der Checkliste, bei "
        "anderen Vorgaben zusaetzlich an Teil B. IT- oder "
        "Automatisierungsbezug darf in der Beschreibung genannt werden, wenn "
        "er den Handlungskern praegt. Uebernehmen Sie keine "
        "Verwaltungshandlungen (z.B. Bescheiderstellung, behoerdliche "
        "Pruefung) und keine rein privaten Handlungen von Buergerinnen und "
        "Buergern als Unternehmenstaetigkeit. Schaetzen Sie in der "
        "Schrittanalyse keine Zeitaufwaende, Stundenloehne, Sachaufwaende, "
        "IT-/Personalaufwaende oder Kosten."
    ),
    CITIZENS: (
        "Jede Taetigkeit muss eine Handlung der Buergerinnen und Buerger "
        "selbst sein. Unzulaessig sind insbesondere verwaltungsinterne "
        "Pruefungen, Bescheiderstellung, interne Ruecksprachen, "
        "Unternehmensablaeufe oder fachliche Schritte Dritter. Geben Sie nur "
        "die minimale, aber vollstaendige Menge buergerseitiger "
        "Haupttaetigkeiten aus. Schaetzen Sie in der Schrittanalyse keine "
        "Zeit- oder Sachaufwaende und keine Kosten."
    ),
}


ADMINISTRATION_PROMPT_RULES: Dict[str, str] = {
    PromptId.PROCESS_COMPILATION: (
        "Buendeln Sie Vorgaben zu Prozessen entlang der Bearbeitungslogik der "
        "zustaendigen Behoerde, nicht entlang einzelner Paragraphen. Typische "
        "Prozessbildende Raster sind: (i) Antrags-/Anerkennungsverfahren mit "
        "Bescheidung, (ii) turnusmaessige Pruefung bzw. laufende Aufsicht und "
        "Kontrolle, (iii) anlassbezogene Einzelfallpruefung (z.B. Verdacht, "
        "Stichprobe, Beschwerde), (iv) Rechtsbehelfs-/Widerspruchsverfahren, "
        "(v) Erstattungs-, Auszahlungs- oder Foerderverfahren, (vi) Register-, "
        "Melde- und Aktenfuehrung, (vii) einmalige interne Umstellung "
        "(IT-Anpassung, Formular- und Merkblattpflege, Schulung). Vorgaben, "
        "die praktisch innerhalb desselben Verfahrensganges erfuellt werden, "
        "gehoeren in denselben Prozess; fachlich klar getrennte Verfahren "
        "bleiben getrennt. Fuehren Sie Vollzugsaufwand auch dann aus, wenn er "
        "durch einen Antrag der Wirtschaft oder der Buergerinnen/Buerger "
        "ausgeloest wird. Erfinden Sie keine Verwaltungsprozesse, zu "
        "denen die Regelung keinen konkreten Vollzugsauftrag enthaelt. "
        "Beruecksichtigen Sie auch das fiskalische Handeln der Verwaltung als "
        "Normadressat (z.B. als Halter von Kfz oder als Bauherr) als Teil des "
        "Erfuellungsaufwands der Verwaltung."
    ),
    PromptId.CASE_GROUP_DEVELOPMENT: (
        "Typische verwaltungsseitige Differenzierungsachsen sind: (i) "
        "Ersterfuellung/Erstanerkennung versus turnusmaessige oder wiederholte "
        "Bearbeitung, (ii) Standardfall mit glatter Bescheidung versus "
        "Sonderpruefung mit Rueckfragen, Anhoerung oder Gutachtenbedarf, "
        "(iii) weitgehend automatisierter oder digital gestuetzter Vollzug "
        "versus manuelle Einzelbearbeitung, (iv) Massengeschaeft mit "
        "standardisierter Pruefung versus aufwaendige Einzelpruefung, "
        "(v) einmaliger Umstellungsaufwand (Schulung, IT-Anpassung, "
        "Formularpflege) versus laufender Vollzug. Bilden Sie solche "
        "Fallgruppen nur, wenn daraus wesentliche Unterschiede im "
        "Bearbeitungsaufwand pro Fall folgen - ausgedrueckt in Zeit pro "
        "Vorgang, erforderlicher Lohngruppe oder benoetigter "
        "IT-/Sachunterstuetzung. Bilden Sie keine Fallgruppen, nur weil "
        "unterschiedliche Paragraphen beruehrt werden oder die materielle "
        "Rechtslage leicht abweicht, solange der Bearbeitungsweg derselbe "
        "bleibt. Setzen Sie den `aenderungsstatus` je Fallgruppe differenziert: "
        "`eingefuehrt` nur bei durch die Regelung neu entstehenden Fallgruppen, "
        "`abgeschafft` nur bei wegfallenden, `geaendert` nur dann, wenn sich "
        "Bearbeitungsaufwand oder Fallzahl der Fallgruppe durch die Regelung "
        "tatsaechlich aendert. Unveraenderte Nebenfallgruppen sind nicht "
        "auszuweisen."
    ),
    PromptId.CASES_CALCULATION: (
        "Fuer die Verwaltung ist die `Anzahl Betroffene` NICHT die Zahl extern "
        "betroffener Buerger oder Unternehmen, sondern die Zahl der jaehrlich "
        "tatsaechlich von der Verwaltung zu bearbeitenden Vorgaenge, Faelle oder "
        "Antraege derselben Fallgruppe. Die `Haeufigkeit pro Jahr` ist in der "
        "Regel 1, es sei denn ein Vorgang wiederholt sich nachweislich mehrfach "
        "pro Jahr pro Fall (z.B. periodische Kontrollen). Setzen Sie niemals "
        "`anzahl_betroffene = 0`, wenn es eine zugeordnete Fallgruppe mit "
        "Bearbeitungsaufwand gibt - ohne Faelle waere die Fallgruppe nicht zu "
        "bilden. Liegen keine konkreten "
        "Zahlen vor, schaetzen Sie sachgerecht basierend auf dem "
        "Normzitat/Regelungsgegenstand und typischen Vollzugsmengen der "
        "zustaendigen Behoerde; geben Sie niemals Platzhalter-Nullen aus."
    ),
}


BUSINESS_PROMPT_RULES: Dict[str, str] = {
    PromptId.PROCESS_COMPILATION: (
        "Buendeln Sie Vorgaben zu Prozessen entlang des operativen Ablaufs im "
        "Unternehmen, nicht entlang einzelner Paragraphen. Typische prozessbildende "
        "Raster sind: (i) Anzeige-, Melde- oder Nachweispflicht gegenueber Behoerden, "
        "(ii) laufende Dokumentations- und Aufbewahrungspflicht, (iii) "
        "Informationspflicht gegenueber Kundinnen/Kunden, Beschaeftigten oder "
        "Geschaeftspartnern, (iv) Beschaffung oder Umruestung von Anlagen, Waren oder "
        "Material, (v) interne Prozess- und IT-Umstellung inklusive Schulung des "
        "Personals, (vi) Mitwirkung bei Pruefungen durch oeffentliche Stellen "
        "(z.B. Betriebspruefung), (vii) fiskalische Pflichten wie Gebuehren oder "
        "Abgaben. Trennen Sie Informationspflichten von anderen Vorgaben, weil "
        "Buerokratiekosten aus Informationspflichten spaeter gesondert fuer den "
        "Buerokratiekostenindex (BKI) auszuweisen sind. Benennen Sie wo moeglich die "
        "betroffenen Wirtschaftszweige oder Unternehmenskreise; pruefen Sie "
        "insbesondere, ob kleine und mittlere Unternehmen (KMU) besonders betroffen "
        "sind. Uebernehmen Sie keine Verwaltungslogik (Bescheide, Vollzugshandeln) "
        "und keine privaten Buergerhandlungen."
    ),
    PromptId.CASE_GROUP_DEVELOPMENT: (
        "Typische wirtschaftsseitige Differenzierungsachsen sind: (i) "
        "Informationspflicht versus sonstige Vorgabe (BKI-Relevanz), (ii) "
        "Ersterfuellung mit Einarbeitung versus Routineerfuellung (Einarbeitung "
        "faellt bei Routine in der Regel weg), (iii) Neuanschaffung versus "
        "Umruestung bestehender Anlagen, (iv) weitgehend automatisierter oder "
        "digital gestuetzter Ablauf versus manuelle Bearbeitung, (v) KMU versus "
        "Grossunternehmen, soweit sich der Aufwand pro Fall wesentlich "
        "unterscheidet, (vi) einmaliger Umstellungsaufwand (IT, Schulung, "
        "Formularpflege) versus laufender Aufwand. Bilden Sie solche Fallgruppen "
        "nur, wenn daraus wesentliche Unterschiede im Personal- oder Sachaufwand "
        "pro Fall folgen. Bilden Sie keine Fallgruppen nur deshalb, weil "
        "unterschiedliche Paragraphen oder Behoerden beruehrt sind, solange der "
        "operative Ablauf im Unternehmen derselbe bleibt. Setzen Sie den "
        "`aenderungsstatus` je Fallgruppe differenziert: `eingefuehrt` nur bei "
        "neu entstehenden Fallgruppen, `abgeschafft` nur bei wegfallenden, "
        "`geaendert` nur dann, wenn sich Aufwand oder Fallzahl der Fallgruppe "
        "durch die Regelung tatsaechlich aendert."
    ),
    PromptId.CASES_CALCULATION: (
        "Bei periodisch zu erfuellenden Vorgaben ergibt sich die Fallzahl aus der "
        "Multiplikation der betroffenen Unternehmen mit der Periodizitaet pro Jahr. "
        "Bei anlassbezogenen Vorgaben ist die jaehrlich zu erwartende Zahl der "
        "Faelle zugrunde zu legen; bei Ueberwachungs- und Kontrollmassnahmen ist "
        "die Fallzahl oft deutlich geringer als die Zahl der Betroffenen "
        "(Stichproben). Einmaliger Erfuellungsaufwand bei Einfuehrung der Regelung "
        "(z.B. IT-Umstellung, Austausch von Anlagen, Erstschulung) ist gesondert "
        "auszuweisen und nicht mit laufenden jaehrlichen Faellen zu vermischen. "
        "Bei Ersatzinvestitionen, die ohnehin im Rahmen der wirtschaftlichen "
        "Nutzungsdauer faellig geworden waeren, sind nur 50 Prozent der "
        "Anschaffungskosten als Erfuellungsaufwand anzusetzen (Sowieso-Anteil), "
        "sofern kein anderer Anteil fachlich begruendet ist. Setzen Sie niemals "
        "`anzahl_betroffene = 0`, wenn es eine zugeordnete Fallgruppe mit "
        "Aufwand gibt; liegen keine konkreten Zahlen vor, schaetzen Sie "
        "sachgerecht basierend auf Wirtschaftszweig und typischen "
        "Unternehmensmengen. Weisen Sie, wenn fachlich relevant, den KMU-Anteil "
        "an der Fallzahl gesondert aus."
    ),
}


CITIZENS_PROMPT_RULES: Dict[str, str] = {
    PromptId.PROCESS_COMPILATION: (
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
        "Fuer Buergerinnen und Buerger koennen sich typische Fallgruppen insbesondere unterscheiden "
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
    PromptId.CASES_CALCULATION: (
        "Bei periodisch zu erfuellenden privaten Pflichten von Buergerinnen und Buergern ergibt sich die Fallzahl "
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
        "nicht in Einzeltaetigkeiten zerlegt wurde, koennen gesicherte Erfahrungswerte "
        "in Personentagen oder Personenmonaten genutzt und anschliessend umgerechnet "
        "werden. Fuer die Beschaeftigten im oeffentlichen Dienst gelten bei einer "
        "40-Stunden-Woche als Richtwerte 1 Personentag = 8 Stunden, 1 Personenmonat = "
        "134 Stunden und 1 Personenjahr = 200 Arbeitstage."
    ),
    BUSINESS: (
        "Eine Reihe von Taetigkeiten laeuft bei Nutzung entsprechender "
        "Informationstechnologie automatisch ab. Aus automatisch ablaufenden Prozessen "
        "resultiert zunaechst kein Zeitaufwand. Sofern keine spezifischen Daten ueber "
        "den Zeitaufwand vorliegen, kann die Zeitwerttabelle Wirtschaft aus Anhang 4 "
        "herangezogen werden. Die Tabelle zu Wegezeiten und -sachkosten kann genutzt "
        "werden, wenn persoenliche Termine bei anderen Stellen oder Behoerden "
        "erforderlich sind. Orientieren Sie sich fuer Standardaktivitaeten zusaetzlich "
        "am Standardkostenmodell und den Methodenhinweisen in Anhang 8. Zur Ermittlung "
        "des Personalaufwands werden die Bearbeitungszeiten mit den einschlaegigen "
        "Lohnsaetzen der Wirtschaft verknuepft. Die festen Lohngruppen sind "
        "A=Niedrig, B=Mittel, C=Hoch, D=Durchschnitt. Ordnen Sie jede benoetigte "
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
        "Plausibilitaet fuer den konkreten Fall.\n\n"
        "Wegezeiten und Wegesachkosten: Wenn die Regelung ein persoenliches Erscheinen "
        "bei einer Behoerde oder Stelle vorschreibt und keine Alternative wie Postweg "
        "oder Online-Verfahren erlaubt, erfassen Sie die Wegezeit in Minuten als "
        "Teil des Zeitaufwands und die Wegesachkosten (Porto, Fahrtkosten fuer OEPNV "
        "oder Kraftstoff fuer das eigene Fahrzeug) in Euro als Teil des Sachaufwands. "
        "Die dazu vorgesehenen Pauschalwerte pro Verwaltungsebene finden Sie in "
        "Anhang 5 'Wegezeiten und -sachkosten'. Fuehren Sie Wegesachkosten nicht als "
        "eigene Taetigkeit aus, sondern integriert in der jeweils ausloesenden "
        "Taetigkeit.\n\n"
        "Sachaufwand umfasst darueber hinaus Gebuehren, Anschaffungen, Materialkosten "
        "sowie zwingend ausgeloeste Kosten fuer Dritte wie Notare oder "
        "Sachverstaendige. Geben Sie den Zeit- und Sachaufwand jeweils fuer gueltige "
        "und vorgeschlagene Rechtslage getrennt an. Wenn fuer eine Taetigkeit kein "
        "Sachaufwand anfaellt, verwenden Sie 0. Wenn fuer eine Taetigkeit kein "
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
{
"normadressat": "{norm_addressee}",
"prozesse": [
    {
    "prozess_id": "",
    "prozess_bezeichnung": "",
    "prozess_beschreibung": "",
    "aenderungsstatus": "",
    "vorgaben": [
        {
            "vorgaben_id": "",
            "normzitat": "",
            "beschreibung": "",
            "aenderungsstatus": ""
        }
    ],
    "fallgruppen": [
        {
            "fallgruppen_id": "",
            "fallgruppe_bezeichnung": "",
            "fallgruppe_beschreibung": "",
            "aenderungsstatus": "",
            "taetigkeiten": [
                {
                    "taetigkeiten_id": "",
                    "taetigkeit": "",
                    "beschreibung": "",
                    "aenderungsstatus": "",
                    "rollen_gueltig": [
                        {
                            "rolle": "",
                            "lohngruppe": "A | B | C | D",
                            "schwierigkeitsgrad": "",
                            "stundenlohn": "",
                            "zeitaufwand_in_min": ""
                        }
                    ],
                    "sachaufwand_gueltig": "",
                    "rollen_vorschlag": [
                        {
                            "rolle": "",
                            "lohngruppe": "A | B | C | D",
                            "schwierigkeitsgrad": "",
                            "stundenlohn": "",
                            "zeitaufwand_in_min": ""
                        }
                    ],
                    "sachaufwand_vorschlag": "",
                    "ausfuehrung_pro_einzelfall": "0 | 1"
                }
            ]
        }
    ]
    }
]
}

Das Feld `normadressat` ist fuer diesen Lauf fest vorgegeben und muss exakt `{norm_addressee}` lauten.
"""


EFFORT_JSON_SCHEMA_BY_ADDRESSEE: Dict[str, str] = {
    CITIZENS: """
{
"normadressat": "citizens",
"prozesse": [
    {
    "prozess_id": "",
    "prozess_bezeichnung": "",
    "prozess_beschreibung": "",
    "aenderungsstatus": "",
    "vorgaben": [
        {
            "vorgaben_id": "",
            "normzitat": "",
            "beschreibung": "",
            "aenderungsstatus": ""
        }
    ],
    "fallgruppen": [
        {
            "fallgruppen_id": "",
            "fallgruppe_bezeichnung": "",
            "fallgruppe_beschreibung": "",
            "aenderungsstatus": "",
            "taetigkeiten": [
                {
                    "taetigkeiten_id": "",
                    "taetigkeit": "",
                    "beschreibung": "",
                    "aenderungsstatus": "",
                    "zeitaufwand_in_min_gueltig": "",
                    "sachaufwand_gueltig": "",
                    "zeitaufwand_in_min_vorschlag": "",
                    "sachaufwand_vorschlag": "",
                    "ausfuehrung_pro_einzelfall": "0 | 1"
                }
            ]
        }
    ]
    }
]
}

Das Feld `normadressat` ist immer `citizens` fuer dieses Schema.
"""
}


# Die eigentlichen vollstaendigen Prompt-Templates stehen hier in der
# fachlichen Abruf-Reihenfolge der Pipeline:
# 1. LAW_SUMMARY
# 2. REGULATIONS_IDENTIFICATION
# 3. PROCESS_COMPILATION
# 4. CASE_GROUP_DEVELOPMENT
# 5. PROCESS_STEP_ANALYSIS
# 6. CASES_CALCULATION
# 7. EFFORT_CALCULATION
#
# Technisch wird per PromptId-Key zugegriffen; diese Reihenfolge ist fuer
# Menschen, damit man die Prompt-Pipeline direkt von oben nach unten lesen kann.
PROMPT_TEMPLATES: Dict[str, str] = {
    # Render contract:
    # - gesetz_gueltig: str
    # - gesetz_vorschlag: str
    PromptId.LAW_SUMMARY: (
        """
        Sie sind Legist im deutschen Bundestag. 

        Vergleichen Sie den derzeit gueltigen Gesetzestext mit dem vorgeschlagenen 
        Gesetzesvorschlag. Leiten Sie daraus ab, was der Gesetzgeber erreichen moechte. 
        Geben Sie strikt JSON zurueck im Format: {{\"title\": \"...\", \"blurb\": \"...\", \"summary\": \"...\"}}.

        {law_mode_context}

        Der 'title' soll ein kurzer Titel sein (max. 12 Woerter), der 'blurb' soll genau ein Satz sein. Fuer die 'summary' geben Sie bitte eine 
        ausfuehrliche Zusammenfassung an, mit Hilfe derer man die Ziele und wesentlichen Unterschiede der Gesetzesaenderung verstehen kann ohne 
        die zwei Gesetzestexte vorliegen zu haben.

        Geltendes Gesetz: {gesetz_gueltig}

        Gesetzesvorschlag: {gesetz_vorschlag}
        """
    ),
    # Render contract:
    # - gesetz_gueltig: str
    # - gesetz_vorschlag: str
    # - law_summary: str, optional if session_id/app_session_id is provided
    PromptId.REGULATIONS_IDENTIFICATION: (
        LEGIST_PROMPT_OPENING
        + """ 
        {law_mode_context}

        Folgendes ist das konsolidierte, geltende Gesetz: {gesetz_gueltig}

        Folgendes konsolidiertes Gesetz wird vorgeschlagen: {gesetz_vorschlag}

        Ihre Aufgabe ist, ausgehend von den konsolidierten Versionen die Gesetzesaenderungen herauszuarbeiten und alle darin enthaltenen Vorgaben 
        (Einzelregelungen) im nachfolgenden Sinne zu identifizieren. 
        Wichtig: Jede Gesetzesaenderung kann keine, eine oder mehrere Vorgaben enthalten. Identifizieren Sie alle relevanten Vorgaben und geben Sie den Status an, 
        also ob es sich um entweder eine Einfuehrung, eine Aenderung, oder eine Streichung/Loeschung handelt.
        Beruecksichtigen Sie dabei auch implizite Aenderungen von Vorgaben, bei denen bisher Betroffene wegfallen, weil sie kuenftig stattdessen einem neuen
        Prozess unterliegen; solche Faelle sind ebenfalls als eigene relevante Vorgaben mit passendem Aenderungsstatus auszuweisen.

        Bestimmen Sie fuer jede Vorgabe ausserdem:
        * welche Normadressaten betroffen sind: administration, business, citizens,
        * ob es sich um eine Informationspflicht der Wirtschaft handelt.

        Zum Normadressaten Verwaltung zaehlen alle mit der Wahrnehmung von Verwaltungsaufgaben betrauten Verwaltungstraeger (rechtsfaehige Koerperschaften, Anstalten und Stiftungen 
        des oeffentlichen Rechts einschliesslich Beliehene im Rahmen der ihnen uebertragenen hoheitlichen Kompetenzen). Soweit Koerperschaften/Anstalten des 
        oeffentlichen Rechts privatwirtschaftlich taetig sind und in Wettbewerb stehen (z. B. kostenpflichtige Schulungen der Kammern; Universitaeten bei 
        Forschungsfoerderungen) sind diese als Wirtschaft zu behandeln. Soweit Unternehmen hoheitliche Aufgaben wahrnehmen (z. B. Beliehene wie Pruefingenieure, 
        Bezirksschornsteinfegermeister, Tieraerzte bei Fleischbeschau), sind diese als Verwaltung zu behandeln. Soweit oeffentliche Unternehmen, die Aufgaben der 
        Daseinsvorsorge im staatlichen Auftrag erfuellen (z. B. Wasserkraftwerke in oeffentlicher Hand) sind diese als Verwaltung zu behandeln. Die Rechtsform 
        bietet nur Anhaltspunkte; massgeblich ist die vorgeschriebene Taetigkeit.

        Der Normadressat Wirtschaft umfasst alle Akteure, die eine wirtschaftliche Taetigkeit am Markt ausueben, wobei die Rechtsform oder eine Gewinnerzielungsabsicht
        nicht ausschlaggebend sind. Hierzu zaehlen primaer private Unternehmen jeder Groesse (einschliesslich KMU), Selbststaendige sowie Freiberufler. Zur Wirtschaft gehoeren
        im Sinne des Erfuellungsaufwands auch gemeinnuetzige Organisationen wie Vereine, Verbaende oder Stiftungen, sofern sie als Arbeitgeber agieren oder Dienstleistungen
        im Wettbewerb anbieten. In Abgrenzung zur Verwaltung sind zudem oeffentliche Institutionen (wie Universitaeten oder Kammern) der Wirtschaft zuzurechnen,
        wenn sie privatwirtschaftlich taetig werden und in Konkurrenz zu privaten Anbietern treten.

        Der Normadressat Buergerinnen und Buerger definiert sich durch natuerliche Personen, die von einer gesetzlichen Regelung in ihrer Rolle als Privatperson betroffen sind.
        Der Aufwand wird dieser Gruppe immer dann zugeordnet, wenn die Taetigkeit der privaten Lebensfuehrung dient und nicht im Rahmen einer beruflichen, gewerblichen
        oder hoheitlichen Aufgabe erfolgt. Ein typisches Beispiel ist die Erfuellung von Verhaltenspflichten im Alltag, wie etwa die Einhaltung der M+S-Reifenpflicht
        bei privaten Kraftfahrzeugen. Im Gegensatz zur Wirtschaft und Verwaltung wird bei den Buergerinnen und Buergern primaer der Zeitaufwand fuer Taetigkeiten
        (z. B. Informationsbeschaffung oder das Ausfuellen von Formularen) sowie der private Sachaufwand ermittelt, ohne dass eine generelle Monetarisierung der Zeit erfolgt.

        Definition von Vorgaben:
        * Vorgaben sind Einzelregelungen, die unmittelbar zu Aenderungen von Kosten oder Zeitaufwand bei den Normadressaten fuehren.
        * Sie beruhen auf bundesrechtlichen Regelungen und verpflichten Normadressaten, bestimmte Ziele zu erreichen, Vorgaben einzuhalten oder Handlungen 
          vorzunehmen bzw. zu unterlassen.
        * Dazu zaehlen auch Verpflichtungen zur Kooperation mit Dritten sowie zur Ueberwachung und Kontrolle von Zustaenden, Handlungen, numerischen Werten oder 
          Verhaltensweisen. Informationspflichten bilden eine Teilmenge der Vorgaben.

        "Unmittelbar" bedeutet, dass der Kosten- oder Zeitaufwand direkt aus der Befolgung der Vorgabe entsteht. Normadressaten muessen die Vorgaben einhalten, 
        um Rechtsverstoesse oder den Verlust von Anspruechen zu vermeiden. Auch Regelungen, die nur Ziele, Grenzwerte oder foerderbedingte Verhaltensaenderungen 
        vorgeben, gelten als Vorgaben, wenn sie direkt Aufwand ausloesen.

        Bei der Identifizierung von Vorgaben ist zu beachten, dass der Gesetzgeber zum Teil neben  Ge- oder Verboten lediglich Ziele oder Grenzwerte festlegt
        oder zum Beispiel durch staatliche Foerderungen Verhaltensaenderungen erreichen will. Auch solche Einzelregelungen sind  als Vorgaben zu verstehen, weil
        sie unmittelbar zur Aenderung von Kosten bzw. Zeitaufwand  bei den Normadressaten fuehren.

        Wichtig fuer den Normadressaten `administration` (Verwaltung): Uebersehen Sie die Verwaltung nicht. Pruefen Sie bei jeder Vorgabe ausdruecklich,
        ob sie der zustaendigen Behoerde einen konkreten Vollzugsauftrag auferlegt – typische Ausloeser sind Antrags-, Anzeige-, Genehmigungs-,
        Anerkennungs-, Melde-, Register- oder Nachweisverfahren, laufende Aufsicht und Kontrollen, anlassbezogene Einzelfallpruefungen,
        Bescheidung und Rechtsbehelfsverfahren, Auszahlungs- oder Foerderverfahren sowie einmalige interne Umstellungen (IT, Formulare,
        Schulung). Wenn die Erfuellung einer Vorgabe durch Wirtschaft oder Buergerinnen/Buerger praktisch nur moeglich ist, weil die
        Verwaltung etwas pruefen, bescheiden, registrieren, kontrollieren oder auszahlen muss, ist `administration` zusaetzlich als
        betroffener Normadressat auszuweisen. Ein bloss mittelbarer Mehraufwand ohne
        konkreten Vollzugsauftrag ist hingegen nicht der Verwaltung zuzuordnen – erfinden Sie keine Verwaltungsvorgaben, wo keine sind.

        Hinweis zu `ist_informationspflicht_wirtschaft`: Dieses Flag ist ausschliesslich fuer den Normadressaten
        Wirtschaft (`business`) vorgesehen und kennzeichnet eine Informationspflicht im Sinne des Leitfadens.
        Setzen Sie das Flag nur dann auf "1", wenn (a) `business` im `normadressaten`-Array enthalten ist UND
        (b) die Vorgabe fuer die Wirtschaft eine Informationspflicht darstellt. In allen anderen Faellen - also
        bei reinen Verwaltungs- oder Buerger-Vorgaben, oder bei Wirtschaftsvorgaben ohne Informationspflicht-Charakter -
        setzen Sie das Flag auf "0".

        Geben Sie nur und ausschliesslich JSON im folgenden Format zurueck:

        {{
          "vorgaben": [
            {{
              "normzitat": "",
              "beschreibung": "",
              "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft",
              "normadressaten": ["administration | business | citizens"],
              "ist_informationspflicht_wirtschaft": "0 | 1"
            }}
          ]
        }}

        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen.
        """
    ),
    # Render contract:
    # - vorgaben_json: JSON string of list[VorgabePayload]
    # - norm_addressee: "administration" | "business" | "citizens"
    # - law_summary: str, optional if session_id/app_session_id is provided
    # Auto-filled by render_prompt:
    # - handbook_process_example
    # - norm_addressee_context
    # - norm_addressee_rule
    PromptId.PROCESS_COMPILATION: (
        LEGIST_PROMPT_OPENING
        + """
        Die Gesetzesaenderung fuehrt zu folgenden Einzelvorgaben fuer den betroffenen Normadressaten: {vorgaben_json}

        {norm_addressee_context}

        Ihre Aufgabe ist, die enthaltenen Vorgaben (Einzelregelungen), welche in der Praxis in einem Zusammenhang erfuellt werden, zu gemeinsamen
        Prozessen zu buendeln. Soweit eine Buendelung von Vorgaben in Prozesse nicht moeglich oder sinnvoll ist, ist die betreffende Einzelvorgabe identisch 
        einem eigenen Prozess zu behandeln. Ein solcher Prozess besteht daher ausschliesslich aus einer Vorgabe. Geben Sie ausserdem den Status an, 
        also ob es sich um entweder eine Einfuehrung, eine Aenderung, oder eine Streichung/Loeschung des Prozesses handelt. Orientieren Sie sich dazu an den 
        Statusangaben der Vorgaben.

        Buendeln Sie Vorgaben aus Unionsrecht und aus nationalem Recht niemals in denselben Prozess. Wenn der zugrunde liegende Rechtsrahmen
        unterschiedlich ist, muessen getrennte Prozesse ausgewiesen werden, auch wenn die praktische Bearbeitung aehnlich erscheint. Die spaetere
        gesonderte Ausweisung EU-bedingten Erfuellungsaufwands muss anhand Ihrer Prozessstruktur weiterhin moeglich bleiben.

        {norm_addressee_rule}

        Offizielles Methodenbeispiel aus dem Leitfaden (woertlich uebernommen):
        {handbook_process_example}

        Geben Sie nur und ausschliesslich JSON im folgenden Format zurueck:

        {{
        "normadressat": "{norm_addressee}",
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

        Das Feld `normadressat` ist fuer diesen Lauf fest vorgegeben und muss exakt `{norm_addressee}` lauten. Bearbeiten Sie ausschliesslich Vorgaben fuer diesen Normadressaten.

        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen.
        """
    ),
    # Render contract:
    # - prozesse_json: JSON string of list[ProzessWithVorgabenPayload]
    # - norm_addressee: "administration" | "business" | "citizens"
    # - law_summary: str, optional if session_id/app_session_id is provided
    # Auto-filled by render_prompt:
    # - handbook_case_group_example
    # - norm_addressee_context
    # - norm_addressee_rule
    PromptId.CASE_GROUP_DEVELOPMENT: (
        LEGIST_PROMPT_OPENING
        + """
        Die Gesetzesaenderung fuehrt zu folgenden, Erfuellungsaufwand ausloesenden Prozessen fuer den betroffenen Normadressaten: {prozesse_json}

        {norm_addressee_context}

        Wenn damit zu rechnen ist, dass der betroffene Normadressat die jeweiligen Prozesse auf unterschiedlichen Wegen erfuellt, sind dafuer sogenannte Fallgruppen zu bilden.
        Dies jedoch nur, soweit durch die verschiedenen Wege wesentliche Unterschiede zu erwarten sind. Fuer jede Fallgruppe ist der Erfuellungsaufwand separat zu
        ermitteln und darzustellen. Dabei ist es unerheblich, ob die Differenzierung erfolgt, weil unterschiedliche Gestaltungsmoeglichkeiten genutzt werden
        oder weil sich die zugrunde liegenden Sachverhalte unterscheiden. Geben Sie ausserdem den Status an, also ob es sich um entweder eine Einfuehrung,
        eine Aenderung, oder eine Streichung/Loeschung der Fallgruppe handelt.

        Soweit eine Bildung von Fallgruppen aus dem jeweiligen Prozess nicht moeglich oder sinnvoll ist, hat der betreffende Prozess nur eine einzige Fallgruppe. 
        Ein solcher Prozess besteht daher ausschliesslich aus einer Fallgruppe.

        {norm_addressee_rule}

        Offizielles Methodenbeispiel aus dem Leitfaden (woertlich uebernommen):
        {handbook_case_group_example}

        Geben Sie nur und ausschliesslich JSON im folgenden Format zurueck:

        {{
        "normadressat": "{norm_addressee}",
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

        Das Feld `normadressat` ist fuer diesen Lauf fest vorgegeben und muss exakt `{norm_addressee}` lauten.

        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen.
        """
    ),
    # Render contract:
    # - case_groups_json: JSON string of list[ProzessWithFallgruppenPayload]
    # - norm_addressee: "administration" | "business" | "citizens"
    # - law_summary: str, optional if session_id/app_session_id is provided
    # Auto-filled by render_prompt:
    # - step_analysis_checklist
    # - step_analysis_addressee_context
    # - step_analysis_addressee_rule
    PromptId.PROCESS_STEP_ANALYSIS: (
        """
        Sie analysieren eine geplante Gesetzesaenderung im Rahmen der Ermittlung
        des Erfuellungsaufwands.

        In diesem Schritt identifizieren Sie ausschliesslich die fachlich
        relevanten Haupttaetigkeiten, die zur Erfuellung einer Vorgabe oder eines
        Prozesses im Einzelfall zu erwarten sind. Diese Taetigkeiten koennen neu
        hinzukommen, sich aendern, wegfallen oder unveraendert bleiben.

        Schaetzen Sie in diesem Schritt keine Minuten, Lohngruppen,
        Stundenloehne, Sachaufwaende oder Kosten.

        Die wesentlichen Unterschiede der Gesetzesaenderung sind wie folgt
        zusammengefasst: {law_summary}

        {step_analysis_addressee_context}

        Die Gesetzesaenderung fuehrt fuer diesen Normadressaten zu folgenden,
        positiven oder negativen Erfuellungsaufwand ausloesenden Prozessen und
        Fallgruppen: {case_groups_json}

        Ihre Aufgabe ist es, die wesentlichen anfallenden Taetigkeiten zur Erfuellung eines Prozesses pro Fallgruppe
        zu identifizieren. Die einzelnen Taetigkeiten koennen vor und nach der Gesetzesaenderung unterschiedlich sein, hinzukommen oder wegfallen, einige Taetigkeiten des
        Prozesses koennen beibehalten bleiben. Geben Sie diesen Aenderungsstatus an, orientieren Sie sich dabei wenn noetig an den vorhandenen
        Statusangaben in den Fallgruppen und Prozessen.

        {step_analysis_addressee_rule}

        Entscheidend ist die Aenderung des Erfuellungsaufwands, nicht die abstrakte Vollbeschreibung des gesamten Verfahrens. Beschreiben Sie daher nur solche
        Taetigkeiten, die fuer die Ermittlung des Unterschieds zwischen geltender Rechtslage und Vorschlag erforderlich sind. Uebernehmen Sie unveraenderte
        Standardschritte nur dann, wenn sie fuer den Vorher-Nachher-Vergleich wirklich benoetigt werden; erfinden Sie keine vollstaendige Verfahrenskette neu,
        wenn sich tatsaechlich nur einzelne Schritte aendern.

        Geben Sie je Taetigkeit `vorgaben_ids` als technische Rueckbindung an
        die ausloesenden Vorgaben dieses Prozesses an. Verwenden Sie nur
        `vorgaben_id`-Werte aus den Vorgaben dieses Prozesses. Wenn im Prozess nur genau eine Vorgabe enthalten ist, verwenden Sie diese ID bei allen
        zugehoerigen Taetigkeiten; wenn mehrere Vorgaben eine Taetigkeit
        gemeinsam ausloesen, geben Sie mehrere passende IDs an.

        {step_analysis_checklist}
        
        Bei Daueraufgaben oder sehr einfachen Pflichterfuellungen reicht eine einzelne, zusammenfassende Haupttaetigkeit aus, wenn eine weitere
        Untergliederung fuer den Vorher-Nachher-Vergleich keinen fachlichen Mehrwert hat.
        
        Geben Sie nur und ausschliesslich JSON im folgenden Format zurueck:

        {{
        "normadressat": "{norm_addressee}",
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
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert",
                            "vorgaben_ids": [""]
                        }},
                        {{
                            "taetigkeit": "",
                            "beschreibung": "",
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert",
                            "vorgaben_ids": [""]
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
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert",
                            "vorgaben_ids": [""]
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
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert",
                            "vorgaben_ids": [""]
                        }},
                        {{
                            "taetigkeit": "",
                            "beschreibung": "",
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert",
                            "vorgaben_ids": [""]
                        }}
                    ]
                }}
            ]
            }}
        ]
        }}

        Das Feld `normadressat` ist fuer diesen Lauf fest vorgegeben und muss exakt `{norm_addressee}` lauten.

        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen.

        """
    ),
    # Render contract:
    # - case_groups_json: JSON string of list[ProzessWithFallgruppenPayload]
    # - norm_addressee: "administration" | "business" | "citizens"
    # - law_summary: str, optional if session_id/app_session_id is provided
    # Auto-filled by render_prompt:
    # - handbook_cases_frequency_example
    # - handbook_cases_case_example
    # - norm_addressee_context
    # - norm_addressee_rule
    PromptId.CASES_CALCULATION: (
        LEGIST_PROMPT_OPENING
        + """
        Die Gesetzesaenderung fuehrt zu folgenden, Erfuellungsaufwand ausloesenden Prozessen fuer den betroffenen Normadressaten, welche durch folgende Fallgruppen 
        differenziert werden: {case_groups_json}

        {norm_addressee_context}

        Ihre Aufgabe ist es, die Aenderung der Fallzahlen jeder dieser Fallgruppen zu bestimmen. Hierzu werden die Haeufigkeit und die Anzahl der Betroffenen 
        vor (_gueltig) und nach (_vorschlag) der geplanten Gesetzesaenderung betrachtet. Bei der Einfuehrung einer Fallgruppe werden typischerweise nur die 
        _vorschlag-Werte angegeben, bei der Loeschung nur die _gueltig-Werte und bei einer Aenderung beide.

        Massgeblich ist auch hier die Aenderung des Erfuellungsaufwands. Schaetzen Sie deshalb nicht losgeloest einen abstrakten Gesamtbestand an Faellen,
        sondern die fuer die geltende und die vorgeschlagene Rechtslage jeweils sachgerechte Fallzahl derselben Fallgruppe.

        Pruefen Sie dabei aktiv, ob die Gesetzesaenderung ueber den reinen Aufwand pro Fall hinaus auch die Fallzahl beeinflusst. Typische Treiber sind
        Verhaltens- und Nachfrageeffekte (ein einfacheres oder attraktiveres Verfahren fuehrt zu mehr Antraegen; hoehere Anforderungen schrecken ab),
        Erweiterung oder Einschraenkung des Adressatenkreises (neue Zielgruppe wird einbezogen bzw. ausgeschlossen), Aenderung der Antrags- oder
        Pruefhaeufigkeit sowie Rechtsklarstellungen, die latente Faelle erstmals in das Verfahren ueberfuehren. Begruenden Sie in der Fallgruppen-
        beschreibung kurz, falls Sie aus solchen Gruenden unterschiedliche Werte fuer _gueltig und _vorschlag ansetzen.

        Identische Werte fuer _gueltig und _vorschlag sind nur dann plausibel, wenn weder Betroffenenkreis noch Haeufigkeit durch die Aenderung
        beruehrt werden und auch kein indirekter Verhaltens- oder Nachfrageeffekt zu erwarten ist. Umgekehrt duerfen Sie Fallzahlen nicht ohne sachlichen
        Grund kuenstlich angleichen, nur weil sich primaer der Aufwand pro Fall aendert.

        Offizielles Methodenbeispiel aus dem Leitfaden (woertlich uebernommen):
        {handbook_cases_frequency_example}

        Offizielles Fallzahlbeispiel aus dem Leitfaden (woertlich uebernommen):
        {handbook_cases_case_example}

        Allgemein gilt: Bei periodisch zu erfuellenden Vorgaben oder Prozessen ergibt sich die Fallzahl aus der Multiplikation der Haeufigkeit mit der Anzahl 
        der Betroffenen. Die Haeufigkeit gibt an, wie oft pro Jahr eine Vorgabe oder ein Prozess erledigt wird bzw. wie haeufig der damit einhergehende 
        Aufwand entsteht. Bei Vorgaben oder Prozessen, die aufgrund der Bearbeitung von Antraegen anlassbezogen erfuellt werden, sollte die Zahl der 
        jaehrlich zu erwartenden Antraege als Fallzahl zugrunde gelegt werden. Bei Schwankungen ist ein sachgerechter Mittelwert zu verwenden. Die Fallzahl 
        fuer Ueberwachungs- und Kontrollmassnahmen ist in der Regel wesentlich geringer.
        Aufwand, der aufgrund der Anpassung an das neue Regelungsvorhaben nur einmal innerhalb einer Organisationseinheit des betroffenen Normadressaten anfaellt, wird als 
        einmaliger Erfuellungsaufwand bzw. Umstellungsaufwannd bezeichnet und ist gesondert auszuweisen.

        {norm_addressee_rule}

        Soweit bestehende Regelungen geaendert werden, koennen Fallzahlen unter Umstaenden auch aus bereits vorliegenden Aufwandsschaetzungen und 
        Gesetzesbegruendungen oder der OnDEA-Datenbank des StBA (https://www.ondea.de/) uebernommen werden. Bevor solche Angaben verwendet werden, sollten 
        sie ggf. aktualisiert werden.

        Geben Sie nur und ausschliesslich JSON im folgenden Format zurueck:

        {{
        "normadressat": "{norm_addressee}",
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

        Das Feld `normadressat` ist fuer diesen Lauf fest vorgegeben und muss exakt `{norm_addressee}` lauten.

        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen.
        """
    ),
    # TODO: How to add this? Die Bereitstellung und Wartung von Informationstechnologie aufgrund der Aenderung von 
    #                        Vorgaben kann jedoch zusaetzlichen Sach- und Personalaufwand erzeugen.
    # Render contract:
    # - step_analysis_json: JSON string of list[ProzessStepAnalysisPayload]
    # - norm_addressee: "administration" | "business" | "citizens"
    # - law_summary: str, optional if session_id/app_session_id is provided
    # Auto-filled by render_prompt:
    # - effort_method_guidance
    # - effort_appendix
    # - effort_json_schema
    # - norm_addressee_context
    PromptId.EFFORT_CALCULATION: (
        LEGIST_PROMPT_OPENING
        + """
        Die Gesetzesaenderung fuehrt zu folgenden, Erfuellungsaufwand ausloesenden Prozessen fuer den betroffenen Normadressaten, welche durch folgende Fallgruppen und 
        Prozessschritte differenziert werden: {step_analysis_json}

        {norm_addressee_context}

        Ihre Aufgabe ist es, den anfallenden Personal- und ggf. Sachaufwand der anfallenden Taetigkeiten pro Einzelfall zu identifizieren. 
        Hierzu werden die Stundenloehne, Zeit- und Sachaufwaende vor (_gueltig) und nach (_vorschlag) der geplanten Gesetzesaenderung betrachtet. Bei der Einfuehrung
        eines Prozessschrittes werden typischerweise nur die _vorschlag-Werte angegeben, bei der Loeschung nur die _gueltig-Werte und bei einer Aenderung beide.

        Entscheidend ist die Aenderung des Erfuellungsaufwands je Fall. Schaetzen Sie daher nicht den gesamten denkbaren Bearbeitungsaufwand eines Verfahrens
        neu, sondern den fuer die geltende und die vorgeschlagene Rechtslage jeweils relevanten Aufwand derselben Taetigkeit. Wenn sich nur ein Teilaspekt
        aendert, darf nicht automatisch der gesamte Schritt neu und vollumfaenglich angesetzt werden. Unveraenderte Aufwaende sollten in _gueltig und
        _vorschlag gleich bleiben; nur geaenderte Mehr- oder Minderaufwaende sind abweichend auszuweisen.

        {effort_method_guidance}

        Unter Sachaufwand faellt der Betriebs-, Unterhaltungs- und Investitionsaufwand, der zur Erfuellung einer Vorgabe oder eines Prozesses zu erwarten ist. 
        Gemeinkosten zaehlen hingegen nicht zum Erfuellungsaufwand. Darueber hinaus notwendige Investitionsaufwendungen des betroffenen Normadressaten sollten bei der 
        Aufwandsermittlung ebenfalls konkret aufgeschluesselt werden. Hierzu zaehlen beispielsweise: 
        • Aufwand fuer die Inanspruchnahme Dritter (z. B. Handwerkerleistungen), 
        • Aufwand fuer die Beschaffung von spezieller Informations- und Kommunikationstechnik, 
        • Aufwand fuer die Nachruestung von Anlagen, 
        • Sachaufwand fuer Wege zu anderen Behoerden oder Stellen (siehe Anhang 5: Wegezeiten und -sachkosten).

        Ausserdem soll angegeben werden, ob die Taetigkeit pro Einzelfall (=1) oder lediglich einmal pro gesamte Fallgruppe (z.B. Einarbeitung in die Vorgabe) ausgefuehrt wird (=0).
        Waehlen Sie =0 immer dann, wenn es sich um einmaligen Umstellungs-, Einfuehrungs-, Abstimmungs- oder Einarbeitungsaufwand handelt, der nicht fuer jeden
        einzelnen Fall erneut anfaellt.

        {effort_appendix}

        Geben Sie nur und ausschliesslich JSON im folgenden Format zurueck: 

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
    render_values.setdefault("law_mode_context", "")
    raw_norm_addressee = render_values.get("norm_addressee")
    if prompt_id in PROMPTS_REQUIRING_NORM_ADDRESSEE and raw_norm_addressee in (None, ""):
        raise KeyError("render_prompt requires explicit norm_addressee")
    norm_addressee = str(raw_norm_addressee or ADMINISTRATION)
    if prompt_id in PROMPTS_REQUIRING_NORM_ADDRESSEE and norm_addressee not in SUPPORTED_NORM_ADDRESSEES:
        raise ValueError(f"Unsupported norm_addressee: {norm_addressee}")
    render_values["norm_addressee_context"] = _render_norm_addressee_context(norm_addressee)
    render_values["norm_addressee_rule"] = _render_prompt_specific_addressee_rule(
        prompt_id,
        norm_addressee,
    )
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
    if prompt_id == PromptId.PROCESS_STEP_ANALYSIS:
        render_values["step_analysis_checklist"] = _render_step_analysis_checklist(norm_addressee)
        render_values["step_analysis_addressee_context"] = _render_step_analysis_addressee_context(
            norm_addressee,
        )
        render_values["step_analysis_addressee_rule"] = _render_step_analysis_addressee_rule(
            norm_addressee,
        )

    if prompt_id == PromptId.EFFORT_CALCULATION:
        render_values["effort_method_guidance"] = _render_effort_method_guidance(norm_addressee)
        render_values["effort_appendix"] = _render_effort_appendix(norm_addressee)
        render_values["effort_json_schema"] = _render_effort_json_schema(norm_addressee)

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

    prompt = template.format(**appendix_values, **render_values)
    return prompt


# Verwaltungs-Checkliste aus Leitfaden Erfuellungsaufwand (Feb 2026),
# Kap. 7.2.1, S. 49 ("Checkliste: Taetigkeiten der Verwaltung zur Erfuellung
# von Vorgaben oder Prozessen"). Enthaelt verwaltungsinterne Taetigkeiten
# (Bescheid erstellen, Eingangsbestaetigung, Ueberwachung/Risikoklassifizierung,
# Zahlungen anweisen) und ist laut Leitfaden ausschliesslich fuer die
# Verwaltung vorgesehen.
_PROCESS_STEP_ANALYSIS_CHECKLIST_ADMINISTRATION = (
    "Als Hilfsmittel fuer die Identifizierung der zu erwartenden Taetigkeiten kann die nachfolgende Checkliste mit moeglichen Taetigkeiten zur Erfuellung \n"
    "        von Vorgaben oder Prozessen herangezogen werden. Es kann sich in einzelnen Faellen anbieten, die Checkliste um spezielle Taetigkeiten zu erweitern.\n\n"
    "        Orientieren Sie die Bildung der Taetigkeiten eng an dieser Checkliste, damit die Prozessschritte zwischen verschiedenen Regelungsvorhaben nachvollziehbar\n"
    "        und vergleichbar bleiben. Bilden Sie keine kuenstlich kleinteiligen Einzelschritte, sondern wenige, fachlich klare Haupttaetigkeiten. Weichen Sie\n"
    "        von einer knappen Darstellung nur ab, wenn der Sachverhalt es fachlich erfordert.\n"
    "        Fassen Sie eng zusammenhaengende Unterhandlungen zu einem gemeinsamen Prozessschritt zusammen, statt sie separat auszuweisen.\n\n"
    "        Checkliste (Verwaltung, Leitfaden Erfuellungsaufwand Feb 2026, Kap. 7.2.1, S. 49):\n"
    "        • Mit der Vorgabe vertraut machen \n"
    "        • Beratung, Fuehren von Vorgespraechen mit Antragstellerinnen und Antragstellern \n"
    "        • Formelle Pruefung, Daten und Informationen sichten und zusammenstellen, Vollstaendigkeitspruefung \n"
    "        • Eingangsbestaetigung oder fehlende Daten/Informationen einholen \n"
    "        • Inhaltliche Pruefung, Berechnungen und Bewertungen durchfuehren \n"
    "        • Interne oder externe Besprechungen (z. B. Anhoerungen) \n"
    "        • Formulare ausfuellen bzw. vervollstaendigen, Daten erfassen, Kennzeichnungen vornehmen \n"
    "        • Ergebnisse/Berechnungen pruefen und ggf. korrigieren \n"
    "        • Datenuebermittlung und Veroeffentlichung \n"
    "        • Zahlungen anweisen \n"
    "        • Korrektur (z. B. aufgrund von Beteiligungsverfahren) bzw. weitere Informationen bei Rueckfragen vorlegen \n"
    "        • Informationen abschliessend aufbereiten \n"
    "        • Bescheid erstellen \n"
    "        • Kopieren, verteilen, archivieren, dokumentieren \n"
    "        • Ueberwachungs- und Aufsichtsmassnahmen, Risikoklassifizierung \n"
    "        • Beschaffen von Waren, Dienstleistungen und/oder zusaetzlichem Personal \n"
    "        • Anpassen von internen Prozessablaeufen \n"
    "        • Teilnahme an Fortbildungen und Schulungen \n"
    "        • Wege zu anderen Behoerden, Organisationen oder Unternehmen \n\n"
    "        In der Praxis sind selten alle oben aufgefuehrten Taetigkeiten relevant. Auch hier gilt: lieber eine kleine Zahl klar abgegrenzter und gut\n"
    "        begruendbarer Haupttaetigkeiten als eine lange Liste kleinteiliger Einzeltaetigkeiten."
)


# Wirtschafts-Checkliste aus Leitfaden Erfuellungsaufwand (Feb 2026),
# Kap. 6.2.1, S. 37-38. Teil A listet Standardaktivitaeten zur Erfuellung
# von Informationspflichten, Teil B ergaenzende Taetigkeiten fuer Vorgaben,
# die keine Informationspflichten sind. Die Verwaltungs-Checkliste (Kap. 7)
# ist fuer die Wirtschaft nicht vorgesehen.
_PROCESS_STEP_ANALYSIS_CHECKLIST_BUSINESS = (
    "Als Hilfsmittel fuer die Identifizierung der zu erwartenden Taetigkeiten koennen die nachfolgenden Checklisten mit moeglichen Taetigkeiten \n"
    "        zur Erfuellung von Vorgaben oder Prozessen herangezogen werden. Es kann sich in einzelnen Faellen anbieten, die Checkliste um spezielle Taetigkeiten zu erweitern.\n\n"
    "        Orientieren Sie die Bildung der Taetigkeiten eng an dieser Checkliste, damit die Prozessschritte zwischen verschiedenen Regelungsvorhaben nachvollziehbar\n"
    "        und vergleichbar bleiben. Bilden Sie keine kuenstlich kleinteiligen Einzelschritte, sondern wenige, fachlich klare Haupttaetigkeiten. Weichen Sie\n"
    "        von einer knappen Darstellung nur ab, wenn der Sachverhalt es fachlich erfordert.\n"
    "        Fassen Sie eng zusammenhaengende Unterhandlungen zu einem gemeinsamen Prozessschritt zusammen, statt sie separat auszuweisen.\n\n"
    "        Checkliste Teil A – Taetigkeiten zur Erfuellung von Informationspflichten der Wirtschaft\n"
    "        (Leitfaden Erfuellungsaufwand Feb 2026, Kap. 6.2.1, S. 37):\n"
    "        • Einarbeitung in die Informationspflicht \n"
    "        • Beschaffung von Daten \n"
    "        • Formulare ausfuellen, Beschriftung, Kennzeichnung \n"
    "        • Berechnungen durchfuehren \n"
    "        • Ueberpruefung der Daten und Eingaben \n"
    "        • Fehlerkorrektur \n"
    "        • Aufbereitung der Daten \n"
    "        • Datenuebermittlung und -veroeffentlichung \n"
    "        • Interne Sitzungen \n"
    "        • Externe Sitzungen (z. B. mit Steuerberaterinnen und -beratern) \n"
    "        • Ausfuehren von Zahlungsanweisungen \n"
    "        • Kopieren, Archivieren, Verteilen \n"
    "        • Mitwirkung bei Pruefung durch oeffentliche Stellen (z. B. Betriebspruefung) \n"
    "        • Korrekturen, die aufgrund von Pruefungen durchgefuehrt werden muessen \n"
    "        • Weitere Informationsbeschaffung \n"
    "        • Fortbildungs- und Schulungsteilnahmen \n\n"
    "        Checkliste Teil B – Moegliche weitere Taetigkeiten bei Vorgaben, die keine Informationspflichten sind\n"
    "        (Leitfaden Erfuellungsaufwand Feb 2026, Kap. 6.2.1, S. 38):\n"
    "        • Beschaffen von Waren- und Sachleistungen \n"
    "        • Beschaffen von Dienstleistungen und/oder zusaetzlichem Personal \n"
    "        • Erbringen von eigenen Leistungen (z. B. Installation von Maschinen) \n"
    "        • Anpassen von internen Prozessablaeufen \n"
    "        • Ueberwachungsmassnahmen (z. B. Kontrolle, ob umgesetzte Vorgabe korrekt durchgefuehrt oder Grenzwerte eingehalten wurden) \n"
    "        • Lagerhaltung, Warenwirtschaft, Produktion \n\n"
    "        In der Praxis sind selten alle oben aufgefuehrten Taetigkeiten relevant. Auch hier gilt: lieber eine kleine Zahl klar abgegrenzter und gut\n"
    "        begruendbarer Haupttaetigkeiten als eine lange Liste kleinteiliger Einzeltaetigkeiten."
)


# Buerger-Checkliste aus Leitfaden Erfuellungsaufwand (Feb 2026),
# Kap. 5.2.1, S. 27 ("Checkliste: Taetigkeiten von Buergerinnen und Buergern
# zur Erfuellung von Vorgaben oder Prozessen"). 14 Standardtaetigkeiten aus
# Sicht der privaten Lebensfuehrung (Antrag, Nachweis, Zahlung, Wege,
# Mitwirkung bei Pruefungen).
_PROCESS_STEP_ANALYSIS_CHECKLIST_CITIZENS = (
    "Als Hilfsmittel fuer die Identifizierung der zu erwartenden Taetigkeiten kann die nachfolgende Checkliste mit moeglichen Taetigkeiten \n"
    "        von Buergerinnen und Buergern zur Erfuellung einer Vorgabe oder eines Prozesses herangezogen werden. Es kann sich in einzelnen\n"
    "        Faellen anbieten, die Checkliste um spezielle Taetigkeiten zu erweitern.\n\n"
    "        Orientieren Sie die Bildung der Taetigkeiten eng an dieser Checkliste, damit die Prozessschritte zwischen verschiedenen Regelungsvorhaben nachvollziehbar\n"
    "        und vergleichbar bleiben. Bilden Sie keine kuenstlich kleinteiligen Einzelschritte, sondern wenige, fachlich klare Haupttaetigkeiten. Weichen Sie\n"
    "        von einer knappen Darstellung nur ab, wenn der Sachverhalt es fachlich erfordert.\n"
    "        Fassen Sie eng zusammenhaengende Unterhandlungen zu einem gemeinsamen Prozessschritt zusammen, statt sie separat auszuweisen.\n\n"
    "        Checkliste (Buergerinnen und Buerger, Leitfaden Erfuellungsaufwand Feb 2026, Kap. 5.2.1, S. 27):\n"
    "        • Mit der Vorgabe vertraut machen \n"
    "        • Beratung in Anspruch nehmen (z. B. Beratungsstellen, Stadtverwaltung, Anwaltskanzlei) \n"
    "        • Daten und Informationen sammeln und zusammenstellen (z. B. Formularvordrucke, Nachweise, Fotos) \n"
    "        • Informationen und Daten aufbereiten (inkl. Berechnungen durchfuehren) \n"
    "        • Formulare ausfuellen \n"
    "        • Schriftstuecke aufsetzen (z. B. Brief, E-Mail) \n"
    "        • Informationen oder Daten an die zustaendigen Stellen uebermitteln \n"
    "        • Bezahlen (z. B. beim Begleichen einer Rechnung per Ueberweisung: Ausfuellen eines Ueberweisungsvordrucks oder Veranlassen einer Online-Ueberweisung) \n"
    "        • Unterlagen kopieren, abheften, abspeichern \n"
    "        • Mitwirkung bei der Pruefung durch oeffentliche sowie beliehene und anerkannte Stellen (z. B. Amtsaerztin bzw. Amtsarzt, technische Gutachten, Hauptuntersuchungen) \n"
    "        • Material beschaffen \n"
    "        • Bestimmte Leistung selbst erbringen oder Dritte beauftragen \n"
    "        • Umsetzung von Vorgaben ueberpruefen \n"
    "        • Wege zu zustaendigen Stellen (z. B. zu einer Behoerde) \n\n"
    "        In der Praxis sind selten alle oben aufgefuehrten Taetigkeiten relevant. Waehlen Sie nur die fuer den Vorher-Nachher-Vergleich \n"
    "        wirklich erforderlichen Haupttaetigkeiten: lieber eine kleine Zahl klar abgegrenzter und gut begruendbarer Haupttaetigkeiten als eine\n"
    "        lange Liste kleinteiliger Einzeltaetigkeiten."
)


def _render_step_analysis_checklist(norm_addressee: str | None) -> str:
    # Der Leitfaden Erfuellungsaufwand (Feb 2026) gibt je Normadressat eine
    # eigene Checkliste vor: Verwaltung (Kap. 7.2.1, S. 49), Wirtschaft
    # (Kap. 6.2.1 Teil A+B, S. 37-38) und Buergerinnen/Buerger
    # (Kap. 5.2.1, S. 27, 14 Bullets).
    if norm_addressee == ADMINISTRATION:
        return _PROCESS_STEP_ANALYSIS_CHECKLIST_ADMINISTRATION
    if norm_addressee == BUSINESS:
        return _PROCESS_STEP_ANALYSIS_CHECKLIST_BUSINESS
    if norm_addressee == CITIZENS:
        return _PROCESS_STEP_ANALYSIS_CHECKLIST_CITIZENS
    return ""


def _render_step_analysis_addressee_context(norm_addressee: str | None) -> str:
    if not norm_addressee:
        return ""
    return PROCESS_STEP_ANALYSIS_ADDRESSEE_CONTEXTS.get(norm_addressee, "")


def _render_step_analysis_addressee_rule(norm_addressee: str | None) -> str:
    if not norm_addressee:
        return ""
    return PROCESS_STEP_ANALYSIS_ADDRESSEE_RULES.get(norm_addressee, "")


def _render_norm_addressee_context(norm_addressee: str | None) -> str:
    if not norm_addressee:
        return ""
    return NORM_ADDRESSEE_PROMPT_OPENINGS.get(norm_addressee, "").strip()


def _render_prompt_specific_addressee_rule(prompt_id: str, norm_addressee: str | None) -> str:
    if norm_addressee == ADMINISTRATION:
        return ADMINISTRATION_PROMPT_RULES.get(prompt_id, "").strip()
    if norm_addressee == BUSINESS:
        return BUSINESS_PROMPT_RULES.get(prompt_id, "").strip()
    if norm_addressee == CITIZENS:
        return CITIZENS_PROMPT_RULES.get(prompt_id, "").strip()
    return ""


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
    schema = EFFORT_JSON_SCHEMA_BY_ADDRESSEE.get(norm_addressee)
    if schema is not None:
        return schema.strip()
    return EFFORT_JSON_SCHEMA_DEFAULT.replace("{norm_addressee}", norm_addressee).strip()
