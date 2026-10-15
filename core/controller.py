"""Gespreksorkestratie: Gemini voor AI, lokale STT/TTS en bronvalidatie."""

from dataclasses import asdict, dataclass, field
from time import perf_counter
from typing import Callable

from ai.agent import AgentResult, AgentRun, DISCLOSURE, _history, analyze_chat
from ai.providers import ERROR_MESSAGES, Provider, ProviderError
from ai.providers.gemini_provider import GeminiProvider
from ai.search import rank_minors
from ai.validation import ValidationError, normalize_minors
from config import EMPTY_DATA_MESSAGE, Settings
from speech.stt import transcribe, validate_wav
from speech.tts import synthesize

STEP_NAMES = ("STT", "Controller", "Retrieval", "LLM", "Validation", "TTS", "Audio output")


@dataclass
class Step:
    name: str
    status: str = "NOT_TESTED"
    detail: str = "Nog niet uitgevoerd."
    elapsed_ms: float = 0


@dataclass
class TurnResult:
    message: str = ""
    result: AgentResult = field(default_factory=lambda: {
        "response": DISCLOSURE, "recommended_minor_ids": [], "needs_more_info": False,
    })
    cards: list[dict] = field(default_factory=list)
    steps: list[Step] = field(default_factory=lambda: [Step(name) for name in STEP_NAMES])
    agent_run: AgentRun | None = None
    audio: bytes | None = None

    def step(self, name: str, status: str, detail: str, elapsed_ms: float = 0) -> None:
        self.steps[STEP_NAMES.index(name)] = Step(name, status, detail, elapsed_ms)

    def table(self) -> list[dict]:
        return [asdict(step) for step in self.steps]


def run_turn(message: str, history: list[dict], minors: object, settings: Settings, *,
             audio: bytes | None = None, speak: bool = False, provider: Provider | None = None,
             stt: Callable | None = None, tts: Callable | None = None) -> TurnResult:
    """Geen mutatie of opslag van historie; UI beheert uitsluitend sessiegeheugen."""
    turn = TurnResult()
    if audio is not None:
        started = perf_counter()
        try:
            message = (stt or transcribe)(audio, settings.whisper_path,
                                         max_seconds=settings.max_audio_seconds, max_bytes=settings.max_audio_bytes)
            turn.step("STT", "PASS", "Nederlandse transcriptie uitgevoerd.", (perf_counter() - started) * 1000)
        except Exception:
            turn.step("STT", "FAIL", "Transcriptie mislukt. Controleer het model en gebruik een geldige WAV-opname van maximaal 60 seconden.")
            turn.result["response"] = DISCLOSURE + "\n\nSpraakherkenning is niet beschikbaar. Je kunt je bericht typen. Controleer Speech-to-Text in Diagnostics."
            return turn
    turn.message = message
    try:
        if not isinstance(message, str) or not message.strip() or len(message) > 8000:
            raise ValidationError("invalid_message")
        turns = _history(history)
        dataset = normalize_minors(minors)
    except (ValidationError, RecursionError):
        turn.step("Controller", "FAIL", "Ongeldige tekst, historie of dataset.")
        turn.result["response"] = DISCLOSURE + "\n\nDe invoer of dataset is ongeldig. Start een nieuw gesprek of controleer de dataset."
        return turn
    turn.step("Controller", "PASS", "Invoer gecontroleerd; historie ongewijzigd doorgegeven.")
    if not dataset:
        turn.step("Retrieval", "BLOCKED", EMPTY_DATA_MESSAGE)
        turn.result["response"] = DISCLOSURE + "\n\n" + EMPTY_DATA_MESSAGE + " Vraag bij twijfel een studieadviseur om hulp."
        return turn
    candidates = rank_minors(message, turns, dataset, settings.retrieval_limit)
    turn.step("Retrieval", "PASS", f"{len(candidates)} kandidaatminoren gerangschikt uit {len(dataset)} bronrecords.")
    try:
        selected_provider = provider if provider is not None else GeminiProvider(settings.gemini_api_key, settings.gemini_model, settings.model_timeout)
        run = analyze_chat(message, turns, candidates, provider=selected_provider)
    except ProviderError as exc:
        code = str(exc) if str(exc) in ERROR_MESSAGES else "invalid_provider_config"
        turn.step("LLM", "BLOCKED", ERROR_MESSAGES[code])
        turn.result["response"] = DISCLOSURE + "\n\n" + ERROR_MESSAGES[code] + " Je kunt ook een studieadviseur raadplegen."
        return turn
    except Exception:
        turn.step("LLM", "FAIL", "Gemini-configuratie ongeldig.")
        turn.result["response"] = DISCLOSURE + "\n\nControleer de Gemini-configuratie in Diagnostics."
        return turn
    turn.agent_run, turn.result = run, run.result
    if not run.model_succeeded:
        blocked = run.error in {"missing_api_key", "missing_model", "gemini_auth_error", "gemini_model_not_found",
                                "gemini_rate_limited", "gemini_unavailable", "gemini_unreachable"}
        turn.step("LLM", "BLOCKED" if blocked or not run.model_called else "FAIL", ERROR_MESSAGES.get(run.error, "Geen modelaanroep uitgevoerd."), run.model_ms)
        return turn
    turn.step("LLM", "PASS", "Modelaanroep gaf een antwoord; standaardprovider is Google Gemini.", run.model_ms)
    if run.error or run.validated_output is None:
        turn.step("Validation", "FAIL", "Modeloutput afgewezen; geen aanbevelingen of TTS uitgevoerd.")
        return turn
    turn.step("Validation", "PASS", "JSON, ID's en bronfragmenten gevalideerd.")
    by_id = {minor["id"]: minor for minor in candidates}
    for recommendation in run.validated_output["recommendations"]:
        minor = by_id[recommendation["minor_id"]]
        turn.cards.append({**minor, "motivation": f'Jouw antwoord: “{recommendation["student_quote"]}”. Inhoud: “{recommendation["description_quote"]}”.'})
    if speak:
        started = perf_counter()
        try:
            turn.audio = (tts or synthesize)(turn.result["response"], settings.piper_path)
            validate_wav(turn.audio, max_seconds=300, max_bytes=20_000_000)
            turn.step("TTS", "PASS", "Gevalideerd antwoord lokaal gesynthetiseerd.", (perf_counter() - started) * 1000)
            turn.step("Audio output", "PASS", "Geldige WAV gereed om af te spelen; hoorbaarheid handmatig beoordelen.")
        except Exception:
            turn.audio = None
            turn.step("TTS", "FAIL", "Piper kon geen geldige audio genereren. Het tekstantwoord blijft beschikbaar.")
    return turn
