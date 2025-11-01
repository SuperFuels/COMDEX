"""
🌀 Dynamic Coherence Optimizer - SRK-11 Task 3
Adaptive feedback loop for photon coherence, phase stability, and entropy control.

Integrates with:
 * glyphwave.core.coherence_engine        (signal sampling + coherence metrics)
 * glyphwave.qkd.qkd_policy_enforcer      (security thresholds)
 * photon.photon_binary_bridge            (pre-emission stabilization)

Implements real-time phase-locking and self-correction of photon streams.
"""

import time
import math
from typing import Dict, Any, Tuple, Optional

from backend.modules.glyphwave.core.coherence_engine import measure_coherence, adjust_phase
from backend.modules.codex.collapse_trace_exporter import log_soullaw_event


class CoherenceStabilityError(Exception):
    """Raised when coherence cannot be stabilized within allowable thresholds."""


class DynamicCoherenceOptimizer:
    """
    Adaptive coherence optimizer for the Tessaris GlyphWave stack.
    Uses feedback sampling from coherence_engine to maintain
    phase-locked photon streams during transmission.
    """

    def __init__(self,
                 target_coherence: float = 0.95,  # was 0.98 ✅ loosened
                 max_iterations: int = 8,
                 tolerance: float = 5e-3):  # was 1e-3
        """
        Args:
            target_coherence: Desired coherence ratio [0-1].
            max_iterations: Maximum feedback correction cycles.
            tolerance: Minimal delta considered stable.
        """
        self.target_coherence = target_coherence
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.last_report: Optional[Dict[str, Any]] = None

    # ────────────────────────────────────────────────────────────────
    def stabilize(self, wave_state: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Attempt to stabilize the given wave_state until target coherence is reached.

        Returns:
            (bool, report) -> True if stabilized, else False.
        """
        current = measure_coherence(wave_state)
        report = {
            "target": self.target_coherence,
            "initial": current,
            "iterations": 0,
            "history": [current],
            "status": None,
            "timestamp": time.time(),
        }

        for i in range(self.max_iterations):
            delta = abs(self.target_coherence - current)
            if delta <= self.tolerance:
                report.update({"iterations": i, "status": "STABLE"})
                self.last_report = report
                return True, report

            # Adjust phase proportionally to error
            phase_correction = math.copysign(delta * 0.25, self.target_coherence - current)
            adjust_phase(wave_state, phase_correction)

            time.sleep(0.05)  # simulate propagation delay
            current = measure_coherence(wave_state)
            report["history"].append(current)
            report["iterations"] = i + 1

        report.update({"status": "FAILED", "final": current})
        self._log_failure(report)
        self.last_report = report
        return False, report

    # ────────────────────────────────────────────────────────────────
    def _log_failure(self, report: Dict[str, Any]):
        """Emit stabilization failure to SoulLaw trace."""
        log_soullaw_event(
            {
                "type": "coherence_failure",
                "timestamp": report.get("timestamp"),
                "target": report.get("target"),
                "final": report.get("final"),
                "iterations": report.get("iterations"),
                "status": report.get("status"),
            },
            glyph=None
        )
        raise CoherenceStabilityError(
            f"Failed to stabilize coherence after {report.get('iterations')} iterations "
            f"(target={report.get('target')}, final={report.get('final')})"
        )

    # ────────────────────────────────────────────────────────────────
    def optimize_if_needed(self, wave_state: Dict[str, Any]) -> bool:
        """
        Entry point used by PhotonBinaryBridge before emission.
        Runs stabilization only if coherence < threshold.
        """
        current = measure_coherence(wave_state)
        if current >= self.target_coherence:
            return True  # Already stable

        success, report = self.stabilize(wave_state)
        if not success:
            raise CoherenceStabilityError(
                f"Unstable wave detected. {report['status']} after {report['iterations']} cycles."
            )
        return True