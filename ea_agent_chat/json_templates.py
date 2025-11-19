sources_template = """
    [
        {
            "Name": "<>",
            "exakte URL": "<>",
            "direktes Zitat": "<>",
            "abgerufen am": "<>"
        }
    ]
"""

sources_verification_template = """
    [
        {
            "Name": "<>",
            "exakte URL": "<>",
            "direktes Zitat": "<>",
            "Validierung exakte URL": "<>",
            "Validierung direktes Zitat": "<>",
            "überprüft am": "<>"
        }
    ]
"""

json_ea_yearly = f"""
    [
        {{
            "Prozessschritt": "<>",
            "Anwendungsfall": "<>",
            "durchgeführt von": "<>",
            "Anzahl Einzelfälle pro Jahr": "<>",
            "Kosten in EUR pro Einzelfall": "<>",
            "Zeitaufwand in Min. pro Einzelfall": "<>",
            "Details zur Einzelfallberechnung": "<>",
            "Details zur Kostenberechnung": "<>",
            "Details zur Zeitberechnung": "<>",
            "Gesetzesgrundlagen für diesen Prozessschritt": ["<>", "<>"],
            "Quellen": {sources_template}
        }}
    ]
"""
