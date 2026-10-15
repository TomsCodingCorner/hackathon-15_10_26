"""Volledig offline Gemini-tests; echte SDK alleen met MockTransport."""

import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import httpx
import pytest
from google import genai

from ai.providers import ProviderError
from ai.providers.gemini_provider import GeminiProvider
from core.controller import run_turn
from core.diagnostics import probe_gemini


@pytest.fixture
def sdk_client(monkeypatch):
    factory = MagicMock()
    client = factory.return_value.__enter__.return_value
    client.models.generate_content.return_value = SimpleNamespace(text='{"status":"gemini_test_geslaagd"}')
    monkeypatch.setattr("ai.providers.gemini_provider.genai.Client", factory)
    return factory, client


def test_official_sdk_uses_configured_key_model_schema_and_timeout(sdk_client):
    factory, client = sdk_client
    provider = GeminiProvider("fake-key", "models/configured-model", timeout=17)
    output = provider.generate("test payload", {"type": "object"}, "Nederlandse systeemprompt")
    assert json.loads(output) == {"status": "gemini_test_geslaagd"}
    kwargs = factory.call_args.kwargs
    assert kwargs["api_key"] == "fake-key"
    assert kwargs["vertexai"] is False and kwargs["enterprise"] is False
    assert kwargs["http_options"].timeout == 17000
    assert kwargs["http_options"].retry_options.attempts == 1
    generation = client.models.generate_content.call_args.kwargs
    assert generation["model"] == "configured-model"
    assert generation["contents"] == "test payload"
    assert generation["config"].response_mime_type == "application/json"
    assert generation["config"].response_json_schema == {"type": "object"}
    assert generation["config"].system_instruction == "Nederlandse systeemprompt"
    factory.return_value.__exit__.assert_called_once()


def test_missing_key_never_creates_client(sdk_client):
    with pytest.raises(ProviderError, match="missing_api_key"):
        GeminiProvider("", "configured-model")
    sdk_client[0].assert_not_called()


@pytest.mark.parametrize("status, expected", [
    (401, "gemini_auth_error"), (403, "gemini_auth_error"),
    (404, "gemini_model_not_found"), (429, "gemini_rate_limited"),
    (400, "gemini_invalid_request"), (500, "gemini_api_error"), (503, "gemini_unavailable"),
])
def test_api_errors_are_classified_without_private_details(sdk_client, status, expected):
    class SDKFailure(RuntimeError):
        code = status
    sdk_client[1].models.generate_content.side_effect = SDKFailure("PRIVATE KEY AND FULL CONVERSATION")
    with pytest.raises(ProviderError) as error:
        GeminiProvider("fake-key", "test-model").generate("private prompt", {}, "system")
    assert str(error.value) == expected
    assert "PRIVATE" not in str(error.value)


@pytest.mark.parametrize("failure, expected", [
    (httpx.ReadTimeout("private"), "gemini_timeout"),
    (httpx.ConnectError("private"), "gemini_unreachable"),
])
def test_timeout_and_network_errors_are_safe(sdk_client, failure, expected):
    sdk_client[1].models.generate_content.side_effect = failure
    with pytest.raises(ProviderError, match=expected):
        GeminiProvider("fake-key", "test-model").generate("payload", {}, "system")


@pytest.mark.parametrize("text", [None, "", "  "])
def test_blocked_or_empty_completion_rejected(sdk_client, text):
    sdk_client[1].models.generate_content.return_value = SimpleNamespace(text=text)
    with pytest.raises(ProviderError, match="gemini_empty_output"):
        GeminiProvider("fake-key", "test-model").generate("payload", {}, "system")


def test_controller_defaults_to_gemini_with_configured_credentials(sdk_client, local_settings, sample_minors, recommendation):
    sdk_client[1].models.generate_content.return_value = SimpleNamespace(text=json.dumps(recommendation))
    turn = run_turn("Ik wil ondernemen", [], sample_minors, local_settings)
    assert turn.result["recommended_minor_ids"] == [sample_minors[0]["id"]]
    assert sdk_client[0].call_args.kwargs["api_key"] == "fake-test-key"
    assert sdk_client[1].models.generate_content.call_args.kwargs["model"] == "fake-gemini-model"


def test_missing_key_blocks_controller_before_api_and_tts(sdk_client, local_settings, sample_minors):
    tts = Mock()
    turn = run_turn("ondernemen", [], sample_minors, replace(local_settings, gemini_api_key=""), speak=True, tts=tts)
    assert turn.steps[3].status == "BLOCKED"
    assert "GEMINI_API_KEY" in turn.result["response"]
    assert all(step.status == "NOT_TESTED" for step in turn.steps[4:])
    sdk_client[0].assert_not_called()
    tts.assert_not_called()


def test_gemini_quota_error_is_honest_diagnostic_block(local_settings):
    provider = Mock(generate=Mock(side_effect=ProviderError("gemini_rate_limited")))
    result = probe_gemini(local_settings, provider)
    assert result["status"] == "BLOCKED"
    assert result["error_code"] == "gemini_rate_limited"
    assert result["mode"] == "live_gemini"
    assert "quota" in result["detail"]


def test_service_unavailable_blocks_downstream_without_disclosing_errors(local_settings, sample_minors):
    provider = Mock(generate=Mock(side_effect=ProviderError("gemini_unavailable")))
    turn = run_turn("Ik wil ondernemen", [], sample_minors, local_settings, provider=provider, speak=True)
    assert turn.steps[3].status == "BLOCKED"
    assert all(step.status == "NOT_TESTED" for step in turn.steps[4:])
    assert not turn.cards and not turn.audio
    assert "503" in turn.result["response"]


@pytest.mark.parametrize("status", [200, 429])
def test_real_sdk_wire_format_key_precedence_and_no_retries(monkeypatch, status):
    real_client = genai.Client
    calls = []
    def handler(request):
        calls.append(request)
        assert request.url.host == "generativelanguage.googleapis.com"
        assert request.headers["x-goog-api-key"] == "explicit-fake-key"
        payload = json.loads(request.content)
        assert payload["generationConfig"]["responseMimeType"] == "application/json"
        assert payload["generationConfig"]["responseJsonSchema"] == {"type": "object"}
        if status == 429:
            return httpx.Response(429, json={"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "PRIVATE"}})
        return httpx.Response(200, json={"candidates": [{"content": {"role": "model", "parts": [{"text": "{}"}]}, "finishReason": "STOP"}]})
    with httpx.Client(transport=httpx.MockTransport(handler), trust_env=False) as http_client:
        def factory(**kwargs):
            kwargs["http_options"].httpx_client = http_client
            return real_client(**kwargs)
        monkeypatch.setenv("GOOGLE_API_KEY", "another-fake-key")
        monkeypatch.setattr("ai.providers.gemini_provider.genai.Client", factory)
        provider = GeminiProvider("explicit-fake-key", "configured-model")
        if status == 200:
            assert provider.generate("payload", {"type": "object"}, "system") == "{}"
        else:
            with pytest.raises(ProviderError, match="gemini_rate_limited"):
                provider.generate("payload", {"type": "object"}, "system")
    assert len(calls) == 1
