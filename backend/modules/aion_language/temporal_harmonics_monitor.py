"""
TemporalHarmonicsMonitor - Phase 39D : Predictive Resonance Analysis
-------------------------------------------------------------------
Analyzes resonance-coherence history from the Resonant Memory Cache (RMC)
to detect oscillatory or decaying temporal patterns.

When harmonic energy exceeds threshold, it spawns predictive goals such as
'anticipate_phase_shift' or 'pre_stabilize_<concept>'.
"""

import time, logging, math
from statistics import mean
from backend.modules.aion_language.resonant_memory_cache import RMC
from backend.modules.aion_photon.goal_engine import GOALS
from backend.modules.aion_knowledge import knowledge_graph_core as akg

logger = logging.getLogger(__name__)
HARMONIC_THRESHOLD = 0.5


class TemporalHarmonicsMonitor:
    def __init__(self):
        # store short-term coherence history per concept
        self.history = {}   # {cid: [coherence_1, coherence_2, ...]}

    def predict_instability(self):
        """
        Phase 40A - Predict upcoming semantic or resonance instability.
        Returns a drift-like vector when harmonic oscillations exceed thresholds.
        Used by the Harmonic Stabilizer Engine (HSE) for anticipatory correction.
        """
        if not hasattr(self, "last_harmonics") or not self.last_harmonics:
            return None

        h = self.last_harmonics
        # Predict drift magnitude based on energy variance
        energy = float(h.get("energy", 0.0))
        variance = float(h.get("variance", 0.0))

        # Simple threshold for instability
        if variance > 0.3 or energy > 1.2:
            return {
                "magnitude": min(1.0, 0.5 * variance + 0.3 * energy),
                "phase": h.get("phase_mean", 0.0),
                "target": h.get("target", "concept:unknown"),
            }
        return None

    # ─────────────────────────────────────────────
    def update_history(self):
        """Record current coherence values from RMC."""
        if not RMC.cache:
            logger.warning("[THM] No cache data to record.")
            return
        for cid, entry in RMC.cache.items():
            self.history.setdefault(cid, []).append(entry.get("coherence", 0.0))
            # keep rolling window of last 10 samples
            self.history[cid] = self.history[cid][-10:]

    # ─────────────────────────────────────────────
    def analyze_harmonics(self):
        """
        Compute oscillation index for each concept using pseudo-FFT energy.
        Detect periodic resonance fluctuations.
        """
        self.update_history()
        events = []

        for cid, series in self.history.items():
            if len(series) < 4:
                continue

            # mean-removed differences
            diffs = [series[i] - mean(series) for i in range(len(series))]
            energy = sum(x**2 for x in diffs) / len(diffs)
            # normalize 0-1
            h_energy = min(1.0, math.sqrt(energy))
            if h_energy >= HARMONIC_THRESHOLD:
                self._predictive_goal(cid, h_energy)
                events.append((cid, h_energy))

        logger.info(f"[THM] Evaluated {len(self.history)} concepts -> {len(events)} harmonic alerts.")
        return events

    # ─────────────────────────────────────────────
    def _predictive_goal(self, cid: str, energy: float):
        """Spawn a forward-looking stabilization goal."""
        goal_name = f"pre_stabilize_{cid.split(':')[-1]}"
        priority = min(1.0, 0.5 + 0.5 * energy)
        GOALS.create_goal(goal_name, priority=priority)
        akg.add_triplet(cid, "predicts_phase_instability", str(round(energy, 3)))
        logger.warning(f"[THM] ⚠️ Predicted phase oscillation in {cid} -> spawned goal:{goal_name} (E={energy:.3f})")


# ─────────────────────────────────────────────
# Global Instance
# ─────────────────────────────────────────────
try:
    THM
except NameError:
    THM = TemporalHarmonicsMonitor()
    print("🕓 TemporalHarmonicsMonitor global instance initialized as THM")