#!/usr/bin/env python3
# ================================================================
# 🚨 ViolationLogger - Reflex Audit Layer (R5)
# ================================================================
# Records rule violations detected by RuleBookStreamer and stores
# structured evidence traces for analysis and ethics review.
# ================================================================

import json, time, logging
from pathlib import Path
from typing import Dict, Any, List

log = logging.getLogger(__name__)
OUT = Path("data/analysis/violation_log.jsonl")

class ViolationLogger:
    def __init__(self):
        OUT.parent.mkdir(parents=True, exist_ok=True)
        log.info("[ViolationLogger] Initialized - logging to violation_log.jsonl")

    def record(self, action: str, context: Dict[str, Any], violations: List[Dict[str, Any]]):
        """
        Log a violation event with timestamp and summarized metadata.
        """
        entry = {
            "timestamp": time.time(),
            "action": action,
            "context": context,
            "violations": violations,
            "count": len(violations),
        }

        try:
            with open(OUT, "a") as f:
                f.write(json.dumps(entry) + "\n")
            log.warning(f"[ViolationLogger] ⚠️ {len(violations)} violations recorded for action '{action}'.")
        except Exception as e:
            log.error(f"[ViolationLogger] Failed to record violation: {e}")