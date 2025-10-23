#!/usr/bin/env python3
"""
📊 Resonance Stability Index (RSI)
──────────────────────────────────
Computes an overall stability score from resonance telemetry.
RSI ∈ [0,1], where 1 = perfectly stable, 0 = chaotic drift.
"""

import math
from backend.quant.telemetry.resonance_telemetry import ResonanceTelemetry


class ResonanceStabilityIndex:
    def __init__(self):
        self.telemetry = ResonanceTelemetry()
        self.last_rsi = 0.0

    def compute(self, metrics=None) -> float:
        """Compute RSI from telemetry metrics."""
        if metrics is None:
            metrics = self.telemetry.update()

        dphi = abs(metrics.get("ΔΦ", 0.0))
        deps = abs(metrics.get("Δε", 0.0))
        mu = metrics.get("μ", 0.0)
        kappa = metrics.get("κ", 0.0)

        # composite drift
        drift = dphi + deps
        coherence = math.exp(-drift * 10.0)
        balance = 1.0 - abs(mu - kappa)
        rsi = max(0.0, min(1.0, 0.5 * coherence + 0.5 * balance))

        self.last_rsi = rsi
        return rsi