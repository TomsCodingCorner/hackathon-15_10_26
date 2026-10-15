from pathlib import Path
from unittest.mock import Mock
import json

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_app_starts_without_keys_or_models(monkeypatch, tmp_path):
    dataset = tmp_path / "minors.json"
    dataset.write_text("[]")
    monkeypatch.setenv("MINORS_PATH", str(dataset))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
    assert not app.exception
    assert app.title[0].value == "MinorAdviseur AI"
    assert any("geen gevalideerde minoren" in item.value for item in app.warning)
    app.chat_input[0].set_value("Ik studeer ICT").run()
    assert not app.exception
    assert len(app.session_state.conversation["messages"]) == 2
    app.run()
    assert len(app.session_state.conversation["messages"]) == 2
    next(button for button in app.button if button.label == "Nieuw gesprek").click().run()
    assert app.session_state.conversation["messages"] == []


def test_diagnostics_page_starts_without_starting_tests(monkeypatch, tmp_path):
    dataset = tmp_path / "minors.json"
    dataset.write_text("[]")
    monkeypatch.setenv("MINORS_PATH", str(dataset))
    start = Mock()
    monkeypatch.setattr("core.test_service.start_tests", start)
    app = AppTest.from_file(str(ROOT / "pages/2_Testing_Diagnostics.py"), default_timeout=15).run()
    assert not app.exception
    assert app.title[0].value == "Testing & Diagnostics"
    assert len(app.tabs) == 7
    start.assert_not_called()


def test_chat_renders_only_validated_cards_with_local_mock(monkeypatch, local_settings, sample_minors, local_provider):
    local_settings.dataset_path.write_text(json.dumps(sample_minors))
    monkeypatch.setenv("MINORS_PATH", str(local_settings.dataset_path))
    monkeypatch.setattr("core.controller.OllamaProvider", Mock(return_value=local_provider))
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
    app.chat_input[0].set_value("Ik wil ondernemen").run()
    assert not app.exception
    assert app.session_state.conversation["messages"][-1]["cards"][0]["id"] == sample_minors[0]["id"]
    assert any(item.value == "TESTDATA Ondernemen" for item in app.subheader)
