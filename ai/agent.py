"""Stateloze Gemini-agent. Publieke interface: chat_with_agent(message, history, minors)."""

import json
import logging
import os
from typing import TypedDict

from google import genai
from google.genai import types

from .prompts import SYSTEM_PROMPT, output_schema
from .validation import ValidationError, normalize_minors, validate_recommendations

logger = logging.getLogger(__name__)
DISCLOSURE = "Je praat met een AI-minoradviseur."
MAX_FOLLOW_UPS = 3
QUESTIONS = {
    "study": "Welke opleiding of studierichting volg je?",
    "interests": "Wat lijkt je interessant: bijvoorbeeld technologie, ondernemen, mensen helpen of creatief werken?",
    "preferences": "Heb je voorkeuren voor locatie, taal of type opdrachten? Geen voorkeur is ook prima.",
}
REFERRAL = "Ik kan met deze informatie en de aangeleverde minoren geen betrouwbaar passend advies geven. Bespreek je mogelijkheden met een studieadviseur."


class AgentResult(TypedDict):
    response: str
    recommended_minor_ids: list[str]
    needs_more_info: bool


def _result(text: str, ids: list[str] | None = None, needs_more_info: bool = False) -> AgentResult:
    return {
        "response": f"{DISCLOSURE}\n\n{text}",
        "recommended_minor_ids": ids or [],
        "needs_more_info": needs_more_info,
    }


def _history(history: object) -> list[dict[str, str]]:
    if not isinstance(history, list) or len(history) > 40:
        raise ValidationError("History moet een lijst van maximaal 40 berichten zijn.")
    clean = []
    for turn in history:
        if not isinstance(turn, dict) or turn.get("role") not in ("user", "assistant", "model"):
            raise ValidationError("History heeft een ongeldige rol.")
        content = turn.get("content")
        if not isinstance(content, str) or not content.strip() or len(content) > 8000:
            raise ValidationError("History heeft ongeldige berichttekst.")
        clean.append({"role": "assistant" if turn["role"] == "model" else turn["role"], "content": content})
    return clean


def chat_with_agent(message: str, history: list[dict], minors: object) -> AgentResult:
    """Geef altijd response, recommended_minor_ids en needs_more_info terug.

    History bevat eerdere {role: user/assistant, content: tekst}-berichten,
    exclusief het huidige bericht. Geen globale gespreksopslag of Streamlit.
    De caller beheert de omgeving en geschiedenis. Zie README voor normalisatie.
    """
    try:
        if not isinstance(message, str) or len(message) > 8000:
            raise ValidationError("Message moet tekst van maximaal 8000 tekens zijn.")
        turns = _history(history)
        dataset = normalize_minors(minors)
    except (ValidationError, RecursionError):
        logger.warning("minor_agent: invalid_input")
        return _result("De berichtinvoer of minorendataset is ongeldig. Laat je team het invoerformaat controleren. Voor inhoudelijk advies kun je terecht bij een studieadviseur.")

    if not dataset:
        return _result("Er zijn geen minoren aangeleverd om te vergelijken. Vraag je studieadviseur om hulp bij het zoeken.")
    if not message.strip():
        return _result("Spreek of typ eerst je vraag of antwoord.", needs_more_info=True)

    api_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        return _result("De AI is nog niet ingesteld: GEMINI_API_KEY ontbreekt. Laat je team de omgevingsvariabele instellen. Je kunt ook een studieadviseur raadplegen.")

    payload = json.dumps({"message": message, "history": turns, "minors": dataset}, ensure_ascii=False)
    # Alleen deze grens vangt SDK-/netwerkfouten af. Log nooit exceptiontekst,
    # API-keys, prompts, brondata of gesprekken; ook geen stacktrace.
    try:
        with genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=30_000)) as client:
            completion = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "").strip() or "gemini-flash-latest",
                contents=payload,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_json_schema=output_schema([minor["id"] for minor in dataset]),
                    temperature=0.2,
                    max_output_tokens=4096,
                ),
            )
            raw_output = completion.text
    except Exception:
        logger.warning("minor_agent: api_error")
        return _result("De AI-dienst is tijdelijk niet bereikbaar. Probeer het later opnieuw of bespreek je vraag met een studieadviseur.")

    try:
        output = json.loads(raw_output)
        validate_recommendations(output, dataset, [message] + [turn["content"] for turn in turns if turn["role"] == "user"])
    except (ValueError, TypeError, RecursionError):
        logger.warning("minor_agent: invalid_model_output")
        return _result("Ik kon het AI-antwoord niet betrouwbaar controleren. Probeer het opnieuw of vraag een studieadviseur om hulp.")

    if output["action"] == "ask":
        question = QUESTIONS[output["question_topic"]]
        assistant_turns = [turn["content"] for turn in turns if turn["role"] == "assistant"]
        if len(assistant_turns) >= MAX_FOLLOW_UPS or any(question in turn for turn in assistant_turns):
            return _result(REFERRAL)
        return _result(question, needs_more_info=True)
    if output["action"] == "refer":
        return _result(REFERRAL)

    by_id = {minor["id"]: minor for minor in dataset}
    lines = ["Op basis van jouw antwoorden passen deze minoren mogelijk bij je:"]
    ids = []
    for number, recommendation in enumerate(output["recommendations"], 1):
        minor = by_id[recommendation["minor_id"]]
        ids.append(minor["id"])
        lines.append(
            f'{number}. {minor["title"]} ({minor["institution"]}). '
            f'De aansluiting bij jouw antwoord “{recommendation["student_quote"]}” '
            f'zie ik in deze minorbeschrijving: “{recommendation["description_quote"]}”. '
            f'Meer informatie: {minor["url"]}'
        )
    lines.append("Dit is oriënterend advies. Controleer toelatingseisen, kosten en actuele beschikbaarheid bij de aanbieder; vraag bij twijfel een studieadviseur.")
    return _result("\n\n".join(lines), ids)
