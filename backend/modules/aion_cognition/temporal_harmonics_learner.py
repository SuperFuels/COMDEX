"""
🎶 Temporal Harmonics Learner - Phase 51
---------------------------------------
Detects cyclic patterns in resonance data (ρ, Ī, SQI) across sessions.
Uses FFT-based spectral analysis to identify dominant harmonic frequencies
and long-term cognitive resonance rhythms.

Inputs :
    data/telemetry/resonance_trends.csv
Outputs:
    data/telemetry/harmonics_report.json
"""

import csv, json, time, logging, math
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

TRENDS_PATH = Path("data/telemetry/resonance_trends.csv")
OUT_PATH    = Path("data/telemetry/harmonics_report.json")

#───────────────────────────────────────────────
# 📡 Load and Preprocess Trend Data
#───────────────────────────────────────────────
def _safe_load_trends():
    """Safely read resonance_trends.csv and return timestamps and SQI values."""
    if not TRENDS_PATH.exists():
        logger.warning("[Harmonics] No resonance trend data found.")
        return [], []
    ts, sqi = [], []
    with open(TRENDS_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts.append(float(row["ts"]))
                sqi.append(float(row["SQI"]))
            except Exception:
                continue
    return ts, sqi


#───────────────────────────────────────────────
# 🎛️ Harmonic Analysis Core
#───────────────────────────────────────────────
def analyze_harmonics(ts, sqi):
    """Perform FFT to identify dominant frequency and harmonic strength."""
    if len(sqi) < 4:
        logger.warning("[Harmonics] Not enough data points for analysis.")
        return {}

    # Normalize signal and compute FFT
    values = np.array(sqi) - np.mean(sqi)
    spectrum = np.fft.fft(values)
    freqs = np.fft.fftfreq(len(sqi), d=1)
    amplitudes = np.abs(spectrum)

    # Exclude DC component (index 0)
    idx = np.argmax(amplitudes[1:]) + 1
    dominant_freq = round(abs(freqs[idx]), 5)
    harmonic_strength = round(amplitudes[idx] / np.max(amplitudes), 4)

    report = {
        "timestamp": time.time(),
        "dominant_freq": dominant_freq,
        "harmonic_strength": harmonic_strength,
        "samples": len(sqi),
        "schema": "TemporalHarmonics.v1"
    }
    logger.info(f"[Harmonics] freq={dominant_freq}, strength={harmonic_strength}")
    return report


#───────────────────────────────────────────────
# 💾 Processing Cycle
#───────────────────────────────────────────────
def compute_temporal_harmonics():
    """End-to-end execution: load -> analyze -> export harmonics report."""
    ts, sqi = _safe_load_trends()
    report = analyze_harmonics(ts, sqi)
    if not report:
        return None

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    json.dump(report, open(OUT_PATH, "w"), indent=2)
    logger.info(f"[Harmonics] Exported harmonics report -> {OUT_PATH}")
    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    compute_temporal_harmonics()