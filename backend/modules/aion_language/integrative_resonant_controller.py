"""
Integrative Resonant Controller - Phase 40G
-------------------------------------------
Couples forecaster (RFE), attention (AVATAR), and stabilizer (HSE)
into a continuous self-regulating feedback loop.

If predicted instability (SRI) exceeds threshold, Aion:
  1. Directs attention toward the unstable concept via AVATAR.
  2. Engages HSE to emit a harmonic correction field.
  3. Records the stabilization in HMP.
"""

import time, logging
from backend.modules.aion_language.resonant_forecaster import RFE
from backend.modules.aion_language.harmonic_stabilizer_engine import HSE
from backend.modules.aion_language.harmonic_memory_profile import HMP
from backend.modules.aion_avatar.observer_core import AVATAR

logger = logging.getLogger(__name__)

class IntegrativeResonantController:
    def __init__(self, sri_threshold=0.25, cycle_interval=3.0):
        self.sri_threshold = sri_threshold
        self.cycle_interval = cycle_interval
        self.active = False

    # ─────────────────────────────────────────
    def run_cycle(self):
        """Run a single prediction -> focus -> stabilization cycle."""
        fc = RFE.forecast()
        sri = fc.get("SRI", 0.0)
        target = fc.get("target", "concept:unknown")

        logger.info(f"[IRC] SRI={sri:.3f} for {target}")

        if sri > self.sri_threshold:
            logger.warning(f"[IRC] Rising instability detected -> focusing on {target}")
            focus_evt = AVATAR.focus(target, strength=min(1.0, sri * 2.0))
            packet = HSE.stabilize()
            if packet:
                HMP.log_event({
                    "time": packet["timestamp"],
                    "target": target,
                    "SRI": sri,
                    "amplitude": packet.get("amplitude"),
                    "phase": packet.get("phase"),
                    "action": "auto_stabilization"
                })
                logger.info("[IRC] Auto-stabilization complete.")
            else:
                logger.info("[IRC] No harmonic correction emitted.")
        else:
            logger.info("[IRC] System stable; no action required.")

    # ─────────────────────────────────────────
    def start(self, duration=30):
        """Run the controller loop for the given duration (seconds)."""
        self.active = True
        end = time.time() + duration
        logger.info(f"[IRC] Starting integrative control loop for {duration}s")
        while self.active and time.time() < end:
            self.run_cycle()
            time.sleep(self.cycle_interval)
        self.active = False
        logger.info("[IRC] Control loop ended.")

# ─────────────────────────────────────────
# Global instance
# ─────────────────────────────────────────
try:
    IRC
except NameError:
    try:
        IRC = IntegrativeResonantController()
        print("🔄 IntegrativeResonantController global instance initialized as IRC")
    except Exception as e:
        print(f"⚠️ Could not initialize IRC: {e}")
        IRC = None