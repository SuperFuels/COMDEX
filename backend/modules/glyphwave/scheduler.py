"""
Phase-aware scheduler and timing system for GlyphWave.
Implements PLL, jitter, drift compensation, and SQI gating
for coherence-aware beam scheduling.
"""

from typing import Dict, Any
from time import time, perf_counter
import random


class PhaseScheduler:
    def __init__(self):
        # Default policy with SQI gating
        self._policy: Dict[str, Any] = {
            "pll_lock": True,
            "slot_ms": 5.0,
            "qos_preempt": True,
            "sqi_min_threshold": 0.25,  # 🧠 SQI gating threshold
        }
        self._metrics = {
            "scheduled": 0,
            "last_lock_error": 0.0,
            "gated_events": 0,
        }
        self.pll = PhaseLockedLoop()
        self.jitter = JitterMonitor()
        self.drift = DriftCompensator()

    # --- Policy Configuration ---
    def set_policy(self, policy: Dict[str, Any]) -> None:
        self._policy.update(policy or {})

    # --- SQI Gating Helper ---
    def _get_current_sqi(self) -> float:
        """Safely read current SQI score from TelemetryHandler if available."""
        try:
            # Use globally registered instance (monkeypatched or live)
            global TelemetryHandler
            if "TelemetryHandler" in globals():
                handler = TelemetryHandler()
                latest = getattr(handler, "_last_metrics", None)
                if latest and "sqi_score" in latest:
                    return float(latest["sqi_score"])
            # Fallback import if not globally injected
            from backend.modules.glyphwave.telemetry_handler import TelemetryHandler as TH
            handler = TH()
            latest = getattr(handler, "_last_metrics", None)
            if latest and "sqi_score" in latest:
                return float(latest["sqi_score"])
        except Exception:
            pass
        return 1.0

    # --- Main Scheduling Function ---
    def schedule(self, gwip: Dict[str, Any]) -> Dict[str, Any]:
        now = time()
        env = gwip.setdefault("envelope", {})
        env["scheduled_at"] = now
        env["slot"] = self._policy["slot_ms"]
        env["pll_offset"] = self.pll.adjust(now)
        env["jitter"] = self.jitter.estimate()
        env["drift"] = self.drift.get_offset()

        # ✅ SQI Gating Layer
        sqi_score = self._get_current_sqi()
        sqi_min = self._policy.get("sqi_min_threshold", 0.25)

        if sqi_score < sqi_min:
            env["gated"] = True
            env["reason"] = f"SQI below threshold ({sqi_score:.3f} < {sqi_min:.2f})"
            self._metrics["gated_events"] += 1
            self._metrics["scheduled"] += 1
            self._metrics["last_lock_error"] = env["pll_offset"]

            print(f"[PhaseScheduler] ⚠️ Gated GWIP due to low SQI ({sqi_score:.3f})")

            # 🧠 NEW: Emit SoulLaw veto event when SQI is too low
            try:
                from backend.modules.codex.collapse_trace_exporter import log_sqi_soullaw_veto
                log_sqi_soullaw_veto(
                    sqi_score=sqi_score,
                    glyph=gwip.get("id", "gwip_unknown"),
                    threshold=sqi_min,
                )
            except Exception as e:
                print(f"[PhaseScheduler] ⚠️ SoulLaw bridge logging failed: {e}")

            return gwip  # packet marked but not scheduled

        # Otherwise, schedule normally
        env["gated"] = False
        env["reason"] = "ok"

        self._metrics["scheduled"] += 1
        self._metrics["last_lock_error"] = env["pll_offset"]

        return gwip

    # --- Metrics Accessor ---
    def metrics(self) -> Dict[str, Any]:
        return dict(self._metrics)


# --- Supporting Components ---

class PhaseLockedLoop:
    def __init__(self, alpha=0.05):
        self.alpha = alpha
        self.lock_time = perf_counter()
        self.offset = 0.0

    def adjust(self, now: float) -> float:
        expected = self.lock_time + self.offset
        error = now - expected
        self.offset += self.alpha * error
        return error


class JitterMonitor:
    def __init__(self):
        self.samples = []
        self.window_size = 32

    def estimate(self) -> float:
        sample = random.gauss(0, 0.002)  # simulate jitter sample
        self.samples.append(sample)
        if len(self.samples) > self.window_size:
            self.samples.pop(0)
        return max(self.samples) - min(self.samples) if self.samples else 0.0


class DriftCompensator:
    def __init__(self):
        self.base_time = perf_counter()
        self.drift_per_sec = random.uniform(-0.0005, 0.0005)

    def get_offset(self) -> float:
        elapsed = perf_counter() - self.base_time
        return self.drift_per_sec * elapsed