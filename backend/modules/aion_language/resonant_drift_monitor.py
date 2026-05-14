"""
ResonantDriftMonitor - Phase 39C : Coherence Deviation Watcher
---------------------------------------------------------------
Monitors the Resonant Memory Cache (RMC) for temporal coherence decay.
When drift exceeds threshold, the system spawns stabilization goals
through the GoalEngine and reinforces the AKG to re-center meaning.
"""

import time, logging
from statistics import mean
from backend.modules.aion_language.resonant_memory_cache import RMC
from backend.modules.aion_photon.goal_engine import GOALS
from backend.modules.aion_knowledge import knowledge_graph_core as akg

logger = logging.getLogger(__name__)
DRIFT_THRESHOLD = 0.4


class ResonantDriftMonitor:
    def __init__(self):
        self.last_snapshot = {}

    def get_drift_vector(self):
        """
        Returns the most recently detected drift vector in normalized form.
        Used by the Harmonic Stabilizer Engine (HSE) for corrective action.
        """
        if not hasattr(self, "last_drift") or not self.last_drift:
            return None

        drift = self.last_drift
        return {
            "magnitude": float(drift.get("magnitude", 0.0)),
            "phase": float(drift.get("phase", 0.0)),
            "target": drift.get("target", "unknown"),
        }

    # ─────────────────────────────────────────────
    def analyze_drift(self):
        """Compare current cache to last snapshot and compute Δcoherence."""
        if not RMC.cache:
            logger.warning("[Drift] No resonance data available.")
            return []

        drift_events = []
        for cid, entry in RMC.cache.items():
            prev = self.last_snapshot.get(cid, {})
            prev_c = prev.get("coherence", entry["coherence"])
            delta = round(entry["coherence"] - prev_c, 3)
            if abs(delta) >= DRIFT_THRESHOLD:
                drift_events.append((cid, delta))
                self._handle_drift(cid, delta)
        self.last_snapshot = {cid: dict(v) for cid, v in RMC.cache.items()}
        logger.info(f"[Drift] Analyzed {len(RMC.cache)} entries -> {len(drift_events)} drift events.")
        return drift_events

    # ─────────────────────────────────────────────
    def _handle_drift(self, cid: str, delta: float):
        """Trigger goal formation for unstable concepts."""
        direction = "increase" if delta < 0 else "reduce"
        goal_name = f"stabilize_{cid.split(':')[-1]}"
        priority = min(1.0, abs(delta))
        GOALS.create_goal(goal_name, priority=priority)
        akg.add_triplet(f"concept:{cid}", "experiences_drift", str(delta))
        logger.warning(f"[Drift] Concept {cid} drifted {delta:+.3f} -> spawned goal:{goal_name}")


# ─────────────────────────────────────────────
# Global Instance
# ─────────────────────────────────────────────
try:
    RDM
except NameError:
    RDM = ResonantDriftMonitor()
    print("🌊 ResonantDriftMonitor global instance initialized as RDM")