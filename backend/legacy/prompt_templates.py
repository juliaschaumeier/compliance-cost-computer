from backend.legacy import json_templates


# ---------- Prompt Templates ----------
# Make sure the prompts only ask the model to
# return content for one single file type !!


class PromptTemplate:
    def __init__(self, name, text, task_type, json_template_name=None, regelung_kurzform=None,
                 expected_answer_file_type=None):
        self.name = name
        self.text = text
        self.task_type = task_type
        self.json_template_name = json_template_name
        self.regelung_kurzform = regelung_kurzform.lower().replace(' ', '_') if regelung_kurzform else None
        self.expected_answer_file_type = expected_answer_file_type


class Instructions(PromptTemplate):
    def __init__(self):
        text = """
Sie sind ein Mitarbeiter der Finanzverwaltung der Bundesrepublik Deutschland. Sie sind ein Experte darin, den 
Erfüllungsaufwand bestimmter Gesetze auf Seiten der Bürger, der Verwaltung und der Wirtschaft abzuschätzen. Hierzu 
geben Sie Auskunft über Fallzahlen, Arbeitsaufwände und Gehaltspauschalen, die an Ihrer Behörde anfallen und helfen, 
den entsprechenden Aufwand für den einzelnen Bürger und/oder das Unternehmen abzuschätzen.
Ihre Antworten geben Sie in dem Format aus, das in der jeweiligen Aufgabe spezifiziert ist. Halten Sie sich strikt 
daran und schließen Sie keine weiteren Informationen oder Decorators ein. 
Seien Sie beim Sammeln von Informationen GRÜNDLICH und überprüfen Sie sie mit Hilfe einer Websuche anhand von QUELLEN 
aus dem Internet, welche Sie mit den entsprechenden direkten Textausschnitten/Zitaten belegen. Stellen Sie sicher, dass 
Sie einen Gesamtüberblick über das Thema und alle Aufgaben haben, bevor Sie antworten.
"""
        super().__init__(name='instructions', text=text, task_type=None)

class JaehrlicherErfuellungsaufwand(PromptTemplate):
    def __init__(self, regelung_kurzform, regelung_text):
        text ="""
Analysieren Sie den jährlichen Erfüllungsaufwand für {0} aus Sicht der Verwaltung anhand der folgenden vier Fragen:
1)  Welche verschiedenen Anwendungsfälle gibt es?
2)  In welche Arbeitsschritte ist der Prozess für jeden Anwendungsfall aus 1) unterteilt, dem eine Behörde bei der 
    Überprüfung dieser Regelung folgt? 
3)  Welche einzelnen Arbeitsschritte aus 2) werden automatisch durchgeführt und welche (auch) manuell? 
4)  Mit welchem Mitarbeiteraufwand in welchen Gehaltsstufen geschieht die manuelle Bearbeitung aus 3)? Leiten Sie hierzu
    Kosten und Zeitaufwand pro Einzelfall ab. 
Als Zahlengrundlage orientieren Sie sich bitte an den derzeit gültigen Werten und verlässlichen Quellen aus dem Internet. 
Eine Beschreibung der Regelung ist im Folgenden zwischen den Tags <Regelung_Start> und <Regelung_Ende> eingeschlossen.
Bitte geben Sie Ihre Antwort in JSON-Syntax aus. Eine Vorlage um Ihre Antwort zu strukturieren finden Sie im Folgenden 
zwischen den Tags <JSON_Start> und <JSON_Ende>. Bitte halten Sie sich exakt an die vorgegebene Struktur und befüllen Sie 
so viele Listenelemente wie Sie brauchen (typischerweise: Anz. Anwendungsfall x Anz. Arbeitsschitte x (Anz. automatisch + 
Anz. manuell). Geben Sie für die Felder "Anzahl Einzelfälle pro Jahr", "Kosten in EUR pro Einzelfall" und  "Zeitaufwand 
in Min. pro Einzelfall" eine einzige Zahl (evtl. mit Kommastellen) an, weitere  Informationen können Sie in den Feldern 
"Details zur ...berechnung" einfügen, wie z.B. die Anteile der Gehaltsstufen.\n\n
<Regelung_Start>{1}<Regelung_Ende>\n\n
<JSON_Start>{2}<JSON_Ende>
""".format(regelung_kurzform, regelung_text, json_templates.json_ea_yearly)
        super().__init__(name='jaehrlicher_erfuellungsaufwand', text=text, task_type='reasoning',
                         json_template_name='json_ea_yearly', regelung_kurzform=regelung_kurzform,
                         expected_answer_file_type='json')


class VisualiseProcess(PromptTemplate):
    def __init__(self):
        text = """Stellen Sie alle Arbeitsschritte, die Sie in der vorherigen Aufgabe identifiziert haben, in Form 
eines Markdown Mermaid Diagramms dar. Achten Sie auf genügend Platz für die Beschriftung der einzelnen Schritte. Die 
derzeit gültige Syntax können Sie unter dieser URL einsehen: https://mermaid.js.org/syntax/flowchart.html#markdown-formatting 
Zu beachten sind Anführungszeichen um Beschriftungen und <br/> als Zeilenumbruch.
 """
        super().__init__(name='visualise_process', text=text, task_type='reasoning', json_template_name=None,
                         expected_answer_file_type='md')


class ChooseBestAnswerFromList(PromptTemplate):
    def __init__(self, answered_prompt, list_of_answers):
        tagged_answers = ""
        for i, answer in enumerate(list_of_answers):
            tagged_answers += f'<Antwort_{i + 1}_Start> ' + answer + f' <Antwort_{i + 1}_Ende>\n\n'
        text = """
Sie sollen bitte aus einer Reihe von Antworten auf eine einzige Frage die beste auswählen.
Die Frage, welche beantwortet wurde, ist durch die Tags <Aufgabe_Start> und <Aufgabe_Ende> markiert, die {0} Antworten, 
welche von LLMs generiert wurden, sie sind für alle i von 1 bis {0} mit den Tags <Antwort_i_Start> und '<Antwort_i_Ende> 
markiert. Nachdem Sie alle Antworten sorgfältig gelesen und verstanden haben, geben Sie die Antwort, die am besten zur
gestellten Aufgabe passt verbatim aus.\n\n
<Aufgabe_Start>{1}<Aufgabe_Ende>\n\n{2}
     """.format(len(list_of_answers), answered_prompt.text, tagged_answers)
        super().__init__(name='choose_best_answer_from_list', text=text, task_type='reasoning', json_template_name=None,
                         expected_answer_file_type=answered_prompt.expected_answer_file_type)


class VerifyWebSources(PromptTemplate):
    def __init__(self, list_of_sources):
        text = """
Sie bekommen eine Listen von Quellen aus dem Internet, die Sie bitte mit Hilfe einer Websuche auf Existenz und 
Richtigkeit überprüfen sollen.
Die Liste der Quellen ist in Anlehnung an das Folgende JSON-Format {} zwischen den Tags <Quellen_Start> und <Quellen_Ende> 
eingeschlossen. Überprüfen Sie jede einzelne Quelle auf
1)  Korrektheit der URL
2)  Korrektheit des direkten Zitats aus dieser Quelle
und geben Sie Ihre Antwort exakt in der folgenden JSON Struktur aus: {}.
<Quellen_Start>{}<Quellen_Ende>
""".format(json_templates.sources_template, json_templates.sources_verification_template, list_of_sources)
        super().__init__(name='verify_web_sources', text=text, task_type='verification',
                         json_template_name='sources_verification_template', expected_answer_file_type='json')


class TestPrompt(PromptTemplate):
    def __init__(self):
        text = """ Bitte beantworten Sie die folgende Frage: Was ist 2 + 2 + eine kleine zufällige Zahl? """
        super().__init__(name='test_prompt', text=text, task_type='verification', json_template_name=None,
                         expected_answer_file_type='txt')


class FollowUpTestPrompt(PromptTemplate):
    def __init__(self):
        text = """ Bitte addieren Sie zu Ihrer vorherigen Antwort noch 3 hinzu, plus eine kleine zufällige Zahl. """
        super().__init__(name='follow_up_test_prompt', text=text, task_type='verification', expected_answer_file_type='txt')


class WebTestInstructions(PromptTemplate):
    def __init__(self):
        text = """
You are an assistant that is able to search the web for information to answer user questions."""
        super().__init__(name='web_test_instructions', text=text, task_type=None)

class WebTestPrompt(PromptTemplate):
    def __init__(self):
        text = """ Use web search to answer the following question: What was a positive news story from today? Cite a specific link please."""
        super().__init__(name='web_test_prompt', text=text, task_type='verification', expected_answer_file_type='txt')
