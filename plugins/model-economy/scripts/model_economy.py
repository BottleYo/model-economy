#!/usr/bin/env python3
"""Command entry point for the Model Economy plugin."""

import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from model_economy_lib.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
