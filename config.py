"""Centrale configuratie; .env uit de repository, omgeving heeft voorrang."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
DEFAULT_GEMINI_MODEL = "gemini-flash-latest"


def load_configuration(path: Path | None = None) -> None:
    """Geen waarden loggen; lees alleen de expliciete repository-.env."""
    load_dotenv(path or ROOT / ".env", override=False, interpolate=False, encoding="utf-8-sig")


load_configuration()


def _path(name: str, default: str) -> Path:
    return Path(os.getenv(name, str(ROOT / default))).expanduser().resolve()


@dataclass(frozen=True)
class Settings:
    dataset_path: Path = field(default_factory=lambda: _path("MINORS_PATH", "data/minors.json"))
    report_path: Path = field(default_factory=lambda: _path("SCRAPE_REPORT_PATH", "data/scrape_report.json"))
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", "").strip(), repr=False, compare=False)
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_GEMINI_MODEL)
    model_timeout: float = 60
    retrieval_limit: int = 12
    whisper_path: Path = field(default_factory=lambda: _path("WHISPER_MODEL_PATH", "models/whisper-small"))
    piper_path: Path = field(default_factory=lambda: _path("PIPER_MODEL_PATH", "models/piper/nl_NL-mls-medium.onnx"))
    runtime_dir: Path = field(default_factory=lambda: _path("RUNTIME_DIR", ".runtime"))
    max_audio_seconds: int = 60
    max_audio_bytes: int = 8_000_000


EMPTY_DATA_MESSAGE = "Er zijn momenteel geen gevalideerde minoren beschikbaar. De scraper of dataset moet eerst worden hersteld."
