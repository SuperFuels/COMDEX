#!/usr/bin/env python3
"""
Runner for AION Demo Bridge.

Keeps a stable entrypoint:
  PYTHONPATH=. python backend/modules/aion_demo/run_demo_bridge.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn


# Ensure repo root on sys.path so "backend...." imports work reliably.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def main() -> None:
    host = os.getenv("AION_DEMO_HOST", "127.0.0.1")
    port = int(os.getenv("AION_DEMO_PORT", "8007"))
    log_level = os.getenv("AION_DEMO_LOG_LEVEL", "info")

    uvicorn.run(
        "backend.modules.aion_demo.demo_bridge:app",
        host=host,
        port=port,
        reload=False,
        log_level=log_level,
    )


if __name__ == "__main__":
    main()
