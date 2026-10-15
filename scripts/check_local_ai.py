"""Expliciete lokale smoke-test zonder studentdata, modellen downloaden of Gemini."""

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Settings
from core.diagnostics import probe_local_model

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=Settings().ollama_model)
    args = parser.parse_args()
    result = probe_local_model(replace(Settings(), ollama_model=args.model))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
