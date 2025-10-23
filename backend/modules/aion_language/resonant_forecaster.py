"""
ResonantForecaster — Phase 40E (Updated)
----------------------------------------
Forecasts near-future resonance stability using recent harmonic memory (HMP),
drift (RDM), and temporal harmonics (THM). Outputs a short-horizon forecast
and a single Stability Risk Index (SRI) for control.

This update ensures safe defaults for RDM/THM attributes and robust operation
even before first detection or initialization.
"""

import time, json, math, logging
from pathlib import Path
from statistics import mean

from backend.modules.aion_language.harmonic_memory_profile import HMP
from backend.modules.aion_language.resonant_drift_monitor import RDM
from backend.modules.aion_language.temporal_harmonics_monitor import THM

logger = logging.getLogger(__name__)
FORECAST_PATH = Path("data/analysis/harmonic_forecast.json")

def _clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


class ResonantForecaster:
    def __init__(self):
        self.last_forecast = None
        # smoothing factors
        self.alpha = 0.5   # EWMA for drift magnitude
        self.beta  = 0.4   # EWMA for harmonic variance

    def _ewma(self, seq, alpha, default=0.0):
        if not seq:
            return default
        y = seq[0]
        for x in seq[1:]:
            y = alpha * x + (1 - alpha) * y
        return y

    def forecast(self, horizon=5):
        """
        Returns:
          {
            "timestamp": ...,
            "sri": <0..1>,
            "drift_trend": [...],
            "variance_trend": [...],
            "phase_trend": [...],
            "horizon": N
          }
        """
        recent = HMP.get_recent_events(n=50)
        drift_series = [e.get("drift_mag", 0.0) for e in recent]
        amp_series   = [e.get("amplitude", 0.0) for e in recent]

        # Safe retrievals from monitors
        last_drift = getattr(RDM, "last_drift", {"magnitude": 0.0})
        last_harm  = getattr(THM, "last_harmonics", {"variance": 0.0, "phase_mean": 0.0})

        drift_mag  = last_drift.get("magnitude", 0.0)
        last_var   = last_harm.get("variance", 0.0)
        last_phase = last_harm.get("phase_mean", 0.0)

        # Seeds for the forecast
        drift_seed = self._ewma(drift_series + [drift_mag], self.alpha, default=drift_mag)
        var_seed   = self._ewma(amp_series  + [last_var],   self.beta,  default=last_var)

        # Simple AR(1)-style projection with mild decay toward 0
        phi = 0.72
        drift_trend    = [drift_seed * (phi ** i) for i in range(1, horizon + 1)]
        variance_trend = [var_seed   * (phi ** i) for i in range(1, horizon + 1)]
        phase_trend    = [last_phase for _ in range(horizon)]

        # Stability Risk Index (higher = more risk)
        sri_raw = 0.6 * mean(drift_trend) + 0.4 * mean(variance_trend)
        sri = _clip(sri_raw)

        forecast = {
            "timestamp": time.time(),
            "sri": round(sri, 3),
            "drift_trend": [round(x, 3) for x in drift_trend],
            "variance_trend": [round(x, 3) for x in variance_trend],
            "phase_trend": [round(x, 3) for x in phase_trend],
            "horizon": horizon,
            "target": last_drift.get("target", "concept:unknown")
        }

        FORECAST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(FORECAST_PATH, "w") as f:
            json.dump(forecast, f, indent=2)

        logger.info(f"[RFE] SRI={forecast['sri']:.3f} horizon={horizon}")
        self.last_forecast = forecast
        return forecast


# ─────────────────────────────────────────
# Global instance
# ─────────────────────────────────────────
try:
    RFE
except NameError:
    RFE = ResonantForecaster()
    print("🔮 ResonantForecaster global instance initialized as RFE")