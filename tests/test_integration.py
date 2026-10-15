import json
from unittest.mock import Mock
from types import SimpleNamespace

import requests

from ai.providers import ProviderError
from core.controller import run_turn
from core.diagnostics import record_turn
from scraper.pipeline import _write_json, load_minors
from scraper.pipeline import run_scrape
from scraper.parser import Listing


def test_mocked_audio_end_to_end_validated_recommendation(local_settings, sample_minors, local_provider, wav_bytes):
    _write_json(local_settings.dataset_path, sample_minors)
    rows = load_minors(local_settings.dataset_path)
    stt, tts = Mock(return_value="Ik wil ondernemen"), Mock(return_value=wav_bytes)
    turn = run_turn("", [], rows, local_settings, audio=wav_bytes, speak=True, provider=local_provider, stt=stt, tts=tts)
    assert all(step.status == "PASS" for step in turn.steps)
    assert turn.result["recommended_minor_ids"] == [rows[0]["id"]]
    assert turn.audio == wav_bytes
    assert tts.call_args.args[0] == turn.result["response"]
    evidence = {}
    record_turn(evidence, turn, mode="mock")
    assert evidence["End-to-end"]["status"] == "PASS" and evidence["End-to-end"]["mode"] == "mock"


def test_empty_data_does_not_mark_downstream_failed(local_settings, local_provider, wav_bytes):
    turn = run_turn("", [], [], local_settings, audio=wav_bytes, speak=True, provider=local_provider,
                    stt=Mock(return_value="Hallo"), tts=Mock())
    assert [step.status for step in turn.steps] == ["PASS", "PASS", "BLOCKED", "NOT_TESTED", "NOT_TESTED", "NOT_TESTED", "NOT_TESTED"]
    local_provider.generate.assert_not_called()


def test_missing_model_stops_before_validation_and_tts(local_settings, sample_minors, local_provider, wav_bytes):
    local_provider.generate.side_effect = ProviderError("model_missing")
    tts = Mock()
    turn = run_turn("", [], sample_minors, local_settings, audio=wav_bytes, speak=True, provider=local_provider,
                    stt=Mock(return_value="ondernemen"), tts=tts)
    assert turn.steps[3].status == "FAIL"
    assert all(step.status == "NOT_TESTED" for step in turn.steps[4:])
    tts.assert_not_called()


def test_stt_failure_keeps_all_downstream_not_tested(local_settings, sample_minors, local_provider, wav_bytes):
    turn = run_turn("", [], sample_minors, local_settings, audio=wav_bytes, speak=True, provider=local_provider,
                    stt=Mock(side_effect=RuntimeError("private audio")))
    assert turn.steps[0].status == "FAIL"
    assert all(step.status == "NOT_TESTED" for step in turn.steps[1:])
    assert "private audio" not in turn.result["response"]


def test_tts_failure_preserves_validated_text(local_settings, sample_minors, local_provider):
    turn = run_turn("ondernemen", [], sample_minors, local_settings, speak=True, provider=local_provider,
                    tts=Mock(side_effect=RuntimeError("private text")))
    assert turn.result["recommended_minor_ids"] == [sample_minors[0]["id"]]
    assert turn.steps[5].status == "FAIL" and turn.audio is None
    assert turn.steps[6].status == "NOT_TESTED"


def test_mock_source_pipeline_file_loader_controller_agent(monkeypatch, local_settings, sample_minors, local_provider):
    """Volledige dataketen met expliciet gemockte bronadapter, geen echte bron."""
    def response(text):
        return SimpleNamespace(status_code=200, text=text, headers={}, close=Mock())
    monkeypatch.setattr(requests.Session, "get", Mock(side_effect=[
        response("User-Agent: *\nAllow: /\n"), response("mock listing"), response("mock detail"),
    ]))
    monkeypatch.setattr("scraper.pipeline.parse_listing", Mock(return_value=Listing([sample_minors[0]["url"]])))
    monkeypatch.setattr("scraper.pipeline.parse_detail", Mock(return_value=sample_minors[0]))
    report = run_scrape(1, local_settings.dataset_path.parent, delay=0)
    rows = load_minors(local_settings.dataset_path)
    turn = run_turn("Ik wil ondernemen", [], rows, local_settings, provider=local_provider)
    assert report["records_valid"] == 1
    assert report["pages_requested"] == 3
    assert turn.cards[0]["id"] == rows[0]["id"]
    assert turn.result["recommended_minor_ids"] == [rows[0]["id"]]
