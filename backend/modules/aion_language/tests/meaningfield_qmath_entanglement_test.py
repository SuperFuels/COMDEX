# ================================================================
# 🧩 Phase 45F.6 - MeaningField ↔ QMath Entanglement Test
# ================================================================
"""
Couples the MeaningFieldEngine (MFG) semantic layer with the
LangField QTensor resonance data and drives it through the
QMath wave operators to simulate symbolic entanglement and
semantic collapse.

Outputs:
    data/tests/meaningfield_qmath_entanglement.json
"""

import json, cmath, logging, random, time
from pathlib import Path
from statistics import mean

# Core engines
from backend.modules.aion_language.meaning_field_engine import MFG
from backend.quant.qmath import qmath_waveops as QW

# Input and output paths
QDATA_PATH = Path("data/qtensor/langfield_resonance.qdata.json")
OUT_PATH   = Path("data/tests/meaningfield_qmath_entanglement.json")

# Logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class MeaningFieldQMathEntangler:
    def __init__(self):
        self.results = {}
        self.timestamp = None

    # ─────────────────────────────────────────
    def _load_qtensor(self):
        if not QDATA_PATH.exists():
            raise FileNotFoundError(f"Missing {QDATA_PATH}")
        with open(QDATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("tensor_field", {})

    # ─────────────────────────────────────────
    def _encode_wave(self, tensor_entry):
        """Convert Φ-ψ-η-Λ tensor entry -> complex wave ψ."""
        Φ = tensor_entry.get("Φ", 1.0)
        ψ = tensor_entry.get("ψ", 1.0)
        η = tensor_entry.get("η", 1.0)
        Λ = tensor_entry.get("Λ", 1.0)
        phase = tensor_entry.get("phase", 0.0)
        amp = (Φ * ψ * η * Λ) ** 0.25
        return amp * cmath.exp(1j * phase)

    # ─────────────────────────────────────────
    def run_entanglement_tests(self):
        logger.info("🔮 Running MeaningField ↔ QMath entanglement tests ...")
        qtensors = self._load_qtensor()
        if not qtensors:
            logger.warning("No QTensor entries found. Aborting.")
            return {}

        # Choose random sample of lexical atoms
        sample_keys = random.sample(list(qtensors.keys()), min(5, len(qtensors)))
        coherence_scores = []
        intensity_scores = []

        for i, key in enumerate(sample_keys):
            t = qtensors[key]
            ψa = self._encode_wave(t)
            ψb = self._encode_wave(random.choice(list(qtensors.values())))

            # Step 1 - superposition
            ψs = QW.superpose(ψa, ψb)
            # Step 2 - entanglement
            ψe_a, ψe_b, ρ = QW.entangle(ψa, ψb)
            # Step 3 - resonance and collapse
            ψr = QW.resonate(ψe_a)
            I  = QW.collapse(ψr)

            coherence_scores.append(ρ)
            intensity_scores.append(I)

            logger.info(f"[{i+1}] {key:<12} ↔ ρ={ρ:.3f}, I={I:.3f}")

        self.results = {
            "timestamp": time.time(),
            "avg_coherence": round(mean(coherence_scores), 3),
            "avg_intensity": round(mean(intensity_scores), 3),
            "samples": sample_keys
        }
        self.timestamp = self.results["timestamp"]
        logger.info(f"✅ Completed entanglement tests | ρ={self.results['avg_coherence']}, I={self.results['avg_intensity']}")

    # ─────────────────────────────────────────
    def export(self):
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"[Entangler] Exported results -> {OUT_PATH}")


# ─────────────────────────────────────────
# CLI Entry
# ─────────────────────────────────────────
if __name__ == "__main__":
    test = MeaningFieldQMathEntangler()
    test.run_entanglement_tests()
    test.export()
    print("✅ MeaningField ↔ QMath Entanglement test complete.")