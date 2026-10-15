"""Vaste pytest-opdracht in een worker; geen shell-input of modelcalls."""

import os
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from concurrent.futures import Future, ThreadPoolExecutor

from config import ROOT, Settings
from .diagnostics import now


def run_tests(settings: Settings, timeout: int = 90) -> dict:
    started = time.perf_counter()
    result = {"status": "FAIL", "passed": 0, "failed": 0, "skipped": 0, "duration": 0,
              "tested_at": now(), "output": "", "mode": "automated_mock_tests"}
    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=settings.runtime_dir, prefix="pytest-") as directory:
            report = os.path.join(directory, "results.xml")
            command = [sys.executable, "-m", "pytest", "tests", "-q", "--tb=short", "--disable-warnings",
                       "--basetemp=" + os.path.join(directory, "tmp"), "--junitxml=" + report]
            env = {**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
            completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True,
                                       encoding="utf-8", errors="replace", timeout=timeout, shell=False)
            result["output"] = (completed.stdout + completed.stderr)[-12000:]
            if os.path.isfile(report):
                tree = ET.parse(report).getroot()
                suites = [tree] if tree.tag == "testsuite" else tree.findall("testsuite")
                total = sum(int(suite.get("tests", 0)) for suite in suites)
                result["failed"] = sum(int(suite.get("failures", 0)) + int(suite.get("errors", 0)) for suite in suites)
                result["skipped"] = sum(int(suite.get("skipped", 0)) for suite in suites)
                result["passed"] = max(0, total - result["failed"] - result["skipped"])
            result["status"] = "PASS" if completed.returncode == 0 and os.path.isfile(report) else "FAIL"
    except subprocess.TimeoutExpired:
        result["output"] = "Testtimeout bereikt; pytest is gestopt."
    except (OSError, ET.ParseError, ValueError):
        result["output"] = "Testuitvoering of rapportverwerking mislukt."
    result["duration"] = round(time.perf_counter() - started, 2)
    return result


def start_tests(settings: Settings) -> Future:
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="local-pytest")
    future = executor.submit(run_tests, settings)
    future.add_done_callback(lambda _: executor.shutdown(wait=False))
    return future
