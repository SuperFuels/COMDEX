#!/usr/bin/env python3
"""
📊 Phase 48B — Semantic Benchmark Reporter
Stores MCI and comprehension trends across cycles.
"""

import json
from pathlib import Path

REPORT_PATH = Path("data/analysis/aion_semantic_benchmark.json")
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

def log_cycle(cycle: int, summary: dict):
    if REPORT_PATH.exists():
        try:
            data = json.loads(REPORT_PATH.read_text())
        except Exception:
            data = []
    else:
        data = []
    data.append({"cycle": cycle, **summary})
    REPORT_PATH.write_text(json.dumps(data, indent=2))
    return True