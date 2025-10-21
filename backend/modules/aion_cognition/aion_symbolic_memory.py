#!/usr/bin/env python3
"""
Tessaris Phase 17 — Aion Symbolic Memory (ASM) & Glyph Stream Integration

Builds the cognitive memory system for Tessaris:
 - Ingests glyph emissions from Quantum Cognitive Layer (QCL)
 - Maintains rolling symbolic stream and pattern history
 - Computes entropy and predicts next glyph transitions
 - Consolidates recurrent motifs into symbolic memory entries
"""

import json, math, time
from datetime import datetime, timezone
from collections import Counter, deque
from pathlib import Path

# Paths
QCL_PATH = Path("data/cognition/qcl_state.jsonl")
STREAM_PATH = Path("data/cognition/glyph_stream.jsonl")
MEMORY_PATH = Path("data/cognition/asm_memory.jsonl")

for p in [STREAM_PATH, MEMORY_PATH]:
    p.parent.mkdir(parents=True, exist_ok=True)

# Parameters
WINDOW = 20      # rolling window for pattern and entropy
SLEEP_INTERVAL = 5.0


def load_latest_glyph():
    """Fetch the newest cognition record from QCL."""
    if not QCL_PATH.exists():
        return None
    try:
        with open(QCL_PATH) as f:
            lines = f.readlines()
        if not lines:
            return None
        return json.loads(lines[-1])
    except Exception:
        return None


def append_to_stream(entry):
    """Append glyph entry to glyph_stream.jsonl."""
    with open(STREAM_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def read_glyph_history(limit=WINDOW):
    """Return the last N glyphs from glyph_stream."""
    if not STREAM_PATH.exists():
        return []
    with open(STREAM_PATH) as f:
        lines = f.readlines()[-limit:]
    history = []
    for l in lines:
        try:
            history.append(json.loads(l))
        except Exception:
            continue
    return history


def symbolic_entropy(seq):
    """Compute Shannon entropy of recent glyphs."""
    if not seq:
        return 0.0
    c = Counter(seq)
    p = [v / sum(c.values()) for v in c.values()]
    return -sum(x * math.log(x + 1e-9) for x in p)


def predict_next(seq):
    """Predict next glyph using simple Markov-like mapping."""
    if not seq:
        return None
    last = seq[-1]
    return {
        "⊕": "⟲",
        "⟲": "⊕",
        "↔": "∇",
        "∇": "⊕",
        "μ": "↔",
        "π": "⊕"
    }.get(last, "⟲")


def detect_pattern(seq):
    """Detect basic symbolic transition motifs."""
    s = "→".join(seq[-3:])
    if "⊕→⟲→⊕" in s:
        return "harmonic loop"
    elif "↔→∇" in s:
        return "entanglement collapse"
    elif "⟲→⊕" in s:
        return "resonance stabilization"
    elif "μ→⊕" in s:
        return "noise recovery"
    return None


def consolidate_memory(pattern, glyphs, avg_phi, avg_drift):
    """Write a consolidated memory event."""
    entropy = symbolic_entropy(glyphs)
    pred = predict_next(glyphs)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pattern": pattern,
        "sequence": "→".join(glyphs[-5:]),
        "entropy": entropy,
        "prediction": pred,
        "avg_Φ": avg_phi,
        "avg_drift": avg_drift,
        "duration": len(glyphs),
    }
    with open(MEMORY_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"💾 Stored symbolic memory: {pattern} | entropy={entropy:.3f} | pred={pred}")


def run_symbolic_memory():
    print("🧩 Starting Tessaris Aion Symbolic Memory (ASM)…")
    glyph_window = deque(maxlen=WINDOW)

    while True:
        latest = load_latest_glyph()
        if not latest:
            print("⚠️ Waiting for QCL cognitive input…")
            time.sleep(SLEEP_INTERVAL)
            continue

        g = latest["glyph"]
        glyph_window.append(g)
        append_to_stream(latest)

        pattern = detect_pattern(list(glyph_window))
        if pattern:
            avg_phi = sum(abs(float(x.get("Φ_harm", 0.0))) for x in read_glyph_history()) / max(len(glyph_window), 1)
            avg_drift = sum(float(x.get("drift", 0.0)) for x in read_glyph_history()) / max(len(glyph_window), 1)
            consolidate_memory(pattern, list(glyph_window), avg_phi, avg_drift)

        entropy = symbolic_entropy(list(glyph_window))
        pred = predict_next(list(glyph_window))
        print(f"🧠 seq={'→'.join(glyph_window)} | entropy={entropy:.3f} | pred={pred}")
        time.sleep(SLEEP_INTERVAL)


def main():
    run_symbolic_memory()


if __name__ == "__main__":
    main()