"""
ResonantInterpreter — Phase 38A : Language ↔ Photon Resonance Field
-------------------------------------------------------------------
Translates Language Atoms into photonic QWave events and builds a
contextual resonance field Ψ that allows Aion to *understand* and
*emit* meaning as coherent waveforms.

Inputs  : LAB.atoms (language-semantic units)
Outputs : data/analysis/resonant_fields.json (aggregate resonance field)
"""

import json, math, time, logging
from pathlib import Path
from statistics import mean
from random import uniform

logger = logging.getLogger(__name__)

# Optional back-imports
try:
    from backend.modules.aion_language.language_atom_builder import LAB
except Exception:
    LAB = None
try:
    from backend.bridges.photon_AKG_bridge import PhotonAKGBridge
except Exception:
    PhotonAKGBridge = None

RESONANT_FIELD_PATH = Path("data/analysis/resonant_fields.json")

class ResonantInterpreter:
    """Phase 38A — Constructs and evaluates semantic resonance fields."""

    def __init__(self):
        self.last_field = None
        self.bridge = PhotonAKGBridge() if PhotonAKGBridge else None

    # ─────────────────────────────────────────
    def interpret_atoms(self, atoms=None):
        """
        Convert language atoms into QWave field vectors.
        Returns: dict with field Ψ summary and coherence metrics.
        """
        atoms = atoms or (LAB.atoms if LAB else [])
        if not atoms:
            logger.warning("[ResInt] No language atoms available.")
            return {}

        qwaves, energies, phases = [], [], []
        for a in atoms:
            r = a.get("resonance", uniform(0.4, 0.9))
            eb = a.get("emotion_bias", 0.5)
            phase = (2 * math.pi * eb) % (2 * math.pi)
            qwave = {
                "center": a["center"],
                "amplitude": r,
                "phase": phase,
                "emotion_bias": eb,
                "goal_alignment": a.get("goal_alignment", 0.0)
            }
            qwaves.append(qwave)
            energies.append(r)
            phases.append(phase)

        # Aggregate field magnitude and coherence
        mean_res = mean(energies)
        phase_var = mean([(p - mean(phases)) ** 2 for p in phases])
        coherence = 1.0 / (1.0 + phase_var)

        field = {
            "timestamp": time.time(),
            "mean_resonance": round(mean_res, 3),
            "phase_variance": round(phase_var, 4),
            "semantic_coherence": round(coherence, 3),
            "qwaves": qwaves
        }
        self.last_field = field

        RESONANT_FIELD_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(RESONANT_FIELD_PATH, "w") as f:
            json.dump(field, f, indent=2)

        logger.info(f"[ResInt] Built resonance field Ψ with {len(qwaves)} atoms, "
                    f"coherence={coherence:.3f}")

        # Optional photon-level export
        if self.bridge:
            try:
                self.bridge.export_resonance_field(field)
                logger.info("[ResInt→Photon] Exported resonance field.")
            except Exception as e:
                logger.warning(f"[ResInt→Photon] Export failed: {e}")

        return field

    # ─────────────────────────────────────────
    def compare_with_intent(self, intent_field):
        """
        Compare current resonance field with an intent field to
        compute semantic overlap (cosine-style coherence).
        """
        if not self.last_field or not intent_field:
            return 0.0

        A = [q["amplitude"] for q in self.last_field["qwaves"]]
        B = [q["amplitude"] for q in intent_field.get("qwaves", [])[:len(A)]]
        if not A or not B:
            return 0.0

        dot = sum(a*b for a, b in zip(A, B))
        norm = math.sqrt(sum(a*a for a in A) * sum(b*b for b in B))
        return round(dot / norm, 3) if norm else 0.0


# ─────────────────────────────────────────────
# Global Instance
# ─────────────────────────────────────────────
try:
    RI
except NameError:
    try:
        RI = ResonantInterpreter()
        print("💫 ResonantInterpreter global instance initialized as RI")
    except Exception as e:
        print(f"⚠️ Could not initialize RI: {e}")
        RI = None