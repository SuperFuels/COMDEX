# ──────────────────────────────────────────────────────────────
#  Tessaris • D4 — πₛ Phase Closure Validator (v2)
#  Validates global phase loop closure in resonance sync.
# ──────────────────────────────────────────────────────────────

import os
import json
import math
import logging
from datetime import datetime, timezone
from statistics import mean

logger = logging.getLogger("PiSPhaseClosureValidator")

class PiSPhaseClosureValidator:
    """
    Verifies the halting / closure condition for resonance cycles:
        Σ φ_i mod 2πₛ ≈ 0
    ensuring that cumulative phase error remains within tolerance.
    """

    def __init__(self, input_path=None, output_path=None, tolerance=0.1):
        self.input_path = input_path or "backend/logs/phase_state_events.jsonl"
        self.output_path = output_path or "backend/logs/validation/piS_closure_report.jsonl"
        self.tolerance = tolerance
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

    # ──────────────────────────────────────────────────────────────
    def run(self):
        """Main execution entrypoint."""
        try:
            phi_values = self._load_phi_values()
            if not phi_values:
                logger.warning("[πₛ] No φ values found — skipping validation.")
                return {"status": "empty", "Δφₛ": None}

            closure_error = self._compute_closure_error(phi_values)
            report = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "count": len(phi_values),
                "Δφₛ": closure_error,
                "status": "ok" if closure_error <= self.tolerance else "drift",
                "threshold": self.tolerance,
            }

            # Save report
            with open(self.output_path, "a") as f:
                f.write(json.dumps(report) + "\n")

            msg = (
                f"[✅] πₛ closure maintained (Δφₛ = {closure_error:.3f} rad)"
                if closure_error <= self.tolerance
                else f"[⚠️] πₛ drift detected (Δφₛ = {closure_error:.3f} rad)"
            )
            logger.info(msg)
            return report

        except Exception as e:
            logger.error(f"[πₛ] Validation failed: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    # ──────────────────────────────────────────────────────────────
    def _load_phi_values(self):
        """Extract φ entries from the phase_state_events log."""
        if not os.path.exists(self.input_path):
            return []
        values = []
        with open(self.input_path, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    phi = entry.get("phi") or entry.get("Φ") or entry.get("\u03a6")
                    if phi is not None:
                        values.append(float(phi))
                except Exception:
                    continue
        return values

    # ──────────────────────────────────────────────────────────────
    def _compute_closure_error(self, phi_values):
        """Compute closure error modulo 2πₛ."""
        total_phase = sum(phi_values)
        mod_phase = total_phase % (2 * math.pi)
        closure_error = min(mod_phase, 2 * math.pi - mod_phase)
        return closure_error

# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    validator = PiSPhaseClosureValidator()
    result = validator.run()
    print(json.dumps(result, indent=2))