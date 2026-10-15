"""Compatibiliteitsentrypoint; voert voortaan de Gemini-proef uit."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_gemini import main

if __name__ == "__main__":
    raise SystemExit(main())
