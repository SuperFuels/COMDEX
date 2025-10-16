"""
Tessaris • πₛ Phase-Closure Validator
------------------------------------------------------------
Validates resonance completion across the Symatics layers.
Ensures that symbolic ↔ photonic ↔ holographic coherence
has re-stabilized after LightWave or QFC feedback events.

Typical use:
    validator = PhaseClosureValidator(threshold=0.82)
    if validator.validate(metrics):
        print("πₛ closure stable ✅")
    else:
        print("πₛ closure incomplete ⚠️")
"""

from typing import List, Dict, Any
import statistics
import logging
import time

logger = logging.getLogger(__name__)


class PhaseClosureValidator:
    """
    Evaluates πₛ phase-closure stability using beam/QFC metrics.
    """

    def __init__(self, threshold: float = 0.8, min_samples: int = 3):
        """
        Args:
            threshold: Minimum mean coherence (qscore) to consider closure complete.
            min_samples: Minimum number of recent telemetry points required.
        """
        self.threshold = threshold
        self.min_samples = min_samples
        self.last_validation_time = None
        self.last_result = None

    # ────────────────────────────────────────────────
    def validate(self, metrics: List[Dict[str, Any]]) -> bool:
        """Check average qscore across telemetry records."""
        if not metrics or len(metrics) < self.min_samples:
            logger.debug("[πₛ] Not enough samples for closure validation.")
            return False

        try:
            scores = [m.get("qscore", 0.0) for m in metrics if isinstance(m, dict)]
            avg_q = statistics.fmean(scores)
            self.last_validation_time = time.time()
            self.last_result = avg_q >= self.threshold

            state = "stable ✅" if self.last_result else "unstable ⚠️"
            logger.info(f"[πₛ] Phase closure {state} | mean q={avg_q:.3f} ≥ {self.threshold}")
            return self.last_result
        except Exception as e:
            logger.error(f"[πₛ] Validation failed: {e}")
            return False

    # ────────────────────────────────────────────────
    def report(self) -> Dict[str, Any]:
        """Return the latest validation snapshot."""
        return {
            "timestamp": self.last_validation_time,
            "closure_ok": self.last_result,
            "threshold": self.threshold,
        }