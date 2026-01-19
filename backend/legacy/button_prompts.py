# Here are the prompts that get relayed on the press of a button. Check Andreas's domain_logic.py

import logging
logger = logging.getLogger("ea_agent")

from backend.legacy import api_helper
from backend.legacy import question_assembler

async def regulation_identification(uploaded_law):
    """
    This function determines a list of individual regulations affected by the 
    law (Vorgaben)
    
    :param uploaded_law: Description
    """
    logger.info("Starting to identify individual regulations affected by the law")

    prompt = f"""
    Du bist Legist im deutschen Bundestag und damit betraut, den Erfüllungsaufwand zu einer geplanten Gesetzesänderung 
    zu berechnen. 

    Folgende Gesetzesänderungen werden vorgenommen:  {uploaded_law}

    Deine Aufgabe ist, ausgehend, von den Gesetzesänderungen, alle darin enthaltenen Vorgaben (Einzelregelungen) im 
    nachfolgendem Sinne zu identifizieren. Jede Gesetzesänderung kann keine, eine oder mehrere Vorgaben enthalten. 
    Identifiziere alle für die Verwaltung zu beachtenden Vorgaben.

    Verwaltung sind alle die mit der Wahrnehmung von Verwaltungsaufgaben betrauten Verwaltungsträger (rechtsfähige 
    Körperschaften, Anstalten und Stiftungen des öffentlichen Rechts einschließlich Beliehene im Rahmen der ihnen 
    übertragenen hoheitlichen Kompetenzen). Soweit Körperschaften/Anstalten des öffentlichen Rechts privatwirtschaftlich 
    tätig sind und in Wettbewerb stehen (z. B. kostenpflichtige Schulungen der Kammern; Universitäten bei 
    Forschungsförderungen) sind diese als Wirtschaft zu behandeln. Soweit Unternehmen hoheitliche Aufgaben wahrnehmen 
    (z. B. Beliehene wie Prüfingenieure, Bezirksschornsteinfegermeister, Tierärzte bei Fleischbeschau), sind diese als 
    Verwaltung zu behandeln. Soweit öffentliche Unternehmen, die Aufgaben der Daseinsvorsorge im staatlichen Auftrag 
    erfüllen (z. B. Wasserkraftwerke in öffentlicher Hand) sind diese als Verwaltung zu behandeln. Die Rechtsform bietet 
    nur Anhaltspunkte; maßgeblich ist die vorgeschriebene Tätigkeit.

    Definition von Vorgaben:

    *   Vorgaben sind Einzelregelungen, die unmittelbar zu Änderungen von Kosten oder Zeitaufwand bei den Normadressaten 
        führen.
    *   Sie beruhen auf bundesrechtlichen Regelungen und verpflichten Normadressaten, bestimmte Ziele zu erreichen, 
        Vorgaben einzuhalten oder Handlungen vorzunehmen bzw. zu unterlassen.
    *   Dazu gehören auch Verpflichtungen zu Kooperation, Überwachung, Kontrolle sowie Informationspflichten (als 
        Teilmenge).

    Unmittelbarkeit bedeutet, dass der Kosten- oder Zeitaufwand direkt aus der Befolgung der Vorgabe entsteht. 
    Normadressaten müssen die Vorgaben einhalten, um Rechtsverstöße oder den Verlust von Ansprüchen zu vermeiden.

    Auch Regelungen, die nur Ziele, Grenzwerte oder förderbedingte Verhaltensänderungen vorgeben, gelten als Vorgaben, 
    wenn sie direkt Aufwand auslösen.

    Wichtig: Relevant sind nur Vorgaben, welche im Vergleich zur derzeitigen Rechtslage einen Mehraufwand bedeuten, 
    welcher zur Berechnung des Erfüllungsaufwand relevant ist!

    Gebe mir nur und ausschließlich einen JSON-String zurück, der zwingend wie folgt formatiert ist:

    {{
        "vorgaben": [
            {{
            "normzitat": "",
            "beschreibung": "",
            }},
            {{
            "normzitat": "",
            "beschreibung": "",
            }}
        ]
    }}

    Verwende keine ein- oder ausleitenden Texte und keine sonstigen Zeichen.  
    """

    logger.info("Querying LLM to identify individual regulations...")
    api_helper.API()
    raw_response = await question_assembler.Question(api, '', prompt)

    logger.info(f"Response received. Length: {len(raw_response)} characters")
    
    try:
        # Clean the response using the new helper function
        # cleaned_response = clean_json_string(raw_response)
        # parsed_response = json.loads(cleaned_response)
        # entries = parsed_response.get("entries", [])
        # print(f"Successfully parsed {len(entries)} amendment proposals")
        # return entries
        return api_helper.Response()
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Raw response: {raw_response}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse LLM response. The AI model returned an invalid JSON format. Please try again."
        )

    

    return
