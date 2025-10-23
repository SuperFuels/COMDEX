"""
Equilibrium Field Solver — Phase 40B
------------------------------------
Computes harmonic inverse fields (Ψ_c) that counteract semantic drift.
Used by the Harmonic Stabilizer Engine (HSE) to restore coherence.
"""

import math, logging
logger = logging.getLogger(__name__)

class EquilibriumFieldSolver:
    def __init__(self):
        self.last_field = None

    # ─────────────────────────────────────────────
    def compute_inverse_field(self, drift: dict, gain: float = 0.3):
        """
        Given a drift vector {magnitude, phase, target}, compute the
        harmonic inverse field Ψ_c = -γ * ΔΨ.
        Returns dict(amplitude, phase, target).
        """
        if not drift:
            logger.warning("[EFS] Empty drift vector.")
            return None

        mag = drift.get("magnitude", 0.0)
        phase = drift.get("phase", 0.0)
        target = drift.get("target", "unknown")

        # Phase inversion (π shift) + adaptive gain
        inv_phase = (phase + math.pi) % (2 * math.pi)
        amp = round(gain * mag, 5)

        field = {"amplitude": amp, "phase": inv_phase, "target": target}
        self.last_field = field
        logger.info(f"[EFS] Generated inverse field → amp={amp}, phase={inv_phase:.3f}")
        return field


# ─────────────────────────────────────────────
try:
    EFS
except NameError:
    try:
        EFS = EquilibriumFieldSolver()
        print("⚖️ EquilibriumFieldSolver global instance initialized as EFS")
    except Exception as e:
        print(f"⚠️ Could not initialize EFS: {e}")
        EFS = None