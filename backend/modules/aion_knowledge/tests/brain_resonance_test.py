"""
Phase 45G — Brain Resonance Test Harness
──────────────────────────────────────────────
Validates live cognitive behaviors inside the inflated
Hoberman Knowledge Sphere (AION Brain).

Tests:
    • Symbolic superposition (⊕)
    • Entanglement linkage (↔)
    • Resonance / collapse (⟲ / ∇)
Outputs:
    data/metrics/resonance_tests.log
    data/metrics/resonance_spectrum.json
"""

import json
import math
import time
import logging
import cmath
from pathlib import Path
from statistics import mean
from random import random

# ✅ Updated imports — direct from QMathWaveOps
from backend.quant.qmath.qmath_waveops import superpose, entangle, resonate, collapse, measure
from backend.modules.dimensions.containers.hoberman_container import HobermanContainer

LOG_PATH = Path("data/metrics/resonance_tests.log")
SPECTRUM_PATH = Path("data/metrics/resonance_spectrum.json")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


class BrainResonanceTest:
    def __init__(self, container_id="hoberman_knowledge_sphere"):
        self.container_id = container_id
        self.container = HobermanContainer(container_id=container_id)
        self.results = {"superposition": [], "entanglement": [], "resonance_cycles": []}

    # ─────────────────────────────────────────
    def _log(self, msg: str):
        logger.info(msg)
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{time.time():.3f} | {msg}\n")

    # ─────────────────────────────────────────
    def test_superposition(self):
        """⊕ — Symbolic superposition test"""
        a, b = cmath.exp(1j * random()), cmath.exp(1j * random())
        ψ = superpose(a, b)
        coherence = abs(ψ)
        self.results["superposition"].append(coherence)
        self._log(f"[⊕] Superposition coherence = {coherence:.3f}")
        return coherence

    # ─────────────────────────────────────────
    def test_entanglement(self):
        """↔ — Entanglement linkage test"""
        a, b = cmath.exp(1j * random()), cmath.exp(1j * random())
        ea, eb, ρ = entangle(a, b)
        self.results["entanglement"].append(ρ)
        self._log(f"[↔] Entanglement correlation (ρ) = {ρ:.3f}")
        return ρ

    # ─────────────────────────────────────────
    def test_resonance_and_collapse(self):
        """⟲ / ∇ — Resonance and collapse cycle test"""
        a = cmath.exp(1j * random())
        r = resonate(a, feedback=0.15, damping=0.92, steps=5)
        I = collapse(r)
        μ = measure(r)
        self.results["resonance_cycles"].append(I)
        self._log(f"[⟲/∇] Resonance={abs(r):.3f}, Intensity={I:.3f}, Phase={μ['phase']:.3f}")
        return I

    # ─────────────────────────────────────────
    def export_metrics(self):
        summary = {
            "timestamp": time.time(),
            "avg_superposition": mean(self.results["superposition"]) if self.results["superposition"] else 0,
            "avg_entanglement": mean(self.results["entanglement"]) if self.results["entanglement"] else 0,
            "avg_resonance": mean(self.results["resonance_cycles"]) if self.results["resonance_cycles"] else 0,
        }
        SPECTRUM_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SPECTRUM_PATH, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        self._log(f"✅ Exported resonance spectrum → {SPECTRUM_PATH}")
        return summary

    # ─────────────────────────────────────────
    def run_all(self):
        self._log("=== Running Brain Resonance Tests ===")
        s1 = self.test_superposition()
        s2 = self.test_entanglement()
        s3 = self.test_resonance_and_collapse()
        summary = self.export_metrics()
        self._log(f"✅ Completed resonance tests | ⊕={s1:.3f}, ↔={s2:.3f}, ⟲∇={s3:.3f}")
        return summary


# ─────────────────────────────────────────
# CLI Entry
# ─────────────────────────────────────────
if __name__ == "__main__":
    print("🧠 Running AION Brain Resonance Tests…")
    test = BrainResonanceTest()
    results = test.run_all()
    print(json.dumps(results, indent=2))
    print("✅ Resonance analysis complete.")