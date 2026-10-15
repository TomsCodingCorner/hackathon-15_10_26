"""Expliciete Gemini JSON-smoke-test; geen studentdata of minorrecords."""

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Settings
from core.diagnostics import probe_gemini


def main() -> int:
    settings = Settings()
    parser = argparse.ArgumentParser(description="Eén echte Gemini-aanroep; gebruikt API-quota.")
    parser.add_argument("--model", default=settings.gemini_model)
    args = parser.parse_args()
    result = probe_gemini(replace(settings, gemini_model=args.model))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
