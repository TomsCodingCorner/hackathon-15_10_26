"""Geen modeldownloads: python scripts/check_environment.py."""

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Settings
from core.diagnostics import environment_checks

if __name__ == "__main__":
    print(json.dumps([asdict(check) for check in environment_checks(Settings())], ensure_ascii=False, indent=2))
