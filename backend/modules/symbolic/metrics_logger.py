# backend/modules/symbolic/metrics_logger.py

import os
import time
import json
from pathlib import Path
from typing import Optional, Dict

LOG_PATH = Path("logs/symbolic_metrics/")
LOG_FILE = LOG_PATH / "metrics_log.jsonl"

def init_logger():
    LOG_PATH.mkdir(parents=True, exist_ok=True)

def log_metrics(
    collapse_per_sec: float,
    decoherence_rate: float,
    *,
    iso_timestamp: bool = False,
    extra: Optional[Dict] = None
):
    """
    Log symbolic runtime metrics to a JSONL file.

    Args:
        collapse_per_sec: Number of symbolic collapses per second.
        decoherence_rate: Decoherence drift rate.
        iso_timestamp: If True, adds ISO 8601 human-readable timestamp.
        extra: Optional dictionary of additional metrics to log.
    """
    init_logger()
    
    entry = {
        "timestamp": time.time(),
        "collapse_per_sec": collapse_per_sec,
        "decoherence_rate": decoherence_rate,
    }

    if iso_timestamp:
        entry["timestamp_iso"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if extra and isinstance(extra, dict):
        entry.update(extra)

    try:
        with open(LOG_FILE, "a", buffering=1) as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[metrics_logger] Failed to write metrics log: {e}")