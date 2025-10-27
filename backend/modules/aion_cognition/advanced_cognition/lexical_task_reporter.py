#!/usr/bin/env python3
"""
📊 AION Advanced Cognition — Reporter
─────────────────────────────────────
Aggregates task performance metrics and exports to analysis reports.
"""

import json, logging, time
from pathlib import Path

log = logging.getLogger(__name__)

REPORT_PATH = Path("data/analysis/aion_advanced_cognition_report.json")
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

def log_cycle(cycle: int, summary: dict):
    if REPORT_PATH.exists():
        data = json.loads(REPORT_PATH.read_text())
    else:
        data = []

    record = {
        "cycle": cycle,
        **summary,
        "timestamp": time.time(),
    }
    data.append(record)
    REPORT_PATH.write_text(json.dumps(data, indent=2))
    log.info(f"[LCE] 🧾 Logged cognition report for cycle {cycle}")
    return record