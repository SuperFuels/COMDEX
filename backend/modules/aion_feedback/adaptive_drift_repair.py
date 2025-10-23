#!/usr/bin/env python3
"""
🩹 Adaptive Drift Repair Loop
─────────────────────────────
Monitors RSI (Resonance Stability Index) and triggers self-correction when
coherence drops below threshold for a sustained period.

Restores stability by damping transitions, resetting predictive bias confidence,
and easing gradient pressure. Logs each repair to data/feedback/drift_repair.log
and emits a telemetry pulse for dashboard visibility.
"""

import time
import json
from pathlib import Path
from backend.quant.telemetry.resonance_telemetry import ResonanceTelemetry


class AdaptiveDriftRepair:
    def __init__(
        self,
        log_path: str = "data/feedback/drift_repair.log",
        threshold: float = 0.6,
        persist_cycles: int = 1,  # trigger immediately for now
    ):
        # Threshold and persistence parameters
        self.threshold = threshold
        self.persist_cycles = persist_cycles
        self.low_counter = 0
        self.last_repair_time = 0.0

        # Logging setup
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Telemetry interface
        self.telemetry = ResonanceTelemetry()

    # ─────────────────────────────────────────────
    def check_and_repair(self, rsi: float, pb, grad, force: bool = False) -> bool:
        """
        Monitor RSI and trigger repair when coherence remains low
        for N cycles, or immediately if 'force=True'.
        """
        repaired = False

        # Step 1 — RSI trend monitoring
        if rsi < self.threshold:
            self.low_counter += 1
        else:
            self.low_counter = 0

        # Step 2 — Repair condition check
        if force or self.low_counter >= self.persist_cycles:
            self.low_counter = 0
            repaired = True
            self.last_repair_time = time.time()

            # Step 3 — Dampen unstable transitions
            if hasattr(pb, "transitions") and isinstance(pb.transitions, dict):
                for k in list(pb.transitions.keys()):
                    pb.transitions[k] *= 0.95

            # Step 4 — Lower confidence to promote re-exploration
            if hasattr(pb, "prediction_confidence"):
                pb.prediction_confidence *= 0.9

            # Step 5 — Normalize ε and k back toward baseline
            pb.epsilon = max(0.1, getattr(pb, "epsilon", 0.2) * 0.95)
            pb.k = max(3, int(getattr(pb, "k", 5) * 0.95))

            # Step 6 — Reduce gradient feedback intensity
            if hasattr(grad, "avg_strength"):
                grad.avg_strength *= 0.9

            # Step 7 — Compose log entry
            entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "RSI": round(rsi, 4),
                "epsilon": round(pb.epsilon, 4),
                "k": pb.k,
                "avg_strength": round(getattr(grad, "avg_strength", 0.0), 6),
                "forced": force,
            }

            # Step 8 — Write to log file
            with open(self.log_path, "a", buffering=1) as f:
                f.write(json.dumps(entry) + "\n")
                f.flush()

            # Step 9 — Emit telemetry pulse
            pulse = {
                "event": "drift_repair",
                "timestamp": entry["timestamp"],
                "RSI": entry["RSI"],
                "epsilon": entry["epsilon"],
                "k": entry["k"],
                "avg_strength": entry["avg_strength"],
            }
            try:
                self.telemetry.emit(pulse)
            except Exception:
                pass  # telemetry emission should never crash repair loop

            print(
                f"🩹 Drift repair triggered "
                f"(RSI={rsi:.3f}) → reset ε={pb.epsilon:.2f}, k={pb.k}"
                f"{' [FORCED]' if force else ''}"
            )

        return repaired


# ─────────────────────────────────────────────
# Diagnostic entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # Quick verification run — ensures file writing and telemetry pulse works
    from backend.modules.aion_prediction.predictive_bias_layer import PredictiveBias
    from backend.modules.aion_learning.gradient_correction_layer import GradientCorrectionLayer

    adr = AdaptiveDriftRepair(threshold=0.9)
    pb = PredictiveBias()
    grad = GradientCorrectionLayer()

    print("🔧 Testing Adaptive Drift Repair (forced low RSI)...")
    adr.check_and_repair(0.3, pb, grad, force=True)

    if adr.log_path.exists():
        print(f"✅ Log written to: {adr.log_path}")
        print(adr.log_path.read_text().splitlines()[-1])
    else:
        print("❌ Log file missing — check permissions or path.")