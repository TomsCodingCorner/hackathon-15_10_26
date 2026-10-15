"""Nederlandse faster-whisper-transcriptie op CPU, uitsluitend lokale modellen."""

import io
import logging
import wave
from functools import lru_cache
from pathlib import Path

from . import SpeechError


def validate_wav(audio: bytes, max_seconds: int = 60, max_bytes: int = 8_000_000) -> float:
    if not isinstance(audio, bytes) or not 44 < len(audio) <= max_bytes:
        raise SpeechError("invalid_audio")
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav:
            frames, rate, channels, width = wav.getnframes(), wav.getframerate(), wav.getnchannels(), wav.getsampwidth()
            duration = frames / rate
            if not (0 < duration <= max_seconds and 8000 <= rate <= 96000 and channels in (1, 2) and width in (1, 2, 3, 4)):
                raise SpeechError("invalid_audio")
            if len(wav.readframes(frames)) != frames * channels * width:
                raise SpeechError("invalid_audio")
            return duration
    except (wave.Error, EOFError, ZeroDivisionError, ValueError):
        raise SpeechError("invalid_audio") from None


def whisper_files_present(path: Path) -> bool:
    try:
        return all((path / name).is_file() and (path / name).stat().st_size > 0
                   for name in ("model.bin", "config.json", "tokenizer.json"))
    except OSError:
        return False


@lru_cache(maxsize=1)
def _load_model(path: str):
    from faster_whisper import WhisperModel
    logging.getLogger("faster_whisper").setLevel(logging.ERROR)
    return WhisperModel(path, device="cpu", compute_type="int8", local_files_only=True)


def transcribe(audio: bytes, model_path: Path, *, max_seconds: int = 60, max_bytes: int = 8_000_000) -> str:
    validate_wav(audio, max_seconds, max_bytes)
    if not whisper_files_present(model_path):
        raise SpeechError("whisper_model_missing")
    try:
        model = _load_model(str(model_path))
        segments, _ = model.transcribe(io.BytesIO(audio), language="nl", beam_size=5, vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        if not text:
            raise SpeechError("no_speech_detected")
        if len(text) > 8000:
            raise SpeechError("transcript_too_long")
        return text
    except ImportError:
        raise SpeechError("stt_package_missing") from None
    except SpeechError:
        raise
    except Exception:
        raise SpeechError("transcription_failed") from None
