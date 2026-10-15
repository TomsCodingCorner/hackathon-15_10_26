import copy
import json
from unittest.mock import Mock, patch

import pytest

from ai.providers import ProviderError
from core.controller import run_turn
from core.session import append_turn, new_conversation


def test_valid_recommendations_and_session_order(local_settings, sample_minors, local_provider):
    session = new_conversation()
    turn = run_turn("Ik studeer ICT en wil ondernemen", [], sample_minors, local_settings, provider=local_provider)
    assert turn.result["recommended_minor_ids"] == [sample_minors[0]["id"]]
    assert len(turn.cards) == 1
    assert turn.cards[0]["url"] == sample_minors[0]["url"]
    assert append_turn(session, turn, "event-1")
    assert [entry["role"] for entry in session["history"]] == ["user", "assistant"]
    assert not append_turn(session, turn, "event-1")
    assert len(session["messages"]) == 2
    assert new_conversation(1)["history"] == []


def test_history_and_user_correction_reach_model(local_settings, sample_minors, local_provider):
    history = [{"role": "user", "content": "Ik wil psychologie"}, {"role": "assistant", "content": "Welke richting?"}]
    before = copy.deepcopy(history)
    run_turn("Correctie: ik wil ondernemen", history, sample_minors, local_settings, provider=local_provider)
    payload = json.loads(local_provider.generate.call_args.args[0])
    assert payload["history"] == before
    assert "Correctie" in payload["message"]
    assert history == before


def test_empty_dataset_blocks_model_and_downstream(local_settings, local_provider):
    tts = Mock()
    turn = run_turn("Hallo", [], [], local_settings, provider=local_provider, speak=True, tts=tts)
    assert "geen gevalideerde minoren" in turn.result["response"]
    assert turn.steps[2].status == "BLOCKED"
    assert all(step.status == "NOT_TESTED" for step in turn.steps[3:])
    local_provider.generate.assert_not_called()
    tts.assert_not_called()


@pytest.mark.parametrize("raw", ["not json", "{}", "null", '"string"'])
def test_invalid_model_output_never_produces_cards_or_audio(raw, local_settings, sample_minors, local_provider):
    local_provider.generate.return_value = raw
    tts = Mock()
    turn = run_turn("ondernemen", [], sample_minors, local_settings, provider=local_provider, speak=True, tts=tts)
    assert turn.steps[4].status == "FAIL"
    assert turn.cards == [] and turn.audio is None
    assert turn.result["recommended_minor_ids"] == []
    tts.assert_not_called()


def test_unknown_minor_is_not_visible_or_spoken(local_settings, sample_minors, local_provider, recommendation):
    recommendation["recommendations"][0]["minor_id"] = "nonexistent-id"
    local_provider.generate.return_value = json.dumps(recommendation)
    turn = run_turn("ondernemen", [], sample_minors, local_settings, provider=local_provider, speak=True, tts=Mock())
    assert not turn.cards and not turn.audio
    assert "nonexistent-id" not in turn.result["response"]


def test_missing_model_is_local_failure_without_external_fallback(local_settings, sample_minors, local_provider):
    local_provider.generate.side_effect = ProviderError("model_missing")
    with patch("ai.agent.genai.Client") as cloud:
        turn = run_turn("ondernemen", [], sample_minors, local_settings, provider=local_provider)
    cloud.assert_not_called()
    assert turn.steps[3].status == "FAIL"
    assert turn.steps[4].status == "NOT_TESTED"
    assert turn.agent_run.error == "model_missing"


def test_question_and_follow_up_context(local_settings, sample_minors, local_provider):
    local_provider.generate.return_value = json.dumps({"action": "ask", "question_topic": "interests", "recommendations": []})
    session = new_conversation()
    turn = run_turn("Ik studeer ICT", [], sample_minors, local_settings, provider=local_provider)
    assert turn.result["needs_more_info"]
    append_turn(session, turn, "1")
    assert "interessant" in session["messages"][-1]["content"]
    local_provider.generate.return_value = json.dumps({"action": "refer", "question_topic": "none", "recommendations": []})
    second = run_turn("Ik weet het niet", session["history"], sample_minors, local_settings, provider=local_provider)
    assert "studieadviseur" in second.result["response"]


def test_invalid_dataset_and_blank_input_do_not_call_model(local_settings, local_provider):
    for message, data in [("", []), ("Hallo", [{"title": "incomplete"}])]:
        turn = run_turn(message, [], data, local_settings, provider=local_provider)
        assert turn.steps[1].status == "FAIL"
    local_provider.generate.assert_not_called()
