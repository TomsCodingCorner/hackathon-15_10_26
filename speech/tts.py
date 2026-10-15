"""Piper synthese naar WAV in geheugen; geen blijvende audiobestanden."""

import io
import json
import wave
from functools import lru_cache
from pathlib import Path

from . import SpeechError
from .stt import validate_wav


def validate_voice(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0 or not Path(str(path) + ".json").is_file():
        raise SpeechError("piper_model_missing")
    try:
        config = json.loads(Path(str(path) + ".json").read_text(encoding="utf-8"))
        code = config["language"]["code"]
        if not isinstance(code, str) or not code.lower().startswith("nl"):
            raise SpeechError("piper_dutch_voice_required")
    except (OSError, ValueError, KeyError, TypeError):
        raise SpeechError("piper_config_invalid") from None


@lru_cache(maxsize=1)
def _load_voice(path: str):
    from piper import PiperVoice
    return PiperVoice.load(path, use_cuda=False)


def synthesize(text: str, model_path: Path) -> bytes:
    if not isinstance(text, str) or not text.strip() or len(text) > 8000:
        raise SpeechError("invalid_tts_text")
    validate_voice(model_path)
    try:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            _load_voice(str(model_path)).synthesize_wav(text, wav)
        audio = buffer.getvalue()
        validate_wav(audio, max_seconds=300, max_bytes=20_000_000)
        return audio
    except ImportError:
        raise SpeechError("tts_package_missing") from None
    except Exception:
        raise SpeechError("synthesis_failed") from None
