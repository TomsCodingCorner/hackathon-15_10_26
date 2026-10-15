"""Stateloze Gemini-agent met gedeelde validatie en injecteerbare provider."""

import json
import logging
from dataclasses import dataclass
from time import perf_counter
from typing import TypedDict

# Zelfde moduleobject als de provider; bestaande callers/testpatches blijven werken.
from google import genai

from .prompts import SYSTEM_PROMPT, output_schema
from .validation import ValidationError, normalize_minors, validate_recommendations
from .providers import ERROR_MESSAGES, Provider, ProviderError
from .providers.gemini_provider import GeminiProvider

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


@dataclass
class AgentRun:
    result: AgentResult
    raw_output: str | None = None
    validated_output: dict | None = None
    error: str | None = None
    model_called: bool = False
    model_succeeded: bool = False
    model_ms: float = 0


def chat_with_agent(message: str, history: list[dict], minors: object, *, provider: Provider | None = None) -> AgentResult:
    """Bestaand uitvoercontract; standaard Gemini uit de omgeving.

    De app gebruikt de centrale Settings en injecteert een GeminiProvider.
    provider= blijft beschikbaar voor geïsoleerde tests en eerdere callers.
    """
    return analyze_chat(message, history, minors, provider=provider).result


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


def analyze_chat(message: str, history: list[dict], minors: object, *, provider: Provider | None = None) -> AgentRun:
    """Geef gecontroleerde uitvoer met tijdelijke technische diagnostiek terug.

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
        return AgentRun(_result("De berichtinvoer of minorendataset is ongeldig. Laat je team het invoerformaat controleren. Voor inhoudelijk advies kun je terecht bij een studieadviseur."), error="invalid_input")

    if not dataset:
        return AgentRun(_result("Er zijn geen minoren aangeleverd om te vergelijken. Vraag je studieadviseur om hulp bij het zoeken."), error="empty_dataset")
    if not message.strip():
        return AgentRun(_result("Spreek of typ eerst je vraag of antwoord.", needs_more_info=True))

    if provider is None:
        try:
            provider = GeminiProvider()
        except ProviderError as exc:
            code = str(exc) if str(exc) in ERROR_MESSAGES else "api_error"
            return AgentRun(_result(ERROR_MESSAGES[code] + " Vraag eventueel een studieadviseur om hulp."), error=code)

    payload = json.dumps({"message": message, "history": turns, "minors": dataset}, ensure_ascii=False)
    # Alleen deze grens vangt SDK-/netwerkfouten af. Log nooit exceptiontekst,
    # API-keys, prompts, brondata of gesprekken; ook geen stacktrace.
    started = perf_counter()
    try:
        raw_output = provider.generate(payload, output_schema([minor["id"] for minor in dataset]), SYSTEM_PROMPT)
    except Exception as exc:
        logger.warning("minor_agent: api_error")
        code = str(exc) if isinstance(exc, ProviderError) and str(exc) in ERROR_MESSAGES else "api_error"
        failure = ERROR_MESSAGES[code] + " Je kunt ook een studieadviseur raadplegen."
        return AgentRun(_result(failure), error=code, model_called=True, model_ms=(perf_counter() - started) * 1000)

    run = AgentRun(_result(""), raw_output=raw_output if isinstance(raw_output, str) else None,
                   model_called=True, model_succeeded=True, model_ms=(perf_counter() - started) * 1000)

    try:
        output = json.loads(raw_output)
        validate_recommendations(output, dataset, [message] + [turn["content"] for turn in turns if turn["role"] == "user"])
    except (ValueError, TypeError, RecursionError):
        logger.warning("minor_agent: invalid_model_output")
        run.result = _result("Ik kon het AI-antwoord niet betrouwbaar controleren. Probeer het opnieuw of vraag een studieadviseur om hulp.")
        run.error = "invalid_model_output"
        return run

    run.validated_output = output
    run.result = _render(output, dataset, turns)
    return run


def _render(output: dict, dataset: list[dict], turns: list[dict]) -> AgentResult:

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
