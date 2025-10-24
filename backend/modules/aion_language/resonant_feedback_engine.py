# ================================================================
# 🌀 Phase 45F.7 — Resonant Feedback Learning Engine
# ================================================================
"""
Adapts the MeaningFieldEngine (MFG) resonance weights based on
entanglement coherence (ρ) and intensity (I) metrics.

Input:
    data/tests/meaningfield_qmath_entanglement.json
    data/qtensor/langfield_resonance.qdata.json

Output:
    data/qtensor/langfield_resonance_adapted.qdata.json
"""

import json, math, time, logging
from pathlib import Path

logger = logging.getLogger(__name__)

METRICS_PATH = Path("data/tests/meaningfield_qmath_entanglement.json")
QDATA_PATH   = Path("data/qtensor/langfield_resonance.qdata.json")
OUT_PATH     = Path("data/qtensor/langfield_resonance_adapted.qdata.json")

class ResonantFeedbackEngine:
    def __init__(self, learning_rate: float = 0.05):
        self.learning_rate = learning_rate
        self.tensor = {}
        self.metrics = {}

    # ------------------------------------------------------------
    def _safe_load(self, path):
        if not path.exists():
            logger.warning(f"[Feedback] Missing {path}")
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ------------------------------------------------------------
    def load(self):
        self.tensor = self._safe_load(QDATA_PATH).get("tensor_field", {})
        self.metrics = self._safe_load(METRICS_PATH)
        logger.info(f"[Feedback] Loaded {len(self.tensor)} tensor atoms and entanglement metrics.")

    # ------------------------------------------------------------
    def adapt(self):
        """Reinforce or dampen lexical amplitudes according to ρ and I."""
        rho = float(self.metrics.get("avg_coherence", 1.0))
        intensity = float(self.metrics.get("avg_intensity", 1.0))
        adjustment = 1.0 + self.learning_rate * (rho - 0.9) + 0.02 * (intensity - 1.0)

        count = 0
        for wid, t in self.tensor.items():
            old_val = t.get("q_val", 1.0)
            new_val = round(old_val * adjustment, 6)
            self.tensor[wid]["q_val"] = new_val
            count += 1
        logger.info(f"[Feedback] Adapted {count} lexical weights with factor={adjustment:.3f}")

    # ------------------------------------------------------------
    def export(self):
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.time(),
                "tensor_field": self.tensor,
                "meta": {
                    "schema": "LangFieldResonance.v2",
                    "adaptation": True,
                    "learning_rate": self.learning_rate
                }
            }, f, indent=2)
        logger.info(f"[Feedback] Exported adapted tensor → {OUT_PATH}")

# ------------------------------------------------------------
# CLI Entry
# ------------------------------------------------------------
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    engine = ResonantFeedbackEngine(learning_rate=0.05)
    engine.load()
    engine.adapt()
    engine.export()
    print("✅ Resonant Feedback Learning phase complete.")