"""Centrale lokale configuratie; geen modeldownloads of verplichte secrets."""

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _path(name: str, default: str) -> Path:
    return Path(os.getenv(name, str(ROOT / default))).expanduser().resolve()


@dataclass(frozen=True)
class Settings:
    dataset_path: Path = field(default_factory=lambda: _path("MINORS_PATH", "data/minors.json"))
    report_path: Path = field(default_factory=lambda: _path("SCRAPE_REPORT_PATH", "data/scrape_report.json"))
    ollama_url: str = field(default_factory=lambda: os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen2.5:3b"))
    model_timeout: float = 60
    retrieval_limit: int = 12
    whisper_path: Path = field(default_factory=lambda: _path("WHISPER_MODEL_PATH", "models/whisper-small"))
    piper_path: Path = field(default_factory=lambda: _path("PIPER_MODEL_PATH", "models/piper/nl_NL-mls-medium.onnx"))
    runtime_dir: Path = field(default_factory=lambda: _path("RUNTIME_DIR", ".runtime"))
    max_audio_seconds: int = 60
    max_audio_bytes: int = 8_000_000


EMPTY_DATA_MESSAGE = "Er zijn momenteel geen gevalideerde minoren beschikbaar. De scraper of dataset moet eerst worden hersteld."
