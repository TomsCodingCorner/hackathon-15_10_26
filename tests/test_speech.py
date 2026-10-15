import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from speech import SpeechError
from speech.stt import transcribe, validate_wav
from speech.tts import synthesize, validate_voice


def whisper_files(path):
    path.mkdir()
    for name in ("model.bin", "config.json", "tokenizer.json"):
        (path / name).write_text("fixture")


def piper_files(path, language="nl_NL"):
    path.write_bytes(b"fake-onnx-test-only")
    path.with_suffix(".onnx.json").write_text(json.dumps({"language": {"code": language}}))


def test_valid_wav_duration(wav_bytes):
    assert validate_wav(wav_bytes) == pytest.approx(0.1)


@pytest.mark.parametrize("audio", [b"", b"not a wav", None, b"RIFF" + b"x" * 100])
def test_invalid_audio_rejected(audio):
    with pytest.raises(SpeechError, match="invalid_audio"):
        validate_wav(audio)


def test_stt_with_mocked_model_is_explicitly_dutch(monkeypatch, local_settings, wav_bytes):
    whisper_files(local_settings.whisper_path)
    model = Mock()
    model.transcribe.return_value = (iter([SimpleNamespace(text=" Ik wil ondernemen. ")]), SimpleNamespace())
    monkeypatch.setattr("speech.stt._load_model", lambda path: model)
    assert transcribe(wav_bytes, local_settings.whisper_path) == "Ik wil ondernemen."
    assert model.transcribe.call_args.kwargs["language"] == "nl"


def test_stt_missing_model_does_not_attempt_download(local_settings, wav_bytes, monkeypatch):
    load = Mock()
    monkeypatch.setattr("speech.stt._load_model", load)
    with pytest.raises(SpeechError, match="whisper_model_missing"):
        transcribe(wav_bytes, local_settings.whisper_path)
    load.assert_not_called()


@pytest.mark.parametrize("failure", [ImportError, RuntimeError])
def test_stt_errors_have_no_audio_or_transcript_details(monkeypatch, local_settings, wav_bytes, failure):
    whisper_files(local_settings.whisper_path)
    monkeypatch.setattr("speech.stt._load_model", Mock(side_effect=failure("PRIVATE TRANSCRIPT")))
    with pytest.raises(SpeechError) as error:
        transcribe(wav_bytes, local_settings.whisper_path)
    assert "PRIVATE" not in str(error.value)


def test_tts_with_mocked_voice_generates_valid_wav(monkeypatch, local_settings):
    piper_files(local_settings.piper_path)
    def write_wav(text, wav):
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(22050)
        wav.writeframes(b"\0\0" * 2205)
    voice = Mock()
    voice.synthesize_wav.side_effect = write_wav
    monkeypatch.setattr("speech.tts._load_voice", lambda path: voice)
    assert validate_wav(synthesize("Hallo", local_settings.piper_path)) == pytest.approx(0.1)
    assert voice.synthesize_wav.call_args.args[0] == "Hallo"


def test_tts_missing_model(local_settings):
    with pytest.raises(SpeechError, match="piper_model_missing"):
        synthesize("Hallo", local_settings.piper_path)


def test_english_piper_voice_is_not_accepted(local_settings):
    piper_files(local_settings.piper_path, "en_US")
    with pytest.raises(SpeechError, match="dutch_voice_required"):
        validate_voice(local_settings.piper_path)


def test_tts_failure_is_safe(monkeypatch, local_settings):
    piper_files(local_settings.piper_path)
    monkeypatch.setattr("speech.tts._load_voice", Mock(side_effect=RuntimeError("PRIVATE TEXT")))
    with pytest.raises(SpeechError, match="synthesis_failed"):
        synthesize("Hallo", local_settings.piper_path)


@pytest.mark.parametrize("text", ["", " ", None])
def test_empty_tts_input(text, local_settings):
    with pytest.raises(SpeechError, match="invalid_tts_text"):
        synthesize(text, local_settings.piper_path)
