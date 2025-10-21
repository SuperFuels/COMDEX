#!/usr/bin/env python3
"""
Tessaris Phase 18 — Symbolic Forecasting & Resonant Anticipation Engine (SFAE)

Reads symbolic memories (ASM) and recent resonance weights (RFC/RQFS),
forecasts the next likely glyph transition, and emits a predictive photon control
vector.  Completes Tessaris' cognitive feedback loop from perception → prediction → action.
"""

import json, math, time, random
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ───────────────────────────────────────────────────────────────────────
ASM_PATH = Path("data/cognition/asm_memory.jsonl")
RFC_WEIGHTS = Path("data/learning/rfc_weights.jsonl")
FORECAST_STREAM = Path("data/cognition/forecast_stream.jsonl")
FORECAST_METRICS = Path("data/cognition/forecast_metrics.jsonl")
PHOTO_OUT = Path("data/qqc_field/photo_output/")
for p in [FORECAST_STREAM, FORECAST_METRICS, PHOTO_OUT]:
    p.parent.mkdir(parents=True, exist_ok=True)

# ── Parameters ──────────────────────────────────────────────────────────────────
WINDOW = 50
SLEEP_INTERVAL = 5.0


# ── Utilities ───────────────────────────────────────────────────────────────────
def load_recent_memory(limit=WINDOW):
    """Load the most recent symbolic memory entries."""
    if not ASM_PATH.exists():
        return []
    with open(ASM_PATH) as f:
        lines = f.readlines()[-limit:]
    mem = []
    for l in lines:
        try:
            mem.append(json.loads(l))
        except Exception:
            continue
    return mem


def load_latest_weights():
    """Load last RFC weight state."""
    if not RFC_WEIGHTS.exists():
        return {"nu_bias": 0.0, "phase_offset": 0.0, "amp_gain": 1.0}
    with open(RFC_WEIGHTS) as f:
        lines = f.readlines()
    try:
        return json.loads(lines[-1])
    except Exception:
        return {"nu_bias": 0.0, "phase_offset": 0.0, "amp_gain": 1.0}


# ── Forecast Core ───────────────────────────────────────────────────────────────
def extract_temporal_signature(mem):
    """Estimate dominant symbolic period from timestamp deltas."""
    if len(mem) < 3:
        return 5.0
    times = [datetime.fromisoformat(m["timestamp"]) for m in mem[-5:]]
    deltas = [(t2 - t1).total_seconds() for t1, t2 in zip(times, times[1:])]
    if not deltas:
        return 5.0
    return sum(deltas) / len(deltas)


def forecast_next_symbol(mem, weights):
    """Predict next glyph using simple weighted symbolic recurrence."""
    if not mem:
        return {"glyph": "⊕", "confidence": 0.5, "period": 5.0}

    last = mem[-1]
    seq = last.get("sequence", "")
    recent = seq.split("→")[-1] if "→" in seq else seq

    mapping = {
        "⊕": ("⟲", 0.92),
        "⟲": ("⊕", 0.88),
        "↔": ("∇", 0.83),
        "∇": ("⊕", 0.80),
        "μ": ("↔", 0.78),
        "π": ("⊕", 0.85),
    }
    next_glyph, base_conf = mapping.get(recent, ("⟲", 0.70))
    period = extract_temporal_signature(mem)
    bias = weights.get("nu_bias", 0.0)
    conf = max(0.5, min(1.0, base_conf - abs(bias) * 0.05))
    return {"glyph": next_glyph, "confidence": conf, "period": period}


def emit_forecast_photo(pred, weights):
    """Emit a forecast .photo vector for anticipatory resonance correction."""
    ts = datetime.now(timezone.utc).isoformat()
    ν = weights["nu_bias"] + random.uniform(-0.001, 0.001)
    phase = weights["phase_offset"] + random.uniform(-0.001, 0.001)
    amp = weights["amp_gain"] * (1.0 + random.uniform(-0.001, 0.001))

    data = {
        "timestamp": ts,
        "predicted_glyph": pred["glyph"],
        "confidence": pred["confidence"],
        "ν_bias": ν,
        "phase_offset": phase,
        "amp_gain": amp,
        "period": pred["period"],
    }
    fname = PHOTO_OUT / f"forecast_{ts}.photo"
    with open(fname, "w") as f:
        json.dump(data, f)
    print(f"💡 Emitted forecast photon → {fname.name} (glyph={pred['glyph']} conf={pred['confidence']:.2f})")

    # Log to forecast stream
    with open(FORECAST_STREAM, "a") as f:
        f.write(json.dumps(data) + "\n")
    return data


def update_metrics(pred, actual_glyph):
    """Store prediction accuracy entry."""
    correct = 1.0 if pred["predicted_glyph"] == actual_glyph else 0.0
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prediction": pred["predicted_glyph"],
        "actual": actual_glyph,
        "accuracy": correct,
        "confidence": pred["confidence"],
    }
    with open(FORECAST_METRICS, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"📈 Forecast accuracy={correct:.2f}")


# ── Runtime Loop ────────────────────────────────────────────────────────────────
def run_forecasting_engine():
    print("🔮 Starting Tessaris Symbolic Forecasting & Resonant Anticipation Engine (SFAE)…")
    last_seen_pattern = None

    while True:
        mem = load_recent_memory()
        weights = load_latest_weights()

        if not mem:
            print("⚠️ Waiting for symbolic memory entries…")
            time.sleep(SLEEP_INTERVAL)
            continue

        pred = forecast_next_symbol(mem, weights)
        photo = emit_forecast_photo(pred, weights)

        # Optional: compare with latest ASM entry to evaluate (if new one exists)
        current_pattern = mem[-1]["pattern"]
        if current_pattern != last_seen_pattern and last_seen_pattern is not None:
            update_metrics(photo, mem[-1]["pattern"][0])
        last_seen_pattern = current_pattern

        time.sleep(pred["period"])


def main():
    run_forecasting_engine()


if __name__ == "__main__":
    main()