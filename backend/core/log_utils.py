# -*- coding: utf-8 -*-
# File: backend/core/log_utils.py
"""
Structured Logging Utility (I9)
─────────────────────────────────────────────
Ensures consistent schema for all runtime logs (CPU, RegistryBridge, GlyphDispatcher).
"""

import json
import time
from typing import Any, Dict


def make_log_event(
    event: str,
    op: str,
    canonical: str,
    args: Any = None,
    kwargs: Dict[str, Any] = None,
    status: str = None,
    result: Any = None,
    error: str = None,
) -> Dict[str, Any]:
    """Builds a structured log event with unified schema."""
    return {
        "event": event,
        "timestamp": time.time(),
        "op": op,
        "canonical": canonical,
        "args": list(args) if args is not None else [],
        "kwargs": kwargs or {},
        "status": status,
        "result": result,
        "error": error,
    }


def log_event(event_dict: Dict[str, Any]) -> None:
    """Pretty-print a structured log event as a single JSON line."""
    print("[LOG]", json.dumps(event_dict, ensure_ascii=False))