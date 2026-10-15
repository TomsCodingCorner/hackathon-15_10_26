from dataclasses import replace

from config import Settings, load_configuration
from core.diagnostics import environment_checks


def test_dotenv_loads_gemini_configuration_without_overwriting_environment(monkeypatch, tmp_path):
    path = tmp_path / ".env"
    path.write_text('GEMINI_API_KEY="file-test-key"\nGEMINI_MODEL=file-test-model\n', encoding="utf-8-sig")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "environment-test-model")
    load_configuration(path)
    settings = Settings()
    assert settings.gemini_api_key == "file-test-key"
    assert settings.gemini_model == "environment-test-model"


def test_secret_is_hidden_in_settings_and_environment_results(local_settings):
    settings = replace(local_settings, gemini_api_key="DO-NOT-DISPLAY-THIS-KEY")
    assert "DO-NOT-DISPLAY-THIS-KEY" not in repr(settings)
    checks = environment_checks(settings)
    assert "DO-NOT-DISPLAY-THIS-KEY" not in repr(checks)
