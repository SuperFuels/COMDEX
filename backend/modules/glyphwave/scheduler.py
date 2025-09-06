"""
Phase-aware scheduler and timing system for GlyphWave.
Implements PLL, jitter, and drift compensation for beam alignment.
"""

from typing import Dict, Any
from time import time, perf_counter
import random


class PhaseScheduler:
    def __init__(self):
        self._policy: Dict[str, Any] = {
            "pll_lock": True,
            "slot_ms": 5.0,
            "qos_preempt": True,
        }
        self._metrics = {
            "scheduled": 0,
            "last_lock_error": 0.0,
        }
        self.pll = PhaseLockedLoop()
        self.jitter = JitterMonitor()
        self.drift = DriftCompensator()

    def set_policy(self, policy: Dict[str, Any]) -> None:
        self._policy.update(policy or {})

    def schedule(self, gwip: Dict[str, Any]) -> Dict[str, Any]:
        now = time()
        env = gwip.setdefault("envelope", {})
        env["scheduled_at"] = now
        env["slot"] = self._policy["slot_ms"]
        env["pll_offset"] = self.pll.adjust(now)
        env["jitter"] = self.jitter.estimate()
        env["drift"] = self.drift.get_offset()

        self._metrics["scheduled"] += 1
        self._metrics["last_lock_error"] = env["pll_offset"]

        return gwip

    def metrics(self) -> Dict[str, Any]:
        return dict(self._metrics)


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