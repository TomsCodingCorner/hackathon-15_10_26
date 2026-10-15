"""Synthetische fixtures; nooit in data/minors.json of de echte chatbot laden."""

import io
import json
import wave
from dataclasses import replace
from unittest.mock import Mock

import pytest
import httpx
import requests

from config import Settings
from scraper.models import stable_id


@pytest.fixture(autouse=True)
def offline_network(monkeypatch):
    """Alle echte HTTP-transports blokkeren; lokale AppTest-socketpairs toestaan."""
    def denied(*args, **kwargs):
        raise AssertionError("Een unittest mag geen echte HTTP-aanroep uitvoeren.")
    async def async_denied(*args, **kwargs):
        raise AssertionError("Een unittest mag geen echte HTTP-aanroep uitvoeren.")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", denied)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", async_denied)
    monkeypatch.setattr(requests.Session, "request", denied)


@pytest.fixture
def local_settings(tmp_path):
    return replace(Settings(), dataset_path=tmp_path / "minors.json", report_path=tmp_path / "scrape_report.json",
                   whisper_path=tmp_path / "whisper", piper_path=tmp_path / "nl.onnx", runtime_dir=tmp_path / "runtime",
                   gemini_api_key="fake-test-key", gemini_model="fake-gemini-model")


@pytest.fixture
def sample_minors():
    url = "https://www.kiesopmaat.nl/modules/fixture/unit/1/"
    return [{"id": stable_id(url), "title": "TESTDATA Ondernemen", "institution": "Fictieve testinstelling",
             "description": "Je leert een onderneming opzetten en een digitaal bedrijfsconcept ontwikkelen.", "url": url}]


@pytest.fixture
def recommendation(sample_minors):
    return {"action": "recommend", "question_topic": "none", "recommendations": [{
        "minor_id": sample_minors[0]["id"], "student_quote": "ondernemen", "description_quote": sample_minors[0]["description"],
    }]}


@pytest.fixture
def local_provider(recommendation):
    return Mock(generate=Mock(return_value=json.dumps(recommendation)))


@pytest.fixture
def wav_bytes():
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0" * 1600)
    return buffer.getvalue()
