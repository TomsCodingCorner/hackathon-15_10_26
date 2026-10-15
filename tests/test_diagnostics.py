import json
import subprocess
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from ai.providers import ProviderError
from core.diagnostics import Check, component_checks, dataset_check, environment_checks, probe_local_model, small_live_scrape
from core.test_service import run_tests


def test_status_classification_rejects_fake_status():
    with pytest.raises(ValueError):
        Check("test", "OK-ish", "invalid")


def test_missing_and_empty_dataset_blocked(local_settings):
    assert dataset_check(local_settings)[0].status == "BLOCKED"
    local_settings.dataset_path.write_text("[]")
    check, rows = dataset_check(local_settings)
    assert check.status == "BLOCKED" and rows == []


@pytest.mark.parametrize("raw", ["not json", "{}", '[{"id":"bad"}]'])
def test_invalid_dataset_fails(local_settings, raw):
    local_settings.dataset_path.write_text(raw)
    assert dataset_check(local_settings)[0].status == "FAIL"


def test_valid_dataset_is_actually_validated(local_settings, sample_minors):
    local_settings.dataset_path.write_text(json.dumps(sample_minors))
    assert dataset_check(local_settings)[0].status == "PASS"


def test_missing_packages_and_unreachable_ollama_are_honest(monkeypatch, local_settings):
    monkeypatch.setattr("core.diagnostics.package_present", lambda name: False)
    monkeypatch.setattr("core.diagnostics.shutil.which", lambda name: None)
    monkeypatch.setattr("core.diagnostics.OllamaProvider.models", Mock(side_effect=ProviderError("ollama_unreachable")))
    checks = {check.name: check for check in environment_checks(local_settings)}
    assert checks["Package: piper"].status == "BLOCKED"
    assert checks["Ollama server"].status == "BLOCKED"
    assert checks["Ollama model"].status == "NOT_TESTED"
    assert checks["Whisper modelbestanden"].status == "BLOCKED"
    assert checks["Tijdelijke schrijfrechten"].status == "PASS"


def test_readiness_is_not_a_functional_pass(monkeypatch, local_settings):
    monkeypatch.setattr("core.diagnostics.OllamaProvider.models", lambda self: ["qwen2.5:3b"])
    ready = {check.name: check for check in environment_checks(local_settings)}
    assert ready["Ollama model"].status == "PASS"
    components = {row["name"]: row for row in component_checks(local_settings)}
    for component in ("AI-provider", "AI-agent", "Speech-to-Text", "Text-to-Speech", "End-to-end"):
        assert components[component]["status"] == "NOT_TESTED"


def test_small_scrape_requires_explicit_permission(local_settings, monkeypatch):
    run = Mock()
    monkeypatch.setattr("core.diagnostics.run_scrape", run)
    with pytest.raises(ValueError):
        small_live_scrape(local_settings, False)
    run.assert_not_called()


def test_small_scrape_is_bounded(local_settings, monkeypatch):
    run = Mock(return_value={"status": "blocked"})
    monkeypatch.setattr("core.diagnostics.run_scrape", run)
    assert small_live_scrape(local_settings, True)["status"] == "blocked"
    assert run.call_args.args[0] == 5
    assert run.call_args.kwargs["retries"] == 0
    assert run.call_args.kwargs["max_requests"] == 12


def test_independent_local_generation_needs_no_dataset(local_settings):
    provider = Mock(generate=Mock(return_value='{"status":"lokale_test_geslaagd"}'))
    result = probe_local_model(local_settings, provider)
    assert result["status"] == "PASS"
    assert result["mode"] == "live_local"
    assert not local_settings.dataset_path.exists()


def test_independent_generation_does_not_pass_invalid_json(local_settings):
    result = probe_local_model(local_settings, Mock(generate=Mock(return_value="not json")))
    assert result["status"] == "FAIL"


def test_pytest_service_fixed_command_and_junit(monkeypatch, local_settings):
    def execute(command, **kwargs):
        report = next(arg.split("=", 1)[1] for arg in command if arg.startswith("--junitxml="))
        from pathlib import Path
        Path(report).write_text('<testsuites><testsuite tests="5" failures="1" errors="0" skipped="1" /></testsuites>')
        assert kwargs["shell"] is False and kwargs["timeout"] == 90
        assert command[1:4] == ["-m", "pytest", "tests"]
        return SimpleNamespace(returncode=1, stdout="x" * 13000, stderr="")
    monkeypatch.setattr("core.test_service.subprocess.run", execute)
    result = run_tests(local_settings)
    assert (result["passed"], result["failed"], result["skipped"]) == (3, 1, 1)
    assert result["status"] == "FAIL" and len(result["output"]) == 12000


def test_pytest_service_timeout_is_reported(monkeypatch, local_settings):
    monkeypatch.setattr("core.test_service.subprocess.run", Mock(side_effect=subprocess.TimeoutExpired("pytest", 90)))
    assert "timeout" in run_tests(local_settings)["output"]
