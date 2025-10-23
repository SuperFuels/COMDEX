"""
ResonantSynchronizer — Phase 39A
--------------------------------
Aligns imported photon-based meaning fields with Aion’s current
internal semantic resonance state.
"""

import json, math, time, logging
from statistics import mean
from backend.modules.aion_language.meaning_field_engine import MFG

logger = logging.getLogger(__name__)

class ResonantSynchronizer:
    def __init__(self):
        self.last_alignment = None

    def align(self, imported_field: dict):
        if not imported_field or not MFG.field:
            logger.warning("[Sync] Missing fields for synchronization.")
            return None

        clusters_self = {c["center"]: c for c in MFG.field.get("clusters", [])}
        clusters_in = {c["center"]: c for c in imported_field.get("clusters", [])}

        shared = set(clusters_self.keys()) & set(clusters_in.keys())
        if not shared:
            logger.warning("[Sync] No overlapping concepts.")
            return {"delta": 1.0, "alignment": 0.0}

        drift_vals = []
        for k in shared:
            a, b = clusters_self[k], clusters_in[k]
            drift_vals.append(abs(a["emotion_bias"] - b["emotion_bias"]) +
                              abs(a["goal_alignment"] - b["goal_alignment"]))

        drift = mean(drift_vals)
        alignment = 1.0 - min(1.0, drift)
        self.last_alignment = alignment
        logger.info(f"[Sync] Alignment={alignment:.3f}, Drift={drift:.3f}")
        return {"delta": drift, "alignment": alignment}