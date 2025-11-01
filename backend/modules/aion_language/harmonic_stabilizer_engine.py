"""
Harmonic Stabilizer Engine - Phase 40A
--------------------------------------
Actively corrects resonance drift detected by RDM or predicted by THM.
Computes inverse harmonic fields via EFS and emits them through the
Photon-AKG bridge. Logs all corrections to HMP for adaptive learning.
"""

import time, logging, math, random
from backend.modules.aion_language.resonant_drift_monitor import RDM
from backend.modules.aion_language.temporal_harmonics_monitor import THM
from backend.modules.aion_language.equilibrium_field_solver import EFS
from backend.modules.aion_language.harmonic_memory_profile import HMP
from backend.bridges.photon_AKG_bridge import PAB  # signal emission layer

logger = logging.getLogger(__name__)

class HarmonicStabilizerEngine:
    def __init__(self):
        self.last_correction = None
        self.gamma = 0.3  # adaptive gain coefficient

    # ─────────────────────────────────────────────
    def stabilize(self):
        """
        Core correction loop.
        1. Read drift vectors from RDM and THM.
        2. Compute counterfield via EFS.
        3. Emit corrective photon signal.
        4. Record the event in HMP.
        """
        drift_vector = RDM.get_drift_vector()
        predicted = THM.predict_instability()

        if not drift_vector and not predicted:
            logger.info("[HSE] No drift or predicted instability detected.")
            return None

        # Combine detected + predicted drift
        total_drift = self._combine_drift(drift_vector, predicted)
        if not total_drift:
            return None

        logger.info(f"[HSE] Stabilizing drift magnitude {total_drift['magnitude']:.3f}")

        # Compute corrective harmonic field
        correction = EFS.compute_inverse_field(total_drift, gain=self.gamma)
        if not correction:
            logger.warning("[HSE] No correction vector computed.")
            return None

        # Emit correction to Photon-AKG Bridge
        packet = {
            "timestamp": time.time(),
            "type": "harmonic_correction",
            "amplitude": correction.get("amplitude", 0.0),
            "phase": correction.get("phase", 0.0),
            "target": correction.get("target", "unknown"),
        }
        PAB.emit(packet)

        # Record in memory profile
        HMP.log_event({
            "time": packet["timestamp"],
            "drift_mag": total_drift["magnitude"],
            "amplitude": packet["amplitude"],
            "phase": packet["phase"],
            "target": packet["target"],
            "gain": self.gamma,
        })

        self.last_correction = packet
        logger.info("[HSE] Harmonic correction emitted and logged.")
        # Update gain after each correction
        self.adapt_gain()
        return packet

    # ─────────────────────────────────────────────
    def _combine_drift(self, drift, predicted):
        """Fuse detected and predicted drifts into a single composite vector."""
        if not drift and not predicted:
            return None
        if drift and not predicted:
            return drift
        if predicted and not drift:
            return predicted

        # Weighted fusion based on temporal confidence
        m = 0.5 * (drift["magnitude"] + predicted["magnitude"])
        phase = (drift.get("phase", 0.0) + predicted.get("phase", 0.0)) / 2
        return {"magnitude": m, "phase": phase, "target": drift.get("target", "unknown")}

    # ─────────────────────────────────────────────
    # Phase 40D - Adaptive Gain Learning
    # ─────────────────────────────────────────────
    def adapt_gain(self):
        """
        Adjusts internal gain coefficient γ based on past correction history.
        Uses error feedback from HMP (difference between drift magnitude and correction amplitude).
        """
        try:
            history = HMP.get_recent_events(n=20)
        except Exception:
            history = []

        if not history:
            return self.gamma

        # Compute average correction error
        errors = []
        for e in history:
            drift_mag = e.get("drift_mag", 0.0)
            amp = e.get("amplitude", 0.0)
            if drift_mag > 0:
                err = abs(drift_mag - amp) / drift_mag
                errors.append(err)

        if not errors:
            return self.gamma

        mean_err = sum(errors) / len(errors)

        # Adjust γ inversely to mean error
        if mean_err > 0.4:
            self.gamma *= 1.15  # increase response
        elif mean_err < 0.2:
            self.gamma *= 0.9   # reduce response

        # Clamp γ between 0.1 and 1.0
        self.gamma = max(0.1, min(self.gamma, 1.0))
        logger.info(f"[HSE] Adaptive gain adjusted -> γ={self.gamma:.3f}")
        return self.gamma


# ─────────────────────────────────────────────
# Global instance
# ─────────────────────────────────────────────
try:
    HSE
except NameError:
    try:
        HSE = HarmonicStabilizerEngine()
        print("🎵 HarmonicStabilizerEngine global instance initialized as HSE")
    except Exception as e:
        print(f"⚠️ Could not initialize HSE: {e}")
        HSE = None