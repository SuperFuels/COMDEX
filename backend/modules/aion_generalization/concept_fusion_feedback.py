#!/usr/bin/env python3
"""
🧬  Aion Stability -> Fusion Feedback Loop - Phase 35.8
───────────────────────────────────────────────────────────────────────────────
Continuously adjusts the concept fusion threshold according to global RSI
variance (stability index) computed from the resonance stream.
"""

import json, statistics, time
from pathlib import Path
import numpy as np

RSI_PATH = Path("data/feedback/resonance_stream.jsonl")
OUTPUT_PATH = Path("data/feedback/fusion_threshold.json")

BASE_THRESHOLD = 0.02       # default RSI similarity threshold
ALPHA = 3.5                 # sensitivity factor
WINDOW = 200                # last N RSI samples to evaluate

def load_rsi_values():
    if not RSI_PATH.exists():
        print(f"⚠️ No RSI stream found at {RSI_PATH}")
        return []
    vals = []
    with RSI_PATH.open() as f:
        for line in f:
            try:
                rec = json.loads(line)
                if "RSI" in rec:
                    vals.append(float(rec["RSI"]))
            except Exception:
                continue
    return vals[-WINDOW:]

def compute_threshold(rsi_values):
    if len(rsi_values) < 2:
        return BASE_THRESHOLD
    var = np.var(rsi_values)
    # Clamp variance into [0, 0.1] to avoid runaway scaling
    var = min(max(var, 0.0), 0.1)
    fusion_threshold = BASE_THRESHOLD * (1 + ALPHA * var)
    return round(fusion_threshold, 5), var

def main():
    print("🔁  Running Stability -> Fusion Feedback Loop (Phase 35.8)...")
    rsi_values = load_rsi_values()
    if not rsi_values:
        print("⚠️ No RSI data available.")
        return

    threshold, var = compute_threshold(rsi_values)
    data = {
        "timestamp": time.time(),
        "base_threshold": BASE_THRESHOLD,
        "variance": var,
        "adjusted_fusion_threshold": threshold,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w") as f:
        json.dump(data, f, indent=2)

    print(f"📊 Mean RSI variance = {var:.5f}")
    print(f"⚙️  Adjusted fusion threshold = {threshold:.5f}")
    print(f"✅ Saved -> {OUTPUT_PATH}")

if __name__ == "__main__":
    main()