import json
from unittest.mock import Mock

import pytest
import requests

from ai.providers import ProviderError
from ai.providers.ollama_provider import OllamaProvider
from ai.search import rank_minors


@pytest.mark.parametrize("url", ["https://api.example.org", "http://192.168.1.1:11434", "http://localhost:11434/redirect", "http://user:password@localhost:11434"])
def test_remote_or_ambiguous_provider_is_rejected(url):
    with pytest.raises(ValueError):
        OllamaProvider(url)


def test_cloud_model_rejected():
    with pytest.raises(ValueError):
        OllamaProvider(model="qwen:cloud")


def test_local_provider_schema_no_redirects_or_proxy(monkeypatch):
    session = Mock()
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=False)
    response = Mock(status_code=200)
    response.json.return_value = {"response": '{"action":"refer"}', "done": True}
    session.request.return_value = response
    monkeypatch.setattr("ai.providers.ollama_provider.requests.Session", lambda: session)
    provider = OllamaProvider()
    assert provider.generate("payload", {"type": "object"}, "system") == '{"action":"refer"}'
    assert session.trust_env is False
    kwargs = session.request.call_args.kwargs
    assert kwargs["allow_redirects"] is False
    assert kwargs["json"]["format"] == {"type": "object"}
    assert kwargs["json"]["stream"] is False


def test_unreachable_ollama_safe_error(monkeypatch):
    monkeypatch.setattr(requests.Session, "request", Mock(side_effect=requests.ConnectionError("private")))
    with pytest.raises(ProviderError, match="ollama_unreachable"):
        OllamaProvider().models()


def test_retrieval_is_deterministic_and_bounded(sample_minors):
    other = {**sample_minors[0], "id": "other", "title": "Psychologie", "description": "Gedrag en begeleiding van mensen in de zorg"}
    rows = [other, sample_minors[0]]
    assert rank_minors("onderneming", [], rows, 1)[0]["id"] == sample_minors[0]["id"]
    assert rank_minors("onbekendwoord", [], rows, 2) == rows
