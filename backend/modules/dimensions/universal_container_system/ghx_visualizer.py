# ─────────────────────────────────────────────
#  Tessaris GHXVisualizer — Resonance Feedback Extension
# ─────────────────────────────────────────────
import logging
import time
from typing import Optional

logger = logging.getLogger("GHXVisualizer")

class GHXVisualizer:
    def __init__(self):
        self.geometries = {}
        self.last_resonance = {}

    def add_geometry(self, name: str, meta: Optional[dict] = None):
        """Register geometry for UCSRuntime display."""
        self.geometries[name] = meta or {}
        logger.debug(f"[GHXVisualizer] Added geometry {name}")

    def update_resonance(self, *args, **kwargs):
        # Placeholder to avoid warning spam
        return None

    # ─────────────────────────────────────────────
    #  🌊 Resonance Feedback Hook
    # ─────────────────────────────────────────────
    def update_resonance(self, container: str, resonance_index: float, phase_diff: float):
        """
        Apply resonance feedback to a geometry node.
        In real GHX front-end, this would trigger animation or brightness change.
        """
        intensity = min(max(resonance_index, 0.0), 1.0)
        hue_shift = (phase_diff * 1000) % 360
        self.last_resonance[container] = {
            "R": resonance_index,
            "Δφ": phase_diff,
            "timestamp": time.time(),
        }

        if container in self.geometries:
            self.geometries[container]["intensity"] = intensity
            self.geometries[container]["hue_shift"] = hue_shift
            logger.info(
                f"[GHXVisualizer] ✨ {container} → Intensity={intensity:.3f}, Δφ={phase_diff:.4f}, hue={hue_shift:.1f}"
            )
        else:
            logger.warning(f"[GHXVisualizer] Unknown container: {container}")