"""Feitelijke readiness en testresultaten; imports zijn geen functiebewijs."""

import importlib.util
import json
import shutil
import sys
import tempfile
from time import perf_counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from ai.providers import ProviderError
from ai.providers.ollama_provider import OllamaProvider
from config import EMPTY_DATA_MESSAGE, Settings
from scraper.pipeline import load_minors, run_scrape
from speech import SpeechError
from speech.stt import whisper_files_present
from speech.tts import validate_voice

STATUSES = {"PASS", "FAIL", "BLOCKED", "NOT_TESTED"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Check:
    name: str
    status: str
    description: str
    detail: str = "Nog niet uitgevoerd."
    remedy: str = ""
    dependencies: str = ""
    mode: str = "readiness"
    checked_at: str = field(default_factory=now)

    def __post_init__(self):
        if self.status not in STATUSES:
            raise ValueError("Onbekende diagnostiekstatus.")


def package_present(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, AttributeError):
        return False


def dataset_check(settings: Settings) -> tuple[Check, list[dict]]:
    try:
        rows = load_minors(settings.dataset_path)
        if not rows:
            return Check("Dataset", "BLOCKED", "JSON-schema, velden, URL's en unieke ID's.", EMPTY_DATA_MESSAGE,
                         "Herstel de toegestane scraper; gebruik geen fictieve chatbotdata."), []
        return Check("Dataset", "PASS", "JSON-schema, velden, URL's en unieke ID's.",
                     f"{len(rows)} geldige unieke records gecontroleerd.", mode="file_validation"), rows
    except FileNotFoundError:
        return Check("Dataset", "BLOCKED", "Lokaal JSON-bestand.", "minors.json ontbreekt.", "Stel MINORS_PATH in of herstel de scraper."), []
    except (OSError, ValueError, RecursionError):
        return Check("Dataset", "FAIL", "Lokaal JSON-bestand.", "Dataset is ongeldig of niet leesbaar.", "Controleer verplichte velden, URL's, beschrijvingen en duplicaten."), []


def scrape_report(settings: Settings) -> dict:
    try:
        value = json.loads(settings.report_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("status") not in {"blocked", "failed", "partial", "success"}:
            raise ValueError
        return value
    except (OSError, ValueError, RecursionError):
        return {"status": "unknown", "errors": [{"code": "report_missing_or_invalid"}]}


def environment_checks(settings: Settings) -> list[Check]:
    checks = [Check("Python", "PASS" if sys.version_info >= (3, 10) else "FAIL", "Python >= 3.10.", sys.version.split()[0])]
    for package in ("streamlit", "requests", "bs4", "pydantic", "pytest", "faster_whisper", "piper"):
        present = package_present(package)
        checks.append(Check("Package: " + package, "PASS" if present else "BLOCKED", "Packagevindbaarheid, geen functieproef.",
                            "Gevonden." if present else "Ontbreekt.", "Installeer requirements.txt of de optionele requirements-speech.txt."))
    checks.append(Check("Ollama installatie", "PASS" if shutil.which("ollama") else "BLOCKED", "CLI op PATH.",
                        "Gevonden." if shutil.which("ollama") else "Niet gevonden; een reeds draaiende server kan wel bereikbaar zijn.", "Installeer Ollama voor Windows."))
    try:
        provider = OllamaProvider(settings.ollama_url, settings.ollama_model, timeout=3)
        models = provider.models()
        checks.append(Check("Ollama server", "PASS", "Lokale GET /api/tags.", "Server bereikbaar; dit is geen generatieproef."))
        available = settings.ollama_model in models
        checks.append(Check("Ollama model", "PASS" if available else "BLOCKED", "Model staat in /api/tags.",
                            settings.ollama_model + (" gevonden; generatie nog niet getest." if available else " ontbreekt."),
                            "Installeer het gekozen lokale model handmatig; downloads zijn niet automatisch."))
    except (ProviderError, ValueError):
        checks.append(Check("Ollama server", "BLOCKED", "Lokale GET /api/tags.", "Lokale server niet bereikbaar of configuratie ongeldig.", "Start ollama serve en controleer OLLAMA_URL."))
        checks.append(Check("Ollama model", "NOT_TESTED", "Modelinventaris.", "Servercontrole niet geslaagd.", dependencies="Ollama server"))
    checks.append(Check("Whisper modelbestanden", "PASS" if whisper_files_present(settings.whisper_path) else "BLOCKED",
                        "model.bin, config.json en tokenizer.json; geen laadproef.", str(settings.whisper_path), "Installeer het CTranslate2-model handmatig; zet WHISPER_MODEL_PATH."))
    try:
        validate_voice(settings.piper_path)
        voice_status, voice_detail = "PASS", "Modelbestand en Nederlandse configuratie gevonden; synthese nog niet getest."
    except (SpeechError, OSError):
        voice_status, voice_detail = "BLOCKED", "Nederlandse stem of bijbehorende .onnx.json ontbreekt/is ongeldig."
    checks.append(Check("Piper modelbestanden", voice_status, "Nederlandse stemconfiguratie, geen syntheseproef.", voice_detail,
                        "Installeer de stem en JSON naast elkaar; zet PIPER_MODEL_PATH."))
    checks.append(dataset_check(settings)[0])
    try:
        settings.runtime_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=settings.runtime_dir) as file:
            file.write(b"write-check")
            file.flush()
        checks.append(Check("Tijdelijke schrijfrechten", "PASS", "Werkelijke schrijfactie zonder gebruikersdata.", str(settings.runtime_dir)))
    except OSError:
        checks.append(Check("Tijdelijke schrijfrechten", "FAIL", "Tijdelijke schrijfactie.", "Niet schrijfbaar.", "Kies een schrijfbare RUNTIME_DIR."))
    return checks


COMPONENTS = [
    ("Scraper", "Bronophaling en productieparser.", "Toegestane productietoegang en echte parserfixtures regelen.", "Internet, bronbeleid"),
    ("Dataset", "Gevalideerde lokale minoren.", "Herstel de scraper/dataset.", "Scraper"),
    ("AI-provider", "Lokale gestructureerde modelgeneratie.", "Start Ollama en installeer het lokale model handmatig.", "Ollama, model"),
    ("AI-agent", "Gesprekscontext, prompt en aanbevelingen.", "Voer een lokale gesprekstest uit.", "AI-provider, Dataset"),
    ("Minor Search", "TF-IDF-kandidaten zonder AI-downloads.", "Voer retrieval uit met gevalideerde data.", "Dataset"),
    ("Outputvalidatie", "Bestaande ID's en letterlijke bronfragmenten.", "Voer een gecontroleerde AI-test uit.", "AI-provider, Dataset"),
    ("Speech-to-Text", "Werkelijke Nederlandse transcriptie.", "Installeer faster-whisper en het lokale model, neem audio op.", "Whisper, WAV-input"),
    ("Text-to-Speech", "Werkelijke Nederlandse Piper-synthese.", "Installeer Piper en een Nederlandse stem en voer synthese uit.", "Piper, stemmodel"),
    ("Controller", "Invoer en gespreksorkestratie.", "Voer een tekst- of audiobeurt uit.", "Invoer, Dataset"),
    ("Streamlit-interface", "UI-start en interactie.", "Beoordeel chat en diagnostiek handmatig; AppTest is afzonderlijk bewijs.", "Streamlit"),
    ("End-to-end", "Audio tot gecontroleerd antwoord en audio-uitvoer.", "Voer de audioketen uit; beoordeel de hoorbaarheid zelf.", "Alle ketenonderdelen"),
]


def component_checks(settings: Settings, evidence: dict | None = None) -> list[dict]:
    evidence = evidence or {}
    report = scrape_report(settings)
    data, _ = dataset_check(settings)
    result = []
    for name, description, remedy, dependencies in COMPONENTS:
        check = Check(name, "NOT_TESTED", description, remedy=remedy, dependencies=dependencies, mode="functional")
        if name == "Scraper":
            check.status = "BLOCKED"  # De huidige productieparser is expliciet onvoltooid.
            check.detail = f'Productieparser onvoltooid. Laatste opgeslagen run: {report.get("status")}, {report.get("scraped_at", "onbekend")}. Geen live controle.'
            check.mode = "historical"
        elif name == "Dataset":
            check = data
        if name in evidence:
            observed = evidence[name]
            check.status = observed["status"]
            check.detail = observed["detail"]
            check.mode = observed.get("mode", "live_local")
            check.checked_at = observed["checked_at"]
        result.append(asdict(check))
    return result


def record_turn(evidence: dict, turn, mode: str = "live_local") -> None:
    mapping = {"STT": "Speech-to-Text", "Controller": "Controller", "Retrieval": "Minor Search",
               "LLM": "AI-provider", "Validation": "Outputvalidatie", "TTS": "Text-to-Speech"}
    for step in turn.steps:
        if step.status != "NOT_TESTED" and step.name in mapping:
            evidence[mapping[step.name]] = {"status": step.status, "detail": step.detail, "mode": mode, "checked_at": now()}
    if turn.agent_run and turn.agent_run.validated_output:
        evidence["AI-agent"] = {"status": "PASS", "detail": "Gecontroleerde agentuitvoer; semantische relevantie nog handmatig beoordelen.", "mode": mode, "checked_at": now()}
    elif turn.agent_run and turn.agent_run.model_called:
        evidence["AI-agent"] = {"status": "FAIL", "detail": "De laatste agenttest kon geen geldig advies opleveren.", "mode": mode, "checked_at": now()}
    if turn.steps[0].status != "NOT_TESTED":
        first_problem = next((step for step in turn.steps if step.status in {"FAIL", "BLOCKED"}), None)
        complete = all(step.status == "PASS" for step in turn.steps)
        evidence["End-to-end"] = {"status": "PASS" if complete else (first_problem.status if first_problem else "NOT_TESTED"),
                                  "detail": "Alle stappen uitgevoerd; hoorbaarheid handmatig beoordelen." if complete else "Audioketen niet voltooid.",
                                  "mode": mode, "checked_at": now()}


def small_live_scrape(settings: Settings, permitted: bool) -> dict:
    if not permitted:
        raise ValueError("Bevestig toegestane toegang voordat de kleine livecontrole wordt gestart.")
    # De bestaande fetcher controleert robots en stopt op 401/403/429; geen bypass.
    if (settings.dataset_path.parent != settings.report_path.parent or settings.dataset_path.name != "minors.json"
            or settings.report_path.name != "scrape_report.json"):
        raise ValueError("Dataset en rapport moeten voor een scrape in dezelfde map staan.")
    return run_scrape(5, settings.dataset_path.parent, delay=1.5, timeout=10, retries=0, max_requests=12)


def probe_local_model(settings: Settings, provider=None) -> dict:
    """Losse echte JSON-generatieproef zonder studentgegevens of minorrecords."""
    started = perf_counter()
    result = {"status": "FAIL", "model": settings.ollama_model, "mode": "live_local", "checked_at": now()}
    schema = {"type": "object", "properties": {"status": {"type": "string", "enum": ["lokale_test_geslaagd"]}},
              "required": ["status"], "additionalProperties": False}
    try:
        local = provider or OllamaProvider(settings.ollama_url, settings.ollama_model, settings.model_timeout)
        raw = local.generate("Technische test zonder studentgegevens. Geef uitsluitend het gevraagde JSON-object.", schema,
                             "Je bent een lokale technische test. Volg uitsluitend het JSON-schema.")
        result["raw_output"] = raw[:4000]
        if json.loads(raw) != {"status": "lokale_test_geslaagd"}:
            raise ValueError
        result["status"] = "PASS"
        result["detail"] = "Werkelijke lokale JSON-generatie en validatie geslaagd; geen minoradvies getest."
    except ProviderError as exc:
        result["status"] = "BLOCKED" if str(exc) in {"model_missing", "ollama_unreachable"} else "FAIL"
        result["detail"] = "Lokale modelaanroep mislukt; controleer server en modelinventaris."
    except (ValueError, TypeError, RecursionError):
        result["detail"] = "JSON-modeloutput of lokale configuratie ongeldig."
    result["elapsed_ms"] = round((perf_counter() - started) * 1000)
    return result
