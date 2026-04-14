# LLM Run Trace — BACKGROUND /sessions/SU98UC/run-all

- request_id: `03deacf217ac4e5798fbb35bb66629c9`
- started_at: 2026-04-14T20:00:49
- duration_ms: 218859
- status_code: 200
- app_session_id: `SU98UC`
- steps: 16 (success=12, failure=0, fallback=4)
- total_tokens: in=106524 out=22694
- total_cost: $0.504133

---
## Step 1 — `law_summary` (success)
- model: `gpt-5.2` | provider: `openai` | attempt: `6e82f99f9784452aa68b2f5460e9bc9f` | elapsed: 9474 ms
- tokens: in=6903 out=564 hidden_thinking=0 | cost: $0.019976

### Prompt

```

        Sie sind Legist im deutschen Bundestag. 

        Vergleichen Sie den derzeit gueltigen Gesetzestext mit dem vorgeschlagenen 
        Gesetzesvorschlag. Leiten Sie daraus ab, was der Gesetzgeber erreichen möchte. 
        Geben Sie strikt JSON zurueck im Format: {"title": "...", "blurb": "...", "summary": "..."}.

        Der 'title' soll ein kurzer Titel sein (max. 12 Wörter), der 'blurb' soll genau ein Satz sein. Für die 'summary' geben Sie bitte eine 
        ausführliche Zusammenfassung an, mit Hilfe derer man die Ziele und wesentlichen Unterschiede der Gesetzesänderung verstehen kann ohne 
        die zwei Gesetzestexte vorliegen zu haben.

        Geltendes Gesetz: § 52 Gemeinnützige Zwecke


(1) Eine Körperschaft verfolgt gemeinnützige Zwecke, wenn ihre Tätigkeit darauf gerichtet ist, die Allgemeinheit auf materiellem, geistigem oder sittlichem Gebiet selbstlos zu fördern. Eine Förderung der Allgemeinheit ist nicht gegeben, wenn der Kreis der Personen, dem die Förderung zugute kommt, fest abgeschlossen ist, zum Beispiel Zugehörigkeit zu einer Familie oder zur Belegschaft eines Unternehmens, oder infolge seiner Abgrenzung, insbesondere nach räumlichen oder beruflichen Merkmalen, dauernd nur klein sein kann. Eine Förderung der Allgemeinheit liegt nicht allein deswegen vor, weil eine Körperschaft ihre Mittel einer Körperschaft des öffentlichen Rechts zuführt.

(2) Unter den Voraussetzungen des Absatzes 1 sind als Förderung der Allgemeinheit anzuerkennen: 1.

die Förderung von Wissenschaft und Forschung;

2.

die Förderung der Religion;

3.

die Förderung des öffentlichen Gesundheitswesens und der öffentlichen Gesundheitspflege, insbesondere die Verhütung und Bekämpfung von übertragbaren Krankheiten, auch durch Krankenhäuser im Sinne des § 67, und von Tierseuchen;

4.

die Förderung der Jugend- und Altenhilfe;

5.

die Förderung von Kunst und Kultur;

6.

die Förderung des Denkmalschutzes und der Denkmalpflege;

7.

die Förderung der Erziehung, Volks- und Berufsbildung einschließlich der Studentenhilfe;

8.

die Förderung des Naturschutzes und der Landschaftspflege im Sinne des Bundesnaturschutzgesetzes und der Naturschutzgesetze der Länder, des Umweltschutzes, einschließlich des Klimaschutzes, des Küstenschutzes und des Hochwasserschutzes;

9.

die Förderung des Wohlfahrtswesens, insbesondere der Zwecke der amtlich anerkannten Verbände der freien Wohlfahrtspflege (§ 23 der Umsatzsteuer-Durchführungsverordnung), ihrer Unterverbände und ihrer angeschlossenen Einrichtungen und Anstalten;

10.

die Förderung der Hilfe für politisch, rassistisch oder religiös Verfolgte, für Flüchtlinge, Vertriebene, Aussiedler, Spätaussiedler, Kriegsopfer, Kriegshinterbliebene, Kriegsbeschädigte und Kriegsgefangene, Zivilbeschädigte und Behinderte sowie Hilfe für Opfer von Straftaten; Förderung des Andenkens an Verfolgte, Kriegs- und Katastrophenopfer; Förderung des Suchdienstes für Vermisste, Förderung der Hilfe für Menschen, die auf Grund ihrer geschlechtlichen Identität oder ihrer geschlechtlichen Orientierung diskriminiert werden;

11.

die Förderung der Rettung aus Lebensgefahr;

12.

die Förderung des Feuer-, Arbeits-, Katastrophen- und Zivilschutzes sowie der Unfallverhütung;

13.

die Förderung internationaler Gesinnung, der Toleranz auf allen Gebieten der Kultur und des Völkerverständigungsgedankens;

14.

die Förderung des Tierschutzes;

15.

die Förderung der Entwicklungszusammenarbeit;

16.

die Förderung von Verbraucherberatung und Verbraucherschutz;

17.

die Förderung der Fürsorge für Strafgefangene und ehemalige Strafgefangene;

18.

die Förderung der Gleichberechtigung von Frauen und Männern;

19.

die Förderung des Schutzes von Ehe und Familie;

20.

die Förderung der Kriminalprävention;

21.

die Förderung des Sports (Schach gilt als Sport);

22.

die Förderung der Heimatpflege, Heimatkunde und der Ortsverschönerung;

23.

die Förderung der Tierzucht, der Pflanzenzucht, der Kleingärtnerei, des traditionellen Brauchtums einschließlich des Karnevals, der Fastnacht und des Faschings, der Soldaten- und Reservistenbetreuung, des Amateurfunkens, des Freifunks, des Modellflugs und des Hundesports;

24.

die allgemeine Förderung des demokratischen Staatswesens im Geltungsbereich dieses Gesetzes; hierzu gehören nicht Bestrebungen, die nur bestimmte Einzelinteressen staatsbürgerlicher Art verfolgen oder die auf den kommunalpolitischen Bereich beschränkt sind;

25.

die Förderung des bürgerschaftlichen Engagements zugunsten gemeinnütziger, mildtätiger und kirchlicher Zwecke;

26.

die Förderung der Unterhaltung und Pflege von Friedhöfen und die Förderung der Unterhaltung von Gedenkstätten für nichtbestattungspflichtige Kinder und Föten;

27.

die Förderung wohngemeinnütziger Zwecke; dies ist die vergünstigte Wohnraumüberlassung an Personen im Sinne des § 53. § 53 Nummer 2 ist mit der Maßgabe anzuwenden, dass die Bezüge nicht höher sein dürfen als das Fünffache des Regelsatzes der Sozialhilfe im Sinne des § 28 des Zwölften Buches Sozialgesetzbuch; beim Alleinstehenden oder Alleinerziehenden tritt an die Stelle des Fünffachen das Sechsfache des Regelsatzes. Die Hilfebedürftigkeit muss zu Beginn des jeweiligen Mietverhältnisses vorliegen.

Sofern der von der Körperschaft verfolgte Zweck nicht unter Satz 1 fällt, aber die Allgemeinheit auf materiellem, geistigem oder sittlichem Gebiet entsprechend selbstlos gefördert wird, kann dieser Zweck für gemeinnützig erklärt werden. Die obersten Finanzbehörden der Länder haben jeweils eine Finanzbehörde im Sinne des Finanzverwaltungsgesetzes zu bestimmen, die für Entscheidungen nach Satz 2 zuständig ist.

        Gesetzesvorschlag: § 52 Gemeinnützige Zwecke


(1) Eine Körperschaft verfolgt gemeinnützige Zwecke, wenn ihre Tätigkeit darauf gerichtet ist, die Allgemeinheit auf materiellem, geistigem oder sittlichem Gebiet selbstlos zu fördern. Eine Förderung der Allgemeinheit ist nicht gegeben, wenn der Kreis der Personen, dem die Förderung zugute kommt, fest abgeschlossen ist, zum Beispiel Zugehörigkeit zu einer Familie oder zur Belegschaft eines Unternehmens, oder infolge seiner Abgrenzung, insbesondere nach räumlichen oder beruflichen Merkmalen, dauernd nur klein sein kann. Eine Förderung der Allgemeinheit liegt nicht allein deswegen vor, weil eine Körperschaft ihre Mittel einer Körperschaft des öffentlichen Rechts zuführt.

(2) Unter den Voraussetzungen des Absatzes 1 sind als Förderung der Allgemeinheit anzuerkennen: 1.

die Förderung von Wissenschaft und Forschung;

2.

die Förderung der Religion;

3.

die Förderung des öffentlichen Gesundheitswesens und der öffentlichen Gesundheitspflege, insbesondere die Verhütung und Bekämpfung von übertragbaren Krankheiten, auch durch Krankenhäuser im Sinne des § 67, und von Tierseuchen;

4.

die Förderung der Jugend- und Altenhilfe;

5.

die Förderung von Kunst und Kultur;

6.

die Förderung des Denkmalschutzes und der Denkmalpflege;

7.

die Förderung der Erziehung, Volks- und Berufsbildung einschließlich der Studentenhilfe;

8.

die Förderung des Naturschutzes und der Landschaftspflege im Sinne des Bundesnaturschutzgesetzes und der Naturschutzgesetze der Länder, des Umweltschutzes, einschließlich des Klimaschutzes, des Küstenschutzes und des Hochwasserschutzes;

9.

die Förderung des Wohlfahrtswesens, insbesondere der Zwecke der amtlich anerkannten Verbände der freien Wohlfahrtspflege (§ 23 der Umsatzsteuer-Durchführungsverordnung), ihrer Unterverbände und ihrer angeschlossenen Einrichtungen und Anstalten;

10.

die Förderung der Hilfe für politisch, rassistisch oder religiös Verfolgte, für Flüchtlinge, Vertriebene, Aussiedler, Spätaussiedler, Kriegsopfer, Kriegshinterbliebene, Kriegsbeschädigte und Kriegsgefangene, Zivilbeschädigte und Behinderte sowie Hilfe für Opfer von Straftaten; Förderung des Andenkens an Verfolgte, Kriegs- und Katastrophenopfer; Förderung des Suchdienstes für Vermisste, Förderung der Hilfe für Menschen, die auf Grund ihrer geschlechtlichen Identität oder ihrer geschlechtlichen Orientierung diskriminiert werden;

11.

die Förderung der Rettung aus Lebensgefahr;

12.

die Förderung des Feuer-, Arbeits-, Katastrophen- und Zivilschutzes sowie der Unfallverhütung;

13.

die Förderung internationaler Gesinnung, der Toleranz auf allen Gebieten der Kultur und des Völkerverständigungsgedankens;

14.

die Förderung des Tierschutzes;

15.

die Förderung der Entwicklungszusammenarbeit;

16.

die Förderung von Verbraucherberatung und Verbraucherschutz;

17.

die Förderung der Fürsorge für Strafgefangene und ehemalige Strafgefangene;

18.

die Förderung der Gleichberechtigung von Frauen und Männern;

19.

die Förderung des Schutzes von Ehe und Familie;

20.

die Förderung der Kriminalprävention;

21.

die Förderung des Sports (Schach gilt als Sport und E-Sport gilt für diese Regelung als Sport);

22.

die Förderung der Heimatpflege, Heimatkunde und der Ortsverschönerung;

23.

die Förderung der Tierzucht, der Pflanzenzucht, der Kleingärtnerei, des traditionellen Brauchtums einschließlich des Karnevals, der Fastnacht und des Faschings, der Soldaten- und Reservistenbetreuung, des Amateurfunkens, des Freifunks, des Modellflugs und des Hundesports;

24.

die allgemeine Förderung des demokratischen Staatswesens im Geltungsbereich dieses Gesetzes; hierzu gehören nicht Bestrebungen, die nur bestimmte Einzelinteressen staatsbürgerlicher Art verfolgen oder die auf den kommunalpolitischen Bereich beschränkt sind;

25.

die Förderung des bürgerschaftlichen Engagements zugunsten gemeinnütziger, mildtätiger und kirchlicher Zwecke;

26.

die Förderung der Unterhaltung und Pflege von Friedhöfen und die Förderung der Unterhaltung von Gedenkstätten für nichtbestattungspflichtige Kinder und Föten;

27.

die Förderung wohngemeinnütziger Zwecke; dies ist die vergünstigte Wohnraumüberlassung an Personen im Sinne des § 53. § 53 Nummer 2 ist mit der Maßgabe anzuwenden, dass die Bezüge nicht höher sein dürfen als das Fünffache des Regelsatzes der Sozialhilfe im Sinne des § 28 des Zwölften Buches Sozialgesetzbuch; beim Alleinstehenden oder Alleinerziehenden tritt an die Stelle des Fünffachen das Sechsfache des Regelsatzes. Die Hilfebedürftigkeit muss zu Beginn des jeweiligen Mietverhältnisses vorliegen.

Sofern der von der Körperschaft verfolgte Zweck nicht unter Satz 1 fällt, aber die Allgemeinheit auf materiellem, geistigem oder sittlichem Gebiet entsprechend selbstlos gefördert wird, kann dieser Zweck für gemeinnützig erklärt werden. Die obersten Finanzbehörden der Länder haben jeweils eine Finanzbehörde im Sinne des Finanzverwaltungsgesetzes zu bestimmen, die für Entscheidungen nach Satz 2 zuständig ist.
        
```

### Raw Response

```
{"title":"E‑Sport als gemeinnütziger Sportzweck anerkennen","blurb":"Der Vorschlag erweitert § 52 AO lediglich dahin, dass E‑Sport für die Gemeinnützigkeit ausdrücklich als Sport gilt.","summary":"Aus dem Vergleich ergibt sich nur eine einzige materielle Änderung: In § 52 Abs. 2 Nr. 21 AO wird der Klammerzusatz von „Schach gilt als Sport“ zu „Schach gilt als Sport und E‑Sport gilt für diese Regelung als Sport“ erweitert. Alle übrigen Tatbestandsvoraussetzungen in Absatz 1 (Allgemeinheitsförderung, Abgrenzung zu geschlossenen Personenkreisen etc.) sowie der restliche Katalog gemeinnütziger Zwecke in Absatz 2 und die Öffnungsklausel am Ende bleiben wortgleich.\n\nZiel des Gesetzgebers ist damit erkennbar eine Klarstellung und Erweiterung des gemeinnützigen Zweckkatalogs zugunsten des E‑Sports: Körperschaften (z.B. Vereine, Stiftungen, gGmbHs), deren Satzungszweck und tatsächliche Geschäftsführung auf die Förderung von E‑Sport gerichtet ist, sollen unter dem bereits anerkannten Zweck „Förderung des Sports“ leichter und rechtssicher als gemeinnützig anerkannt werden. Praktisch bedeutet dies eine Reduzierung von Rechtsunsicherheit und uneinheitlicher Verwaltungspraxis, weil E‑Sport nicht mehr (nur) über andere Zwecke (z.B. Jugendhilfe, Bildung, Kultur, digitale Kompetenzen) „mitbegründet“ werden müsste, sondern unmittelbar als Sportförderung gemeinnützig sein kann.\n\nWesentliche Unterschiede/Wirkungen der Änderung:\n- Erweiterter Anwendungsbereich von Nr. 21: Sportvereine im Sinne der Gemeinnützigkeit sollen ausdrücklich auch E‑Sport-Vereine umfassen.\n- Rechtsfolgeebene (implizit): E‑Sport‑Organisationen können damit eher Zugang zu typischen Gemeinnützigkeitsfolgen erhalten (insbesondere steuerliche Begünstigungen, Spendenabzugsfähigkeit für Zuwendungen an die Körperschaft, erleichterte Mittelakquise), soweit sie die allgemeinen Gemeinnützigkeitsanforderungen (Selbstlosigkeit, Ausschließlichkeit, Unmittelbarkeit, tatsächliche Geschäftsführung, kein geschlossener Begünstigtenkreis) erfüllen.\n- Keine Ausweitung anderer Zwecke/keine Änderung der Grunddefinition: Die Änderung schafft keinen neuen eigenständigen Zweck außerhalb des Sportbegriffs, sondern ordnet E‑Sport ausdrücklich dem bestehenden Zweck „Sport“ zu und lässt die übrige Systematik des § 52 AO unverändert."}
```

---

## Step 2 — `regulations_identification` (success)
- model: `gpt-5.2` | provider: `openai` | attempt: `c16ff58ac70f43559f078b011d7a55b4` | elapsed: 10303 ms
- tokens: in=9033 out=715 hidden_thinking=0 | cost: $0.025818

### Prompt

```

    Sie sind Legist im deutschen Bundestag und damit betraut, die 
    Erfüllungsaufwandsänderung zu einer geplanten Gesetzesänderung zu berechnen.

    Insbesondere werden zur Ermittlung der zu erwartenden Änderung des Aufwands 
    pro Fall die wesentlichen Tätigkeiten identifiziert, die zur Erfüllung 
    einer Vorgabe oder eines Prozesses im Einzelfall zu erwarten sind. Diese 
    schließen Tätigkeiten ein, welche neu hinzukommen, welche sich ändern und 
    welche wegfallen. Für diese Tätigkeiten werden die zu erwartenden Änderungen des 
    Zeit-, Personal- sowie Sachaufwands ermittelt.

    Die wesentlichen Unterschiede der Gesetzesänderung sind wie folgt 
    zusammengefasst: Aus dem Vergleich ergibt sich nur eine einzige materielle Änderung: In § 52 Abs. 2 Nr. 21 AO wird der Klammerzusatz von „Schach gilt als Sport“ zu „Schach gilt als Sport und E‑Sport gilt für diese Regelung als Sport“ erweitert. Alle übrigen Tatbestandsvoraussetzungen in Absatz 1 (Allgemeinheitsförderung, Abgrenzung zu geschlossenen Personenkreisen etc.) sowie der restliche Katalog gemeinnütziger Zwecke in Absatz 2 und die Öffnungsklausel am Ende bleiben wortgleich.

Ziel des Gesetzgebers ist damit erkennbar eine Klarstellung und Erweiterung des gemeinnützigen Zweckkatalogs zugunsten des E‑Sports: Körperschaften (z.B. Vereine, Stiftungen, gGmbHs), deren Satzungszweck und tatsächliche Geschäftsführung auf die Förderung von E‑Sport gerichtet ist, sollen unter dem bereits anerkannten Zweck „Förderung des Sports“ leichter und rechtssicher als gemeinnützig anerkannt werden. Praktisch bedeutet dies eine Reduzierung von Rechtsunsicherheit und uneinheitlicher Verwaltungspraxis, weil E‑Sport nicht mehr (nur) über andere Zwecke (z.B. Jugendhilfe, Bildung, Kultur, digitale Kompetenzen) „mitbegründet“ werden müsste, sondern unmittelbar als Sportförderung gemeinnützig sein kann.

Wesentliche Unterschiede/Wirkungen der Änderung:
- Erweiterter Anwendungsbereich von Nr. 21: Sportvereine im Sinne der Gemeinnützigkeit sollen ausdrücklich auch E‑Sport-Vereine umfassen.
- Rechtsfolgeebene (implizit): E‑Sport‑Organisationen können damit eher Zugang zu typischen Gemeinnützigkeitsfolgen erhalten (insbesondere steuerliche Begünstigungen, Spendenabzugsfähigkeit für Zuwendungen an die Körperschaft, erleichterte Mittelakquise), soweit sie die allgemeinen Gemeinnützigkeitsanforderungen (Selbstlosigkeit, Ausschließlichkeit, Unmittelbarkeit, tatsächliche Geschäftsführung, kein geschlossener Begünstigtenkreis) erfüllen.
- Keine Ausweitung anderer Zwecke/keine Änderung der Grunddefinition: Die Änderung schafft keinen neuen eigenständigen Zweck außerhalb des Sportbegriffs, sondern ordnet E‑Sport ausdrücklich dem bestehenden Zweck „Sport“ zu und lässt die übrige Systematik des § 52 AO unverändert.

     
        Folgendes ist das konsolidierte, geltende Gesetz: § 52 Gemeinnützige Zwecke


(1) Eine Körperschaft verfolgt gemeinnützige Zwecke, wenn ihre Tätigkeit darauf gerichtet ist, die Allgemeinheit auf materiellem, geistigem oder sittlichem Gebiet selbstlos zu fördern. Eine Förderung der Allgemeinheit ist nicht gegeben, wenn der Kreis der Personen, dem die Förderung zugute kommt, fest abgeschlossen ist, zum Beispiel Zugehörigkeit zu einer Familie oder zur Belegschaft eines Unternehmens, oder infolge seiner Abgrenzung, insbesondere nach räumlichen oder beruflichen Merkmalen, dauernd nur klein sein kann. Eine Förderung der Allgemeinheit liegt nicht allein deswegen vor, weil eine Körperschaft ihre Mittel einer Körperschaft des öffentlichen Rechts zuführt.

(2) Unter den Voraussetzungen des Absatzes 1 sind als Förderung der Allgemeinheit anzuerkennen: 1.

die Förderung von Wissenschaft und Forschung;

2.

die Förderung der Religion;

3.

die Förderung des öffentlichen Gesundheitswesens und der öffentlichen Gesundheitspflege, insbesondere die Verhütung und Bekämpfung von übertragbaren Krankheiten, auch durch Krankenhäuser im Sinne des § 67, und von Tierseuchen;

4.

die Förderung der Jugend- und Altenhilfe;

5.

die Förderung von Kunst und Kultur;

6.

die Förderung des Denkmalschutzes und der Denkmalpflege;

7.

die Förderung der Erziehung, Volks- und Berufsbildung einschließlich der Studentenhilfe;

8.

die Förderung des Naturschutzes und der Landschaftspflege im Sinne des Bundesnaturschutzgesetzes und der Naturschutzgesetze der Länder, des Umweltschutzes, einschließlich des Klimaschutzes, des Küstenschutzes und des Hochwasserschutzes;

9.

die Förderung des Wohlfahrtswesens, insbesondere der Zwecke der amtlich anerkannten Verbände der freien Wohlfahrtspflege (§ 23 der Umsatzsteuer-Durchführungsverordnung), ihrer Unterverbände und ihrer angeschlossenen Einrichtungen und Anstalten;

10.

die Förderung der Hilfe für politisch, rassistisch oder religiös Verfolgte, für Flüchtlinge, Vertriebene, Aussiedler, Spätaussiedler, Kriegsopfer, Kriegshinterbliebene, Kriegsbeschädigte und Kriegsgefangene, Zivilbeschädigte und Behinderte sowie Hilfe für Opfer von Straftaten; Förderung des Andenkens an Verfolgte, Kriegs- und Katastrophenopfer; Förderung des Suchdienstes für Vermisste, Förderung der Hilfe für Menschen, die auf Grund ihrer geschlechtlichen Identität oder ihrer geschlechtlichen Orientierung diskriminiert werden;

11.

die Förderung der Rettung aus Lebensgefahr;

12.

die Förderung des Feuer-, Arbeits-, Katastrophen- und Zivilschutzes sowie der Unfallverhütung;

13.

die Förderung internationaler Gesinnung, der Toleranz auf allen Gebieten der Kultur und des Völkerverständigungsgedankens;

14.

die Förderung des Tierschutzes;

15.

die Förderung der Entwicklungszusammenarbeit;

16.

die Förderung von Verbraucherberatung und Verbraucherschutz;

17.

die Förderung der Fürsorge für Strafgefangene und ehemalige Strafgefangene;

18.

die Förderung der Gleichberechtigung von Frauen und Männern;

19.

die Förderung des Schutzes von Ehe und Familie;

20.

die Förderung der Kriminalprävention;

21.

die Förderung des Sports (Schach gilt als Sport);

22.

die Förderung der Heimatpflege, Heimatkunde und der Ortsverschönerung;

23.

die Förderung der Tierzucht, der Pflanzenzucht, der Kleingärtnerei, des traditionellen Brauchtums einschließlich des Karnevals, der Fastnacht und des Faschings, der Soldaten- und Reservistenbetreuung, des Amateurfunkens, des Freifunks, des Modellflugs und des Hundesports;

24.

die allgemeine Förderung des demokratischen Staatswesens im Geltungsbereich dieses Gesetzes; hierzu gehören nicht Bestrebungen, die nur bestimmte Einzelinteressen staatsbürgerlicher Art verfolgen oder die auf den kommunalpolitischen Bereich beschränkt sind;

25.

die Förderung des bürgerschaftlichen Engagements zugunsten gemeinnütziger, mildtätiger und kirchlicher Zwecke;

26.

die Förderung der Unterhaltung und Pflege von Friedhöfen und die Förderung der Unterhaltung von Gedenkstätten für nichtbestattungspflichtige Kinder und Föten;

27.

die Förderung wohngemeinnütziger Zwecke; dies ist die vergünstigte Wohnraumüberlassung an Personen im Sinne des § 53. § 53 Nummer 2 ist mit der Maßgabe anzuwenden, dass die Bezüge nicht höher sein dürfen als das Fünffache des Regelsatzes der Sozialhilfe im Sinne des § 28 des Zwölften Buches Sozialgesetzbuch; beim Alleinstehenden oder Alleinerziehenden tritt an die Stelle des Fünffachen das Sechsfache des Regelsatzes. Die Hilfebedürftigkeit muss zu Beginn des jeweiligen Mietverhältnisses vorliegen.

Sofern der von der Körperschaft verfolgte Zweck nicht unter Satz 1 fällt, aber die Allgemeinheit auf materiellem, geistigem oder sittlichem Gebiet entsprechend selbstlos gefördert wird, kann dieser Zweck für gemeinnützig erklärt werden. Die obersten Finanzbehörden der Länder haben jeweils eine Finanzbehörde im Sinne des Finanzverwaltungsgesetzes zu bestimmen, die für Entscheidungen nach Satz 2 zuständig ist.

        Folgendes konsolidiertes Gesetz wird vorgeschlagen: § 52 Gemeinnützige Zwecke


(1) Eine Körperschaft verfolgt gemeinnützige Zwecke, wenn ihre Tätigkeit darauf gerichtet ist, die Allgemeinheit auf materiellem, geistigem oder sittlichem Gebiet selbstlos zu fördern. Eine Förderung der Allgemeinheit ist nicht gegeben, wenn der Kreis der Personen, dem die Förderung zugute kommt, fest abgeschlossen ist, zum Beispiel Zugehörigkeit zu einer Familie oder zur Belegschaft eines Unternehmens, oder infolge seiner Abgrenzung, insbesondere nach räumlichen oder beruflichen Merkmalen, dauernd nur klein sein kann. Eine Förderung der Allgemeinheit liegt nicht allein deswegen vor, weil eine Körperschaft ihre Mittel einer Körperschaft des öffentlichen Rechts zuführt.

(2) Unter den Voraussetzungen des Absatzes 1 sind als Förderung der Allgemeinheit anzuerkennen: 1.

die Förderung von Wissenschaft und Forschung;

2.

die Förderung der Religion;

3.

die Förderung des öffentlichen Gesundheitswesens und der öffentlichen Gesundheitspflege, insbesondere die Verhütung und Bekämpfung von übertragbaren Krankheiten, auch durch Krankenhäuser im Sinne des § 67, und von Tierseuchen;

4.

die Förderung der Jugend- und Altenhilfe;

5.

die Förderung von Kunst und Kultur;

6.

die Förderung des Denkmalschutzes und der Denkmalpflege;

7.

die Förderung der Erziehung, Volks- und Berufsbildung einschließlich der Studentenhilfe;

8.

die Förderung des Naturschutzes und der Landschaftspflege im Sinne des Bundesnaturschutzgesetzes und der Naturschutzgesetze der Länder, des Umweltschutzes, einschließlich des Klimaschutzes, des Küstenschutzes und des Hochwasserschutzes;

9.

die Förderung des Wohlfahrtswesens, insbesondere der Zwecke der amtlich anerkannten Verbände der freien Wohlfahrtspflege (§ 23 der Umsatzsteuer-Durchführungsverordnung), ihrer Unterverbände und ihrer angeschlossenen Einrichtungen und Anstalten;

10.

die Förderung der Hilfe für politisch, rassistisch oder religiös Verfolgte, für Flüchtlinge, Vertriebene, Aussiedler, Spätaussiedler, Kriegsopfer, Kriegshinterbliebene, Kriegsbeschädigte und Kriegsgefangene, Zivilbeschädigte und Behinderte sowie Hilfe für Opfer von Straftaten; Förderung des Andenkens an Verfolgte, Kriegs- und Katastrophenopfer; Förderung des Suchdienstes für Vermisste, Förderung der Hilfe für Menschen, die auf Grund ihrer geschlechtlichen Identität oder ihrer geschlechtlichen Orientierung diskriminiert werden;

11.

die Förderung der Rettung aus Lebensgefahr;

12.

die Förderung des Feuer-, Arbeits-, Katastrophen- und Zivilschutzes sowie der Unfallverhütung;

13.

die Förderung internationaler Gesinnung, der Toleranz auf allen Gebieten der Kultur und des Völkerverständigungsgedankens;

14.

die Förderung des Tierschutzes;

15.

die Förderung der Entwicklungszusammenarbeit;

16.

die Förderung von Verbraucherberatung und Verbraucherschutz;

17.

die Förderung der Fürsorge für Strafgefangene und ehemalige Strafgefangene;

18.

die Förderung der Gleichberechtigung von Frauen und Männern;

19.

die Förderung des Schutzes von Ehe und Familie;

20.

die Förderung der Kriminalprävention;

21.

die Förderung des Sports (Schach gilt als Sport und E-Sport gilt für diese Regelung als Sport);

22.

die Förderung der Heimatpflege, Heimatkunde und der Ortsverschönerung;

23.

die Förderung der Tierzucht, der Pflanzenzucht, der Kleingärtnerei, des traditionellen Brauchtums einschließlich des Karnevals, der Fastnacht und des Faschings, der Soldaten- und Reservistenbetreuung, des Amateurfunkens, des Freifunks, des Modellflugs und des Hundesports;

24.

die allgemeine Förderung des demokratischen Staatswesens im Geltungsbereich dieses Gesetzes; hierzu gehören nicht Bestrebungen, die nur bestimmte Einzelinteressen staatsbürgerlicher Art verfolgen oder die auf den kommunalpolitischen Bereich beschränkt sind;

25.

die Förderung des bürgerschaftlichen Engagements zugunsten gemeinnütziger, mildtätiger und kirchlicher Zwecke;

26.

die Förderung der Unterhaltung und Pflege von Friedhöfen und die Förderung der Unterhaltung von Gedenkstätten für nichtbestattungspflichtige Kinder und Föten;

27.

die Förderung wohngemeinnütziger Zwecke; dies ist die vergünstigte Wohnraumüberlassung an Personen im Sinne des § 53. § 53 Nummer 2 ist mit der Maßgabe anzuwenden, dass die Bezüge nicht höher sein dürfen als das Fünffache des Regelsatzes der Sozialhilfe im Sinne des § 28 des Zwölften Buches Sozialgesetzbuch; beim Alleinstehenden oder Alleinerziehenden tritt an die Stelle des Fünffachen das Sechsfache des Regelsatzes. Die Hilfebedürftigkeit muss zu Beginn des jeweiligen Mietverhältnisses vorliegen.

Sofern der von der Körperschaft verfolgte Zweck nicht unter Satz 1 fällt, aber die Allgemeinheit auf materiellem, geistigem oder sittlichem Gebiet entsprechend selbstlos gefördert wird, kann dieser Zweck für gemeinnützig erklärt werden. Die obersten Finanzbehörden der Länder haben jeweils eine Finanzbehörde im Sinne des Finanzverwaltungsgesetzes zu bestimmen, die für Entscheidungen nach Satz 2 zuständig ist.

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

        Wichtig fuer den Normadressaten `administration` (Verwaltung): Uebersehen Sie die Verwaltung nicht. Pruefen Sie bei jeder Vorgabe ausdruecklich,
        ob sie der zustaendigen Behoerde einen konkreten Vollzugsauftrag auferlegt – typische Auslöser sind Antrags-, Anzeige-, Genehmigungs-,
        Anerkennungs-, Melde-, Register- oder Nachweisverfahren, laufende Aufsicht und Kontrollen, anlassbezogene Einzelfallpruefungen,
        Bescheidung und Rechtsbehelfsverfahren, Auszahlungs- oder Foerderverfahren sowie einmalige interne Umstellungen (IT, Formulare,
        Schulung). Wenn die Erfuellung einer Vorgabe durch Wirtschaft oder Buergerinnen/Buerger praktisch nur moeglich ist, weil die
        Verwaltung etwas pruefen, bescheiden, registrieren, kontrollieren oder auszahlen muss, ist `administration` zusaetzlich als
        betroffener Normadressat auszuweisen und die Vorgabe als Spiegelsituation zu kennzeichnen. Ein bloss mittelbarer Mehraufwand ohne
        konkreten Vollzugsauftrag ist hingegen nicht der Verwaltung zuzuordnen – erfinden Sie keine Verwaltungsvorgaben, wo keine sind.

        Geben Sie nur und ausschließlich JSON im folgenden Format zurück:

        {
          "vorgaben": [
            {
              "normzitat": "",
              "beschreibung": "",
              "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft",
              "normadressaten": ["administration | business | citizens"],
              "ist_informationspflicht_wirtschaft": "0 | 1",
              "spiegelsituation": {
                "liegt_vor": "0 | 1",
                "normadressaten": ["administration | business | citizens"],
                "beschreibung": "",
                "mirror_anchor_key": ""
              }
            }
          ]
        }

        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen.
        
```

### Raw Response

```
{
  "vorgaben": [
    {
      "normzitat": "§ 52 Abs. 2 Nr. 21 AO",
      "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).",
      "aenderungsstatus": "geaendert",
      "normadressaten": [
        "business",
        "administration"
      ],
      "ist_informationspflicht_wirtschaft": "0",
      "spiegelsituation": {
        "liegt_vor": "1",
        "normadressaten": [
          "administration"
        ],
        "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).",
        "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"
      }
    },
    {
      "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)",
      "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.",
      "aenderungsstatus": "geaendert",
      "normadressaten": [
        "business",
        "administration"
      ],
      "ist_informationspflicht_wirtschaft": "0",
      "spiegelsituation": {
        "liegt_vor": "1",
        "normadressaten": [
          "administration"
        ],
        "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).",
        "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"
      }
    }
  ]
}
```

---

## Step 3 — `process_compilation` (success)
- model: `gpt-5.2` | provider: `openai` | attempt: `86f1d74542d84dac940fa52d36e97b36` | elapsed: 7727 ms
- tokens: in=7070 out=647 hidden_thinking=0 | cost: $0.021431

### Prompt

```

    Sie sind Legist im deutschen Bundestag und damit betraut, die 
    Erfüllungsaufwandsänderung zu einer geplanten Gesetzesänderung zu berechnen.

    Insbesondere werden zur Ermittlung der zu erwartenden Änderung des Aufwands 
    pro Fall die wesentlichen Tätigkeiten identifiziert, die zur Erfüllung 
    einer Vorgabe oder eines Prozesses im Einzelfall zu erwarten sind. Diese 
    schließen Tätigkeiten ein, welche neu hinzukommen, welche sich ändern und 
    welche wegfallen. Für diese Tätigkeiten werden die zu erwartenden Änderungen des 
    Zeit-, Personal- sowie Sachaufwands ermittelt.

    Die wesentlichen Unterschiede der Gesetzesänderung sind wie folgt 
    zusammengefasst: Aus dem Vergleich ergibt sich nur eine einzige materielle Änderung: In § 52 Abs. 2 Nr. 21 AO wird der Klammerzusatz von „Schach gilt als Sport“ zu „Schach gilt als Sport und E‑Sport gilt für diese Regelung als Sport“ erweitert. Alle übrigen Tatbestandsvoraussetzungen in Absatz 1 (Allgemeinheitsförderung, Abgrenzung zu geschlossenen Personenkreisen etc.) sowie der restliche Katalog gemeinnütziger Zwecke in Absatz 2 und die Öffnungsklausel am Ende bleiben wortgleich.

Ziel des Gesetzgebers ist damit erkennbar eine Klarstellung und Erweiterung des gemeinnützigen Zweckkatalogs zugunsten des E‑Sports: Körperschaften (z.B. Vereine, Stiftungen, gGmbHs), deren Satzungszweck und tatsächliche Geschäftsführung auf die Förderung von E‑Sport gerichtet ist, sollen unter dem bereits anerkannten Zweck „Förderung des Sports“ leichter und rechtssicher als gemeinnützig anerkannt werden. Praktisch bedeutet dies eine Reduzierung von Rechtsunsicherheit und uneinheitlicher Verwaltungspraxis, weil E‑Sport nicht mehr (nur) über andere Zwecke (z.B. Jugendhilfe, Bildung, Kultur, digitale Kompetenzen) „mitbegründet“ werden müsste, sondern unmittelbar als Sportförderung gemeinnützig sein kann.

Wesentliche Unterschiede/Wirkungen der Änderung:
- Erweiterter Anwendungsbereich von Nr. 21: Sportvereine im Sinne der Gemeinnützigkeit sollen ausdrücklich auch E‑Sport-Vereine umfassen.
- Rechtsfolgeebene (implizit): E‑Sport‑Organisationen können damit eher Zugang zu typischen Gemeinnützigkeitsfolgen erhalten (insbesondere steuerliche Begünstigungen, Spendenabzugsfähigkeit für Zuwendungen an die Körperschaft, erleichterte Mittelakquise), soweit sie die allgemeinen Gemeinnützigkeitsanforderungen (Selbstlosigkeit, Ausschließlichkeit, Unmittelbarkeit, tatsächliche Geschäftsführung, kein geschlossener Begünstigtenkreis) erfüllen.
- Keine Ausweitung anderer Zwecke/keine Änderung der Grunddefinition: Die Änderung schafft keinen neuen eigenständigen Zweck außerhalb des Sportbegriffs, sondern ordnet E‑Sport ausdrücklich dem bestehenden Zweck „Sport“ zu und lässt die übrige Systematik des § 52 AO unverändert.

    
        Die Gesetzesänderung führt zu folgenden Einzelvorgaben für den betroffenen Normadressaten: [{"vorgaben_id": 11, "normzitat": "§ 52 Abs. 2 Nr. 21 AO", "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}}, {"vorgaben_id": 12, "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)", "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}}]
        

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

        Buendeln Sie Vorgaben aus Unionsrecht und aus nationalem Recht niemals in denselben Prozess. Wenn der zugrunde liegende Rechtsrahmen
        unterschiedlich ist, muessen getrennte Prozesse ausgewiesen werden, auch wenn die praktische Bearbeitung aehnlich erscheint. Die spaetere
        gesonderte Ausweisung EU-bedingten Erfuellungsaufwands muss anhand Ihrer Prozessstruktur weiterhin moeglich bleiben.

        Offizielles Methodenbeispiel aus dem Leitfaden (woertlich uebernommen):
        

        Geben Sie nur und ausschließlich JSON im folgenden Format zurück: 

        {
        "prozesse": [
            {
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft",
            "vorgaben": [
                {
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                }
            ]
            },
            {
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft",
            "vorgaben": [
                {
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                },
                {
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                }
            ]
            }
        ]
        }

        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 
        

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
        Fallgruppen, Taetigkeiten, Fallzahlen oder Werte, sofern diese nicht
        ausdruecklich als Spiegelwirkung der Verwaltung zuzurechnen sind. Vermeiden
        Sie zugleich, aus Vorsicht ganze Vollzugsstraenge wegzulassen: wenn eine
        Regelung die Verwaltung zur Pruefung, Bescheidung oder Aufsicht verpflichtet,
        ist dieser Vollzugsaufwand auszuweisen, auch wenn er aus einem wirtschafts-
        oder buergerseitigen Antrag ausgeloest wird.

Zusatz fuer die Verwaltung bei der Prozessbildung: Buendeln Sie Vorgaben zu Prozessen entlang der Bearbeitungslogik der zustaendigen Behoerde, nicht entlang einzelner Paragraphen. Typische Prozessbildende Raster sind: (i) Antrags-/Anerkennungsverfahren mit Bescheidung, (ii) turnusmaessige Pruefung bzw. laufende Aufsicht und Kontrolle, (iii) anlassbezogene Einzelfallpruefung (z.B. Verdacht, Stichprobe, Beschwerde), (iv) Rechtsbehelfs-/Widerspruchsverfahren, (v) Erstattungs-, Auszahlungs- oder Foerderverfahren, (vi) Register-, Melde- und Aktenfuehrung, (vii) einmalige interne Umstellung (IT-Anpassung, Formular- und Merkblattpflege, Schulung). Vorgaben, die praktisch innerhalb desselben Verfahrensganges erfuellt werden, gehoeren in denselben Prozess; fachlich klar getrennte Verfahren bleiben getrennt. Fuehren Sie Vollzugsaufwand auch dann aus, wenn er durch einen Antrag der Wirtschaft oder der Buergerinnen/Buerger ausgeloest wird - die Verwaltungstaetigkeit ist ein eigener Prozess auf der Spiegelseite. Erfinden Sie keine Verwaltungsprozesse, zu denen die Regelung keinen konkreten Vollzugsauftrag enthaelt.
```

### Raw Response

```
{
  "prozesse": [
    {
      "prozess_bezeichnung": "Pruefung und Bescheidung der Gemeinnuetzigkeit bei E-Sport-Foerderung als Sport (Anerkennungs-/Freistellungsverfahren)",
      "prozess_beschreibung": "Bearbeitung von Verfahren, in denen Koerperschaften ihre Gemeinnuetzigkeit/Steuerbeguenzigung (z. B. im Rahmen von Feststellungs-, Veranlagungs- und Freistellungsverfahren) geltend machen und die Finanzbehoerde die Einordnung des Satzungszwecks und der tatsaechlichen Geschaeftsfuehrung unter den gemeinnuetzigkeitsrechtlichen Zweck \"Foerderung des Sports\" nun ausdruecklich einschliesslich E-Sport prueft. Hierzu gehoeren die Anpassung bzw. Anwendung der pruefungsleitenden Arbeitsschritte und Begruendungstexte (Einordnung E-Sport als Sport), die Wuerdigung der unveraenderten allgemeinen Gemeinnuetzigkeitsvoraussetzungen sowie die Bescheidung/kommunikative Rueckfragen im Einzelfall. Der Prozess bildet zugleich die Spiegelsituation ab: Die Verwaltungshandlung wird typischerweise durch das Begehren der Koerperschaft ausgeloest, ist aber als eigener Vollzugsvorgang der Finanzverwaltung auszuweisen.",
      "aenderungsstatus": "geaendert",
      "vorgaben": [
        {
          "vorgaben_id": "11",
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO",
          "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).",
          "aenderungsstatus": "geaendert"
        },
        {
          "vorgaben_id": "12",
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)",
          "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.",
          "aenderungsstatus": "geaendert"
        }
      ]
    }
  ]
}
```

---

## Step 4 — `process_compilation` (success)
- model: `gpt-5.2` | provider: `openai` | attempt: `a33ce9ae921c428d85b167d67824f0b4` | elapsed: 7518 ms
- tokens: in=6849 out=659 hidden_thinking=0 | cost: $0.021212

### Prompt

```

    Sie sind Legist im deutschen Bundestag und damit betraut, die 
    Erfüllungsaufwandsänderung zu einer geplanten Gesetzesänderung zu berechnen.

    Insbesondere werden zur Ermittlung der zu erwartenden Änderung des Aufwands 
    pro Fall die wesentlichen Tätigkeiten identifiziert, die zur Erfüllung 
    einer Vorgabe oder eines Prozesses im Einzelfall zu erwarten sind. Diese 
    schließen Tätigkeiten ein, welche neu hinzukommen, welche sich ändern und 
    welche wegfallen. Für diese Tätigkeiten werden die zu erwartenden Änderungen des 
    Zeit-, Personal- sowie Sachaufwands ermittelt.

    Die wesentlichen Unterschiede der Gesetzesänderung sind wie folgt 
    zusammengefasst: Aus dem Vergleich ergibt sich nur eine einzige materielle Änderung: In § 52 Abs. 2 Nr. 21 AO wird der Klammerzusatz von „Schach gilt als Sport“ zu „Schach gilt als Sport und E‑Sport gilt für diese Regelung als Sport“ erweitert. Alle übrigen Tatbestandsvoraussetzungen in Absatz 1 (Allgemeinheitsförderung, Abgrenzung zu geschlossenen Personenkreisen etc.) sowie der restliche Katalog gemeinnütziger Zwecke in Absatz 2 und die Öffnungsklausel am Ende bleiben wortgleich.

Ziel des Gesetzgebers ist damit erkennbar eine Klarstellung und Erweiterung des gemeinnützigen Zweckkatalogs zugunsten des E‑Sports: Körperschaften (z.B. Vereine, Stiftungen, gGmbHs), deren Satzungszweck und tatsächliche Geschäftsführung auf die Förderung von E‑Sport gerichtet ist, sollen unter dem bereits anerkannten Zweck „Förderung des Sports“ leichter und rechtssicher als gemeinnützig anerkannt werden. Praktisch bedeutet dies eine Reduzierung von Rechtsunsicherheit und uneinheitlicher Verwaltungspraxis, weil E‑Sport nicht mehr (nur) über andere Zwecke (z.B. Jugendhilfe, Bildung, Kultur, digitale Kompetenzen) „mitbegründet“ werden müsste, sondern unmittelbar als Sportförderung gemeinnützig sein kann.

Wesentliche Unterschiede/Wirkungen der Änderung:
- Erweiterter Anwendungsbereich von Nr. 21: Sportvereine im Sinne der Gemeinnützigkeit sollen ausdrücklich auch E‑Sport-Vereine umfassen.
- Rechtsfolgeebene (implizit): E‑Sport‑Organisationen können damit eher Zugang zu typischen Gemeinnützigkeitsfolgen erhalten (insbesondere steuerliche Begünstigungen, Spendenabzugsfähigkeit für Zuwendungen an die Körperschaft, erleichterte Mittelakquise), soweit sie die allgemeinen Gemeinnützigkeitsanforderungen (Selbstlosigkeit, Ausschließlichkeit, Unmittelbarkeit, tatsächliche Geschäftsführung, kein geschlossener Begünstigtenkreis) erfüllen.
- Keine Ausweitung anderer Zwecke/keine Änderung der Grunddefinition: Die Änderung schafft keinen neuen eigenständigen Zweck außerhalb des Sportbegriffs, sondern ordnet E‑Sport ausdrücklich dem bestehenden Zweck „Sport“ zu und lässt die übrige Systematik des § 52 AO unverändert.

    
        Die Gesetzesänderung führt zu folgenden Einzelvorgaben für den betroffenen Normadressaten: [{"vorgaben_id": 11, "normzitat": "§ 52 Abs. 2 Nr. 21 AO", "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}}, {"vorgaben_id": 12, "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)", "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}}]
        

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

        Buendeln Sie Vorgaben aus Unionsrecht und aus nationalem Recht niemals in denselben Prozess. Wenn der zugrunde liegende Rechtsrahmen
        unterschiedlich ist, muessen getrennte Prozesse ausgewiesen werden, auch wenn die praktische Bearbeitung aehnlich erscheint. Die spaetere
        gesonderte Ausweisung EU-bedingten Erfuellungsaufwands muss anhand Ihrer Prozessstruktur weiterhin moeglich bleiben.

        Offizielles Methodenbeispiel aus dem Leitfaden (woertlich uebernommen):
        → Beispiele für Prozesse:
1. Die UV-Schutz-Verordnung dient dem Schutz der menschlichen Gesundheit vor schädlichen
UV-Strahlen bei der Benutzung von Solarien. Bei der Ermittlung des Erfüllungsaufwands wurden
für den Normadressaten Wirtschaft die einzelnen Vorgaben zu Prozessen zusammengefasst:
– Nachrüstung/Austausch von alten Bestrahlungsgeräten
– Anschaffung von Schutzbrillen
– Durchführung von Beratungsgesprächen
– Schulung des Personals
2. Im Rahmen des Erfüllungsaufwandprojekts „Betriebliche Beauftragte“ wurden die gesetzli-
chen Grundlagen aus Sicht der Normadressaten untersucht, um die Prozesse zu identifizieren,
aus denen sich Erfüllungsaufwand ableiten lässt. Dabei wurden einzelne Prozesse weiter unter-
gliedert, um die Ermittlung des Erfüllungsaufwands zu erleichtern.
– Verfahren zur Bestellung der Betriebsbeauftragten
– Materielle Unterstützung der Beauftragten durch das Unternehmen/den Betrieb (Bereitstellen
von Hilfspersonal, Räumen etc., Teilnahme an Schulungen ermöglichen, Lohn- und Gehalts-
kosten für die Beauftragten)
– Beteiligung der Beauftragten an Prozessen im Unternehmen

        Geben Sie nur und ausschließlich JSON im folgenden Format zurück: 

        {
        "prozesse": [
            {
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft",
            "vorgaben": [
                {
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                }
            ]
            },
            {
            "prozess_bezeichnung": "",
            "prozess_beschreibung": "",
            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft",
            "vorgaben": [
                {
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                },
                {
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                }
            ]
            }
        ]
        }

        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 
        

Dieser Lauf betrifft den Normadressaten Wirtschaft.

        Beruecksichtigen Sie ausschliesslich den Erfuellungsaufwand der Wirtschaft.
        Analysieren Sie nur wirtschaftsbezogene Prozesse, Fallgruppen, Taetigkeiten,
        Fallzahlen und Werte. Uebernehmen Sie keine Verwaltungslogik, Verwaltungswerte
        oder buergerbezogenen Inhalte, sofern diese nicht ausdruecklich als Spiegelwirkung
        oder wirtschaftsrelevante Folge der Vorgabe begruendet sind. Informationspflichten
        der Wirtschaft, Spiegelsituationen, interne Umstellungen, externe Dienstleistungen
        sowie wirtschaftsspezifische Pruef-, Melde-, Nachweis- und Dokumentationspflichten
        sind mitzudenken.
```

### Raw Response

```
{
  "prozesse": [
    {
      "prozess_bezeichnung": "Gemeinnuetzigkeitsantrag/Steuerbeguenstigungsnachweis fuer E-Sport-Koerperschaften unter Zweck 'Foerderung des Sports' (inkl. Anpassung von Satzung/Begruendung/Unterlagen)",
      "prozess_beschreibung": "Korporationen der Wirtschaft (z. B. E-Sport-Vereine, gGmbHs, Stiftungen) richten die Geltendmachung der Gemeinnuetzigkeit bzw. Steuerbeguenstigungen kuenftig rechtssicherer auf den Zweck 'Foerderung des Sports' aus, da E-Sport fuer § 52 Abs. 2 Nr. 21 AO ausdruecklich als Sport gilt. Im Rahmen der (Neu-)Beantragung bzw. laufenden Nachweisfuehrung/Begruendung gegenueber der Finanzverwaltung (z. B. Feststellung/Veranlagung/Freistellung) verlagert sich der Begruendungspfad weg von alternativen gemeinnuetzigen Zwecken (z. B. Jugendhilfe/Bildung/Kultur) hin zur unmittelbaren Sportfoerderung; dadurch entfaellt in betroffenen Faellen der zusaetzliche Begruendungs- und Abgrenzungsaufwand ueber andere Zwecke und es kann interner Aufwand zur Umstellung der Standardtexte/Argumentation/Unterlagen anfallen.",
      "aenderungsstatus": "geaendert",
      "vorgaben": [
        {
          "vorgaben_id": "11",
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO",
          "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).",
          "aenderungsstatus": "geaendert"
        },
        {
          "vorgaben_id": "12",
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)",
          "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.",
          "aenderungsstatus": "geaendert"
        }
      ]
    }
  ]
}
```

---

## Step 5 — `case_group_development` (success)
- model: `gpt-5.2` | provider: `openai` | attempt: `6bedb5f758a04a9182a84a0389027856` | elapsed: 12578 ms
- tokens: in=7552 out=1116 hidden_thinking=0 | cost: $0.028840

### Prompt

```

    Sie sind Legist im deutschen Bundestag und damit betraut, die 
    Erfüllungsaufwandsänderung zu einer geplanten Gesetzesänderung zu berechnen.

    Insbesondere werden zur Ermittlung der zu erwartenden Änderung des Aufwands 
    pro Fall die wesentlichen Tätigkeiten identifiziert, die zur Erfüllung 
    einer Vorgabe oder eines Prozesses im Einzelfall zu erwarten sind. Diese 
    schließen Tätigkeiten ein, welche neu hinzukommen, welche sich ändern und 
    welche wegfallen. Für diese Tätigkeiten werden die zu erwartenden Änderungen des 
    Zeit-, Personal- sowie Sachaufwands ermittelt.

    Die wesentlichen Unterschiede der Gesetzesänderung sind wie folgt 
    zusammengefasst: Aus dem Vergleich ergibt sich nur eine einzige materielle Änderung: In § 52 Abs. 2 Nr. 21 AO wird der Klammerzusatz von „Schach gilt als Sport“ zu „Schach gilt als Sport und E‑Sport gilt für diese Regelung als Sport“ erweitert. Alle übrigen Tatbestandsvoraussetzungen in Absatz 1 (Allgemeinheitsförderung, Abgrenzung zu geschlossenen Personenkreisen etc.) sowie der restliche Katalog gemeinnütziger Zwecke in Absatz 2 und die Öffnungsklausel am Ende bleiben wortgleich.

Ziel des Gesetzgebers ist damit erkennbar eine Klarstellung und Erweiterung des gemeinnützigen Zweckkatalogs zugunsten des E‑Sports: Körperschaften (z.B. Vereine, Stiftungen, gGmbHs), deren Satzungszweck und tatsächliche Geschäftsführung auf die Förderung von E‑Sport gerichtet ist, sollen unter dem bereits anerkannten Zweck „Förderung des Sports“ leichter und rechtssicher als gemeinnützig anerkannt werden. Praktisch bedeutet dies eine Reduzierung von Rechtsunsicherheit und uneinheitlicher Verwaltungspraxis, weil E‑Sport nicht mehr (nur) über andere Zwecke (z.B. Jugendhilfe, Bildung, Kultur, digitale Kompetenzen) „mitbegründet“ werden müsste, sondern unmittelbar als Sportförderung gemeinnützig sein kann.

Wesentliche Unterschiede/Wirkungen der Änderung:
- Erweiterter Anwendungsbereich von Nr. 21: Sportvereine im Sinne der Gemeinnützigkeit sollen ausdrücklich auch E‑Sport-Vereine umfassen.
- Rechtsfolgeebene (implizit): E‑Sport‑Organisationen können damit eher Zugang zu typischen Gemeinnützigkeitsfolgen erhalten (insbesondere steuerliche Begünstigungen, Spendenabzugsfähigkeit für Zuwendungen an die Körperschaft, erleichterte Mittelakquise), soweit sie die allgemeinen Gemeinnützigkeitsanforderungen (Selbstlosigkeit, Ausschließlichkeit, Unmittelbarkeit, tatsächliche Geschäftsführung, kein geschlossener Begünstigtenkreis) erfüllen.
- Keine Ausweitung anderer Zwecke/keine Änderung der Grunddefinition: Die Änderung schafft keinen neuen eigenständigen Zweck außerhalb des Sportbegriffs, sondern ordnet E‑Sport ausdrücklich dem bestehenden Zweck „Sport“ zu und lässt die übrige Systematik des § 52 AO unverändert.

    
        Die Gesetzesänderung führt zu folgenden, Erfüllungsaufwand auslösenden Prozessen für den betroffenen Normadressaten: [{"prozess_id": 13, "prozess_bezeichnung": "Pruefung und Bescheidung der Gemeinnuetzigkeit bei E-Sport-Foerderung als Sport (Anerkennungs-/Freistellungsverfahren)", "prozess_beschreibung": "Bearbeitung von Verfahren, in denen Koerperschaften ihre Gemeinnuetzigkeit/Steuerbeguenzigung (z. B. im Rahmen von Feststellungs-, Veranlagungs- und Freistellungsverfahren) geltend machen und die Finanzbehoerde die Einordnung des Satzungszwecks und der tatsaechlichen Geschaeftsfuehrung unter den gemeinnuetzigkeitsrechtlichen Zweck \"Foerderung des Sports\" nun ausdruecklich einschliesslich E-Sport prueft. Hierzu gehoeren die Anpassung bzw. Anwendung der pruefungsleitenden Arbeitsschritte und Begruendungstexte (Einordnung E-Sport als Sport), die Wuerdigung der unveraenderten allgemeinen Gemeinnuetzigkeitsvoraussetzungen sowie die Bescheidung/kommunikative Rueckfragen im Einzelfall. Der Prozess bildet zugleich die Spiegelsituation ab: Die Verwaltungshandlung wird typischerweise durch das Begehren der Koerperschaft ausgeloest, ist aber als eigener Vollzugsvorgang der Finanzverwaltung auszuweisen.", "aenderungsstatus": "geaendert", "vorgaben": [{"vorgaben_id": 11, "normzitat": "§ 52 Abs. 2 Nr. 21 AO", "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}}, {"vorgaben_id": 12, "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)", "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}}]}]
        

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
        

        Geben Sie nur und ausschließlich JSON im folgenden Format zurück: 

        {
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
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft"
                },
                {
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft"
                }
            ]
            },
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
                },
                {
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                }
            ], 
            "fallgruppen": [
                {
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft"
                }
            ]
            }
        ]
        }
        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 
        

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
        Fallgruppen, Taetigkeiten, Fallzahlen oder Werte, sofern diese nicht
        ausdruecklich als Spiegelwirkung der Verwaltung zuzurechnen sind. Vermeiden
        Sie zugleich, aus Vorsicht ganze Vollzugsstraenge wegzulassen: wenn eine
        Regelung die Verwaltung zur Pruefung, Bescheidung oder Aufsicht verpflichtet,
        ist dieser Vollzugsaufwand auszuweisen, auch wenn er aus einem wirtschafts-
        oder buergerseitigen Antrag ausgeloest wird.

Zusatz fuer die Verwaltung bei der Fallgruppenbildung: Typische verwaltungsseitige Differenzierungsachsen sind: (i) Ersterfuellung/Erstanerkennung versus turnusmaessige oder wiederholte Bearbeitung, (ii) Standardfall mit glatter Bescheidung versus Sonderpruefung mit Rueckfragen, Anhoerung oder Gutachtenbedarf, (iii) weitgehend automatisierter oder digital gestuetzter Vollzug versus manuelle Einzelbearbeitung, (iv) Massengeschaeft mit standardisierter Pruefung versus aufwaendige Einzelpruefung, (v) einmaliger Umstellungsaufwand (Schulung, IT-Anpassung, Formularpflege) versus laufender Vollzug. Bilden Sie solche Fallgruppen nur, wenn daraus wesentliche Unterschiede im Bearbeitungsaufwand pro Fall folgen - ausgedrueckt in Zeit pro Vorgang, erforderlicher Lohngruppe oder benoetigter IT-/Sachunterstuetzung. Bilden Sie keine Fallgruppen, nur weil unterschiedliche Paragraphen beruehrt werden oder die materielle Rechtslage leicht abweicht, solange der Bearbeitungsweg derselbe bleibt. Setzen Sie den `aenderungsstatus` je Fallgruppe differenziert: `eingefuehrt` nur bei durch die Regelung neu entstehenden Fallgruppen, `abgeschafft` nur bei wegfallenden, `geaendert` nur dann, wenn sich Bearbeitungsaufwand oder Fallzahl der Fallgruppe durch die Regelung tatsaechlich aendert. Unveraenderte Nebenfallgruppen sind nicht auszuweisen. Bei Spiegelsituationen zur Wirtschaft oder zu Buergerinnen/Buergern muss die Zahl der Verwaltungs-Fallgruppen nicht 1:1 zur Gegenseite passen, aber jeder Kernfall einer Verwaltungs-Fallgruppe muss auf der Spiegelseite auffindbar sein.
```

### Raw Response

```
{
  "prozesse": [
    {
      "prozess_id": 13,
      "prozess_bezeichnung": "Pruefung und Bescheidung der Gemeinnuetzigkeit bei E-Sport-Foerderung als Sport (Anerkennungs-/Freistellungsverfahren)",
      "prozess_beschreibung": "Bearbeitung von Verfahren, in denen Koerperschaften ihre Gemeinnuetzigkeit/Steuerbeguenzigung (z. B. im Rahmen von Feststellungs-, Veranlagungs- und Freistellungsverfahren) geltend machen und die Finanzbehoerde die Einordnung des Satzungszwecks und der tatsaechlichen Geschaeftsfuehrung unter den gemeinnuetzigkeitsrechtlichen Zweck \"Foerderung des Sports\" nun ausdruecklich einschliesslich E-Sport prueft. Hierzu gehoeren die Anpassung bzw. Anwendung der pruefungsleitenden Arbeitsschritte und Begruendungstexte (Einordnung E-Sport als Sport), die Wuerdigung der unveraenderten allgemeinen Gemeinnuetzigkeitsvoraussetzungen sowie die Bescheidung/kommunikative Rueckfragen im Einzelfall. Der Prozess bildet zugleich die Spiegelsituation ab: Die Verwaltungshandlung wird typischerweise durch das Begehren der Koerperschaft ausgeloest, ist aber als eigener Vollzugsvorgang der Finanzverwaltung auszuweisen.",
      "aenderungsstatus": "geaendert",
      "vorgaben": [
        {
          "vorgaben_id": 11,
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO",
          "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).",
          "aenderungsstatus": "geaendert"
        },
        {
          "vorgaben_id": 12,
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)",
          "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.",
          "aenderungsstatus": "geaendert"
        }
      ],
      "fallgruppen": [
        {
          "fallgruppe_bezeichnung": "Standardfall: Einordnung E-Sport als Sport ohne besondere Rueckfragen (Erst- oder laufendes Verfahren)",
          "fallgruppe_beschreibung": "Die Koerperschaft beantragt bzw. macht die Steuerbeguenstigung geltend und legt eine Satzung/Taetigkeitsdarstellung vor, bei der E-Sport-Foerderung klar erkennbar ist und die uebrigen Gemeinnuetzigkeitsvoraussetzungen nach Aktenlage unproblematisch erfuellt sind. Die Finanzbehoerde ordnet den Zweck im Pruefschritt nun unmittelbar unter \"Foerderung des Sports\" (inkl. E-Sport) ein und verwendet standardisierte Begruendungstexte/Arbeitshinweise; der bisher in Teilen erforderliche Umweg ueber alternative Zwecke entfaellt. Der Aufwand pro Fall aendert sich durch verkuerzte/pragmatisierte Begruendung und weniger Abgrenzungspruefung.",
          "aenderungsstatus": "geaendert"
        },
        {
          "fallgruppe_bezeichnung": "Sonderfall: Abgrenzungs-/Vertiefungspruefung trotz Klarstellung (Rueckfragen/Anhoerung)",
          "fallgruppe_beschreibung": "Faelle mit E-Sport-Bezug, in denen trotz Einordnungsmöglichkeit als Sport besonderer Klaerungsbedarf besteht (z. B. unklare Ausgestaltung der tatsaechlichen Geschaeftsfuehrung, Mischzwecke, kommerzielle Naehe, geschlossener Teilnehmerkreis, Mittelverwendung, Verguetungen, Veranstaltungs-/Ligaformate). Die Finanzbehoerde fuehrt vertiefte Pruefung durch (Rueckfragen, Anforderung weiterer Unterlagen, ggf. Anhoerung) und bescheidet erst nach Wuerdigung; gegenueber der Vorlage kann sich der Abgrenzungspruefpfad zwar in Richtung Nr. 21 verschieben, der Aufwand bleibt aber durch Einzelfallpruefung wesentlich hoeher als im Standardfall.",
          "aenderungsstatus": "geaendert"
        }
      ]
    }
  ]
}
```

---

## Step 6 — `case_group_development` (success)
- model: `gpt-5.2` | provider: `openai` | attempt: `734a3ef157a747b88c60b271c0cb8283` | elapsed: 16656 ms
- tokens: in=7183 out=1328 hidden_thinking=0 | cost: $0.031162

### Prompt

```

    Sie sind Legist im deutschen Bundestag und damit betraut, die 
    Erfüllungsaufwandsänderung zu einer geplanten Gesetzesänderung zu berechnen.

    Insbesondere werden zur Ermittlung der zu erwartenden Änderung des Aufwands 
    pro Fall die wesentlichen Tätigkeiten identifiziert, die zur Erfüllung 
    einer Vorgabe oder eines Prozesses im Einzelfall zu erwarten sind. Diese 
    schließen Tätigkeiten ein, welche neu hinzukommen, welche sich ändern und 
    welche wegfallen. Für diese Tätigkeiten werden die zu erwartenden Änderungen des 
    Zeit-, Personal- sowie Sachaufwands ermittelt.

    Die wesentlichen Unterschiede der Gesetzesänderung sind wie folgt 
    zusammengefasst: Aus dem Vergleich ergibt sich nur eine einzige materielle Änderung: In § 52 Abs. 2 Nr. 21 AO wird der Klammerzusatz von „Schach gilt als Sport“ zu „Schach gilt als Sport und E‑Sport gilt für diese Regelung als Sport“ erweitert. Alle übrigen Tatbestandsvoraussetzungen in Absatz 1 (Allgemeinheitsförderung, Abgrenzung zu geschlossenen Personenkreisen etc.) sowie der restliche Katalog gemeinnütziger Zwecke in Absatz 2 und die Öffnungsklausel am Ende bleiben wortgleich.

Ziel des Gesetzgebers ist damit erkennbar eine Klarstellung und Erweiterung des gemeinnützigen Zweckkatalogs zugunsten des E‑Sports: Körperschaften (z.B. Vereine, Stiftungen, gGmbHs), deren Satzungszweck und tatsächliche Geschäftsführung auf die Förderung von E‑Sport gerichtet ist, sollen unter dem bereits anerkannten Zweck „Förderung des Sports“ leichter und rechtssicher als gemeinnützig anerkannt werden. Praktisch bedeutet dies eine Reduzierung von Rechtsunsicherheit und uneinheitlicher Verwaltungspraxis, weil E‑Sport nicht mehr (nur) über andere Zwecke (z.B. Jugendhilfe, Bildung, Kultur, digitale Kompetenzen) „mitbegründet“ werden müsste, sondern unmittelbar als Sportförderung gemeinnützig sein kann.

Wesentliche Unterschiede/Wirkungen der Änderung:
- Erweiterter Anwendungsbereich von Nr. 21: Sportvereine im Sinne der Gemeinnützigkeit sollen ausdrücklich auch E‑Sport-Vereine umfassen.
- Rechtsfolgeebene (implizit): E‑Sport‑Organisationen können damit eher Zugang zu typischen Gemeinnützigkeitsfolgen erhalten (insbesondere steuerliche Begünstigungen, Spendenabzugsfähigkeit für Zuwendungen an die Körperschaft, erleichterte Mittelakquise), soweit sie die allgemeinen Gemeinnützigkeitsanforderungen (Selbstlosigkeit, Ausschließlichkeit, Unmittelbarkeit, tatsächliche Geschäftsführung, kein geschlossener Begünstigtenkreis) erfüllen.
- Keine Ausweitung anderer Zwecke/keine Änderung der Grunddefinition: Die Änderung schafft keinen neuen eigenständigen Zweck außerhalb des Sportbegriffs, sondern ordnet E‑Sport ausdrücklich dem bestehenden Zweck „Sport“ zu und lässt die übrige Systematik des § 52 AO unverändert.

    
        Die Gesetzesänderung führt zu folgenden, Erfüllungsaufwand auslösenden Prozessen für den betroffenen Normadressaten: [{"prozess_id": 14, "prozess_bezeichnung": "Gemeinnuetzigkeitsantrag/Steuerbeguenstigungsnachweis fuer E-Sport-Koerperschaften unter Zweck 'Foerderung des Sports' (inkl. Anpassung von Satzung/Begruendung/Unterlagen)", "prozess_beschreibung": "Korporationen der Wirtschaft (z. B. E-Sport-Vereine, gGmbHs, Stiftungen) richten die Geltendmachung der Gemeinnuetzigkeit bzw. Steuerbeguenstigungen kuenftig rechtssicherer auf den Zweck 'Foerderung des Sports' aus, da E-Sport fuer § 52 Abs. 2 Nr. 21 AO ausdruecklich als Sport gilt. Im Rahmen der (Neu-)Beantragung bzw. laufenden Nachweisfuehrung/Begruendung gegenueber der Finanzverwaltung (z. B. Feststellung/Veranlagung/Freistellung) verlagert sich der Begruendungspfad weg von alternativen gemeinnuetzigen Zwecken (z. B. Jugendhilfe/Bildung/Kultur) hin zur unmittelbaren Sportfoerderung; dadurch entfaellt in betroffenen Faellen der zusaetzliche Begruendungs- und Abgrenzungsaufwand ueber andere Zwecke und es kann interner Aufwand zur Umstellung der Standardtexte/Argumentation/Unterlagen anfallen.", "aenderungsstatus": "geaendert", "vorgaben": [{"vorgaben_id": 11, "normzitat": "§ 52 Abs. 2 Nr. 21 AO", "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}}, {"vorgaben_id": 12, "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)", "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}}]}]
        

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
        → Beispiel für Bildung von Fallgruppen (fiktiv):
Unternehmen, die bestimmte Industrieanlagen betreiben, sind zur Einhaltung neuer Vorgaben
und strengerer Schadstoffgrenzwerte verpflichtet. Es ist davon auszugehen, dass 80 Prozent der
1 000 betroffenen Unternehmen ihre bestehenden Anlagen lediglich mit neuen Filtersystemen
ausrüsten werden, während die restlichen 20 Prozent ihre Altanlagen komplett durch neue er-
setzen müssen, um die verschärften Grenzwerte einzuhalten. Es wird angenommen, dass der
Aufwand zur Umrüstung bestehender Anlagen sehr viel geringer ist als der Aufwand für den Er-
satz der Altanlagen durch Neuanlagen. Für die Ermittlung des Erfüllungsaufwands werden des-
halb zwei Fallgruppen gebildet:
Fallgruppe 1 Umrüstung bestehender Anlagen (800 Unternehmen)
Fallgruppe 2 Ersatz von Altanlagen durch Neuanlagen (200 Unternehmen)

        Geben Sie nur und ausschließlich JSON im folgenden Format zurück: 

        {
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
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft"
                },
                {
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft"
                }
            ]
            },
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
                },
                {
                    "vorgaben_id": "",
                    "normzitat": "",
                    "beschreibung": "",
                    "aenderungsstatus": ""
                }
            ], 
            "fallgruppen": [
                {
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft"
                }
            ]
            }
        ]
        }
        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 
        

Dieser Lauf betrifft den Normadressaten Wirtschaft.

        Beruecksichtigen Sie ausschliesslich den Erfuellungsaufwand der Wirtschaft.
        Analysieren Sie nur wirtschaftsbezogene Prozesse, Fallgruppen, Taetigkeiten,
        Fallzahlen und Werte. Uebernehmen Sie keine Verwaltungslogik, Verwaltungswerte
        oder buergerbezogenen Inhalte, sofern diese nicht ausdruecklich als Spiegelwirkung
        oder wirtschaftsrelevante Folge der Vorgabe begruendet sind. Informationspflichten
        der Wirtschaft, Spiegelsituationen, interne Umstellungen, externe Dienstleistungen
        sowie wirtschaftsspezifische Pruef-, Melde-, Nachweis- und Dokumentationspflichten
        sind mitzudenken.
```

### Raw Response

```
{
  "prozesse": [
    {
      "prozess_id": 14,
      "prozess_bezeichnung": "Gemeinnuetzigkeitsantrag/Steuerbeguenstigungsnachweis fuer E-Sport-Koerperschaften unter Zweck 'Foerderung des Sports' (inkl. Anpassung von Satzung/Begruendung/Unterlagen)",
      "prozess_beschreibung": "Korporationen der Wirtschaft (z. B. E-Sport-Vereine, gGmbHs, Stiftungen) richten die Geltendmachung der Gemeinnuetzigkeit bzw. Steuerbeguenstigungen kuenftig rechtssicherer auf den Zweck 'Foerderung des Sports' aus, da E-Sport fuer § 52 Abs. 2 Nr. 21 AO ausdruecklich als Sport gilt. Im Rahmen der (Neu-)Beantragung bzw. laufenden Nachweisfuehrung/Begruendung gegenueber der Finanzverwaltung (z. B. Feststellung/Veranlagung/Freistellung) verlagert sich der Begruendungspfad weg von alternativen gemeinnuetzigen Zwecken (z. B. Jugendhilfe/Bildung/Kultur) hin zur unmittelbaren Sportfoerderung; dadurch entfaellt in betroffenen Faellen der zusaetzliche Begruendungs- und Abgrenzungsaufwand ueber andere Zwecke und es kann interner Aufwand zur Umstellung der Standardtexte/Argumentation/Unterlagen anfallen.",
      "aenderungsstatus": "geaendert",
      "vorgaben": [
        {
          "vorgaben_id": 11,
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO",
          "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).",
          "aenderungsstatus": "geaendert"
        },
        {
          "vorgaben_id": 12,
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)",
          "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.",
          "aenderungsstatus": "geaendert"
        }
      ],
      "fallgruppen": [
        {
          "fallgruppe_bezeichnung": "Neuantrag/Erstanerkennung Gemeinnuetzigkeit fuer E-Sport-Koerperschaft unter Zweck 'Foerderung des Sports' (statt alternativer Zwecke)",
          "fallgruppe_beschreibung": "E-Sport-Koerperschaften, die erstmals die Gemeinnuetzigkeit/Steuerbeguenstigung beantragen, koennen den Antrag und die Begruendung unmittelbar auf 'Foerderung des Sports' stuetzen. Im Vergleich zur bisherigen (unsicheren) Praxis entfaellt typischerweise zusaetzlicher Begruendungs- und Abgrenzungsaufwand, der zuvor fuer die Herleitung ueber alternative gemeinnuetzige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) sowie fuer entsprechende Satzungs- und Konzeptbegruendungen angefallen waere. Ggf. verbleibt ein einmaliger interner Aufwand zur Erstellung/Anpassung von Standardtexten, Satzungsbausteinen und Nachweisunterlagen auf den Sportzweck mit E-Sport-Bezug.",
          "aenderungsstatus": "geaendert"
        },
        {
          "fallgruppe_bezeichnung": "Bestandskoerperschaft: Umstellung/Anpassung Satzung, Zweckformulierung und Nachweisfuehrung auf 'Sport (inkl. E-Sport)'",
          "fallgruppe_beschreibung": "Bereits bestehende E-Sport-Koerperschaften mit laufender Gemeinnuetzigkeitsfuehrung (z. B. gueltiger Freistellungsbescheid bzw. turnusmaessige Nachweis- und Erklaerungsprozesse), die bisher (aus Rechtsunsicherheit) teilweise ueber alternative Zwecke argumentiert oder Mischbegruendungen genutzt haben, stellen ihre Standardargumentation, Unterlagen und ggf. die Satzungszweckbeschreibung auf 'Foerderung des Sports' um. Dies kann einen einmaligen internen Abstimmungs- und Dokumentationsaufwand (inkl. ggf. externer Beratung/Steuerberatung) ausloesen; zugleich reduziert sich kuenftig der wiederkehrende Begruendungs- und Abgrenzungsaufwand, weil der zusaetzliche alternative Begruendungspfad entfaellt.",
          "aenderungsstatus": "geaendert"
        },
        {
          "fallgruppe_bezeichnung": "Bestandskoerperschaft: Keine materielle Umstellung erforderlich (E-Sport bereits als Sport behandelt/abgebildet)",
          "fallgruppe_beschreibung": "E-Sport-Koerperschaften, die bereits vor der Klarstellung ihre Gemeinnuetzigkeit unter 'Foerderung des Sports' (oder in der praktischen Umsetzung gleichwertig) begruendet und dokumentiert haben, muessen keine oder nur minimale Anpassungen vornehmen (z. B. Aktualisierung von Textbausteinen/Verweisen). Der wesentliche Effekt liegt in reduzierter Rechtsunsicherheit ohne nennenswerten zusaetzlichen internen Zeit- oder Sachaufwand.",
          "aenderungsstatus": "geaendert"
        }
      ]
    }
  ]
}
```

---

## Step 7 — `process_step_analysis` (success)
- model: `gpt-5.2` | provider: `openai` | attempt: `562bf144ffbc4c4f932d28d379f2ed7e` | elapsed: 33704 ms
- tokens: in=9421 out=2825 hidden_thinking=0 | cost: $0.056037

### Prompt

```

    Sie sind Legist im deutschen Bundestag und damit betraut, die 
    Erfüllungsaufwandsänderung zu einer geplanten Gesetzesänderung zu berechnen.

    Insbesondere werden zur Ermittlung der zu erwartenden Änderung des Aufwands 
    pro Fall die wesentlichen Tätigkeiten identifiziert, die zur Erfüllung 
    einer Vorgabe oder eines Prozesses im Einzelfall zu erwarten sind. Diese 
    schließen Tätigkeiten ein, welche neu hinzukommen, welche sich ändern und 
    welche wegfallen. Für diese Tätigkeiten werden die zu erwartenden Änderungen des 
    Zeit-, Personal- sowie Sachaufwands ermittelt.

    Die wesentlichen Unterschiede der Gesetzesänderung sind wie folgt 
    zusammengefasst: Aus dem Vergleich ergibt sich nur eine einzige materielle Änderung: In § 52 Abs. 2 Nr. 21 AO wird der Klammerzusatz von „Schach gilt als Sport“ zu „Schach gilt als Sport und E‑Sport gilt für diese Regelung als Sport“ erweitert. Alle übrigen Tatbestandsvoraussetzungen in Absatz 1 (Allgemeinheitsförderung, Abgrenzung zu geschlossenen Personenkreisen etc.) sowie der restliche Katalog gemeinnütziger Zwecke in Absatz 2 und die Öffnungsklausel am Ende bleiben wortgleich.

Ziel des Gesetzgebers ist damit erkennbar eine Klarstellung und Erweiterung des gemeinnützigen Zweckkatalogs zugunsten des E‑Sports: Körperschaften (z.B. Vereine, Stiftungen, gGmbHs), deren Satzungszweck und tatsächliche Geschäftsführung auf die Förderung von E‑Sport gerichtet ist, sollen unter dem bereits anerkannten Zweck „Förderung des Sports“ leichter und rechtssicher als gemeinnützig anerkannt werden. Praktisch bedeutet dies eine Reduzierung von Rechtsunsicherheit und uneinheitlicher Verwaltungspraxis, weil E‑Sport nicht mehr (nur) über andere Zwecke (z.B. Jugendhilfe, Bildung, Kultur, digitale Kompetenzen) „mitbegründet“ werden müsste, sondern unmittelbar als Sportförderung gemeinnützig sein kann.

Wesentliche Unterschiede/Wirkungen der Änderung:
- Erweiterter Anwendungsbereich von Nr. 21: Sportvereine im Sinne der Gemeinnützigkeit sollen ausdrücklich auch E‑Sport-Vereine umfassen.
- Rechtsfolgeebene (implizit): E‑Sport‑Organisationen können damit eher Zugang zu typischen Gemeinnützigkeitsfolgen erhalten (insbesondere steuerliche Begünstigungen, Spendenabzugsfähigkeit für Zuwendungen an die Körperschaft, erleichterte Mittelakquise), soweit sie die allgemeinen Gemeinnützigkeitsanforderungen (Selbstlosigkeit, Ausschließlichkeit, Unmittelbarkeit, tatsächliche Geschäftsführung, kein geschlossener Begünstigtenkreis) erfüllen.
- Keine Ausweitung anderer Zwecke/keine Änderung der Grunddefinition: Die Änderung schafft keinen neuen eigenständigen Zweck außerhalb des Sportbegriffs, sondern ordnet E‑Sport ausdrücklich dem bestehenden Zweck „Sport“ zu und lässt die übrige Systematik des § 52 AO unverändert.

    
        Die Gesetzesänderung führt zu folgenden, positiven oder negativen Erfüllungsaufwand auslösenden Prozessen für den betroffenen Normadressaten, welche durch folgende 
        Fallgruppen differenziert werden: [{"prozess_id": 13, "prozess_bezeichnung": "Pruefung und Bescheidung der Gemeinnuetzigkeit bei E-Sport-Foerderung als Sport (Anerkennungs-/Freistellungsverfahren)", "prozess_beschreibung": "Bearbeitung von Verfahren, in denen Koerperschaften ihre Gemeinnuetzigkeit/Steuerbeguenzigung (z. B. im Rahmen von Feststellungs-, Veranlagungs- und Freistellungsverfahren) geltend machen und die Finanzbehoerde die Einordnung des Satzungszwecks und der tatsaechlichen Geschaeftsfuehrung unter den gemeinnuetzigkeitsrechtlichen Zweck \"Foerderung des Sports\" nun ausdruecklich einschliesslich E-Sport prueft. Hierzu gehoeren die Anpassung bzw. Anwendung der pruefungsleitenden Arbeitsschritte und Begruendungstexte (Einordnung E-Sport als Sport), die Wuerdigung der unveraenderten allgemeinen Gemeinnuetzigkeitsvoraussetzungen sowie die Bescheidung/kommunikative Rueckfragen im Einzelfall. Der Prozess bildet zugleich die Spiegelsituation ab: Die Verwaltungshandlung wird typischerweise durch das Begehren der Koerperschaft ausgeloest, ist aber als eigener Vollzugsvorgang der Finanzverwaltung auszuweisen.", "aenderungsstatus": "geaendert", "vorgaben": [{"vorgaben_id": 11, "normzitat": "§ 52 Abs. 2 Nr. 21 AO", "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}}, {"vorgaben_id": 12, "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)", "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}}], "fallgruppen": [{"fallgruppen_id": 23, "fallgruppe_bezeichnung": "Standardfall: Einordnung E-Sport als Sport ohne besondere Rueckfragen (Erst- oder laufendes Verfahren)", "fallgruppe_beschreibung": "Die Koerperschaft beantragt bzw. macht die Steuerbeguenstigung geltend und legt eine Satzung/Taetigkeitsdarstellung vor, bei der E-Sport-Foerderung klar erkennbar ist und die uebrigen Gemeinnuetzigkeitsvoraussetzungen nach Aktenlage unproblematisch erfuellt sind. Die Finanzbehoerde ordnet den Zweck im Pruefschritt nun unmittelbar unter \"Foerderung des Sports\" (inkl. E-Sport) ein und verwendet standardisierte Begruendungstexte/Arbeitshinweise; der bisher in Teilen erforderliche Umweg ueber alternative Zwecke entfaellt. Der Aufwand pro Fall aendert sich durch verkuerzte/pragmatisierte Begruendung und weniger Abgrenzungspruefung.", "aenderungsstatus": "geaendert", "spiegelsituationen": [{"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}, {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}]}, {"fallgruppen_id": 24, "fallgruppe_bezeichnung": "Sonderfall: Abgrenzungs-/Vertiefungspruefung trotz Klarstellung (Rueckfragen/Anhoerung)", "fallgruppe_beschreibung": "Faelle mit E-Sport-Bezug, in denen trotz Einordnungsmöglichkeit als Sport besonderer Klaerungsbedarf besteht (z. B. unklare Ausgestaltung der tatsaechlichen Geschaeftsfuehrung, Mischzwecke, kommerzielle Naehe, geschlossener Teilnehmerkreis, Mittelverwendung, Verguetungen, Veranstaltungs-/Ligaformate). Die Finanzbehoerde fuehrt vertiefte Pruefung durch (Rueckfragen, Anforderung weiterer Unterlagen, ggf. Anhoerung) und bescheidet erst nach Wuerdigung; gegenueber der Vorlage kann sich der Abgrenzungspruefpfad zwar in Richtung Nr. 21 verschieben, der Aufwand bleibt aber durch Einzelfallpruefung wesentlich hoeher als im Standardfall.", "aenderungsstatus": "geaendert", "spiegelsituationen": [{"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}, {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}]}]}]
        

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

        Ordnen Sie jede Taetigkeit denjenigen Vorgaben des Prozesses zu, die diese Taetigkeit fachlich ausloesen. Geben Sie dazu je Taetigkeit das Feld
        `vorgaben_ids` als Liste der passenden `vorgaben_id`-Werte an. Wenn im Prozess nur genau eine Vorgabe enthalten ist, soll diese eine `vorgaben_id`
        auch bei allen zugehoerigen Taetigkeiten angegeben werden.

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
        
        {
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
                            "taetigkeit": "",
                            "beschreibung": "",
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert",
                            "vorgaben_ids": [""]
                        },
                        {
                            "taetigkeit": "",
                            "beschreibung": "",
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert",
                            "vorgaben_ids": [""]
                        }
                    ]
                },
                {
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "",
                    "taetigkeiten": [ 
                        {
                            "taetigkeit": "",
                            "beschreibung": "",
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert",
                            "vorgaben_ids": [""]
                        }
                    ]
                }
            ]
            },
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
                },
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
                            "taetigkeit": "",
                            "beschreibung": "",
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert",
                            "vorgaben_ids": [""]
                        },
                        {
                            "taetigkeit": "",
                            "beschreibung": "",
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert",
                            "vorgaben_ids": [""]
                        }
                    ]
                }
            ]
            }
        ]
        }
        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 

        

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
        Fallgruppen, Taetigkeiten, Fallzahlen oder Werte, sofern diese nicht
        ausdruecklich als Spiegelwirkung der Verwaltung zuzurechnen sind. Vermeiden
        Sie zugleich, aus Vorsicht ganze Vollzugsstraenge wegzulassen: wenn eine
        Regelung die Verwaltung zur Pruefung, Bescheidung oder Aufsicht verpflichtet,
        ist dieser Vollzugsaufwand auszuweisen, auch wenn er aus einem wirtschafts-
        oder buergerseitigen Antrag ausgeloest wird.

Zusatz fuer die Verwaltung bei der Schrittanalyse: Jede Taetigkeit beschreibt eine Bearbeitungshandlung der Verwaltung pro einzelnem Vorgang (z.B. Unterlagen sichten, Zweckzuordnung pruefen, Bescheid erstellen). Weisen Sie pro Taetigkeit mindestens eine Lohngruppe (A=einfacher/mittlerer Dienst, B=gehobener Dienst, C=hoeherer Dienst, D=Durchschnitt) mit realistischem Zeitaufwand in Minuten aus. Null-Zeitaufwaende sind nur zulaessig, wenn die Taetigkeit tatsaechlich entfaellt (aenderungsstatus=abgeschafft) oder durch IT-Automatisierung ersetzt ist; in diesem Fall ist dies in der Beschreibung zu begruenden.
```

### Raw Response

```
{
  "prozesse": [
    {
      "prozess_id": 13,
      "prozess_bezeichnung": "Pruefung und Bescheidung der Gemeinnuetzigkeit bei E-Sport-Foerderung als Sport (Anerkennungs-/Freistellungsverfahren)",
      "prozess_beschreibung": "Bearbeitung von Verfahren, in denen Koerperschaften ihre Gemeinnuetzigkeit/Steuerbeguenzigung (z. B. im Rahmen von Feststellungs-, Veranlagungs- und Freistellungsverfahren) geltend machen und die Finanzbehoerde die Einordnung des Satzungszwecks und der tatsaechlichen Geschaeftsfuehrung unter den gemeinnuetzigkeitsrechtlichen Zweck \"Foerderung des Sports\" nun ausdruecklich einschliesslich E-Sport prueft. Hierzu gehoeren die Anpassung bzw. Anwendung der pruefungsleitenden Arbeitsschritte und Begruendungstexte (Einordnung E-Sport als Sport), die Wuerdigung der unveraenderten allgemeinen Gemeinnuetzigkeitsvoraussetzungen sowie die Bescheidung/kommunikative Rueckfragen im Einzelfall. Der Prozess bildet zugleich die Spiegelsituation ab: Die Verwaltungshandlung wird typischerweise durch das Begehren der Koerperschaft ausgeloest, ist aber als eigener Vollzugsvorgang der Finanzverwaltung auszuweisen.",
      "aenderungsstatus": "geaendert",
      "vorgaben": [
        {
          "vorgaben_id": 11,
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO",
          "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).",
          "aenderungsstatus": "geaendert"
        },
        {
          "vorgaben_id": 12,
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)",
          "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.",
          "aenderungsstatus": "geaendert"
        }
      ],
      "fallgruppen": [
        {
          "fallgruppen_id": 23,
          "fallgruppe_bezeichnung": "Standardfall: Einordnung E-Sport als Sport ohne besondere Rueckfragen (Erst- oder laufendes Verfahren)",
          "fallgruppe_beschreibung": "Die Koerperschaft beantragt bzw. macht die Steuerbeguenstigung geltend und legt eine Satzung/Taetigkeitsdarstellung vor, bei der E-Sport-Foerderung klar erkennbar ist und die uebrigen Gemeinnuetzigkeitsvoraussetzungen nach Aktenlage unproblematisch erfuellt sind. Die Finanzbehoerde ordnet den Zweck im Pruefschritt nun unmittelbar unter \"Foerderung des Sports\" (inkl. E-Sport) ein und verwendet standardisierte Begruendungstexte/Arbeitshinweise; der bisher in Teilen erforderliche Umweg ueber alternative Zwecke entfaellt. Der Aufwand pro Fall aendert sich durch verkuerzte/pragmatisierte Begruendung und weniger Abgrenzungspruefung.",
          "aenderungsstatus": "geaendert",
          "taetigkeiten": [
            {
              "taetigkeit": "Unterlagen sichten und Vollstaendigkeit pruefen (Satzung/Taetigkeitsdarstellung mit E-Sport-Bezug)",
              "beschreibung": "Sichtung der eingereichten Satzung, Anlagen und Taetigkeitsdarstellung; formelle Vollstaendigkeits- und Plausibilitaetspruefung. Gegenueber der Rechtslage aendert sich dieser Schritt im Kern nicht, wird aber i.d.R. mit kuerzerer Nacharbeitung zur Zweckzuordnung verbunden, weil E-Sport nicht mehr ueber alternative Zwecke 'mitbegruendet' werden muss.",
              "aenderungsstatus": "geaendert",
              "vorgaben_ids": [
                11,
                12
              ],
              "lohn_und_zeit": [
                {
                  "lohngruppe": "B",
                  "zeit_minuten": 20
                }
              ]
            },
            {
              "taetigkeit": "Inhaltliche Zweckzuordnung: E-Sport als Sport nach Nr. 21 feststellen",
              "beschreibung": "Pruefung und Feststellung, dass der satzungsmaessige Zweck und die tatsaechliche Geschaeftsfuehrung (soweit aktenkundig) unter \"Foerderung des Sports\" fallen, wobei E-Sport nun ausdruecklich einbezogen ist. Der Aufwand sinkt gegenueber der bisherigen (uneinheitlichen) Einordnung, weil die rechtliche Subsumtion/Argumentation fuer die Sportqualifikation vereinfacht ist.",
              "aenderungsstatus": "geaendert",
              "vorgaben_ids": [
                11
              ],
              "lohn_und_zeit": [
                {
                  "lohngruppe": "B",
                  "zeit_minuten": 25
                }
              ]
            },
            {
              "taetigkeit": "Wegfall/Reduktion des alternativen Pruefpfads (Jugendhilfe/Bildung/Kultur etc.)",
              "beschreibung": "Bisher: zusaetzliche Prüfung, ob und wie E-Sport-Foerderung tragfaehig über andere gemeinnuetzige Zwecke zu begruenden ist (inkl. Abgrenzungspruefung, zusaetzliche Begruendungstexte). Kuenftig: entfaellt typischerweise im Standardfall, weil die Einordnung vorrangig als Sportfoerderung erfolgen kann.",
              "aenderungsstatus": "abgeschafft",
              "vorgaben_ids": [
                12
              ],
              "lohn_und_zeit": [
                {
                  "lohngruppe": "B",
                  "zeit_minuten": 0
                }
              ]
            },
            {
              "taetigkeit": "Bescheid/Entscheidungstext erstellen und Akte dokumentieren (Standardbausteine mit E-Sport-Bezug)",
              "beschreibung": "Erstellung/Anpassung des Bescheids (z. B. Feststellung/Freistellung) unter Verwendung angepasster Standardformulierungen zur Einordnung von E-Sport als Sport; kurze Dokumentation/Vermerk in der Akte. Gegenueber vorher geaendert durch kuerzere und standardisierte Begruendung sowie weniger Erlaeuterungsbedarf zur Zweckherleitung.",
              "aenderungsstatus": "geaendert",
              "vorgaben_ids": [
                11,
                12
              ],
              "lohn_und_zeit": [
                {
                  "lohngruppe": "B",
                  "zeit_minuten": 20
                }
              ]
            }
          ]
        },
        {
          "fallgruppen_id": 24,
          "fallgruppe_bezeichnung": "Sonderfall: Abgrenzungs-/Vertiefungspruefung trotz Klarstellung (Rueckfragen/Anhoerung)",
          "fallgruppe_beschreibung": "Faelle mit E-Sport-Bezug, in denen trotz Einordnungsmöglichkeit als Sport besonderer Klaerungsbedarf besteht (z. B. unklare Ausgestaltung der tatsaechlichen Geschaeftsfuehrung, Mischzwecke, kommerzielle Naehe, geschlossener Teilnehmerkreis, Mittelverwendung, Verguetungen, Veranstaltungs-/Ligaformate). Die Finanzbehoerde fuehrt vertiefte Pruefung durch (Rueckfragen, Anforderung weiterer Unterlagen, ggf. Anhoerung) und bescheidet erst nach Wuerdigung; gegenueber der Vorlage kann sich der Abgrenzungspruefpfad zwar in Richtung Nr. 21 verschieben, der Aufwand bleibt aber durch Einzelfallpruefung wesentlich hoeher als im Standardfall.",
          "aenderungsstatus": "geaendert",
          "taetigkeiten": [
            {
              "taetigkeit": "Unterlagen sichten, Sachverhalt strukturieren und Pruefschwerpunkte festlegen (E-Sport-Fall mit Besonderheiten)",
              "beschreibung": "Sichtung/Strukturierung der Unterlagen (Satzung, Ordnungen, Verträge/Kooperationen, Veranstaltungs-/Ligaformate, Mittelverwendung); Ableitung der Pruefschwerpunkte (z. B. Selbstlosigkeit, geschlossener Beguenstigtenkreis, kommerzielle Naehe). Gegenueber vorher geaendert, weil die Vorpruefung zur Sportqualifikation klarer ist und frueher in die materiellen Abgrenzungsfragen ueberleitet.",
              "aenderungsstatus": "geaendert",
              "vorgaben_ids": [
                11,
                12
              ],
              "lohn_und_zeit": [
                {
                  "lohngruppe": "B",
                  "zeit_minuten": 30
                }
              ]
            },
            {
              "taetigkeit": "Rueckfragen/Anforderung weiterer Unterlagen und ggf. Anhoerung",
              "beschreibung": "Kommunikation mit der Koerperschaft zur Klaerung streitiger/unklarer Punkte (z. B. tatsaechliche Geschaeftsfuehrung, Mischzwecke, Teilnehmerkreis, Verguetungen, Sponsoring/kommerzieller Zuschnitt); ggf. Anhoerung und Nachforderung von Nachweisen. Grundsaetzlich unveraendert als Verfahrenshandlung; kann jedoch in einzelnen Faellen kuerzer ausfallen, soweit die Zweckherleitung nicht mehr ueber alternative Zwecke gefuehrt werden muss.",
              "aenderungsstatus": "geaendert",
              "vorgaben_ids": [
                12
              ],
              "lohn_und_zeit": [
                {
                  "lohngruppe": "B",
                  "zeit_minuten": 60
                }
              ]
            },
            {
              "taetigkeit": "Vertiefte inhaltliche Pruefung und Bewertung (inkl. Einordnung E-Sport als Sport + Gemeinnuetzigkeitskriterien)",
              "beschreibung": "Vertiefte rechtliche und tatsaechliche Wuerdigung: Einordnung des E-Sport-Bezugs unter Sportfoerderung nach Nr. 21 sowie (unveraendert) Pruefung der allgemeinen Gemeinnuetzigkeitsvoraussetzungen und Abgrenzungen (z. B. Ausschliesslichkeit, Unmittelbarkeit, Selbstlosigkeit, kein geschlossener Beguenstigtenkreis, Mittelverwendung). Gegenueber vorher geaendert durch Vereinfachung im Teilaspekt 'Sportqualifikation' und Wegfall des Zwangs, eine alternative Zweckkette als Hauptbegruendung aufzubauen.",
              "aenderungsstatus": "geaendert",
              "vorgaben_ids": [
                11,
                12
              ],
              "lohn_und_zeit": [
                {
                  "lohngruppe": "B",
                  "zeit_minuten": 90
                },
                {
                  "lohngruppe": "C",
                  "zeit_minuten": 20
                }
              ]
            },
            {
              "taetigkeit": "Entscheidung treffen, Bescheid begruenden/erstellen und Dokumentation (inkl. Abweichungs- und Abgrenzungsbegruendung)",
              "beschreibung": "Erstellung des (ggf. ablehnenden/teilweise ablehnenden) Bescheids inkl. ausfuehrlicher Begruendung, Vermerken und Dokumentation der Abgrenzung. Gegenueber vorher geaendert, weil die Textbausteine zur Sportqualifikation angepasst/standardisierbar sind; der vertiefte Teil bleibt fallbedingt aufwendig.",
              "aenderungsstatus": "geaendert",
              "vorgaben_ids": [
                11,
                12
              ],
              "lohn_und_zeit": [
                {
                  "lohngruppe": "B",
                  "zeit_minuten": 45
                },
                {
                  "lohngruppe": "C",
                  "zeit_minuten": 15
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

---

## Step 8 — `process_step_analysis` (success)
- model: `gpt-5.2` | provider: `openai` | attempt: `d1c786c32586415ea446a10b9e520ef9` | elapsed: 35488 ms
- tokens: in=9589 out=2929 hidden_thinking=0 | cost: $0.057787

### Prompt

```

    Sie sind Legist im deutschen Bundestag und damit betraut, die 
    Erfüllungsaufwandsänderung zu einer geplanten Gesetzesänderung zu berechnen.

    Insbesondere werden zur Ermittlung der zu erwartenden Änderung des Aufwands 
    pro Fall die wesentlichen Tätigkeiten identifiziert, die zur Erfüllung 
    einer Vorgabe oder eines Prozesses im Einzelfall zu erwarten sind. Diese 
    schließen Tätigkeiten ein, welche neu hinzukommen, welche sich ändern und 
    welche wegfallen. Für diese Tätigkeiten werden die zu erwartenden Änderungen des 
    Zeit-, Personal- sowie Sachaufwands ermittelt.

    Die wesentlichen Unterschiede der Gesetzesänderung sind wie folgt 
    zusammengefasst: Aus dem Vergleich ergibt sich nur eine einzige materielle Änderung: In § 52 Abs. 2 Nr. 21 AO wird der Klammerzusatz von „Schach gilt als Sport“ zu „Schach gilt als Sport und E‑Sport gilt für diese Regelung als Sport“ erweitert. Alle übrigen Tatbestandsvoraussetzungen in Absatz 1 (Allgemeinheitsförderung, Abgrenzung zu geschlossenen Personenkreisen etc.) sowie der restliche Katalog gemeinnütziger Zwecke in Absatz 2 und die Öffnungsklausel am Ende bleiben wortgleich.

Ziel des Gesetzgebers ist damit erkennbar eine Klarstellung und Erweiterung des gemeinnützigen Zweckkatalogs zugunsten des E‑Sports: Körperschaften (z.B. Vereine, Stiftungen, gGmbHs), deren Satzungszweck und tatsächliche Geschäftsführung auf die Förderung von E‑Sport gerichtet ist, sollen unter dem bereits anerkannten Zweck „Förderung des Sports“ leichter und rechtssicher als gemeinnützig anerkannt werden. Praktisch bedeutet dies eine Reduzierung von Rechtsunsicherheit und uneinheitlicher Verwaltungspraxis, weil E‑Sport nicht mehr (nur) über andere Zwecke (z.B. Jugendhilfe, Bildung, Kultur, digitale Kompetenzen) „mitbegründet“ werden müsste, sondern unmittelbar als Sportförderung gemeinnützig sein kann.

Wesentliche Unterschiede/Wirkungen der Änderung:
- Erweiterter Anwendungsbereich von Nr. 21: Sportvereine im Sinne der Gemeinnützigkeit sollen ausdrücklich auch E‑Sport-Vereine umfassen.
- Rechtsfolgeebene (implizit): E‑Sport‑Organisationen können damit eher Zugang zu typischen Gemeinnützigkeitsfolgen erhalten (insbesondere steuerliche Begünstigungen, Spendenabzugsfähigkeit für Zuwendungen an die Körperschaft, erleichterte Mittelakquise), soweit sie die allgemeinen Gemeinnützigkeitsanforderungen (Selbstlosigkeit, Ausschließlichkeit, Unmittelbarkeit, tatsächliche Geschäftsführung, kein geschlossener Begünstigtenkreis) erfüllen.
- Keine Ausweitung anderer Zwecke/keine Änderung der Grunddefinition: Die Änderung schafft keinen neuen eigenständigen Zweck außerhalb des Sportbegriffs, sondern ordnet E‑Sport ausdrücklich dem bestehenden Zweck „Sport“ zu und lässt die übrige Systematik des § 52 AO unverändert.

    
        Die Gesetzesänderung führt zu folgenden, positiven oder negativen Erfüllungsaufwand auslösenden Prozessen für den betroffenen Normadressaten, welche durch folgende 
        Fallgruppen differenziert werden: [{"prozess_id": 14, "prozess_bezeichnung": "Gemeinnuetzigkeitsantrag/Steuerbeguenstigungsnachweis fuer E-Sport-Koerperschaften unter Zweck 'Foerderung des Sports' (inkl. Anpassung von Satzung/Begruendung/Unterlagen)", "prozess_beschreibung": "Korporationen der Wirtschaft (z. B. E-Sport-Vereine, gGmbHs, Stiftungen) richten die Geltendmachung der Gemeinnuetzigkeit bzw. Steuerbeguenstigungen kuenftig rechtssicherer auf den Zweck 'Foerderung des Sports' aus, da E-Sport fuer § 52 Abs. 2 Nr. 21 AO ausdruecklich als Sport gilt. Im Rahmen der (Neu-)Beantragung bzw. laufenden Nachweisfuehrung/Begruendung gegenueber der Finanzverwaltung (z. B. Feststellung/Veranlagung/Freistellung) verlagert sich der Begruendungspfad weg von alternativen gemeinnuetzigen Zwecken (z. B. Jugendhilfe/Bildung/Kultur) hin zur unmittelbaren Sportfoerderung; dadurch entfaellt in betroffenen Faellen der zusaetzliche Begruendungs- und Abgrenzungsaufwand ueber andere Zwecke und es kann interner Aufwand zur Umstellung der Standardtexte/Argumentation/Unterlagen anfallen.", "aenderungsstatus": "geaendert", "vorgaben": [{"vorgaben_id": 11, "normzitat": "§ 52 Abs. 2 Nr. 21 AO", "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}}, {"vorgaben_id": 12, "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)", "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}}], "fallgruppen": [{"fallgruppen_id": 25, "fallgruppe_bezeichnung": "Neuantrag/Erstanerkennung Gemeinnuetzigkeit fuer E-Sport-Koerperschaft unter Zweck 'Foerderung des Sports' (statt alternativer Zwecke)", "fallgruppe_beschreibung": "E-Sport-Koerperschaften, die erstmals die Gemeinnuetzigkeit/Steuerbeguenstigung beantragen, koennen den Antrag und die Begruendung unmittelbar auf 'Foerderung des Sports' stuetzen. Im Vergleich zur bisherigen (unsicheren) Praxis entfaellt typischerweise zusaetzlicher Begruendungs- und Abgrenzungsaufwand, der zuvor fuer die Herleitung ueber alternative gemeinnuetzige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) sowie fuer entsprechende Satzungs- und Konzeptbegruendungen angefallen waere. Ggf. verbleibt ein einmaliger interner Aufwand zur Erstellung/Anpassung von Standardtexten, Satzungsbausteinen und Nachweisunterlagen auf den Sportzweck mit E-Sport-Bezug.", "aenderungsstatus": "geaendert", "spiegelsituationen": [{"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}, {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}]}, {"fallgruppen_id": 26, "fallgruppe_bezeichnung": "Bestandskoerperschaft: Umstellung/Anpassung Satzung, Zweckformulierung und Nachweisfuehrung auf 'Sport (inkl. E-Sport)'", "fallgruppe_beschreibung": "Bereits bestehende E-Sport-Koerperschaften mit laufender Gemeinnuetzigkeitsfuehrung (z. B. gueltiger Freistellungsbescheid bzw. turnusmaessige Nachweis- und Erklaerungsprozesse), die bisher (aus Rechtsunsicherheit) teilweise ueber alternative Zwecke argumentiert oder Mischbegruendungen genutzt haben, stellen ihre Standardargumentation, Unterlagen und ggf. die Satzungszweckbeschreibung auf 'Foerderung des Sports' um. Dies kann einen einmaligen internen Abstimmungs- und Dokumentationsaufwand (inkl. ggf. externer Beratung/Steuerberatung) ausloesen; zugleich reduziert sich kuenftig der wiederkehrende Begruendungs- und Abgrenzungsaufwand, weil der zusaetzliche alternative Begruendungspfad entfaellt.", "aenderungsstatus": "geaendert", "spiegelsituationen": [{"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}, {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}]}, {"fallgruppen_id": 27, "fallgruppe_bezeichnung": "Bestandskoerperschaft: Keine materielle Umstellung erforderlich (E-Sport bereits als Sport behandelt/abgebildet)", "fallgruppe_beschreibung": "E-Sport-Koerperschaften, die bereits vor der Klarstellung ihre Gemeinnuetzigkeit unter 'Foerderung des Sports' (oder in der praktischen Umsetzung gleichwertig) begruendet und dokumentiert haben, muessen keine oder nur minimale Anpassungen vornehmen (z. B. Aktualisierung von Textbausteinen/Verweisen). Der wesentliche Effekt liegt in reduzierter Rechtsunsicherheit ohne nennenswerten zusaetzlichen internen Zeit- oder Sachaufwand.", "aenderungsstatus": "geaendert", "spiegelsituationen": [{"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}, {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}]}]}]
        

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

        Ordnen Sie jede Taetigkeit denjenigen Vorgaben des Prozesses zu, die diese Taetigkeit fachlich ausloesen. Geben Sie dazu je Taetigkeit das Feld
        `vorgaben_ids` als Liste der passenden `vorgaben_id`-Werte an. Wenn im Prozess nur genau eine Vorgabe enthalten ist, soll diese eine `vorgaben_id`
        auch bei allen zugehoerigen Taetigkeiten angegeben werden.

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
        
        {
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
                            "taetigkeit": "",
                            "beschreibung": "",
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert",
                            "vorgaben_ids": [""]
                        },
                        {
                            "taetigkeit": "",
                            "beschreibung": "",
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert",
                            "vorgaben_ids": [""]
                        }
                    ]
                },
                {
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "",
                    "taetigkeiten": [ 
                        {
                            "taetigkeit": "",
                            "beschreibung": "",
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert",
                            "vorgaben_ids": [""]
                        }
                    ]
                }
            ]
            },
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
                },
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
                            "taetigkeit": "",
                            "beschreibung": "",
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert",
                            "vorgaben_ids": [""]
                        },
                        {
                            "taetigkeit": "",
                            "beschreibung": "",
                            "aenderungsstatus": "eingefuehrt | geaendert | abgeschafft | unveraendert",
                            "vorgaben_ids": [""]
                        }
                    ]
                }
            ]
            }
        ]
        }
        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 

        

Dieser Lauf betrifft den Normadressaten Wirtschaft.

        Beruecksichtigen Sie ausschliesslich den Erfuellungsaufwand der Wirtschaft.
        Analysieren Sie nur wirtschaftsbezogene Prozesse, Fallgruppen, Taetigkeiten,
        Fallzahlen und Werte. Uebernehmen Sie keine Verwaltungslogik, Verwaltungswerte
        oder buergerbezogenen Inhalte, sofern diese nicht ausdruecklich als Spiegelwirkung
        oder wirtschaftsrelevante Folge der Vorgabe begruendet sind. Informationspflichten
        der Wirtschaft, Spiegelsituationen, interne Umstellungen, externe Dienstleistungen
        sowie wirtschaftsspezifische Pruef-, Melde-, Nachweis- und Dokumentationspflichten
        sind mitzudenken.
```

### Raw Response

```
{
  "prozesse": [
    {
      "prozess_id": 14,
      "prozess_bezeichnung": "Gemeinnuetzigkeitsantrag/Steuerbeguenstigungsnachweis fuer E-Sport-Koerperschaften unter Zweck 'Foerderung des Sports' (inkl. Anpassung von Satzung/Begruendung/Unterlagen)",
      "prozess_beschreibung": "Korporationen der Wirtschaft (z. B. E-Sport-Vereine, gGmbHs, Stiftungen) richten die Geltendmachung der Gemeinnuetzigkeit bzw. Steuerbeguenstigungen kuenftig rechtssicherer auf den Zweck 'Foerderung des Sports' aus, da E-Sport fuer § 52 Abs. 2 Nr. 21 AO ausdruecklich als Sport gilt. Im Rahmen der (Neu-)Beantragung bzw. laufenden Nachweisfuehrung/Begruendung gegenueber der Finanzverwaltung (z. B. Feststellung/Veranlagung/Freistellung) verlagert sich der Begruendungspfad weg von alternativen gemeinnuetzigen Zwecken (z. B. Jugendhilfe/Bildung/Kultur) hin zur unmittelbaren Sportfoerderung; dadurch entfaellt in betroffenen Faellen der zusaetzliche Begruendungs- und Abgrenzungsaufwand ueber andere Zwecke und es kann interner Aufwand zur Umstellung der Standardtexte/Argumentation/Unterlagen anfallen.",
      "aenderungsstatus": "geaendert",
      "vorgaben": [
        {
          "vorgaben_id": 11,
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO",
          "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).",
          "aenderungsstatus": "geaendert"
        },
        {
          "vorgaben_id": 12,
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)",
          "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.",
          "aenderungsstatus": "geaendert"
        }
      ],
      "fallgruppen": [
        {
          "fallgruppen_id": 25,
          "fallgruppe_bezeichnung": "Neuantrag/Erstanerkennung Gemeinnuetzigkeit fuer E-Sport-Koerperschaft unter Zweck 'Foerderung des Sports' (statt alternativer Zwecke)",
          "fallgruppe_beschreibung": "E-Sport-Koerperschaften, die erstmals die Gemeinnuetzigkeit/Steuerbeguenstigung beantragen, koennen den Antrag und die Begruendung unmittelbar auf 'Foerderung des Sports' stuetzen. Im Vergleich zur bisherigen (unsicheren) Praxis entfaellt typischerweise zusaetzlicher Begruendungs- und Abgrenzungsaufwand, der zuvor fuer die Herleitung ueber alternative gemeinnuetzige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) sowie fuer entsprechende Satzungs- und Konzeptbegruendungen angefallen waere. Ggf. verbleibt ein einmaliger interner Aufwand zur Erstellung/Anpassung von Standardtexten, Satzungsbausteinen und Nachweisunterlagen auf den Sportzweck mit E-Sport-Bezug.",
          "aenderungsstatus": "geaendert",
          "taetigkeiten": [
            {
              "taetigkeit": "Begruendungs- und Nachweiskonzept von alternativen Zwecken auf 'Foerderung des Sports (inkl. E-Sport)' umstellen",
              "beschreibung": "Im Neuantrag wird die Argumentationslinie/Begruendung so angepasst, dass E-Sport unmittelbar als Sportfoerderung dargestellt wird (statt Herleitung ueber Jugendhilfe/Bildung/Kultur). Dazu werden die beizufuegenden Kurzkonzepte, Taetigkeitsdarstellungen und Textbausteine entsprechend neu ausgerichtet.",
              "aenderungsstatus": "geaendert",
              "vorgaben_ids": [
                11,
                12
              ]
            },
            {
              "taetigkeit": "Zusaetzlichen Abgrenzungs- und Darlegungsaufwand ueber alternative gemeinnuetzige Zwecke entfallen lassen",
              "beschreibung": "Soweit bisher (aus Rechtsunsicherheit) zusaetzliche Darlegungen/Abgrenzungen zu alternativen Zwecken erforderlich waren (z. B. gesonderte Bildungs-/Jugendhilfe-Begruendung, Doppelbegruendung, Plausibilisierung eines Alternativzwecks), wird dieser Begruendungspfad im Antrag nicht mehr erstellt bzw. nicht mehr in gleicher Tiefe ausgearbeitet.",
              "aenderungsstatus": "abgeschafft",
              "vorgaben_ids": [
                12
              ]
            },
            {
              "taetigkeit": "Satzungszweck/-bausteine und Anlagen fuer den Antrag auf Sportzweck mit E-Sport-Bezug zuschneiden",
              "beschreibung": "Erstellung/Anpassung von Satzungsformulierungen (Zweck/Verwirklichung) bzw. der einzureichenden Anlagen (z. B. Musterformulierungen, Taetigkeitsbeschreibungen) so, dass die Foerderung des Sports durch E-Sport inhaltlich konsistent dargestellt wird; dies umfasst auch interne Abstimmung und Finalisierung der Unterlagen.",
              "aenderungsstatus": "geaendert",
              "vorgaben_ids": [
                11
              ]
            },
            {
              "taetigkeit": "Antragsunterlagen finalisieren und einreichen (inkl. Dokumentation/Ablage der geaenderten Begruendung)",
              "beschreibung": "Zusammenstellung der finalen Unterlagen und Einreichung in der ueblichen Form; die Taetigkeit bleibt als Standardvorgang bestehen, wird aber inhaltlich durch die geaenderte Rechtsgrundlage (Sport inkl. E-Sport) mitangepasst (Versionierung/Ablage der neuen Textstaende).",
              "aenderungsstatus": "geaendert",
              "vorgaben_ids": [
                11,
                12
              ]
            }
          ]
        },
        {
          "fallgruppen_id": 26,
          "fallgruppe_bezeichnung": "Bestandskoerperschaft: Umstellung/Anpassung Satzung, Zweckformulierung und Nachweisfuehrung auf 'Sport (inkl. E-Sport)'",
          "fallgruppe_beschreibung": "Bereits bestehende E-Sport-Koerperschaften mit laufender Gemeinnuetzigkeitsfuehrung (z. B. gueltiger Freistellungsbescheid bzw. turnusmaessige Nachweis- und Erklaerungsprozesse), die bisher (aus Rechtsunsicherheit) teilweise ueber alternative Zwecke argumentiert oder Mischbegruendungen genutzt haben, stellen ihre Standardargumentation, Unterlagen und ggf. die Satzungszweckbeschreibung auf 'Foerderung des Sports' um. Dies kann einen einmaligen internen Abstimmungs- und Dokumentationsaufwand (inkl. ggf. externer Beratung/Steuerberatung) ausloesen; zugleich reduziert sich kuenftig der wiederkehrende Begruendungs- und Abgrenzungsaufwand, weil der zusaetzliche alternative Begruendungspfad entfaellt.",
          "aenderungsstatus": "geaendert",
          "taetigkeiten": [
            {
              "taetigkeit": "Interne Analyse/Entscheidung zur Umstellung der Gemeinnuetzigkeitsbegruendung auf 'Sport (inkl. E-Sport)'",
              "beschreibung": "Pruefung der bisherigen Begruendung (Alternativzwecke/Mischbegruendung) und Festlegung, kuenftig vorrangig/allein auf Nr. 21 (Sport inkl. E-Sport) abzustellen; inkl. Abstimmung im Vorstand/Management und Festlegung der notwendigen Anpassungen an Dokumentenstandards.",
              "aenderungsstatus": "eingefuehrt",
              "vorgaben_ids": [
                11,
                12
              ]
            },
            {
              "taetigkeit": "Satzung und Standardunterlagen (Textbausteine, Taetigkeitsdarstellung, Nachweislogik) anpassen und versionieren",
              "beschreibung": "Einmalige Ueberarbeitung von Satzungszweck/Verwirklichung (soweit erforderlich) sowie der wiederverwendeten Begruendungstexte und Nachweisunterlagen, sodass die Sportfoerderung durch E-Sport konsistent und rechtssicher dargestellt ist; inkl. Dokumentation/Ablage der geaenderten Versionen.",
              "aenderungsstatus": "geaendert",
              "vorgaben_ids": [
                11
              ]
            },
            {
              "taetigkeit": "Wiederkehrenden zusaetzlichen Begruendungs- und Abgrenzungsteil ueber Alternativzwecke kuerzen/streichen",
              "beschreibung": "In der laufenden Nachweisfuehrung gegenueber der Finanzverwaltung (z. B. im Rahmen turnusmaessiger Unterlagenzusammenstellung) entfaellt bzw. reduziert sich der bisherige Zusatzaufwand, der allein daraus resultierte, E-Sport ueber andere Zwecke mit zu begruenden oder abzugrenzen.",
              "aenderungsstatus": "abgeschafft",
              "vorgaben_ids": [
                12
              ]
            },
            {
              "taetigkeit": "Ggf. externe Unterstuetzung (z. B. Steuerberatung) fuer Umstellung/Pruefung der Unterlagen einholen",
              "beschreibung": "Soweit ueblich oder risikoorientiert veranlasst: Einholung/Verwertung externer Beratung zur Anpassung der Satzung/Begruendung und zur Minimierung von Anerkennungsrisiken; diese Taetigkeit entsteht typischerweise einmalig im Zuge der Umstellung.",
              "aenderungsstatus": "eingefuehrt",
              "vorgaben_ids": [
                11,
                12
              ]
            }
          ]
        },
        {
          "fallgruppen_id": 27,
          "fallgruppe_bezeichnung": "Bestandskoerperschaft: Keine materielle Umstellung erforderlich (E-Sport bereits als Sport behandelt/abgebildet)",
          "fallgruppe_beschreibung": "E-Sport-Koerperschaften, die bereits vor der Klarstellung ihre Gemeinnuetzigkeit unter 'Foerderung des Sports' (oder in der praktischen Umsetzung gleichwertig) begruendet und dokumentiert haben, muessen keine oder nur minimale Anpassungen vornehmen (z. B. Aktualisierung von Textbausteinen/Verweisen). Der wesentliche Effekt liegt in reduzierter Rechtsunsicherheit ohne nennenswerten zusaetzlichen internen Zeit- oder Sachaufwand.",
          "aenderungsstatus": "geaendert",
          "taetigkeiten": [
            {
              "taetigkeit": "Minimale Aktualisierung von Standardtexten/Verweisen auf die Klarstellung 'E-Sport gilt als Sport'",
              "beschreibung": "Soweit genutzt: kurze Anpassung bestehender Textbausteine (z. B. in Anschreiben, Begruendungspapieren, internen FAQs) bzw. Ergaenzung eines Verweises auf die explizite Einordnung von E-Sport als Sport; ohne inhaltliche Umstellung der uebrigen Nachweisfuehrung.",
              "aenderungsstatus": "geaendert",
              "vorgaben_ids": [
                11
              ]
            },
            {
              "taetigkeit": "Zusaetzliche Vorsorge-/Alternativbegruendungen (Backup-Zwecke) nicht mehr vorhalten",
              "beschreibung": "Soweit bislang aus Vorsicht parallel Alternativzwecke oder Ersatzargumentationen dokumentiert/mitgefuehrt wurden, koennen diese kuenftig entfallen (z. B. keine fortlaufende Pflege von Doppelbegruendungen).",
              "aenderungsstatus": "abgeschafft",
              "vorgaben_ids": [
                12
              ]
            },
            {
              "taetigkeit": "Laufende Nachweisfuehrung unter Sportzweck fortsetzen (nur geringfuegig beruehrt)",
              "beschreibung": "Die regulaeren, ohnehin bestehenden Schritte zur Nachweisfuehrung/Unterlagenbereitstellung bleiben im Kern gleich; sie werden lediglich um die rechtssichere Einordnung ergaenzt, ohne dass ein zusaetzlicher Aufwand entsteht.",
              "aenderungsstatus": "unveraendert",
              "vorgaben_ids": [
                11,
                12
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

---

## Step 9 — `cases_calculation` (success)
- model: `gpt-5.2` | provider: `openai` | attempt: `a8d40c083d444508aeb374d8a80e800f` | elapsed: 15955 ms
- tokens: in=9291 out=1277 hidden_thinking=0 | cost: $0.034137

### Prompt

```

    Sie sind Legist im deutschen Bundestag und damit betraut, die 
    Erfüllungsaufwandsänderung zu einer geplanten Gesetzesänderung zu berechnen.

    Insbesondere werden zur Ermittlung der zu erwartenden Änderung des Aufwands 
    pro Fall die wesentlichen Tätigkeiten identifiziert, die zur Erfüllung 
    einer Vorgabe oder eines Prozesses im Einzelfall zu erwarten sind. Diese 
    schließen Tätigkeiten ein, welche neu hinzukommen, welche sich ändern und 
    welche wegfallen. Für diese Tätigkeiten werden die zu erwartenden Änderungen des 
    Zeit-, Personal- sowie Sachaufwands ermittelt.

    Die wesentlichen Unterschiede der Gesetzesänderung sind wie folgt 
    zusammengefasst: Aus dem Vergleich ergibt sich nur eine einzige materielle Änderung: In § 52 Abs. 2 Nr. 21 AO wird der Klammerzusatz von „Schach gilt als Sport“ zu „Schach gilt als Sport und E‑Sport gilt für diese Regelung als Sport“ erweitert. Alle übrigen Tatbestandsvoraussetzungen in Absatz 1 (Allgemeinheitsförderung, Abgrenzung zu geschlossenen Personenkreisen etc.) sowie der restliche Katalog gemeinnütziger Zwecke in Absatz 2 und die Öffnungsklausel am Ende bleiben wortgleich.

Ziel des Gesetzgebers ist damit erkennbar eine Klarstellung und Erweiterung des gemeinnützigen Zweckkatalogs zugunsten des E‑Sports: Körperschaften (z.B. Vereine, Stiftungen, gGmbHs), deren Satzungszweck und tatsächliche Geschäftsführung auf die Förderung von E‑Sport gerichtet ist, sollen unter dem bereits anerkannten Zweck „Förderung des Sports“ leichter und rechtssicher als gemeinnützig anerkannt werden. Praktisch bedeutet dies eine Reduzierung von Rechtsunsicherheit und uneinheitlicher Verwaltungspraxis, weil E‑Sport nicht mehr (nur) über andere Zwecke (z.B. Jugendhilfe, Bildung, Kultur, digitale Kompetenzen) „mitbegründet“ werden müsste, sondern unmittelbar als Sportförderung gemeinnützig sein kann.

Wesentliche Unterschiede/Wirkungen der Änderung:
- Erweiterter Anwendungsbereich von Nr. 21: Sportvereine im Sinne der Gemeinnützigkeit sollen ausdrücklich auch E‑Sport-Vereine umfassen.
- Rechtsfolgeebene (implizit): E‑Sport‑Organisationen können damit eher Zugang zu typischen Gemeinnützigkeitsfolgen erhalten (insbesondere steuerliche Begünstigungen, Spendenabzugsfähigkeit für Zuwendungen an die Körperschaft, erleichterte Mittelakquise), soweit sie die allgemeinen Gemeinnützigkeitsanforderungen (Selbstlosigkeit, Ausschließlichkeit, Unmittelbarkeit, tatsächliche Geschäftsführung, kein geschlossener Begünstigtenkreis) erfüllen.
- Keine Ausweitung anderer Zwecke/keine Änderung der Grunddefinition: Die Änderung schafft keinen neuen eigenständigen Zweck außerhalb des Sportbegriffs, sondern ordnet E‑Sport ausdrücklich dem bestehenden Zweck „Sport“ zu und lässt die übrige Systematik des § 52 AO unverändert.

    
        Die Gesetzesänderung führt zu folgenden, Erfüllungsaufwand auslösenden Prozessen für den betroffenen Normadressaten, welche durch folgende Fallgruppen 
        differenziert werden: [{"prozess_id": 13, "prozess_bezeichnung": "Pruefung und Bescheidung der Gemeinnuetzigkeit bei E-Sport-Foerderung als Sport (Anerkennungs-/Freistellungsverfahren)", "prozess_beschreibung": "Bearbeitung von Verfahren, in denen Koerperschaften ihre Gemeinnuetzigkeit/Steuerbeguenzigung (z. B. im Rahmen von Feststellungs-, Veranlagungs- und Freistellungsverfahren) geltend machen und die Finanzbehoerde die Einordnung des Satzungszwecks und der tatsaechlichen Geschaeftsfuehrung unter den gemeinnuetzigkeitsrechtlichen Zweck \"Foerderung des Sports\" nun ausdruecklich einschliesslich E-Sport prueft. Hierzu gehoeren die Anpassung bzw. Anwendung der pruefungsleitenden Arbeitsschritte und Begruendungstexte (Einordnung E-Sport als Sport), die Wuerdigung der unveraenderten allgemeinen Gemeinnuetzigkeitsvoraussetzungen sowie die Bescheidung/kommunikative Rueckfragen im Einzelfall. Der Prozess bildet zugleich die Spiegelsituation ab: Die Verwaltungshandlung wird typischerweise durch das Begehren der Koerperschaft ausgeloest, ist aber als eigener Vollzugsvorgang der Finanzverwaltung auszuweisen.", "aenderungsstatus": "geaendert", "vorgaben": [{"vorgaben_id": 11, "normzitat": "§ 52 Abs. 2 Nr. 21 AO", "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}}, {"vorgaben_id": 12, "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)", "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}}], "fallgruppen": [{"fallgruppen_id": 23, "fallgruppe_bezeichnung": "Standardfall: Einordnung E-Sport als Sport ohne besondere Rueckfragen (Erst- oder laufendes Verfahren)", "fallgruppe_beschreibung": "Die Koerperschaft beantragt bzw. macht die Steuerbeguenstigung geltend und legt eine Satzung/Taetigkeitsdarstellung vor, bei der E-Sport-Foerderung klar erkennbar ist und die uebrigen Gemeinnuetzigkeitsvoraussetzungen nach Aktenlage unproblematisch erfuellt sind. Die Finanzbehoerde ordnet den Zweck im Pruefschritt nun unmittelbar unter \"Foerderung des Sports\" (inkl. E-Sport) ein und verwendet standardisierte Begruendungstexte/Arbeitshinweise; der bisher in Teilen erforderliche Umweg ueber alternative Zwecke entfaellt. Der Aufwand pro Fall aendert sich durch verkuerzte/pragmatisierte Begruendung und weniger Abgrenzungspruefung.", "aenderungsstatus": "geaendert", "spiegelsituationen": [{"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}, {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}]}, {"fallgruppen_id": 24, "fallgruppe_bezeichnung": "Sonderfall: Abgrenzungs-/Vertiefungspruefung trotz Klarstellung (Rueckfragen/Anhoerung)", "fallgruppe_beschreibung": "Faelle mit E-Sport-Bezug, in denen trotz Einordnungsmöglichkeit als Sport besonderer Klaerungsbedarf besteht (z. B. unklare Ausgestaltung der tatsaechlichen Geschaeftsfuehrung, Mischzwecke, kommerzielle Naehe, geschlossener Teilnehmerkreis, Mittelverwendung, Verguetungen, Veranstaltungs-/Ligaformate). Die Finanzbehoerde fuehrt vertiefte Pruefung durch (Rueckfragen, Anforderung weiterer Unterlagen, ggf. Anhoerung) und bescheidet erst nach Wuerdigung; gegenueber der Vorlage kann sich der Abgrenzungspruefpfad zwar in Richtung Nr. 21 verschieben, der Aufwand bleibt aber durch Einzelfallpruefung wesentlich hoeher als im Standardfall.", "aenderungsstatus": "geaendert", "spiegelsituationen": [{"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}, {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}]}]}]
        

        Ihre Aufgabe ist es, die Änderung der Fallzahlen jeder dieser Fallgruppen zu bestimmen. Hierzu werden die Häufigkeit und die Anzahl der Betroffenen 
        vor (_gueltig) und nach (_vorschlag) der geplanten Gesetzesänderung betrachtet. Bei der Einführung einer Fallgruppe werden typischerweise nur die 
        _vorschlag-Werte angegeben, bei der Löschung nur die _gueltig-Werte und bei einer Änderung beide.

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

        Bei Spiegelsituationen gilt: Wenn aus einem anderen Normadressaten bereits spiegelnde Fallzahlen vorliegen und der zugrunde liegende Sachverhalt
        logisch 1:1 gekoppelt ist, sind dieselben Mengen zu übernehmen statt sie erneut unabhängig zu schätzen. Beispiel: Wenn 500 neue Vereine gegründet
        werden und deshalb 500 Anträge bei der Verwaltung zu bearbeiten sind, muss dieselbe Fallzahl auf beiden Seiten zugrunde gelegt werden; unterschiedlich
        sind dann nur die Tätigkeiten und Kosten, nicht die Zahl der Fälle.

        Wenn strukturierte Spiegel-Matches mit `sync_cases = 1`, `sync_addressees = 1` oder `sync_frequency = 1` vorliegen, befolgen Sie diese Vorgaben
        vorrangig. Solche Matches sind als autoritative Synchronisierungshinweise zu behandeln und nicht erneut frei zu ueberschreiben.

        Offizielles Methodenbeispiel aus dem Leitfaden (woertlich uebernommen):
        → Beispiele für jährliche Häufigkeit bei periodisch zu erfüllenden Vorgaben:
Vorgabe ist periodisch zu erfüllen
- einmal jährlich: Häufigkeit = 1
- halbjährlich: Häufigkeit = 2
- monatlich: Häufigkeit = 12
- alle 5 Jahre: Häufigkeit = 0,2

        Offizielles Fallzahlbeispiel aus dem Leitfaden (woertlich uebernommen):
        

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
        
        {
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
                    "anzahl_betroffene_gueltig": "",
                    "haeufigkeit_pro_jahr_gueltig": "",
                    "anzahl_betroffene_vorschlag": "",
                    "haeufigkeit_pro_jahr_vorschlag": ""
                },
                {
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "",
                    "anzahl_betroffene_gueltig": "",
                    "haeufigkeit_pro_jahr_gueltig": "",
                    "anzahl_betroffene_vorschlag": "",
                    "haeufigkeit_pro_jahr_vorschlag": ""
                }
            ]
            },
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
                },
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
                    "anzahl_betroffene_gueltig": "",
                    "haeufigkeit_pro_jahr_gueltig": "",
                    "anzahl_betroffene_vorschlag": "",
                    "haeufigkeit_pro_jahr_vorschlag": ""
                }
            ]
            }
        ]
        }
        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 
        

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
        Fallgruppen, Taetigkeiten, Fallzahlen oder Werte, sofern diese nicht
        ausdruecklich als Spiegelwirkung der Verwaltung zuzurechnen sind. Vermeiden
        Sie zugleich, aus Vorsicht ganze Vollzugsstraenge wegzulassen: wenn eine
        Regelung die Verwaltung zur Pruefung, Bescheidung oder Aufsicht verpflichtet,
        ist dieser Vollzugsaufwand auszuweisen, auch wenn er aus einem wirtschafts-
        oder buergerseitigen Antrag ausgeloest wird.

Zusatz fuer die Verwaltung bei der Fallzahlermittlung: Fuer die Verwaltung ist die `Anzahl Betroffene` NICHT die Zahl extern betroffener Buerger oder Unternehmen, sondern die Zahl der jaehrlich tatsaechlich von der Verwaltung zu bearbeitenden Vorgaenge, Faelle oder Antraege derselben Fallgruppe. Die `Haeufigkeit pro Jahr` ist in der Regel 1, es sei denn ein Vorgang wiederholt sich nachweislich mehrfach pro Jahr pro Fall (z.B. periodische Kontrollen). Setzen Sie niemals `anzahl_betroffene = 0`, wenn es eine zugeordnete Fallgruppe mit Bearbeitungsaufwand gibt - ohne Faelle waere die Fallgruppe nicht zu bilden. Wenn eine Spiegelsituation zu Wirtschaft oder Buergerinnen/Buergern besteht (z.B. 500 Antraege werden gestellt und von der Verwaltung bearbeitet), uebernehmen Sie dieselbe Fallzahl deterministisch; die Anzahl der Antragsteller und die Anzahl der zu bearbeitenden Vorgaenge sind dann identisch. Liegen keine konkreten Zahlen vor, schaetzen Sie sachgerecht basierend auf dem Normzitat/Regelungsgegenstand und typischen Vollzugsmengen der zustaendigen Behoerde; geben Sie niemals Platzhalter-Nullen aus.
```

### Raw Response

```
{
  "prozesse": [
    {
      "prozess_id": 13,
      "prozess_bezeichnung": "Pruefung und Bescheidung der Gemeinnuetzigkeit bei E-Sport-Foerderung als Sport (Anerkennungs-/Freistellungsverfahren)",
      "prozess_beschreibung": "Bearbeitung von Verfahren, in denen Koerperschaften ihre Gemeinnuetzigkeit/Steuerbeguenzigung (z. B. im Rahmen von Feststellungs-, Veranlagungs- und Freistellungsverfahren) geltend machen und die Finanzbehoerde die Einordnung des Satzungszwecks und der tatsaechlichen Geschaeftsfuehrung unter den gemeinnuetzigkeitsrechtlichen Zweck \"Foerderung des Sports\" nun ausdruecklich einschliesslich E-Sport prueft. Hierzu gehoeren die Anpassung bzw. Anwendung der pruefungsleitenden Arbeitsschritte und Begruendungstexte (Einordnung E-Sport als Sport), die Wuerdigung der unveraenderten allgemeinen Gemeinnuetzigkeitsvoraussetzungen sowie die Bescheidung/kommunikative Rueckfragen im Einzelfall. Der Prozess bildet zugleich die Spiegelsituation ab: Die Verwaltungshandlung wird typischerweise durch das Begehren der Koerperschaft ausgeloest, ist aber als eigener Vollzugsvorgang der Finanzverwaltung auszuweisen.",
      "aenderungsstatus": "geaendert",
      "vorgaben": [
        {
          "vorgaben_id": 11,
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO",
          "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).",
          "aenderungsstatus": "geaendert"
        },
        {
          "vorgaben_id": 12,
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)",
          "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.",
          "aenderungsstatus": "geaendert"
        }
      ],
      "fallgruppen": [
        {
          "fallgruppen_id": 23,
          "fallgruppe_bezeichnung": "Standardfall: Einordnung E-Sport als Sport ohne besondere Rueckfragen (Erst- oder laufendes Verfahren)",
          "fallgruppe_beschreibung": "Vor der Klarstellung wurden nur solche Verfahren als \"Sport\"-Fall dieser Art gefuehrt, in denen E-Sport bereits ausnahmsweise als Sport akzeptiert bzw. ohne Streit durchgewunken wurde; ein erheblicher Teil der E-Sport-bezogenen Gemeinnuetzigkeitsverfahren lief dagegen entweder unter alternativen Zweckbegruendungen oder wurde gar nicht erst als Antrag initiiert (Rechtsunsicherheit). Nach der Gesetzesaenderung ist mit einem Nachfrageeffekt zu rechnen (mehr Antraege/mehr Umstellungen bestehender Koerperschaften auf den Zweck \"Sport\"), zugleich verschiebt sich ein Teil der bislang streitigen/abgrenzungsintensiven Faelle in den Standardpfad, weil der Zweck \"E-Sport als Sport\" nun unmittelbar tragfaehig begruendet werden kann.",
          "aenderungsstatus": "geaendert",
          "anzahl_betroffene_gueltig": 600,
          "haeufigkeit_pro_jahr_gueltig": 1,
          "anzahl_betroffene_vorschlag": 1200,
          "haeufigkeit_pro_jahr_vorschlag": 1
        },
        {
          "fallgruppen_id": 24,
          "fallgruppe_bezeichnung": "Sonderfall: Abgrenzungs-/Vertiefungspruefung trotz Klarstellung (Rueckfragen/Anhoerung)",
          "fallgruppe_beschreibung": "Vor der Klarstellung fuehrten E-Sport-Bezuege haeufig zu vertiefter Pruefung (insb. Abgrenzung zu kommerziellen Strukturen, Mischzwecken, geschlossenen Teilnehmerkreisen), sodass ein substanzieller Anteil der einschlaegigen Verfahren in diese Sonderfallgruppe fiel. Nach der Gesetzesaenderung reduziert sich dieser Anteil, weil der zentrale Streitpunkt (Einordnung als Sport) entfaellt und damit weniger Rueckfragen/Anhoerungen allein zur Zweckqualifikation erforderlich sind; gleichwohl verbleiben vertiefte Pruefungen in Einzelfaellen (tatsaechliche Geschaeftsfuehrung, Mittelverwendung etc.). Insgesamt wird daher mit leicht sinkender Fallzahl in der Sonderfallgruppe gerechnet, trotz insgesamt steigender Gesamtverfahren, weil Faelle in den Standardpfad wechseln.",
          "aenderungsstatus": "geaendert",
          "anzahl_betroffene_gueltig": 400,
          "haeufigkeit_pro_jahr_gueltig": 1,
          "anzahl_betroffene_vorschlag": 300,
          "haeufigkeit_pro_jahr_vorschlag": 1
        }
      ]
    }
  ]
}
```

---

## Step 10 — `effort_calculation` (success)
- model: `gpt-5.2` | provider: `openai` | attempt: `440b8423b6334783a40d187fe4c7bb1a` | elapsed: 37032 ms
- tokens: in=11929 out=3979 hidden_thinking=0 | cost: $0.076582

### Prompt

```

    Sie sind Legist im deutschen Bundestag und damit betraut, die 
    Erfüllungsaufwandsänderung zu einer geplanten Gesetzesänderung zu berechnen.

    Insbesondere werden zur Ermittlung der zu erwartenden Änderung des Aufwands 
    pro Fall die wesentlichen Tätigkeiten identifiziert, die zur Erfüllung 
    einer Vorgabe oder eines Prozesses im Einzelfall zu erwarten sind. Diese 
    schließen Tätigkeiten ein, welche neu hinzukommen, welche sich ändern und 
    welche wegfallen. Für diese Tätigkeiten werden die zu erwartenden Änderungen des 
    Zeit-, Personal- sowie Sachaufwands ermittelt.

    Die wesentlichen Unterschiede der Gesetzesänderung sind wie folgt 
    zusammengefasst: Aus dem Vergleich ergibt sich nur eine einzige materielle Änderung: In § 52 Abs. 2 Nr. 21 AO wird der Klammerzusatz von „Schach gilt als Sport“ zu „Schach gilt als Sport und E‑Sport gilt für diese Regelung als Sport“ erweitert. Alle übrigen Tatbestandsvoraussetzungen in Absatz 1 (Allgemeinheitsförderung, Abgrenzung zu geschlossenen Personenkreisen etc.) sowie der restliche Katalog gemeinnütziger Zwecke in Absatz 2 und die Öffnungsklausel am Ende bleiben wortgleich.

Ziel des Gesetzgebers ist damit erkennbar eine Klarstellung und Erweiterung des gemeinnützigen Zweckkatalogs zugunsten des E‑Sports: Körperschaften (z.B. Vereine, Stiftungen, gGmbHs), deren Satzungszweck und tatsächliche Geschäftsführung auf die Förderung von E‑Sport gerichtet ist, sollen unter dem bereits anerkannten Zweck „Förderung des Sports“ leichter und rechtssicher als gemeinnützig anerkannt werden. Praktisch bedeutet dies eine Reduzierung von Rechtsunsicherheit und uneinheitlicher Verwaltungspraxis, weil E‑Sport nicht mehr (nur) über andere Zwecke (z.B. Jugendhilfe, Bildung, Kultur, digitale Kompetenzen) „mitbegründet“ werden müsste, sondern unmittelbar als Sportförderung gemeinnützig sein kann.

Wesentliche Unterschiede/Wirkungen der Änderung:
- Erweiterter Anwendungsbereich von Nr. 21: Sportvereine im Sinne der Gemeinnützigkeit sollen ausdrücklich auch E‑Sport-Vereine umfassen.
- Rechtsfolgeebene (implizit): E‑Sport‑Organisationen können damit eher Zugang zu typischen Gemeinnützigkeitsfolgen erhalten (insbesondere steuerliche Begünstigungen, Spendenabzugsfähigkeit für Zuwendungen an die Körperschaft, erleichterte Mittelakquise), soweit sie die allgemeinen Gemeinnützigkeitsanforderungen (Selbstlosigkeit, Ausschließlichkeit, Unmittelbarkeit, tatsächliche Geschäftsführung, kein geschlossener Begünstigtenkreis) erfüllen.
- Keine Ausweitung anderer Zwecke/keine Änderung der Grunddefinition: Die Änderung schafft keinen neuen eigenständigen Zweck außerhalb des Sportbegriffs, sondern ordnet E‑Sport ausdrücklich dem bestehenden Zweck „Sport“ zu und lässt die übrige Systematik des § 52 AO unverändert.

    
        Die Gesetzesänderung führt zu folgenden, Erfüllungsaufwand auslösenden Prozessen für den betroffenen Normadressaten, welche durch folgende Fallgruppen und 
        Prozessschritte differenziert werden: [{"prozess_id": 13, "prozess_bezeichnung": "Pruefung und Bescheidung der Gemeinnuetzigkeit bei E-Sport-Foerderung als Sport (Anerkennungs-/Freistellungsverfahren)", "prozess_beschreibung": "Bearbeitung von Verfahren, in denen Koerperschaften ihre Gemeinnuetzigkeit/Steuerbeguenzigung (z. B. im Rahmen von Feststellungs-, Veranlagungs- und Freistellungsverfahren) geltend machen und die Finanzbehoerde die Einordnung des Satzungszwecks und der tatsaechlichen Geschaeftsfuehrung unter den gemeinnuetzigkeitsrechtlichen Zweck \"Foerderung des Sports\" nun ausdruecklich einschliesslich E-Sport prueft. Hierzu gehoeren die Anpassung bzw. Anwendung der pruefungsleitenden Arbeitsschritte und Begruendungstexte (Einordnung E-Sport als Sport), die Wuerdigung der unveraenderten allgemeinen Gemeinnuetzigkeitsvoraussetzungen sowie die Bescheidung/kommunikative Rueckfragen im Einzelfall. Der Prozess bildet zugleich die Spiegelsituation ab: Die Verwaltungshandlung wird typischerweise durch das Begehren der Koerperschaft ausgeloest, ist aber als eigener Vollzugsvorgang der Finanzverwaltung auszuweisen.", "aenderungsstatus": "geaendert", "vorgaben": [{"vorgaben_id": 11, "normzitat": "§ 52 Abs. 2 Nr. 21 AO", "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}}, {"vorgaben_id": 12, "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)", "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}}], "fallgruppen": [{"fallgruppen_id": 23, "fallgruppe_bezeichnung": "Standardfall: Einordnung E-Sport als Sport ohne besondere Rueckfragen (Erst- oder laufendes Verfahren)", "fallgruppe_beschreibung": "Die Koerperschaft beantragt bzw. macht die Steuerbeguenstigung geltend und legt eine Satzung/Taetigkeitsdarstellung vor, bei der E-Sport-Foerderung klar erkennbar ist und die uebrigen Gemeinnuetzigkeitsvoraussetzungen nach Aktenlage unproblematisch erfuellt sind. Die Finanzbehoerde ordnet den Zweck im Pruefschritt nun unmittelbar unter \"Foerderung des Sports\" (inkl. E-Sport) ein und verwendet standardisierte Begruendungstexte/Arbeitshinweise; der bisher in Teilen erforderliche Umweg ueber alternative Zwecke entfaellt. Der Aufwand pro Fall aendert sich durch verkuerzte/pragmatisierte Begruendung und weniger Abgrenzungspruefung.", "aenderungsstatus": "geaendert", "spiegelsituationen": [{"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}, {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}], "taetigkeiten": [{"taetigkeiten_id": 93, "taetigkeit": "Unterlagen sichten und Vollstaendigkeit pruefen (Satzung/Taetigkeitsdarstellung mit E-Sport-Bezug)", "beschreibung": "Sichtung der eingereichten Satzung, Anlagen und Taetigkeitsdarstellung; formelle Vollstaendigkeits- und Plausibilitaetspruefung. Gegenueber der Rechtslage aendert sich dieser Schritt im Kern nicht, wird aber i.d.R. mit kuerzerer Nacharbeitung zur Zweckzuordnung verbunden, weil E-Sport nicht mehr ueber alternative Zwecke 'mitbegruendet' werden muss.", "aenderungsstatus": "geaendert", "vorgaben_ids": [11, 12]}, {"taetigkeiten_id": 94, "taetigkeit": "Inhaltliche Zweckzuordnung: E-Sport als Sport nach Nr. 21 feststellen", "beschreibung": "Pruefung und Feststellung, dass der satzungsmaessige Zweck und die tatsaechliche Geschaeftsfuehrung (soweit aktenkundig) unter \"Foerderung des Sports\" fallen, wobei E-Sport nun ausdruecklich einbezogen ist. Der Aufwand sinkt gegenueber der bisherigen (uneinheitlichen) Einordnung, weil die rechtliche Subsumtion/Argumentation fuer die Sportqualifikation vereinfacht ist.", "aenderungsstatus": "geaendert", "vorgaben_ids": [11]}, {"taetigkeiten_id": 95, "taetigkeit": "Wegfall/Reduktion des alternativen Pruefpfads (Jugendhilfe/Bildung/Kultur etc.)", "beschreibung": "Bisher: zusaetzliche Prüfung, ob und wie E-Sport-Foerderung tragfaehig über andere gemeinnuetzige Zwecke zu begruenden ist (inkl. Abgrenzungspruefung, zusaetzliche Begruendungstexte). Kuenftig: entfaellt typischerweise im Standardfall, weil die Einordnung vorrangig als Sportfoerderung erfolgen kann.", "aenderungsstatus": "abgeschafft", "vorgaben_ids": [12]}, {"taetigkeiten_id": 96, "taetigkeit": "Bescheid/Entscheidungstext erstellen und Akte dokumentieren (Standardbausteine mit E-Sport-Bezug)", "beschreibung": "Erstellung/Anpassung des Bescheids (z. B. Feststellung/Freistellung) unter Verwendung angepasster Standardformulierungen zur Einordnung von E-Sport als Sport; kurze Dokumentation/Vermerk in der Akte. Gegenueber vorher geaendert durch kuerzere und standardisierte Begruendung sowie weniger Erlaeuterungsbedarf zur Zweckherleitung.", "aenderungsstatus": "geaendert", "vorgaben_ids": [11, 12]}]}, {"fallgruppen_id": 24, "fallgruppe_bezeichnung": "Sonderfall: Abgrenzungs-/Vertiefungspruefung trotz Klarstellung (Rueckfragen/Anhoerung)", "fallgruppe_beschreibung": "Faelle mit E-Sport-Bezug, in denen trotz Einordnungsmöglichkeit als Sport besonderer Klaerungsbedarf besteht (z. B. unklare Ausgestaltung der tatsaechlichen Geschaeftsfuehrung, Mischzwecke, kommerzielle Naehe, geschlossener Teilnehmerkreis, Mittelverwendung, Verguetungen, Veranstaltungs-/Ligaformate). Die Finanzbehoerde fuehrt vertiefte Pruefung durch (Rueckfragen, Anforderung weiterer Unterlagen, ggf. Anhoerung) und bescheidet erst nach Wuerdigung; gegenueber der Vorlage kann sich der Abgrenzungspruefpfad zwar in Richtung Nr. 21 verschieben, der Aufwand bleibt aber durch Einzelfallpruefung wesentlich hoeher als im Standardfall.", "aenderungsstatus": "geaendert", "spiegelsituationen": [{"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}, {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}], "taetigkeiten": [{"taetigkeiten_id": 97, "taetigkeit": "Unterlagen sichten, Sachverhalt strukturieren und Pruefschwerpunkte festlegen (E-Sport-Fall mit Besonderheiten)", "beschreibung": "Sichtung/Strukturierung der Unterlagen (Satzung, Ordnungen, Verträge/Kooperationen, Veranstaltungs-/Ligaformate, Mittelverwendung); Ableitung der Pruefschwerpunkte (z. B. Selbstlosigkeit, geschlossener Beguenstigtenkreis, kommerzielle Naehe). Gegenueber vorher geaendert, weil die Vorpruefung zur Sportqualifikation klarer ist und frueher in die materiellen Abgrenzungsfragen ueberleitet.", "aenderungsstatus": "geaendert", "vorgaben_ids": [11, 12]}, {"taetigkeiten_id": 98, "taetigkeit": "Rueckfragen/Anforderung weiterer Unterlagen und ggf. Anhoerung", "beschreibung": "Kommunikation mit der Koerperschaft zur Klaerung streitiger/unklarer Punkte (z. B. tatsaechliche Geschaeftsfuehrung, Mischzwecke, Teilnehmerkreis, Verguetungen, Sponsoring/kommerzieller Zuschnitt); ggf. Anhoerung und Nachforderung von Nachweisen. Grundsaetzlich unveraendert als Verfahrenshandlung; kann jedoch in einzelnen Faellen kuerzer ausfallen, soweit die Zweckherleitung nicht mehr ueber alternative Zwecke gefuehrt werden muss.", "aenderungsstatus": "geaendert", "vorgaben_ids": [12]}, {"taetigkeiten_id": 99, "taetigkeit": "Vertiefte inhaltliche Pruefung und Bewertung (inkl. Einordnung E-Sport als Sport + Gemeinnuetzigkeitskriterien)", "beschreibung": "Vertiefte rechtliche und tatsaechliche Wuerdigung: Einordnung des E-Sport-Bezugs unter Sportfoerderung nach Nr. 21 sowie (unveraendert) Pruefung der allgemeinen Gemeinnuetzigkeitsvoraussetzungen und Abgrenzungen (z. B. Ausschliesslichkeit, Unmittelbarkeit, Selbstlosigkeit, kein geschlossener Beguenstigtenkreis, Mittelverwendung). Gegenueber vorher geaendert durch Vereinfachung im Teilaspekt 'Sportqualifikation' und Wegfall des Zwangs, eine alternative Zweckkette als Hauptbegruendung aufzubauen.", "aenderungsstatus": "geaendert", "vorgaben_ids": [11, 12]}, {"taetigkeiten_id": 100, "taetigkeit": "Entscheidung treffen, Bescheid begruenden/erstellen und Dokumentation (inkl. Abweichungs- und Abgrenzungsbegruendung)", "beschreibung": "Erstellung des (ggf. ablehnenden/teilweise ablehnenden) Bescheids inkl. ausfuehrlicher Begruendung, Vermerken und Dokumentation der Abgrenzung. Gegenueber vorher geaendert, weil die Textbausteine zur Sportqualifikation angepasst/standardisierbar sind; der vertiefte Teil bleibt fallbedingt aufwendig.", "aenderungsstatus": "geaendert", "vorgaben_ids": [11, 12]}]}]}]

        Ihre Aufgabe ist es, den anfallenden Personal- und ggf. Sachaufwand der anfallenden Tätigkeiten pro Einzelfall zu identifizieren. 
        Hierzu werden die Stundenlöhne, Zeit- und Sachaufwände vor (_gueltig) und nach (_vorschlag) der geplanten Gesetzesänderung betrachtet. Bei der Einführung
        eines Prozessschrittes werden typischerweise nur die _vorschlag-Werte angegeben, bei der Löschung nur die _gueltig-Werte und bei einer Änderung beide.

        Entscheidend ist die Aenderung des Erfuellungsaufwands je Fall. Schaetzen Sie daher nicht den gesamten denkbaren Bearbeitungsaufwand eines Verfahrens
        neu, sondern den fuer die geltende und die vorgeschlagene Rechtslage jeweils relevanten Aufwand derselben Taetigkeit. Wenn sich nur ein Teilaspekt
        aendert, darf nicht automatisch der gesamte Schritt neu und vollumfaenglich angesetzt werden. Unveraenderte Aufwaende sollten in _gueltig und
        _vorschlag gleich bleiben; nur geaenderte Mehr- oder Minderaufwaende sind abweichend auszuweisen.

        Eine Reihe von Taetigkeiten laeuft bei Nutzung entsprechender Informationstechnologie automatisch ab. Aus automatisch ablaufenden Prozessen resultiert zunaechst kein Zeitaufwand. Sofern keine spezifischen Daten ueber den Zeitaufwand vorliegen, kann die Zeitwerttabelle Verwaltung herangezogen werden. Zudem kann die Tabelle zu Wegezeiten und -sachkosten genutzt werden, wenn persoenliche Termine bei anderen Stellen oder Behoerden erforderlich sind. Zur Ermittlung des Personalaufwands werden die Bearbeitungszeiten mit den laufbahnspezifischen Lohnsaetzen der Verwaltung verknuepft. Die festen Lohngruppen sind A=Einfacher und mittlerer Dienst, B=Gehobener Dienst, C=Hoeherer Dienst, D=Durchschnitt. Ordnen Sie jede benoetigte Bearbeitungsstufe genau einer dieser Gruppen zu. Eine einzige Lohngruppe ist der Regelfall; mehrere Lohngruppen sind nur bei klar getrennten Bearbeitungsstufen zulaessig, etwa Bearbeitung und anschliessende Freigabe. Vermeiden Sie schematische Mehrfachbefuellung. Wenn der zu erfuellende Prozess nicht in Einzeltätigkeiten zerlegt wurde, koennen gesicherte Erfahrungswerte in Personentagen oder Personenmonaten genutzt und anschliessend umgerechnet werden. Fuer die Beschaeftigten im oeffentlichen Dienst gelten bei einer 40-Stunden-Woche als Richtwerte 1 Personentag = 8 Stunden, 1 Personenmonat = 134 Stunden und 1 Personenjahr = 200 Arbeitstage.

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

        Anhang Verwaltung:

### Anhang 5: Wegezeiten und -sachkosten

Wegezeiten umfassen den Zeitaufwand des Normadressaten, um von seinem Wohnort bzw. Sitz zur zuständigen Behörde zu gelangen. Die Wegesachkosten beschreiben den Sachaufwand, um diesen Weg zurückzulegen und beinhalten beispielsweise Fahrkarten für den ÖPNV oder Kraftstoff für das eigene Fahrzeug.

Wegezeiten und Wegesachkosten werden bei der Ermittlung des Erfüllungsaufwands berücksichtigt, wenn die jeweilige Regelung ein persönliches Erscheinen in einer Behörde oder Stelle vorschreibt und keine Alternativen wie den Postweg oder Online-Verfahren erlaubt. Gleiches gilt, wenn Behördenvertreterinnen und -vertreter verpflichtet sind, beispielsweise im Rahmen von Gremiensitzungen persönlich andere Ämter oder Stellen aufzusuchen.

Die folgende Tabelle zeigt pauschale Wegezeiten und -sachkosten in Abhängigkeit der zuständigen Verwaltungsebene. Gibt es belastbare Anhaltspunkte dafür, dass der nach der Tabelle ermittelte Wert aller Wahrscheinlichkeit nach über- oder unterzeichnet ist, sollte der aus Fachsicht realistischere Wert für die Ermittlung genutzt werden.

*Wegezeiten und -sachkosten nach Verwaltungsebene*

| Verwaltungsebene | Wegezeiten (Min.) | Wegesachkosten (Euro) |
| --- | --- | --- |
| Gemeinde | 15 | 1,10 |
| Kreis | 22 | 3,10 |
| Regierungsbezirk/Land | 59 | 13,20 |
| Durchschnitt | 20 | 2,60 |


### Anhang 7: Zeitwerttabelle Verwaltung

Liegen noch keine vergleichbaren Daten für den Zeitaufwand einzelner Tätigkeiten vor, kann auf die sogenannte Zeitwerttabelle Verwaltung zurückgegriffen werden. Die Zeitwerttabelle weist für einen großen Teil der auf Seite 46 angegebenen Standardaktivitäten Minutenwerte aus. Die Standardaktivitäten sind nach dem Grad der Schwierigkeit in einfach, mittel und hoch gestaffelt.

Der nach der Zeitwerttabelle ermittelte Zeitwert (das heißt der Zeitaufwand für eine Tätigkeit) sollte immer anhand begründbarer Einschätzungen aus fachlicher Sicht überprüft werden. Gibt es belastbare Anhaltspunkte dafür, dass der nach der Tabelle ermittelte Wert aller Wahrscheinlichkeit nach zu hoch oder zu niedrig angesetzt ist, sollte der aus Fachsicht realistischere Wert für die Ermittlung genutzt werden.

*Zeitwerttabelle Verwaltung*

| Nr. | Standardaktivität | Einfache Komplexität (Min.) | Mittlere Komplexität (Min.) | Hohe Komplexität (Min.) | Erläuterung |
| --- | --- | --- | --- | --- | --- |
| 1 | Einarbeiten in die Vorgabe | 2 | 13 | 413 | Welcher Aufwand entsteht regelmäßig, um sich mit der gesetzlichen Verpflichtung vertraut zu machen? |
| 2 | Beraten, Vorgespräche führen | 3 | 30 | 460 (1 PT) | Welcher Aufwand fällt zur Beantwortung von Fragen durch Bürgerinnen und Bürger oder Unternehmen und der Klärung von Sachverhalten an? |
| 3 | Formelle Prüfung, Daten sichten | 5 | 30 | 110 | Welcher Aufwand entsteht durch Kontrolle auf Vollständigkeit und Richtigkeit von vorhandenen Informationen wie z. B. Nachweisen? |
| 4 | Eingang bestätigen oder Einholen fehlender Daten | 5 | 10 | 22 | Welcher Aufwand entsteht durch Eingangsbestätigungen oder die Nachforderung fehlender Daten? |
| 5 | Inhaltliche Prüfung, Daten erfassen | 8 | 60 | 480 (1 PT) | Welcher Aufwand fällt durch die Prüfung von Formularen, Belegen und Berechnungen sowie durch das elektronische Erfassen an? |
| 6 | Berechnungen durchführen | 9 | 120 | X[^7] | Welcher Aufwand fällt für Berechnungen, Bewertungen und Zählungen an? |
| 7 | Ergebnisse/Berechnungen überprüfen und ggf. korrigieren | 4 | 30 | 1 170 (3,7 PT) | Welcher Aufwand entsteht durch die Prüfung von Ergebnissen z. B. durch das Vieraugenprinzip oder Mitzeichnungen? |
| 8 | Interne Sitzungen | 2 | 60 | 2 120 (4,4 PT) | Welcher Aufwand entsteht durch notwendige interne Sitzungen? |
| 9 | Externe Sitzungen | 5 | 80 | 2 640 (5,5 PT) | Welcher Aufwand entsteht durch notwendige externe Sitzungen z. B. mit externen Sachverständigen oder anderen Behörden? |
| 10 | Daten übermitteln oder veröffentlichen | 1 | 10 | 60 | Welcher Aufwand fällt an, um Informationen zu veröffentlichen oder an andere öffentliche Stellen weiterzugeben? |
| 11 | Abschließende Informationen aufbereiten, Bescheid erstellen | 5 | 60 | 480 (1 PT) | Welcher Aufwand entsteht z. B. durch das Erstellen von Bescheiden oder Vermerken? |
| 12 | Zahlungen anweisen, annehmen oder überwachen | 1 | 5 | 18 | Welcher Aufwand fällt für Überweisungen oder die Prüfung von Zahlungsein- und -ausgängen an? |
| 13 | Korrektur bzw. weitere Informationen bei Rückfragen vorlegen | 30 | 60 | 120 | Welcher Aufwand entsteht durch Rückfragen nach Bescheiderhalt und ggf. Fehlerkorrekturen? |
| 14 | Kopieren, archivieren, verteilen | 2 | 10 | 20 | Welcher Aufwand entsteht durch Kopier- oder Archivierungstätigkeiten und das Verteilen von Informationen innerhalb der Behörde? |
| 15 | Fortbildungen und Schulungen | 1 | 3 | 2 640 (5,5 PT) | Welcher Aufwand entsteht dadurch, dass die Erfüllung einer Vorgabe eine Schulung voraussetzt? |
| 16 | Überwachungs- und Aufsichtsmaßnahmen | 8 | 156 | 25 000 (52,1 PT) | Welcher Aufwand fällt durch Begehungen in Betrieben oder Besuchen bei Bürgerinnen und Bürgern an? |
| 17 | Anpassen von internen Prozessen | 12 | 4 080 (8,5 PT) | 67 200 (140 PT) | Welcher Aufwand entsteht, wenn interne Prozesse verändert oder angepasst werden müssen? |

[^7]: Aufgrund methodischer Unterschiede wurde hier auf die Darstellung von „hoch“ verzichtet.

PT: Persontag(e)
Stand: Januar 2025; Quelle: StBA


### Anhang 8: Lohnkostentabelle Verwaltung

In Anlehnung an die Lohnkostentabelle für Informationspflichten der Wirtschaft nach dem Standardkosten-Modell wurde für die Verwaltung vom StBA eine eigene Tariflohntabelle entwickelt. Analog zum Bereich Wirtschaft werden die Standardlohnsätze der Verwaltung getrennt nach Hierarchieebene und Qualifikationsniveau in Euro ausgewiesen.

*Lohnkosten pro Stunde in Euro*

| Verwaltungsebene | Einfacher und mittlerer Dienst | Gehobener Dienst | Höherer Dienst | Durchschnitt |
| --- | --- | --- | --- | --- |
| Bund | 33,80 | 40,40 | 67,60 | 44,40 |
| Länder | 30,50 | 43,20 | 69,30 | 46,70 |
| Kommunen | 25,50 | 42,20 | 70,40 | 40,70 |
| Sozialversicherung | 30,30 | 46,30 | 73,20 | 48,10 |
| Durchschnitt Öffentliche Verwaltung, Verteidigung, Sozialversicherung | 27,30 | 42,90 | 69,30 | 44,40 |

Stand: 2025; Quelle: StBA

*Lohnkosten pro Mitarbeiterkapazität (MAK) in Euro*

| Verwaltungsebene | Einfacher und mittlerer Dienst | Gehobener Dienst | Höherer Dienst | Durchschnitt |
| --- | --- | --- | --- | --- |
| Bund | 54 080 | 64 640 | 108 160 | 71 040 |
| Länder | 48 800 | 69 120 | 110 880 | 74 720 |
| Kommunen | 40 800 | 67 520 | 112 640 | 65 120 |
| Sozialversicherung | 48 480 | 74 080 | 117 120 | 76 960 |
| Durchschnitt Öffentliche Verwaltung, Verteidigung, Sozialversicherung | 43 680 | 68 640 | 110 880 | 71 040 |

Stand: 2025; Quelle: StBA
1 MAK = 1 Personenjahr à 200 Arbeitstage mit je 8 Stunden


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
        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 
        

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
        Fallgruppen, Taetigkeiten, Fallzahlen oder Werte, sofern diese nicht
        ausdruecklich als Spiegelwirkung der Verwaltung zuzurechnen sind. Vermeiden
        Sie zugleich, aus Vorsicht ganze Vollzugsstraenge wegzulassen: wenn eine
        Regelung die Verwaltung zur Pruefung, Bescheidung oder Aufsicht verpflichtet,
        ist dieser Vollzugsaufwand auszuweisen, auch wenn er aus einem wirtschafts-
        oder buergerseitigen Antrag ausgeloest wird.
```

### Raw Response

```
{
  "prozesse": [
    {
      "prozess_id": "13",
      "prozess_bezeichnung": "Pruefung und Bescheidung der Gemeinnuetzigkeit bei E-Sport-Foerderung als Sport (Anerkennungs-/Freistellungsverfahren)",
      "prozess_beschreibung": "Bearbeitung von Verfahren, in denen Koerperschaften ihre Gemeinnuetzigkeit/Steuerbeguenzigung (z. B. im Rahmen von Feststellungs-, Veranlagungs- und Freistellungsverfahren) geltend machen und die Finanzbehoerde die Einordnung des Satzungszwecks und der tatsaechlichen Geschaeftsfuehrung unter den gemeinnuetzigkeitsrechtlichen Zweck \"Foerderung des Sports\" nun ausdruecklich einschliesslich E-Sport prueft. Hierzu gehoeren die Anpassung bzw. Anwendung der pruefungsleitenden Arbeitsschritte und Begruendungstexte (Einordnung E-Sport als Sport), die Wuerdigung der unveraenderten allgemeinen Gemeinnuetzigkeitsvoraussetzungen sowie die Bescheidung/kommunikative Rueckfragen im Einzelfall. Der Prozess bildet zugleich die Spiegelsituation ab: Die Verwaltungshandlung wird typischerweise durch das Begehren der Koerperschaft ausgeloest, ist aber als eigener Vollzugsvorgang der Finanzverwaltung auszuweisen.",
      "aenderungsstatus": "geaendert",
      "vorgaben": [
        {
          "vorgaben_id": "11",
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO",
          "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).",
          "aenderungsstatus": "geaendert"
        },
        {
          "vorgaben_id": "12",
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)",
          "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.",
          "aenderungsstatus": "geaendert"
        }
      ],
      "fallgruppen": [
        {
          "fallgruppen_id": "23",
          "fallgruppe_bezeichnung": "Standardfall: Einordnung E-Sport als Sport ohne besondere Rueckfragen (Erst- oder laufendes Verfahren)",
          "fallgruppe_beschreibung": "Die Koerperschaft beantragt bzw. macht die Steuerbeguenstigung geltend und legt eine Satzung/Taetigkeitsdarstellung vor, bei der E-Sport-Foerderung klar erkennbar ist und die uebrigen Gemeinnuetzigkeitsvoraussetzungen nach Aktenlage unproblematisch erfuellt sind. Die Finanzbehoerde ordnet den Zweck im Pruefschritt nun unmittelbar unter \"Foerderung des Sports\" (inkl. E-Sport) ein und verwendet standardisierte Begruendungstexte/Arbeitshinweise; der bisher in Teilen erforderliche Umweg ueber alternative Zwecke entfaellt. Der Aufwand pro Fall aendert sich durch verkuerzte/pragmatisierte Begruendung und weniger Abgrenzungspruefung.",
          "aenderungsstatus": "geaendert",
          "taetigkeiten": [
            {
              "taetigkeiten_id": "93",
              "taetigkeit": "Unterlagen sichten und Vollstaendigkeit pruefen (Satzung/Taetigkeitsdarstellung mit E-Sport-Bezug)",
              "beschreibung": "Sichtung der eingereichten Satzung, Anlagen und Taetigkeitsdarstellung; formelle Vollstaendigkeits- und Plausibilitaetspruefung. Gegenueber der Rechtslage aendert sich dieser Schritt im Kern nicht, wird aber i.d.R. mit kuerzerer Nacharbeitung zur Zweckzuordnung verbunden, weil E-Sport nicht mehr ueber alternative Zwecke 'mitbegruendet' werden muss.",
              "aenderungsstatus": "geaendert",
              "rollen_gueltig": [
                {
                  "rolle": "Sachbearbeitung Gemeinnuetzigkeit (Finanzamt)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "43.20",
                  "zeitaufwand_in_min": "30"
                }
              ],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [
                {
                  "rolle": "Sachbearbeitung Gemeinnuetzigkeit (Finanzamt)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "43.20",
                  "zeitaufwand_in_min": "28"
                }
              ],
              "sachaufwand_vorschlag": "0",
              "ausfuehrung_pro_einzelfall": "1"
            },
            {
              "taetigkeiten_id": "94",
              "taetigkeit": "Inhaltliche Zweckzuordnung: E-Sport als Sport nach Nr. 21 feststellen",
              "beschreibung": "Pruefung und Feststellung, dass der satzungsmaessige Zweck und die tatsaechliche Geschaeftsfuehrung (soweit aktenkundig) unter \"Foerderung des Sports\" fallen, wobei E-Sport nun ausdruecklich einbezogen ist. Der Aufwand sinkt gegenueber der bisherigen (uneinheitlichen) Einordnung, weil die rechtliche Subsumtion/Argumentation fuer die Sportqualifikation vereinfacht ist.",
              "aenderungsstatus": "geaendert",
              "rollen_gueltig": [
                {
                  "rolle": "Sachbearbeitung Gemeinnuetzigkeit (Finanzamt)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "43.20",
                  "zeitaufwand_in_min": "20"
                }
              ],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [
                {
                  "rolle": "Sachbearbeitung Gemeinnuetzigkeit (Finanzamt)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "einfach",
                  "stundenlohn": "43.20",
                  "zeitaufwand_in_min": "10"
                }
              ],
              "sachaufwand_vorschlag": "0",
              "ausfuehrung_pro_einzelfall": "1"
            },
            {
              "taetigkeiten_id": "95",
              "taetigkeit": "Wegfall/Reduktion des alternativen Pruefpfads (Jugendhilfe/Bildung/Kultur etc.)",
              "beschreibung": "Bisher: zusaetzliche Prüfung, ob und wie E-Sport-Foerderung tragfaehig über andere gemeinnuetzige Zwecke zu begruenden ist (inkl. Abgrenzungspruefung, zusaetzliche Begruendungstexte). Kuenftig: entfaellt typischerweise im Standardfall, weil die Einordnung vorrangig als Sportfoerderung erfolgen kann.",
              "aenderungsstatus": "abgeschafft",
              "rollen_gueltig": [
                {
                  "rolle": "Sachbearbeitung Gemeinnuetzigkeit (Finanzamt)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "43.20",
                  "zeitaufwand_in_min": "25"
                }
              ],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [
                {
                  "rolle": "Sachbearbeitung Gemeinnuetzigkeit (Finanzamt)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "einfach",
                  "stundenlohn": "43.20",
                  "zeitaufwand_in_min": "0"
                }
              ],
              "sachaufwand_vorschlag": "0",
              "ausfuehrung_pro_einzelfall": "1"
            },
            {
              "taetigkeiten_id": "96",
              "taetigkeit": "Bescheid/Entscheidungstext erstellen und Akte dokumentieren (Standardbausteine mit E-Sport-Bezug)",
              "beschreibung": "Erstellung/Anpassung des Bescheids (z. B. Feststellung/Freistellung) unter Verwendung angepasster Standardformulierungen zur Einordnung von E-Sport als Sport; kurze Dokumentation/Vermerk in der Akte. Gegenueber vorher geaendert durch kuerzere und standardisierte Begruendung sowie weniger Erlaeuterungsbedarf zur Zweckherleitung.",
              "aenderungsstatus": "geaendert",
              "rollen_gueltig": [
                {
                  "rolle": "Sachbearbeitung Gemeinnuetzigkeit (Finanzamt)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "43.20",
                  "zeitaufwand_in_min": "60"
                }
              ],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [
                {
                  "rolle": "Sachbearbeitung Gemeinnuetzigkeit (Finanzamt)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "43.20",
                  "zeitaufwand_in_min": "55"
                }
              ],
              "sachaufwand_vorschlag": "0",
              "ausfuehrung_pro_einzelfall": "1"
            }
          ]
        },
        {
          "fallgruppen_id": "24",
          "fallgruppe_bezeichnung": "Sonderfall: Abgrenzungs-/Vertiefungspruefung trotz Klarstellung (Rueckfragen/Anhoerung)",
          "fallgruppe_beschreibung": "Faelle mit E-sport-Bezug, in denen trotz Einordnungsmöglichkeit als Sport besonderer Klaerungsbedarf besteht (z. B. unklare Ausgestaltung der tatsaechlichen Geschaeftsfuehrung, Mischzwecke, kommerzielle Naehe, geschlossener Teilnehmerkreis, Mittelverwendung, Verguetungen, Veranstaltungs-/Ligaformate). Die Finanzbehoerde fuehrt vertiefte Pruefung durch (Rueckfragen, Anforderung weiterer Unterlagen, ggf. Anhoerung) und bescheidet erst nach Wuerdigung; gegenueber der Vorlage kann sich der Abgrenzungspruefpfad zwar in Richtung Nr. 21 verschieben, der Aufwand bleibt aber durch Einzelfallpruefung wesentlich hoeher als im Standardfall.",
          "aenderungsstatus": "geaendert",
          "taetigkeiten": [
            {
              "taetigkeiten_id": "97",
              "taetigkeit": "Unterlagen sichten, Sachverhalt strukturieren und Pruefschwerpunkte festlegen (E-Sport-Fall mit Besonderheiten)",
              "beschreibung": "Sichtung/Strukturierung der Unterlagen (Satzung, Ordnungen, Verträge/Kooperationen, Veranstaltungs-/Ligaformate, Mittelverwendung); Ableitung der Pruefschwerpunkte (z. B. Selbstlosigkeit, geschlossener Beguenstigtenkreis, kommerzielle Naehe). Gegenueber vorher geaendert, weil die Vorpruefung zur Sportqualifikation klarer ist und frueher in die materiellen Abgrenzungsfragen ueberleitet.",
              "aenderungsstatus": "geaendert",
              "rollen_gueltig": [
                {
                  "rolle": "Sachbearbeitung Gemeinnuetzigkeit (Finanzamt)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "hoch",
                  "stundenlohn": "43.20",
                  "zeitaufwand_in_min": "110"
                }
              ],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [
                {
                  "rolle": "Sachbearbeitung Gemeinnuetzigkeit (Finanzamt)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "hoch",
                  "stundenlohn": "43.20",
                  "zeitaufwand_in_min": "105"
                }
              ],
              "sachaufwand_vorschlag": "0",
              "ausfuehrung_pro_einzelfall": "1"
            },
            {
              "taetigkeiten_id": "98",
              "taetigkeit": "Rueckfragen/Anforderung weiterer Unterlagen und ggf. Anhoerung",
              "beschreibung": "Kommunikation mit der Koerperschaft zur Klaerung streitiger/unklarer Punkte (z. B. tatsaechliche Geschaeftsfuehrung, Mischzwecke, Teilnehmerkreis, Verguetungen, Sponsoring/kommerzieller Zuschnitt); ggf. Anhoerung und Nachforderung von Nachweisen. Grundsaetzlich unveraendert als Verfahrenshandlung; kann jedoch in einzelnen Faellen kuerzer ausfallen, soweit die Zweckherleitung nicht mehr ueber alternative Zwecke gefuehrt werden muss.",
              "aenderungsstatus": "geaendert",
              "rollen_gueltig": [
                {
                  "rolle": "Sachbearbeitung Gemeinnuetzigkeit (Finanzamt)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "43.20",
                  "zeitaufwand_in_min": "60"
                }
              ],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [
                {
                  "rolle": "Sachbearbeitung Gemeinnuetzigkeit (Finanzamt)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "43.20",
                  "zeitaufwand_in_min": "55"
                }
              ],
              "sachaufwand_vorschlag": "0",
              "ausfuehrung_pro_einzelfall": "1"
            },
            {
              "taetigkeiten_id": "99",
              "taetigkeit": "Vertiefte inhaltliche Pruefung und Bewertung (inkl. Einordnung E-Sport als Sport + Gemeinnuetzigkeitskriterien)",
              "beschreibung": "Vertiefte rechtliche und tatsaechliche Wuerdigung: Einordnung des E-Sport-Bezugs unter Sportfoerderung nach Nr. 21 sowie (unveraendert) Pruefung der allgemeinen Gemeinnuetzigkeitsvoraussetzungen und Abgrenzungen (z. B. Ausschliesslichkeit, Unmittelbarkeit, Selbstlosigkeit, kein geschlossener Beguenstigtenkreis, Mittelverwendung). Gegenueber vorher geaendert durch Vereinfachung im Teilaspekt 'Sportqualifikation' und Wegfall des Zwangs, eine alternative Zweckkette als Hauptbegruendung aufzubauen.",
              "aenderungsstatus": "geaendert",
              "rollen_gueltig": [
                {
                  "rolle": "Sachbearbeitung Gemeinnuetzigkeit (Finanzamt)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "hoch",
                  "stundenlohn": "43.20",
                  "zeitaufwand_in_min": "180"
                }
              ],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [
                {
                  "rolle": "Sachbearbeitung Gemeinnuetzigkeit (Finanzamt)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "hoch",
                  "stundenlohn": "43.20",
                  "zeitaufwand_in_min": "170"
                }
              ],
              "sachaufwand_vorschlag": "0",
              "ausfuehrung_pro_einzelfall": "1"
            },
            {
              "taetigkeiten_id": "100",
              "taetigkeit": "Entscheidung treffen, Bescheid begruenden/erstellen und Dokumentation (inkl. Abweichungs- und Abgrenzungsbegruendung)",
              "beschreibung": "Erstellung des (ggf. ablehnenden/teilweise ablehnenden) Bescheids inkl. ausfuehrlicher Begruendung, Vermerken und Dokumentation der Abgrenzung. Gegenueber vorher geaendert, weil die Textbausteine zur Sportqualifikation angepasst/standardisierbar sind; der vertiefte Teil bleibt fallbedingt aufwendig.",
              "aenderungsstatus": "geaendert",
              "rollen_gueltig": [
                {
                  "rolle": "Sachbearbeitung Gemeinnuetzigkeit (Finanzamt)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "hoch",
                  "stundenlohn": "43.20",
                  "zeitaufwand_in_min": "120"
                }
              ],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [
                {
                  "rolle": "Sachbearbeitung Gemeinnuetzigkeit (Finanzamt)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "hoch",
                  "stundenlohn": "43.20",
                  "zeitaufwand_in_min": "115"
                }
              ],
              "sachaufwand_vorschlag": "0",
              "ausfuehrung_pro_einzelfall": "1"
            }
          ]
        }
      ]
    }
  ]
}
```

---

## Step 11 — `cases_calculation` (fallback)
- model: `gpt-5.2` | provider: `openai` | attempt: `a8d40c083d444508aeb374d8a80e800f` | elapsed: - ms
- fallback_kind: `cases_legacy_key_alias`

---

## Step 12 — `effort_calculation` (fallback)
- model: `gpt-5.2` | provider: `openai` | attempt: `440b8423b6334783a40d187fe4c7bb1a` | elapsed: - ms
- fallback_kind: `effort_legacy_key_alias`

---

## Step 13 — `cases_calculation` (success)
- model: `gpt-5.2` | provider: `openai` | attempt: `d57aa77e9e2249539a3d89a633698e64` | elapsed: 18503 ms
- tokens: in=9343 out=1523 hidden_thinking=0 | cost: $0.037672

### Prompt

```

    Sie sind Legist im deutschen Bundestag und damit betraut, die 
    Erfüllungsaufwandsänderung zu einer geplanten Gesetzesänderung zu berechnen.

    Insbesondere werden zur Ermittlung der zu erwartenden Änderung des Aufwands 
    pro Fall die wesentlichen Tätigkeiten identifiziert, die zur Erfüllung 
    einer Vorgabe oder eines Prozesses im Einzelfall zu erwarten sind. Diese 
    schließen Tätigkeiten ein, welche neu hinzukommen, welche sich ändern und 
    welche wegfallen. Für diese Tätigkeiten werden die zu erwartenden Änderungen des 
    Zeit-, Personal- sowie Sachaufwands ermittelt.

    Die wesentlichen Unterschiede der Gesetzesänderung sind wie folgt 
    zusammengefasst: Aus dem Vergleich ergibt sich nur eine einzige materielle Änderung: In § 52 Abs. 2 Nr. 21 AO wird der Klammerzusatz von „Schach gilt als Sport“ zu „Schach gilt als Sport und E‑Sport gilt für diese Regelung als Sport“ erweitert. Alle übrigen Tatbestandsvoraussetzungen in Absatz 1 (Allgemeinheitsförderung, Abgrenzung zu geschlossenen Personenkreisen etc.) sowie der restliche Katalog gemeinnütziger Zwecke in Absatz 2 und die Öffnungsklausel am Ende bleiben wortgleich.

Ziel des Gesetzgebers ist damit erkennbar eine Klarstellung und Erweiterung des gemeinnützigen Zweckkatalogs zugunsten des E‑Sports: Körperschaften (z.B. Vereine, Stiftungen, gGmbHs), deren Satzungszweck und tatsächliche Geschäftsführung auf die Förderung von E‑Sport gerichtet ist, sollen unter dem bereits anerkannten Zweck „Förderung des Sports“ leichter und rechtssicher als gemeinnützig anerkannt werden. Praktisch bedeutet dies eine Reduzierung von Rechtsunsicherheit und uneinheitlicher Verwaltungspraxis, weil E‑Sport nicht mehr (nur) über andere Zwecke (z.B. Jugendhilfe, Bildung, Kultur, digitale Kompetenzen) „mitbegründet“ werden müsste, sondern unmittelbar als Sportförderung gemeinnützig sein kann.

Wesentliche Unterschiede/Wirkungen der Änderung:
- Erweiterter Anwendungsbereich von Nr. 21: Sportvereine im Sinne der Gemeinnützigkeit sollen ausdrücklich auch E‑Sport-Vereine umfassen.
- Rechtsfolgeebene (implizit): E‑Sport‑Organisationen können damit eher Zugang zu typischen Gemeinnützigkeitsfolgen erhalten (insbesondere steuerliche Begünstigungen, Spendenabzugsfähigkeit für Zuwendungen an die Körperschaft, erleichterte Mittelakquise), soweit sie die allgemeinen Gemeinnützigkeitsanforderungen (Selbstlosigkeit, Ausschließlichkeit, Unmittelbarkeit, tatsächliche Geschäftsführung, kein geschlossener Begünstigtenkreis) erfüllen.
- Keine Ausweitung anderer Zwecke/keine Änderung der Grunddefinition: Die Änderung schafft keinen neuen eigenständigen Zweck außerhalb des Sportbegriffs, sondern ordnet E‑Sport ausdrücklich dem bestehenden Zweck „Sport“ zu und lässt die übrige Systematik des § 52 AO unverändert.

    
        Die Gesetzesänderung führt zu folgenden, Erfüllungsaufwand auslösenden Prozessen für den betroffenen Normadressaten, welche durch folgende Fallgruppen 
        differenziert werden: [{"prozess_id": 14, "prozess_bezeichnung": "Gemeinnuetzigkeitsantrag/Steuerbeguenstigungsnachweis fuer E-Sport-Koerperschaften unter Zweck 'Foerderung des Sports' (inkl. Anpassung von Satzung/Begruendung/Unterlagen)", "prozess_beschreibung": "Korporationen der Wirtschaft (z. B. E-Sport-Vereine, gGmbHs, Stiftungen) richten die Geltendmachung der Gemeinnuetzigkeit bzw. Steuerbeguenstigungen kuenftig rechtssicherer auf den Zweck 'Foerderung des Sports' aus, da E-Sport fuer § 52 Abs. 2 Nr. 21 AO ausdruecklich als Sport gilt. Im Rahmen der (Neu-)Beantragung bzw. laufenden Nachweisfuehrung/Begruendung gegenueber der Finanzverwaltung (z. B. Feststellung/Veranlagung/Freistellung) verlagert sich der Begruendungspfad weg von alternativen gemeinnuetzigen Zwecken (z. B. Jugendhilfe/Bildung/Kultur) hin zur unmittelbaren Sportfoerderung; dadurch entfaellt in betroffenen Faellen der zusaetzliche Begruendungs- und Abgrenzungsaufwand ueber andere Zwecke und es kann interner Aufwand zur Umstellung der Standardtexte/Argumentation/Unterlagen anfallen.", "aenderungsstatus": "geaendert", "vorgaben": [{"vorgaben_id": 11, "normzitat": "§ 52 Abs. 2 Nr. 21 AO", "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}}, {"vorgaben_id": 12, "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)", "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}}], "fallgruppen": [{"fallgruppen_id": 25, "fallgruppe_bezeichnung": "Neuantrag/Erstanerkennung Gemeinnuetzigkeit fuer E-Sport-Koerperschaft unter Zweck 'Foerderung des Sports' (statt alternativer Zwecke)", "fallgruppe_beschreibung": "E-Sport-Koerperschaften, die erstmals die Gemeinnuetzigkeit/Steuerbeguenstigung beantragen, koennen den Antrag und die Begruendung unmittelbar auf 'Foerderung des Sports' stuetzen. Im Vergleich zur bisherigen (unsicheren) Praxis entfaellt typischerweise zusaetzlicher Begruendungs- und Abgrenzungsaufwand, der zuvor fuer die Herleitung ueber alternative gemeinnuetzige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) sowie fuer entsprechende Satzungs- und Konzeptbegruendungen angefallen waere. Ggf. verbleibt ein einmaliger interner Aufwand zur Erstellung/Anpassung von Standardtexten, Satzungsbausteinen und Nachweisunterlagen auf den Sportzweck mit E-Sport-Bezug.", "aenderungsstatus": "geaendert", "spiegelsituationen": [{"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}, {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}]}, {"fallgruppen_id": 26, "fallgruppe_bezeichnung": "Bestandskoerperschaft: Umstellung/Anpassung Satzung, Zweckformulierung und Nachweisfuehrung auf 'Sport (inkl. E-Sport)'", "fallgruppe_beschreibung": "Bereits bestehende E-Sport-Koerperschaften mit laufender Gemeinnuetzigkeitsfuehrung (z. B. gueltiger Freistellungsbescheid bzw. turnusmaessige Nachweis- und Erklaerungsprozesse), die bisher (aus Rechtsunsicherheit) teilweise ueber alternative Zwecke argumentiert oder Mischbegruendungen genutzt haben, stellen ihre Standardargumentation, Unterlagen und ggf. die Satzungszweckbeschreibung auf 'Foerderung des Sports' um. Dies kann einen einmaligen internen Abstimmungs- und Dokumentationsaufwand (inkl. ggf. externer Beratung/Steuerberatung) ausloesen; zugleich reduziert sich kuenftig der wiederkehrende Begruendungs- und Abgrenzungsaufwand, weil der zusaetzliche alternative Begruendungspfad entfaellt.", "aenderungsstatus": "geaendert", "spiegelsituationen": [{"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}, {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}]}, {"fallgruppen_id": 27, "fallgruppe_bezeichnung": "Bestandskoerperschaft: Keine materielle Umstellung erforderlich (E-Sport bereits als Sport behandelt/abgebildet)", "fallgruppe_beschreibung": "E-Sport-Koerperschaften, die bereits vor der Klarstellung ihre Gemeinnuetzigkeit unter 'Foerderung des Sports' (oder in der praktischen Umsetzung gleichwertig) begruendet und dokumentiert haben, muessen keine oder nur minimale Anpassungen vornehmen (z. B. Aktualisierung von Textbausteinen/Verweisen). Der wesentliche Effekt liegt in reduzierter Rechtsunsicherheit ohne nennenswerten zusaetzlichen internen Zeit- oder Sachaufwand.", "aenderungsstatus": "geaendert", "spiegelsituationen": [{"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}, {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}]}]}]
        

        Ihre Aufgabe ist es, die Änderung der Fallzahlen jeder dieser Fallgruppen zu bestimmen. Hierzu werden die Häufigkeit und die Anzahl der Betroffenen 
        vor (_gueltig) und nach (_vorschlag) der geplanten Gesetzesänderung betrachtet. Bei der Einführung einer Fallgruppe werden typischerweise nur die 
        _vorschlag-Werte angegeben, bei der Löschung nur die _gueltig-Werte und bei einer Änderung beide.

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

        Bei Spiegelsituationen gilt: Wenn aus einem anderen Normadressaten bereits spiegelnde Fallzahlen vorliegen und der zugrunde liegende Sachverhalt
        logisch 1:1 gekoppelt ist, sind dieselben Mengen zu übernehmen statt sie erneut unabhängig zu schätzen. Beispiel: Wenn 500 neue Vereine gegründet
        werden und deshalb 500 Anträge bei der Verwaltung zu bearbeiten sind, muss dieselbe Fallzahl auf beiden Seiten zugrunde gelegt werden; unterschiedlich
        sind dann nur die Tätigkeiten und Kosten, nicht die Zahl der Fälle.

        Wenn strukturierte Spiegel-Matches mit `sync_cases = 1`, `sync_addressees = 1` oder `sync_frequency = 1` vorliegen, befolgen Sie diese Vorgaben
        vorrangig. Solche Matches sind als autoritative Synchronisierungshinweise zu behandeln und nicht erneut frei zu ueberschreiben.

        Offizielles Methodenbeispiel aus dem Leitfaden (woertlich uebernommen):
        → Beispiele für jährliche Häufigkeit bei periodisch zu erfüllenden Vorgaben:
Vorgabe ist periodisch zu erfüllen
- einmal jährlich: Häufigkeit = 1
- halbjährlich: Häufigkeit = 2
- monatlich: Häufigkeit = 12
- alle 5 Jahre: Häufigkeit = 0,2

        Offizielles Fallzahlbeispiel aus dem Leitfaden (woertlich uebernommen):
        

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
        
        {
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
                    "anzahl_betroffene_gueltig": "",
                    "haeufigkeit_pro_jahr_gueltig": "",
                    "anzahl_betroffene_vorschlag": "",
                    "haeufigkeit_pro_jahr_vorschlag": ""
                },
                {
                    "fallgruppen_id": "",
                    "fallgruppe_bezeichnung": "",
                    "fallgruppe_beschreibung": "",
                    "aenderungsstatus": "",
                    "anzahl_betroffene_gueltig": "",
                    "haeufigkeit_pro_jahr_gueltig": "",
                    "anzahl_betroffene_vorschlag": "",
                    "haeufigkeit_pro_jahr_vorschlag": ""
                }
            ]
            },
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
                },
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
                    "anzahl_betroffene_gueltig": "",
                    "haeufigkeit_pro_jahr_gueltig": "",
                    "anzahl_betroffene_vorschlag": "",
                    "haeufigkeit_pro_jahr_vorschlag": ""
                }
            ]
            }
        ]
        }
        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 
        

Dieser Lauf betrifft den Normadressaten Wirtschaft.

        Beruecksichtigen Sie ausschliesslich den Erfuellungsaufwand der Wirtschaft.
        Analysieren Sie nur wirtschaftsbezogene Prozesse, Fallgruppen, Taetigkeiten,
        Fallzahlen und Werte. Uebernehmen Sie keine Verwaltungslogik, Verwaltungswerte
        oder buergerbezogenen Inhalte, sofern diese nicht ausdruecklich als Spiegelwirkung
        oder wirtschaftsrelevante Folge der Vorgabe begruendet sind. Informationspflichten
        der Wirtschaft, Spiegelsituationen, interne Umstellungen, externe Dienstleistungen
        sowie wirtschaftsspezifische Pruef-, Melde-, Nachweis- und Dokumentationspflichten
        sind mitzudenken.
```

### Raw Response

```
{
  "prozesse": [
    {
      "prozess_id": 14,
      "prozess_bezeichnung": "Gemeinnuetzigkeitsantrag/Steuerbeguenstigungsnachweis fuer E-Sport-Koerperschaften unter Zweck 'Foerderung des Sports' (inkl. Anpassung von Satzung/Begruendung/Unterlagen)",
      "prozess_beschreibung": "Korporationen der Wirtschaft (z. B. E-Sport-Vereine, gGmbHs, Stiftungen) richten die Geltendmachung der Gemeinnuetzigkeit bzw. Steuerbeguenstigungen kuenftig rechtssicherer auf den Zweck 'Foerderung des Sports' aus, da E-Sport fuer § 52 Abs. 2 Nr. 21 AO ausdruecklich als Sport gilt. Im Rahmen der (Neu-)Beantragung bzw. laufenden Nachweisfuehrung/Begruendung gegenueber der Finanzverwaltung (z. B. Feststellung/Veranlagung/Freistellung) verlagert sich der Begruendungspfad weg von alternativen gemeinnuetzigen Zwecken (z. B. Jugendhilfe/Bildung/Kultur) hin zur unmittelbaren Sportfoerderung; dadurch entfaellt in betroffenen Faellen der zusaetzliche Begruendungs- und Abgrenzungsaufwand ueber andere Zwecke und es kann interner Aufwand zur Umstellung der Standardtexte/Argumentation/Unterlagen anfallen.",
      "aenderungsstatus": "geaendert",
      "vorgaben": [
        {
          "vorgaben_id": 11,
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO",
          "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).",
          "aenderungsstatus": "geaendert"
        },
        {
          "vorgaben_id": 12,
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)",
          "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.",
          "aenderungsstatus": "geaendert"
        }
      ],
      "fallgruppen": [
        {
          "fallgruppen_id": 25,
          "fallgruppe_bezeichnung": "Neuantrag/Erstanerkennung Gemeinnuetzigkeit fuer E-Sport-Koerperschaft unter Zweck 'Foerderung des Sports' (statt alternativer Zwecke)",
          "fallgruppe_beschreibung": "Anlassbezogene Antraege (jaehrliche Antragsfaelle). Durch die ausdrueckliche Einordnung von E-Sport als Sport sinkt die Rechtsunsicherheit und der Anreiz/Bedarf, Antraege ueber alternative Zwecke zu begruenden. Zugleich ist ein moderater Nachfrageeffekt plausibel, weil bislang zurueckgestellte oder nicht gestellte Erstantraege (wegen unsicherer Anerkennung) kuenftig eher gestellt werden. Daher wird die Zahl der jaehrlich neu antragstellenden E-Sport-Koerperschaften unter dem Zweck 'Foerderung des Sports' im Vorschlag hoeher angesetzt als unter geltender Rechtslage (mehr Erstantraege/Neugruendungen, die den Antrag nun stellen).",
          "aenderungsstatus": "geaendert",
          "anzahl_betroffene_gueltig": 120,
          "haeufigkeit_pro_jahr_gueltig": 1,
          "anzahl_betroffene_vorschlag": 160,
          "haeufigkeit_pro_jahr_vorschlag": 1
        },
        {
          "fallgruppen_id": 26,
          "fallgruppe_bezeichnung": "Bestandskoerperschaft: Umstellung/Anpassung Satzung, Zweckformulierung und Nachweisfuehrung auf 'Sport (inkl. E-Sport)'",
          "fallgruppe_beschreibung": "Einmaliger Umstellungsaufwand bei bereits bestehenden E-Sport-Koerperschaften, die bislang (ganz oder teilweise) ueber alternative Zwecke/Mischbegruendungen gearbeitet haben. Durch die Klarstellung entsteht fuer einen Teil der Bestandskoerperschaften ein Anlass, Satzung/Standardtexte/Dokumentation auf den Sportzweck umzustellen (ggf. inkl. externer Beratung). Dieser Umstellungsprozess faellt im Jahr des Inkrafttretens einmal pro betroffener Koerperschaft an; unter geltender Rechtslage existiert dieser Umstellungsanlass nicht. Daher: gueltig = 0; vorschlag = geschaetzter Anteil der Bestandskoerperschaften mit Umstellungsbedarf.",
          "aenderungsstatus": "geaendert",
          "anzahl_betroffene_gueltig": 0,
          "haeufigkeit_pro_jahr_gueltig": 0,
          "anzahl_betroffene_vorschlag": 600,
          "haeufigkeit_pro_jahr_vorschlag": 1
        },
        {
          "fallgruppen_id": 27,
          "fallgruppe_bezeichnung": "Bestandskoerperschaft: Keine materielle Umstellung erforderlich (E-Sport bereits als Sport behandelt/abgebildet)",
          "fallgruppe_beschreibung": "Bestandskoerperschaften, die bereits vor der Klarstellung ihre Gemeinnuetzigkeit faktisch unter 'Foerderung des Sports' abgebildet hatten, haben keinen Umstellungsprozess (kein ausloesender Aufwand). Die Gesetzesaenderung reduziert hier primaer Rechtsunsicherheit, ohne dass ein eigener, erfuellungsaufwandrelevanter Vorgang ausgeloest wird. Daher bleibt die fallzahlrelevante Menge fuer diesen Prozess (Umstellung/Anpassung) sowohl gueltig als auch vorschlag bei 0.",
          "aenderungsstatus": "geaendert",
          "anzahl_betroffene_gueltig": 0,
          "haeufigkeit_pro_jahr_gueltig": 0,
          "anzahl_betroffene_vorschlag": 0,
          "haeufigkeit_pro_jahr_vorschlag": 0
        }
      ]
    }
  ]
}
```

---

## Step 14 — `effort_calculation` (success)
- model: `gpt-5.2` | provider: `openai` | attempt: `7add13f416c644b6a7ed66411aa8665f` | elapsed: 47954 ms
- tokens: in=12361 out=5132 hidden_thinking=0 | cost: $0.093480

### Prompt

```

    Sie sind Legist im deutschen Bundestag und damit betraut, die 
    Erfüllungsaufwandsänderung zu einer geplanten Gesetzesänderung zu berechnen.

    Insbesondere werden zur Ermittlung der zu erwartenden Änderung des Aufwands 
    pro Fall die wesentlichen Tätigkeiten identifiziert, die zur Erfüllung 
    einer Vorgabe oder eines Prozesses im Einzelfall zu erwarten sind. Diese 
    schließen Tätigkeiten ein, welche neu hinzukommen, welche sich ändern und 
    welche wegfallen. Für diese Tätigkeiten werden die zu erwartenden Änderungen des 
    Zeit-, Personal- sowie Sachaufwands ermittelt.

    Die wesentlichen Unterschiede der Gesetzesänderung sind wie folgt 
    zusammengefasst: Aus dem Vergleich ergibt sich nur eine einzige materielle Änderung: In § 52 Abs. 2 Nr. 21 AO wird der Klammerzusatz von „Schach gilt als Sport“ zu „Schach gilt als Sport und E‑Sport gilt für diese Regelung als Sport“ erweitert. Alle übrigen Tatbestandsvoraussetzungen in Absatz 1 (Allgemeinheitsförderung, Abgrenzung zu geschlossenen Personenkreisen etc.) sowie der restliche Katalog gemeinnütziger Zwecke in Absatz 2 und die Öffnungsklausel am Ende bleiben wortgleich.

Ziel des Gesetzgebers ist damit erkennbar eine Klarstellung und Erweiterung des gemeinnützigen Zweckkatalogs zugunsten des E‑Sports: Körperschaften (z.B. Vereine, Stiftungen, gGmbHs), deren Satzungszweck und tatsächliche Geschäftsführung auf die Förderung von E‑Sport gerichtet ist, sollen unter dem bereits anerkannten Zweck „Förderung des Sports“ leichter und rechtssicher als gemeinnützig anerkannt werden. Praktisch bedeutet dies eine Reduzierung von Rechtsunsicherheit und uneinheitlicher Verwaltungspraxis, weil E‑Sport nicht mehr (nur) über andere Zwecke (z.B. Jugendhilfe, Bildung, Kultur, digitale Kompetenzen) „mitbegründet“ werden müsste, sondern unmittelbar als Sportförderung gemeinnützig sein kann.

Wesentliche Unterschiede/Wirkungen der Änderung:
- Erweiterter Anwendungsbereich von Nr. 21: Sportvereine im Sinne der Gemeinnützigkeit sollen ausdrücklich auch E‑Sport-Vereine umfassen.
- Rechtsfolgeebene (implizit): E‑Sport‑Organisationen können damit eher Zugang zu typischen Gemeinnützigkeitsfolgen erhalten (insbesondere steuerliche Begünstigungen, Spendenabzugsfähigkeit für Zuwendungen an die Körperschaft, erleichterte Mittelakquise), soweit sie die allgemeinen Gemeinnützigkeitsanforderungen (Selbstlosigkeit, Ausschließlichkeit, Unmittelbarkeit, tatsächliche Geschäftsführung, kein geschlossener Begünstigtenkreis) erfüllen.
- Keine Ausweitung anderer Zwecke/keine Änderung der Grunddefinition: Die Änderung schafft keinen neuen eigenständigen Zweck außerhalb des Sportbegriffs, sondern ordnet E‑Sport ausdrücklich dem bestehenden Zweck „Sport“ zu und lässt die übrige Systematik des § 52 AO unverändert.

    
        Die Gesetzesänderung führt zu folgenden, Erfüllungsaufwand auslösenden Prozessen für den betroffenen Normadressaten, welche durch folgende Fallgruppen und 
        Prozessschritte differenziert werden: [{"prozess_id": 14, "prozess_bezeichnung": "Gemeinnuetzigkeitsantrag/Steuerbeguenstigungsnachweis fuer E-Sport-Koerperschaften unter Zweck 'Foerderung des Sports' (inkl. Anpassung von Satzung/Begruendung/Unterlagen)", "prozess_beschreibung": "Korporationen der Wirtschaft (z. B. E-Sport-Vereine, gGmbHs, Stiftungen) richten die Geltendmachung der Gemeinnuetzigkeit bzw. Steuerbeguenstigungen kuenftig rechtssicherer auf den Zweck 'Foerderung des Sports' aus, da E-Sport fuer § 52 Abs. 2 Nr. 21 AO ausdruecklich als Sport gilt. Im Rahmen der (Neu-)Beantragung bzw. laufenden Nachweisfuehrung/Begruendung gegenueber der Finanzverwaltung (z. B. Feststellung/Veranlagung/Freistellung) verlagert sich der Begruendungspfad weg von alternativen gemeinnuetzigen Zwecken (z. B. Jugendhilfe/Bildung/Kultur) hin zur unmittelbaren Sportfoerderung; dadurch entfaellt in betroffenen Faellen der zusaetzliche Begruendungs- und Abgrenzungsaufwand ueber andere Zwecke und es kann interner Aufwand zur Umstellung der Standardtexte/Argumentation/Unterlagen anfallen.", "aenderungsstatus": "geaendert", "vorgaben": [{"vorgaben_id": 11, "normzitat": "§ 52 Abs. 2 Nr. 21 AO", "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}}, {"vorgaben_id": 12, "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)", "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.", "aenderungsstatus": "geaendert", "normadressaten": ["administration", "business"], "ist_informationspflicht_wirtschaft": false, "spiegelsituation": {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}}], "fallgruppen": [{"fallgruppen_id": 25, "fallgruppe_bezeichnung": "Neuantrag/Erstanerkennung Gemeinnuetzigkeit fuer E-Sport-Koerperschaft unter Zweck 'Foerderung des Sports' (statt alternativer Zwecke)", "fallgruppe_beschreibung": "E-Sport-Koerperschaften, die erstmals die Gemeinnuetzigkeit/Steuerbeguenstigung beantragen, koennen den Antrag und die Begruendung unmittelbar auf 'Foerderung des Sports' stuetzen. Im Vergleich zur bisherigen (unsicheren) Praxis entfaellt typischerweise zusaetzlicher Begruendungs- und Abgrenzungsaufwand, der zuvor fuer die Herleitung ueber alternative gemeinnuetzige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) sowie fuer entsprechende Satzungs- und Konzeptbegruendungen angefallen waere. Ggf. verbleibt ein einmaliger interner Aufwand zur Erstellung/Anpassung von Standardtexten, Satzungsbausteinen und Nachweisunterlagen auf den Sportzweck mit E-Sport-Bezug.", "aenderungsstatus": "geaendert", "spiegelsituationen": [{"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}, {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}], "taetigkeiten": [{"taetigkeiten_id": 101, "taetigkeit": "Begruendungs- und Nachweiskonzept von alternativen Zwecken auf 'Foerderung des Sports (inkl. E-Sport)' umstellen", "beschreibung": "Im Neuantrag wird die Argumentationslinie/Begruendung so angepasst, dass E-Sport unmittelbar als Sportfoerderung dargestellt wird (statt Herleitung ueber Jugendhilfe/Bildung/Kultur). Dazu werden die beizufuegenden Kurzkonzepte, Taetigkeitsdarstellungen und Textbausteine entsprechend neu ausgerichtet.", "aenderungsstatus": "geaendert", "vorgaben_ids": [11, 12]}, {"taetigkeiten_id": 102, "taetigkeit": "Zusaetzlichen Abgrenzungs- und Darlegungsaufwand ueber alternative gemeinnuetzige Zwecke entfallen lassen", "beschreibung": "Soweit bisher (aus Rechtsunsicherheit) zusaetzliche Darlegungen/Abgrenzungen zu alternativen Zwecken erforderlich waren (z. B. gesonderte Bildungs-/Jugendhilfe-Begruendung, Doppelbegruendung, Plausibilisierung eines Alternativzwecks), wird dieser Begruendungspfad im Antrag nicht mehr erstellt bzw. nicht mehr in gleicher Tiefe ausgearbeitet.", "aenderungsstatus": "abgeschafft", "vorgaben_ids": [12]}, {"taetigkeiten_id": 103, "taetigkeit": "Satzungszweck/-bausteine und Anlagen fuer den Antrag auf Sportzweck mit E-Sport-Bezug zuschneiden", "beschreibung": "Erstellung/Anpassung von Satzungsformulierungen (Zweck/Verwirklichung) bzw. der einzureichenden Anlagen (z. B. Musterformulierungen, Taetigkeitsbeschreibungen) so, dass die Foerderung des Sports durch E-Sport inhaltlich konsistent dargestellt wird; dies umfasst auch interne Abstimmung und Finalisierung der Unterlagen.", "aenderungsstatus": "geaendert", "vorgaben_ids": [11]}, {"taetigkeiten_id": 104, "taetigkeit": "Antragsunterlagen finalisieren und einreichen (inkl. Dokumentation/Ablage der geaenderten Begruendung)", "beschreibung": "Zusammenstellung der finalen Unterlagen und Einreichung in der ueblichen Form; die Taetigkeit bleibt als Standardvorgang bestehen, wird aber inhaltlich durch die geaenderte Rechtsgrundlage (Sport inkl. E-Sport) mitangepasst (Versionierung/Ablage der neuen Textstaende).", "aenderungsstatus": "geaendert", "vorgaben_ids": [11, 12]}]}, {"fallgruppen_id": 26, "fallgruppe_bezeichnung": "Bestandskoerperschaft: Umstellung/Anpassung Satzung, Zweckformulierung und Nachweisfuehrung auf 'Sport (inkl. E-Sport)'", "fallgruppe_beschreibung": "Bereits bestehende E-Sport-Koerperschaften mit laufender Gemeinnuetzigkeitsfuehrung (z. B. gueltiger Freistellungsbescheid bzw. turnusmaessige Nachweis- und Erklaerungsprozesse), die bisher (aus Rechtsunsicherheit) teilweise ueber alternative Zwecke argumentiert oder Mischbegruendungen genutzt haben, stellen ihre Standardargumentation, Unterlagen und ggf. die Satzungszweckbeschreibung auf 'Foerderung des Sports' um. Dies kann einen einmaligen internen Abstimmungs- und Dokumentationsaufwand (inkl. ggf. externer Beratung/Steuerberatung) ausloesen; zugleich reduziert sich kuenftig der wiederkehrende Begruendungs- und Abgrenzungsaufwand, weil der zusaetzliche alternative Begruendungspfad entfaellt.", "aenderungsstatus": "geaendert", "spiegelsituationen": [{"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}, {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}], "taetigkeiten": [{"taetigkeiten_id": 105, "taetigkeit": "Interne Analyse/Entscheidung zur Umstellung der Gemeinnuetzigkeitsbegruendung auf 'Sport (inkl. E-Sport)'", "beschreibung": "Pruefung der bisherigen Begruendung (Alternativzwecke/Mischbegruendung) und Festlegung, kuenftig vorrangig/allein auf Nr. 21 (Sport inkl. E-Sport) abzustellen; inkl. Abstimmung im Vorstand/Management und Festlegung der notwendigen Anpassungen an Dokumentenstandards.", "aenderungsstatus": "eingefuehrt", "vorgaben_ids": [11, 12]}, {"taetigkeiten_id": 106, "taetigkeit": "Satzung und Standardunterlagen (Textbausteine, Taetigkeitsdarstellung, Nachweislogik) anpassen und versionieren", "beschreibung": "Einmalige Ueberarbeitung von Satzungszweck/Verwirklichung (soweit erforderlich) sowie der wiederverwendeten Begruendungstexte und Nachweisunterlagen, sodass die Sportfoerderung durch E-Sport konsistent und rechtssicher dargestellt ist; inkl. Dokumentation/Ablage der geaenderten Versionen.", "aenderungsstatus": "geaendert", "vorgaben_ids": [11]}, {"taetigkeiten_id": 107, "taetigkeit": "Wiederkehrenden zusaetzlichen Begruendungs- und Abgrenzungsteil ueber Alternativzwecke kuerzen/streichen", "beschreibung": "In der laufenden Nachweisfuehrung gegenueber der Finanzverwaltung (z. B. im Rahmen turnusmaessiger Unterlagenzusammenstellung) entfaellt bzw. reduziert sich der bisherige Zusatzaufwand, der allein daraus resultierte, E-Sport ueber andere Zwecke mit zu begruenden oder abzugrenzen.", "aenderungsstatus": "abgeschafft", "vorgaben_ids": [12]}, {"taetigkeiten_id": 108, "taetigkeit": "Ggf. externe Unterstuetzung (z. B. Steuerberatung) fuer Umstellung/Pruefung der Unterlagen einholen", "beschreibung": "Soweit ueblich oder risikoorientiert veranlasst: Einholung/Verwertung externer Beratung zur Anpassung der Satzung/Begruendung und zur Minimierung von Anerkennungsrisiken; diese Taetigkeit entsteht typischerweise einmalig im Zuge der Umstellung.", "aenderungsstatus": "eingefuehrt", "vorgaben_ids": [11, 12]}]}, {"fallgruppen_id": 27, "fallgruppe_bezeichnung": "Bestandskoerperschaft: Keine materielle Umstellung erforderlich (E-Sport bereits als Sport behandelt/abgebildet)", "fallgruppe_beschreibung": "E-Sport-Koerperschaften, die bereits vor der Klarstellung ihre Gemeinnuetzigkeit unter 'Foerderung des Sports' (oder in der praktischen Umsetzung gleichwertig) begruendet und dokumentiert haben, muessen keine oder nur minimale Anpassungen vornehmen (z. B. Aktualisierung von Textbausteinen/Verweisen). Der wesentliche Effekt liegt in reduzierter Rechtsunsicherheit ohne nennenswerten zusaetzlichen internen Zeit- oder Sachaufwand.", "aenderungsstatus": "geaendert", "spiegelsituationen": [{"liegt_vor": true, "normadressaten": [], "beschreibung": "Soweit Körperschaften (z. B. E‑Sport‑Vereine/gGmbHs/Stiftungen) ihre Gemeinnützigkeit bzw. Steuerbegünstigung unter dem Zweck „Förderung des Sports“ geltend machen (z. B. im Rahmen von Anerkennungs-/Feststellungs- bzw. Veranlagungs- und Freistellungsverfahren), müssen die zuständigen Finanzbehörden die Einordnung von E‑Sport unter Nr. 21 im Einzelfall prüfen und bei Vorliegen der übrigen Voraussetzungen entsprechend bescheiden (inkl. ggf. Anpassung interner Prüfschritte/Arbeitshinweise/Formulierungen).", "mirror_anchor_key": "gemeinnuetzigkeit-esport-als-sport"}, {"liegt_vor": true, "normadressaten": [], "beschreibung": "Wenn Körperschaften ihre Gemeinnützigkeit/Steuerbegünstigung künftig auf „Sport (inkl. E‑Sport)“ stützen, reduziert/verschiebt sich korrespondierend der Prüfaufwand der Finanzverwaltung weg von der Einordnung unter alternative Zwecke hin zur Prüfung unter Nr. 21 (neben den unveränderten allgemeinen Gemeinnützigkeitsvoraussetzungen).", "mirror_anchor_key": "pruefpfad-wechsel-esport-gemeinnuetzigkeit"}], "taetigkeiten": [{"taetigkeiten_id": 109, "taetigkeit": "Minimale Aktualisierung von Standardtexten/Verweisen auf die Klarstellung 'E-Sport gilt als Sport'", "beschreibung": "Soweit genutzt: kurze Anpassung bestehender Textbausteine (z. B. in Anschreiben, Begruendungspapieren, internen FAQs) bzw. Ergaenzung eines Verweises auf die explizite Einordnung von E-Sport als Sport; ohne inhaltliche Umstellung der uebrigen Nachweisfuehrung.", "aenderungsstatus": "geaendert", "vorgaben_ids": [11]}, {"taetigkeiten_id": 110, "taetigkeit": "Zusaetzliche Vorsorge-/Alternativbegruendungen (Backup-Zwecke) nicht mehr vorhalten", "beschreibung": "Soweit bislang aus Vorsicht parallel Alternativzwecke oder Ersatzargumentationen dokumentiert/mitgefuehrt wurden, koennen diese kuenftig entfallen (z. B. keine fortlaufende Pflege von Doppelbegruendungen).", "aenderungsstatus": "abgeschafft", "vorgaben_ids": [12]}, {"taetigkeiten_id": 111, "taetigkeit": "Laufende Nachweisfuehrung unter Sportzweck fortsetzen (nur geringfuegig beruehrt)", "beschreibung": "Die regulaeren, ohnehin bestehenden Schritte zur Nachweisfuehrung/Unterlagenbereitstellung bleiben im Kern gleich; sie werden lediglich um die rechtssichere Einordnung ergaenzt, ohne dass ein zusaetzlicher Aufwand entsteht.", "aenderungsstatus": "unveraendert", "vorgaben_ids": [11, 12]}]}]}]

        Ihre Aufgabe ist es, den anfallenden Personal- und ggf. Sachaufwand der anfallenden Tätigkeiten pro Einzelfall zu identifizieren. 
        Hierzu werden die Stundenlöhne, Zeit- und Sachaufwände vor (_gueltig) und nach (_vorschlag) der geplanten Gesetzesänderung betrachtet. Bei der Einführung
        eines Prozessschrittes werden typischerweise nur die _vorschlag-Werte angegeben, bei der Löschung nur die _gueltig-Werte und bei einer Änderung beide.

        Entscheidend ist die Aenderung des Erfuellungsaufwands je Fall. Schaetzen Sie daher nicht den gesamten denkbaren Bearbeitungsaufwand eines Verfahrens
        neu, sondern den fuer die geltende und die vorgeschlagene Rechtslage jeweils relevanten Aufwand derselben Taetigkeit. Wenn sich nur ein Teilaspekt
        aendert, darf nicht automatisch der gesamte Schritt neu und vollumfaenglich angesetzt werden. Unveraenderte Aufwaende sollten in _gueltig und
        _vorschlag gleich bleiben; nur geaenderte Mehr- oder Minderaufwaende sind abweichend auszuweisen.

        Eine Reihe von Taetigkeiten laeuft bei Nutzung entsprechender Informationstechnologie automatisch ab. Aus automatisch ablaufenden Prozessen resultiert zunaechst kein Zeitaufwand. Sofern keine spezifischen Daten ueber den Zeitaufwand vorliegen, kann die Zeitwerttabelle Wirtschaft aus Anhang 4 herangezogen werden. Die Tabelle zu Wegezeiten und -sachkosten kann genutzt werden, wenn persoenliche Termine bei anderen Stellen oder Behoerden erforderlich sind. Orientieren Sie sich fuer Standardaktivitaeten zusaetzlich am Standardkostenmodell und den Methodenhinweisen in Anhang 8. Zur Ermittlung des Personalaufwands werden die Bearbeitungszeiten mit den einschlaegigen Lohnsaetzen der Wirtschaft verknuepft. Die festen Lohngruppen sind A=Niedrig, B=Mittel, C=Hoch, D=Durchschnitt. Ordnen Sie jede benoetigte Bearbeitungsstufe genau einer dieser Gruppen zu. Eine einzige Lohngruppe ist der Regelfall; mehrere Lohngruppen sind nur bei klar getrennten Bearbeitungsstufen zulaessig, etwa operative Bearbeitung und anschliessende Freigabe. Vermeiden Sie schematische Mehrfachbefuellung. Buerokratiekosten der Wirtschaft sind spaeter getrennt auszuweisen. Ersatzinvestitionen sind nur zur Haelfte als Erfuellungsaufwand anzusetzen, soweit kein anderer Anteil fachlich begruendet ist.

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

        Anhang Wirtschaft:

### Anhang 5: Wegezeiten und -sachkosten

Wegezeiten umfassen den Zeitaufwand des Normadressaten, um von seinem Wohnort bzw. Sitz zur zuständigen Behörde zu gelangen. Die Wegesachkosten beschreiben den Sachaufwand, um diesen Weg zurückzulegen und beinhalten beispielsweise Fahrkarten für den ÖPNV oder Kraftstoff für das eigene Fahrzeug.

Wegezeiten und Wegesachkosten werden bei der Ermittlung des Erfüllungsaufwands berücksichtigt, wenn die jeweilige Regelung ein persönliches Erscheinen in einer Behörde oder Stelle vorschreibt und keine Alternativen wie den Postweg oder Online-Verfahren erlaubt. Gleiches gilt, wenn Behördenvertreterinnen und -vertreter verpflichtet sind, beispielsweise im Rahmen von Gremiensitzungen persönlich andere Ämter oder Stellen aufzusuchen.

Die folgende Tabelle zeigt pauschale Wegezeiten und -sachkosten in Abhängigkeit der zuständigen Verwaltungsebene. Gibt es belastbare Anhaltspunkte dafür, dass der nach der Tabelle ermittelte Wert aller Wahrscheinlichkeit nach über- oder unterzeichnet ist, sollte der aus Fachsicht realistischere Wert für die Ermittlung genutzt werden.

*Wegezeiten und -sachkosten nach Verwaltungsebene*

| Verwaltungsebene | Wegezeiten (Min.) | Wegesachkosten (Euro) |
| --- | --- | --- |
| Gemeinde | 15 | 1,10 |
| Kreis | 22 | 3,10 |
| Regierungsbezirk/Land | 59 | 13,20 |
| Durchschnitt | 20 | 2,60 |


### Anhang: Zeitwerttabelle Wirtschaft

*Zeitwerttabelle Wirtschaft fuer Informationspflichten*

| Nr. | Standardaktivitaet | Einfach (Min.) | Mittel (Min.) | Hoch (Min.) | Erlaeuterung |
| --- | --- | --- | --- | --- | --- |
| 1 | Einarbeitung in die Informationspflicht | 3 | 5 | 60 | Welcher Aufwand entsteht regelmaessig, um sich mit der gesetzlichen Verpflichtung vertraut zu machen? |
| 2 | Beschaffung von Daten | 2 | 10 | 120 | Welcher Aufwand faellt durch die Beschaffung notwendiger Informationen und Daten an? |
| 3 | Formulare ausfuellen, Beschriftung, Kennzeichnung | 3 | 5 | 30 | Welcher Aufwand entsteht z. B. durch das Ausfuellen eines Antragsformulars? |
| 4 | Berechnungen durchfuehren | 2 | 20 | 240 | Welche Berechnungen, Bewertungen, Zaehlungen muessen durchgefuehrt werden? |
| 5 | Ueberpruefung der Daten und Eingaben | 1 | 10 | 60 | Entsteht Aufwand durch Kontrollmassnahmen? |
| 6 | Fehlerkorrektur | 2 | 10 | 60 | Entsteht Aufwand durch Korrekturmassnahmen? |
| 7 | Aufbereitung der Daten | 3 | 20 | 300 | Welcher Aufwand entsteht durch die Aufbereitung von Daten? |
| 8 | Datenuebermittlung und Veroeffentlichung | 1 | 2 | 5 | Welcher Aufwand entsteht durch die Datenuebermittlung und/oder Veroeffentlichung von Daten oder Informationen? |
| 9 | Interne Sitzungen | 5 | 60 | 600 (1,3 PT) | Welcher Aufwand entsteht durch notwendige interne Sitzungen? |
| 10 | Externe Sitzungen | 10 | 60 | 480 (1 PT) | Welcher Aufwand entsteht durch notwendige externe Sitzungen (z. B. mit Steuerberatung)? |
| 11 | Ausfuehren von Zahlungsanweisungen | 2 | 4 | 15 | Entsteht Aufwand z. B. durch die Veranlassung einer Online-Ueberweisung? |
| 12 | Kopieren, Archivieren, Verteilen | 1 | 2 | 12 | Entsteht Aufwand z. B. durch Kopiertaetigkeiten oder Archivierungsarbeiten? |
| 13 | Pruefung durch oeffentliche Stellen | 5 | 50 | 480 (1 PT) | Welcher Aufwand wird z. B. durch die Betriebspruefung ausgeloest? |
| 14 | Korrekturen, die aufgrund von Pruefungen durchgefuehrt werden muessen | 4 | 30 | 500 (1 PT) | Entsteht Aufwand durch Korrekturen und eine Ueberarbeitung der Daten? |
| 15 | Weitere Informationsbeschaffung | 3 | 15 | 120 | Entsteht Aufwand durch zusaetzliche Informationsbereitstellung? |
| 16 | Fortbildungs- und Schulungsteilnahmen | 2 | 33 | 600 (1,3 PT) | Entsteht Aufwand dadurch, dass die Erfuellung einer Informationspflicht eine Schulung voraussetzt? |
| 17 | Anpassen von internen Prozessen | 300 | 720 (1,5 PT) | 3 480 (7,3 PT) | Welcher Aufwand entsteht, wenn interne Prozesse veraendert oder angepasst werden muessen? |
| 18 | Ueberwachungsmassnahmen | 30 | 240 | 4 200 (8,8 PT) | Entsteht Aufwand durch das Mitwirken bei Ueberwachungsmassnahmen z. B. durch Behoerden wie die Bafin? |
| 19 | Beschaffen von Dienstleistungen | 10 | 60 | 300 | Entsteht Zeitaufwand fuer die Beschaffung von externen Dienstleistungen wie z. B. fuer Gutachten oder Abnahmen? |


### Anhang: Lohnkostentabelle Wirtschaft

*Lohnkosten pro Stunde in Euro*

| Wirtschaftsabschnitt | Niedrig | Mittel | Hoch | Durchschnitt |
| --- | --- | --- | --- | --- |
| A Land- und Forstwirtschaft, Fischerei | 22,70 | 25,60 | 45,80 | 25,00 |
| B Bergbau und Gewinnung von Steinen und Erden | 32,60 | 41,80 | 85,60 | 45,00 |
| C Verarbeitendes Gewerbe | 31,60 | 44,20 | 76,20 | 46,20 |
| D Energieversorgung | 33,60 | 54,90 | 80,70 | 57,80 |
| E Wasserversorgung; Abwasser- und Abfallentsorgung und Beseitigung von Umweltverschmutzungen | 28,50 | 37,00 | 64,70 | 37,40 |
| F Baugewerbe | 26,10 | 33,70 | 59,50 | 33,70 |
| G Handel; Instandhaltung und Reparatur von Kraftfahrzeugen | 23,60 | 32,40 | 62,40 | 33,40 |
| H Verkehr und Lagerei | 25,90 | 32,20 | 62,80 | 32,10 |
| I Gastgewerbe | 21,70 | 24,40 | 39,70 | 23,60 |
| J Information und Kommunikation | 25,10 | 49,90 | 63,70 | 52,80 |
| K Erbringung von Finanz- und Versicherungsdienstleistungen | 29,00 | 54,40 | 93,10 | 57,90 |
| L Grundstuecks- und Wohnungswesen | 24,10 | 34,70 | 56,20 | 35,00 |
| M Erbringung von freiberuflichen, wissenschaftlichen und technischen Dienstleistungen | 25,50 | 40,90 | 64,20 | 46,70 |
| N Erbringung von sonstigen wirtschaftlichen Dienstleistungen | 23,30 | 30,20 | 55,00 | 28,00 |
| P Erziehung und Unterricht | 26,30 | 36,40 | 53,10 | 43,20 |
| Q Gesundheits- und Sozialwesen | 27,00 | 34,20 | 62,00 | 36,90 |
| R Kunst, Unterhaltung und Erholung | 22,90 | 32,20 | 51,00 | 31,70 |
| S Erbringung von sonstigen Dienstleistungen | 23,60 | 30,30 | 49,00 | 32,10 |
| Gesamtwirtschaft (A-S ohne O) | 26,10 | 37,10 | 62,40 | 38,60 |


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
        Verwenden Sie keine ein- oder ausleitenden Texte und keine sonstigen Zeichen. 
        

Dieser Lauf betrifft den Normadressaten Wirtschaft.

        Beruecksichtigen Sie ausschliesslich den Erfuellungsaufwand der Wirtschaft.
        Analysieren Sie nur wirtschaftsbezogene Prozesse, Fallgruppen, Taetigkeiten,
        Fallzahlen und Werte. Uebernehmen Sie keine Verwaltungslogik, Verwaltungswerte
        oder buergerbezogenen Inhalte, sofern diese nicht ausdruecklich als Spiegelwirkung
        oder wirtschaftsrelevante Folge der Vorgabe begruendet sind. Informationspflichten
        der Wirtschaft, Spiegelsituationen, interne Umstellungen, externe Dienstleistungen
        sowie wirtschaftsspezifische Pruef-, Melde-, Nachweis- und Dokumentationspflichten
        sind mitzudenken.
```

### Raw Response

```
{
  "prozesse": [
    {
      "prozess_id": "14",
      "prozess_bezeichnung": "Gemeinnuetzigkeitsantrag/Steuerbeguenstigungsnachweis fuer E-Sport-Koerperschaften unter Zweck 'Foerderung des Sports' (inkl. Anpassung von Satzung/Begruendung/Unterlagen)",
      "prozess_beschreibung": "Korporationen der Wirtschaft (z. B. E-Sport-Vereine, gGmbHs, Stiftungen) richten die Geltendmachung der Gemeinnuetzigkeit bzw. Steuerbeguenstigungen kuenftig rechtssicherer auf den Zweck 'Foerderung des Sports' aus, da E-Sport fuer § 52 Abs. 2 Nr. 21 AO ausdruecklich als Sport gilt. Im Rahmen der (Neu-)Beantragung bzw. laufenden Nachweisfuehrung/Begruendung gegenueber der Finanzverwaltung (z. B. Feststellung/Veranlagung/Freistellung) verlagert sich der Begruendungspfad weg von alternativen gemeinnuetzigen Zwecken (z. B. Jugendhilfe/Bildung/Kultur) hin zur unmittelbaren Sportfoerderung; dadurch entfaellt in betroffenen Faellen der zusaetzliche Begruendungs- und Abgrenzungsaufwand ueber andere Zwecke und es kann interner Aufwand zur Umstellung der Standardtexte/Argumentation/Unterlagen anfallen.",
      "aenderungsstatus": "geaendert",
      "vorgaben": [
        {
          "vorgaben_id": "11",
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO",
          "beschreibung": "Klarstellung/Erweiterung des gemeinnützigen Zweckkatalogs zur „Förderung des Sports“: Für die Anwendung der Nr. 21 gilt künftig neben Schach auch E‑Sport ausdrücklich als Sport. Dadurch können Körperschaften mit satzungsmäßigem und tatsächlich ausgeübtem Zweck der E‑Sport-Förderung den gemeinnützigen Zweck „Förderung des Sports“ unmittelbar heranziehen (statt dies über andere Zwecke zu begründen).",
          "aenderungsstatus": "geaendert"
        },
        {
          "vorgaben_id": "12",
          "normzitat": "§ 52 Abs. 2 Nr. 21 AO (Klammerzusatz)",
          "beschreibung": "Implizite Umstellung des maßgeblichen Prüf- und Begründungswegs: Fälle, in denen E‑Sport-Förderung bisher nicht (oder nur unsicher) als „Sport“ behandelt wurde und daher auf alternative gemeinnützige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) ausweichen musste, unterliegen künftig vorrangig der (vereinfachten) Einordnung als Sportförderung. Dadurch entfällt in diesen Fällen der bisher notwendige zusätzliche Begründungs- bzw. Abgrenzungsaufwand über andere Zwecke als eigenständiger Prüfpfad.",
          "aenderungsstatus": "geaendert"
        }
      ],
      "fallgruppen": [
        {
          "fallgruppen_id": "25",
          "fallgruppe_bezeichnung": "Neuantrag/Erstanerkennung Gemeinnuetzigkeit fuer E-Sport-Koerperschaft unter Zweck 'Foerderung des Sports' (statt alternativer Zwecke)",
          "fallgruppe_beschreibung": "E-Sport-Koerperschaften, die erstmals die Gemeinnuetzigkeit/Steuerbeguenstigung beantragen, koennen den Antrag und die Begruendung unmittelbar auf 'Foerderung des Sports' stuetzen. Im Vergleich zur bisherigen (unsicheren) Praxis entfaellt typischerweise zusaetzlicher Begruendungs- und Abgrenzungsaufwand, der zuvor fuer die Herleitung ueber alternative gemeinnuetzige Zwecke (z. B. Jugendhilfe/Bildung/Kultur) sowie fuer entsprechende Satzungs- und Konzeptbegruendungen angefallen waere. Ggf. verbleibt ein einmaliger interner Aufwand zur Erstellung/Anpassung von Standardtexten, Satzungsbausteinen und Nachweisunterlagen auf den Sportzweck mit E-Sport-Bezug.",
          "aenderungsstatus": "geaendert",
          "taetigkeiten": [
            {
              "taetigkeiten_id": "101",
              "taetigkeit": "Begruendungs- und Nachweiskonzept von alternativen Zwecken auf 'Foerderung des Sports (inkl. E-Sport)' umstellen",
              "beschreibung": "Im Neuantrag wird die Argumentationslinie/Begruendung so angepasst, dass E-Sport unmittelbar als Sportfoerderung dargestellt wird (statt Herleitung ueber Jugendhilfe/Bildung/Kultur). Dazu werden die beizufuegenden Kurzkonzepte, Taetigkeitsdarstellungen und Textbausteine entsprechend neu ausgerichtet.",
              "aenderungsstatus": "geaendert",
              "rollen_gueltig": [
                {
                  "rolle": "Sachbearbeitung/Antragserstellung (Verein/gGmbH)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "32,20",
                  "zeitaufwand_in_min": "60"
                },
                {
                  "rolle": "Leitung/Vorstand (Freigabe der Begruendungslinie)",
                  "lohngruppe": "C",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "51,00",
                  "zeitaufwand_in_min": "15"
                }
              ],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [
                {
                  "rolle": "Sachbearbeitung/Antragserstellung (Verein/gGmbH)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "32,20",
                  "zeitaufwand_in_min": "40"
                },
                {
                  "rolle": "Leitung/Vorstand (Freigabe der Begruendungslinie)",
                  "lohngruppe": "C",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "51,00",
                  "zeitaufwand_in_min": "10"
                }
              ],
              "sachaufwand_vorschlag": "0",
              "ausfuehrung_pro_einzelfall": "1"
            },
            {
              "taetigkeiten_id": "102",
              "taetigkeit": "Zusaetzlichen Abgrenzungs- und Darlegungsaufwand ueber alternative gemeinnuetzige Zwecke entfallen lassen",
              "beschreibung": "Soweit bisher (aus Rechtsunsicherheit) zusaetzliche Darlegungen/Abgrenzungen zu alternativen Zwecken erforderlich waren (z. B. gesonderte Bildungs-/Jugendhilfe-Begruendung, Doppelbegruendung, Plausibilisierung eines Alternativzwecks), wird dieser Begruendungspfad im Antrag nicht mehr erstellt bzw. nicht mehr in gleicher Tiefe ausgearbeitet.",
              "aenderungsstatus": "abgeschafft",
              "rollen_gueltig": [
                {
                  "rolle": "Sachbearbeitung/Antragserstellung (zusaetzlicher Alternativzweck-Teil)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "32,20",
                  "zeitaufwand_in_min": "45"
                }
              ],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [],
              "sachaufwand_vorschlag": "0",
              "ausfuehrung_pro_einzelfall": "1"
            },
            {
              "taetigkeiten_id": "103",
              "taetigkeit": "Satzungszweck/-bausteine und Anlagen fuer den Antrag auf Sportzweck mit E-Sport-Bezug zuschneiden",
              "beschreibung": "Erstellung/Anpassung von Satzungsformulierungen (Zweck/Verwirklichung) bzw. der einzureichenden Anlagen (z. B. Musterformulierungen, Taetigkeitsbeschreibungen) so, dass die Foerderung des Sports durch E-Sport inhaltlich konsistent dargestellt wird; dies umfasst auch interne Abstimmung und Finalisierung der Unterlagen.",
              "aenderungsstatus": "geaendert",
              "rollen_gueltig": [
                {
                  "rolle": "Sachbearbeitung/Unterlagenbearbeitung (Satzung/Anlagen)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "32,20",
                  "zeitaufwand_in_min": "90"
                },
                {
                  "rolle": "Leitung/Vorstand (Satzungs-/Unterlagenfreigabe)",
                  "lohngruppe": "C",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "51,00",
                  "zeitaufwand_in_min": "20"
                }
              ],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [
                {
                  "rolle": "Sachbearbeitung/Unterlagenbearbeitung (Satzung/Anlagen)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "32,20",
                  "zeitaufwand_in_min": "75"
                },
                {
                  "rolle": "Leitung/Vorstand (Satzungs-/Unterlagenfreigabe)",
                  "lohngruppe": "C",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "51,00",
                  "zeitaufwand_in_min": "15"
                }
              ],
              "sachaufwand_vorschlag": "0",
              "ausfuehrung_pro_einzelfall": "1"
            },
            {
              "taetigkeiten_id": "104",
              "taetigkeit": "Antragsunterlagen finalisieren und einreichen (inkl. Dokumentation/Ablage der geaenderten Begruendung)",
              "beschreibung": "Zusammenstellung der finalen Unterlagen und Einreichung in der ueblichen Form; die Taetigkeit bleibt als Standardvorgang bestehen, wird aber inhaltlich durch die geaenderte Rechtsgrundlage (Sport inkl. E-Sport) mitangepasst (Versionierung/Ablage der neuen Textstaende).",
              "aenderungsstatus": "geaendert",
              "rollen_gueltig": [
                {
                  "rolle": "Sachbearbeitung (Finalisierung/Einreichung/Ablage)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "einfach",
                  "stundenlohn": "32,20",
                  "zeitaufwand_in_min": "20"
                }
              ],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [
                {
                  "rolle": "Sachbearbeitung (Finalisierung/Einreichung/Ablage)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "einfach",
                  "stundenlohn": "32,20",
                  "zeitaufwand_in_min": "20"
                }
              ],
              "sachaufwand_vorschlag": "0",
              "ausfuehrung_pro_einzelfall": "1"
            }
          ]
        },
        {
          "fallgruppen_id": "26",
          "fallgruppe_bezeichnung": "Bestandskoerperschaft: Umstellung/Anpassung Satzung, Zweckformulierung und Nachweisfuehrung auf 'Sport (inkl. E-Sport)'",
          "fallgruppe_beschreibung": "Bereits bestehende E-Sport-Koerperschaften mit laufender Gemeinnuetzigkeitsfuehrung (z. B. gueltiger Freistellungsbescheid bzw. turnusmaessige Nachweis- und Erklaerungsprozesse), die bisher (aus Rechtsunsicherheit) teilweise ueber alternative Zwecke argumentiert oder Mischbegruendungen genutzt haben, stellen ihre Standardargumentation, Unterlagen und ggf. die Satzungszweckbeschreibung auf 'Foerderung des Sports' um. Dies kann einen einmaligen internen Abstimmungs- und Dokumentationsaufwand (inkl. ggf. externer Beratung/Steuerberatung) ausloesen; zugleich reduziert sich kuenftig der wiederkehrende Begruendungs- und Abgrenzungsaufwand, weil der zusaetzliche alternative Begruendungspfad entfaellt.",
          "aenderungsstatus": "geaendert",
          "taetigkeiten": [
            {
              "taetigkeiten_id": "105",
              "taetigkeit": "Interne Analyse/Entscheidung zur Umstellung der Gemeinnuetzigkeitsbegruendung auf 'Sport (inkl. E-Sport)'",
              "beschreibung": "Pruefung der bisherigen Begruendung (Alternativzwecke/Mischbegruendung) und Festlegung, kuenftig vorrangig/allein auf Nr. 21 (Sport inkl. E-Sport) abzustellen; inkl. Abstimmung im Vorstand/Management und Festlegung der notwendigen Anpassungen an Dokumentenstandards.",
              "aenderungsstatus": "eingefuehrt",
              "rollen_gueltig": [],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [
                {
                  "rolle": "Leitung/Vorstand (Entscheidung/Abstimmung)",
                  "lohngruppe": "C",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "51,00",
                  "zeitaufwand_in_min": "30"
                },
                {
                  "rolle": "Sachbearbeitung (Zuarbeit/Analyse Unterlagenstand)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "32,20",
                  "zeitaufwand_in_min": "30"
                }
              ],
              "sachaufwand_vorschlag": "0",
              "ausfuehrung_pro_einzelfall": "0"
            },
            {
              "taetigkeiten_id": "106",
              "taetigkeit": "Satzung und Standardunterlagen (Textbausteine, Taetigkeitsdarstellung, Nachweislogik) anpassen und versionieren",
              "beschreibung": "Einmalige Ueberarbeitung von Satzungszweck/Verwirklichung (soweit erforderlich) sowie der wiederverwendeten Begruendungstexte und Nachweisunterlagen, sodass die Sportfoerderung durch E-Sport konsistent und rechtssicher dargestellt ist; inkl. Dokumentation/Ablage der geaenderten Versionen.",
              "aenderungsstatus": "geaendert",
              "rollen_gueltig": [
                {
                  "rolle": "Sachbearbeitung (Pflege von Alternativzweck-/Mischbegruendung in Standardunterlagen)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "32,20",
                  "zeitaufwand_in_min": "60"
                },
                {
                  "rolle": "Leitung/Vorstand (Freigabe Standardunterlagen)",
                  "lohngruppe": "C",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "51,00",
                  "zeitaufwand_in_min": "15"
                }
              ],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [
                {
                  "rolle": "Sachbearbeitung (Ueberarbeitung/Versionierung auf Sport inkl. E-Sport)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "32,20",
                  "zeitaufwand_in_min": "90"
                },
                {
                  "rolle": "Leitung/Vorstand (Freigabe Standardunterlagen)",
                  "lohngruppe": "C",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "51,00",
                  "zeitaufwand_in_min": "20"
                }
              ],
              "sachaufwand_vorschlag": "0",
              "ausfuehrung_pro_einzelfall": "0"
            },
            {
              "taetigkeiten_id": "107",
              "taetigkeit": "Wiederkehrenden zusaetzlichen Begruendungs- und Abgrenzungsteil ueber Alternativzwecke kuerzen/streichen",
              "beschreibung": "In der laufenden Nachweisfuehrung gegenueber der Finanzverwaltung (z. B. im Rahmen turnusmaessiger Unterlagenzusammenstellung) entfaellt bzw. reduziert sich der bisherige Zusatzaufwand, der allein daraus resultierte, E-Sport ueber andere Zwecke mit zu begruenden oder abzugrenzen.",
              "aenderungsstatus": "abgeschafft",
              "rollen_gueltig": [
                {
                  "rolle": "Sachbearbeitung (wiederkehrender Alternativzweck-Zusatzteil je Nachweiszyklus)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "32,20",
                  "zeitaufwand_in_min": "30"
                }
              ],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [],
              "sachaufwand_vorschlag": "0",
              "ausfuehrung_pro_einzelfall": "1"
            },
            {
              "taetigkeiten_id": "108",
              "taetigkeit": "Ggf. externe Unterstuetzung (z. B. Steuerberatung) fuer Umstellung/Pruefung der Unterlagen einholen",
              "beschreibung": "Soweit ueblich oder risikoorientiert veranlasst: Einholung/Verwertung externer Beratung zur Anpassung der Satzung/Begruendung und zur Minimierung von Anerkennungsrisiken; diese Taetigkeit entsteht typischerweise einmalig im Zuge der Umstellung.",
              "aenderungsstatus": "eingefuehrt",
              "rollen_gueltig": [],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [
                {
                  "rolle": "Sachbearbeitung (Beschaffung/Abstimmung mit externer Steuerberatung)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "32,20",
                  "zeitaufwand_in_min": "60"
                }
              ],
              "sachaufwand_vorschlag": "250",
              "ausfuehrung_pro_einzelfall": "0"
            }
          ]
        },
        {
          "fallgruppen_id": "27",
          "fallgruppe_bezeichnung": "Bestandskoerperschaft: Keine materielle Umstellung erforderlich (E-Sport bereits als Sport behandelt/abgebildet)",
          "fallgruppe_beschreibung": "E-Sport-Koerperschaften, die bereits vor der Klarstellung ihre Gemeinnuetzigkeit unter 'Foerderung des Sports' (oder in der praktischen Umsetzung gleichwertig) begruendet und dokumentiert haben, muessen keine oder nur minimale Anpassungen vornehmen (z. B. Aktualisierung von Textbausteinen/Verweisen). Der wesentliche Effekt liegt in reduzierter Rechtsunsicherheit ohne nennenswerten zusaetzlichen internen Zeit- oder Sachaufwand.",
          "aenderungsstatus": "geaendert",
          "taetigkeiten": [
            {
              "taetigkeiten_id": "109",
              "taetigkeit": "Minimale Aktualisierung von Standardtexten/Verweisen auf die Klarstellung 'E-Sport gilt als Sport'",
              "beschreibung": "Soweit genutzt: kurze Anpassung bestehender Textbausteine (z. B. in Anschreiben, Begruendungspapieren, internen FAQs) bzw. Ergaenzung eines Verweises auf die explizite Einordnung von E-Sport als Sport; ohne inhaltliche Umstellung der uebrigen Nachweisfuehrung.",
              "aenderungsstatus": "geaendert",
              "rollen_gueltig": [
                {
                  "rolle": "Sachbearbeitung (Textbausteinpflege)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "einfach",
                  "stundenlohn": "32,20",
                  "zeitaufwand_in_min": "5"
                }
              ],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [
                {
                  "rolle": "Sachbearbeitung (Textbausteinpflege)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "einfach",
                  "stundenlohn": "32,20",
                  "zeitaufwand_in_min": "5"
                }
              ],
              "sachaufwand_vorschlag": "0",
              "ausfuehrung_pro_einzelfall": "1"
            },
            {
              "taetigkeiten_id": "110",
              "taetigkeit": "Zusaetzliche Vorsorge-/Alternativbegruendungen (Backup-Zwecke) nicht mehr vorhalten",
              "beschreibung": "Soweit bislang aus Vorsicht parallel Alternativzwecke oder Ersatzargumentationen dokumentiert/mitgefuehrt wurden, koennen diese kuenftig entfallen (z. B. keine fortlaufende Pflege von Doppelbegruendungen).",
              "aenderungsstatus": "abgeschafft",
              "rollen_gueltig": [
                {
                  "rolle": "Sachbearbeitung (Pflege Backup-Begruendung)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "einfach",
                  "stundenlohn": "32,20",
                  "zeitaufwand_in_min": "10"
                }
              ],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [],
              "sachaufwand_vorschlag": "0",
              "ausfuehrung_pro_einzelfall": "1"
            },
            {
              "taetigkeiten_id": "111",
              "taetigkeit": "Laufende Nachweisfuehrung unter Sportzweck fortsetzen (nur geringfuegig beruehrt)",
              "beschreibung": "Die regulaeren, ohnehin bestehenden Schritte zur Nachweisfuehrung/Unterlagenbereitstellung bleiben im Kern gleich; sie werden lediglich um die rechtssichere Einordnung ergaenzt, ohne dass ein zusaetzlicher Aufwand entsteht.",
              "aenderungsstatus": "unveraendert",
              "rollen_gueltig": [
                {
                  "rolle": "Sachbearbeitung (laufende Nachweisfuehrung)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "32,20",
                  "zeitaufwand_in_min": "60"
                }
              ],
              "sachaufwand_gueltig": "0",
              "rollen_vorschlag": [
                {
                  "rolle": "Sachbearbeitung (laufende Nachweisfuehrung)",
                  "lohngruppe": "B",
                  "schwierigkeitsgrad": "mittel",
                  "stundenlohn": "32,20",
                  "zeitaufwand_in_min": "60"
                }
              ],
              "sachaufwand_vorschlag": "0",
              "ausfuehrung_pro_einzelfall": "1"
            }
          ]
        }
      ]
    }
  ]
}
```

---

## Step 15 — `cases_calculation` (fallback)
- model: `gpt-5.2` | provider: `openai` | attempt: `d57aa77e9e2249539a3d89a633698e64` | elapsed: - ms
- fallback_kind: `cases_legacy_key_alias`

---

## Step 16 — `effort_calculation` (fallback)
- model: `gpt-5.2` | provider: `openai` | attempt: `7add13f416c644b6a7ed66411aa8665f` | elapsed: - ms
- fallback_kind: `effort_legacy_key_alias`
