# ──────────────────────────────────────────────
#  Tessaris • Morphic Feedback Controller (Stage 3 HQCE)
#  Regulates ψ–κ–T field stability and coherence feedback in real time.
# ──────────────────────────────────────────────

import numpy as np
import time
import logging
from typing import Dict, List, Optional, Any

try:
    # Optional live telemetry link
    from backend.modules.holograms.hst_websocket_streamer import broadcast_replay_paths_hst
except Exception:
    broadcast_replay_paths_hst = None

logger = logging.getLogger(__name__)


class MorphicFeedbackController:
    """
    HQCE Stage-3 controller — stabilizes holographic ψ–κ–T field coherence.

    • Monitors live ψ–κ–T signatures from HSTGenerator
    • Adjusts resonance field parameters adaptively
    • Outputs correction maps for renderer + analyzer feedback
    """

    def __init__(
        self,
        target_coherence: float = 0.92,
        smoothing_factor: float = 0.25,
        regulator_gain: float = 0.5,
        damping: float = 0.8,
    ):
        self.target_coherence = target_coherence
        self.smoothing_factor = smoothing_factor
        self.regulator_gain = regulator_gain
        self.damping = damping
        self.last_signature: Optional[Dict[str, float]] = None
        self.last_adjustment: Optional[Dict[str, Any]] = None
        self._stabilization_log: List[Dict[str, Any]] = []

        self._last_deviation = 0.0
        self._smoothed_coherence = None
        logger.info("[MorphicFeedbackController] Initialized HQCE feedback regulator.")

    # ────────────────────────────────────────────
    #  Core Regulation Entry
    # ────────────────────────────────────────────
    def regulate(
        self, psi_kappa_T: Dict[str, float], field_nodes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compute coherence deviation and return correction parameters.
        Also emits optional broadcast to visualization layer.
        """
        if not psi_kappa_T or not field_nodes:
            logger.warning(
                "[MorphicFeedbackController] Missing ψ–κ–T or field data, skipping regulation."
            )
            return {"status": "no_data"}

        psi = psi_kappa_T.get("psi", 0.0)
        kappa = psi_kappa_T.get("kappa", 0.0)
        T = psi_kappa_T.get("T", 1.0)

        # Smooth average coherence
        coherence_values = [n.get("coherence", 0.5) for n in field_nodes]
        avg_coherence = float(np.mean(coherence_values)) if coherence_values else 0.5
        if self._smoothed_coherence is None:
            self._smoothed_coherence = avg_coherence
        else:
            self._smoothed_coherence = (
                self.smoothing_factor * avg_coherence
                + (1 - self.smoothing_factor) * self._smoothed_coherence
            )

        deviation = self.target_coherence - self._smoothed_coherence

        # Adaptive gain modulation (reduce overshoot)
        gain = self.regulator_gain * (1.0 - 0.5 * abs(self._last_deviation))
        corrective_factor = gain * deviation * self.damping
        self._last_deviation = deviation

        # Compute adjustments
        adjusted_psi = psi + corrective_factor * self.smoothing_factor
        adjusted_kappa = kappa - corrective_factor * 0.5

        adjustment = {
            "timestamp": time.time(),
            "psi": adjusted_psi,
            "kappa": adjusted_kappa,
            "T": T,
            "avg_coherence": self._smoothed_coherence,
            "target_coherence": self.target_coherence,
            "correction": corrective_factor,
            "gain": gain,
            "status": "stabilized" if abs(deviation) < 0.02 else "adjusting",
        }

        self.last_signature = psi_kappa_T
        self.last_adjustment = adjustment
        self._stabilization_log.append(adjustment)

        # Optional live telemetry broadcast
        if broadcast_replay_paths_hst:
            try:
                payload = {
                    "type": "morphic_feedback",
                    "psi_kappa_T": adjustment,
                    "timestamp": time.time(),
                }
                broadcast_replay_paths_hst(payload)
            except Exception as e:
                logger.debug(f"[MorphicFeedbackController] Telemetry broadcast failed: {e}")

        logger.info(
            f"[MorphicFeedbackController] ΔC={deviation:+.4f} → {adjustment['status']} | ψ={adjusted_psi:.3f} κ={adjusted_kappa:.3f}"
        )
        return adjustment

    # ────────────────────────────────────────────
    #  Field Diagnostics
    # ────────────────────────────────────────────
    def compute_field_stability(self, field_nodes: List[Dict[str, Any]]) -> float:
        """Return 0–1 coherence stability metric (1 = uniform)."""
        coherences = [n.get("coherence", 0.5) for n in field_nodes]
        if not coherences:
            return 0.0
        std_dev = float(np.std(coherences))
        return max(0.0, 1.0 - std_dev)

    def summarize_recent(self, n: int = 5) -> List[Dict[str, Any]]:
        """Return last n stabilization records."""
        return self._stabilization_log[-n:]

    def export_last_adjustment(self) -> Optional[Dict[str, Any]]:
        """Return last adjustment for external systems."""
        return self.last_adjustment

    # ────────────────────────────────────────────
    #  Visualization Support
    # ────────────────────────────────────────────
    def generate_field_overlay(self, field_nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Produce an overlay with coherence corrections per node.
        """
        if not field_nodes or not self.last_adjustment:
            return field_nodes

        corr = self.last_adjustment.get("correction", 0.0)
        for n in field_nodes:
            c = n.get("coherence", 0.5)
            n["coherence"] = np.clip(c + corr * 0.1, 0.0, 1.0)
            n["stabilized_color"] = self._color_from_coherence(n["coherence"])
        return field_nodes

    def _color_from_coherence(self, v: float) -> str:
        v = np.clip(v, 0.0, 1.0)
        if v < 0.5:
            return f"rgb({int(0)}, {int(128 + v*255)}, 255)"
        else:
            g = int(255 * (1 - (v - 0.5) * 2))
            return f"rgb(255, {g}, {int(120 + 120*v)})"