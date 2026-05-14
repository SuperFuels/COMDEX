#!/usr/bin/env python3
"""
🧠  Aion Cognitive Stability Heatmap - Phase 35.6.1
───────────────────────────────────────────────────────────────────────────────
Visualizes RSI variance (stability) across concept fields over time windows.
Now optimized for readability and relevance:
    * Blue = stable / coherent resonance
    * Red  = high variance / drift
    * Sorted by dynamic intensity (top concepts only)
"""

import json, statistics, time
from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from backend.modules.aion_knowledge import knowledge_graph_core as akg

# ── Paths ───────────────────────────────────────────────
RSI_PATH = Path("data/feedback/resonance_stream.jsonl")
OUTPUT   = Path("data/analysis/concept_stability_heatmap.png")

# ── Parameters ──────────────────────────────────────────
WINDOW_SIZE  = 50       # RSI samples per time bin
MIN_SAMPLES  = 3        # min RSI per concept per window
COLORMAP     = "coolwarm"
TOP_N        = 30       # only show top-N most dynamic concepts

# ── Utilities ───────────────────────────────────────────
def load_rsi_stream():
    """Load RSI values as (timestamp, symbol, RSI)."""
    if not RSI_PATH.exists():
        print(f"⚠️  No RSI data at {RSI_PATH}")
        return []
    records = []
    with RSI_PATH.open() as f:
        for line in f:
            try:
                r = json.loads(line)
                if "symbol" in r and "RSI" in r and isinstance(r["RSI"], (int, float)):
                    ts = r.get("timestamp") or time.time()
                    records.append((float(ts), r["symbol"], float(r["RSI"])))
            except Exception:
                continue
    return sorted(records, key=lambda x: x[0])

def group_by_window(records, window_size):
    """Group RSI samples into time windows."""
    if not records:
        return []
    windows = []
    current, bucket = records[0][0], []
    for ts, sym, rsi in records:
        if ts - current < window_size:
            bucket.append((sym, rsi))
        else:
            windows.append((current, bucket))
            current = ts
            bucket = [(sym, rsi)]
    if bucket:
        windows.append((current, bucket))
    return windows

# ── Main Process ─────────────────────────────────────────
def build_heatmap():
    print("🧠  Generating Cognitive Stability Heatmap (Phase 35.6.1)...")
    records = load_rsi_stream()
    if not records:
        print("⚠️  No RSI records available.")
        return

    windows = group_by_window(records, WINDOW_SIZE)
    concepts = akg.export_concepts()
    concept_names = list(concepts.keys())
    heatmap_data = []

    for _, (ts, bucket) in enumerate(windows):
        symbol_map = {}
        for sym, rsi in bucket:
            symbol_map.setdefault(sym, []).append(rsi)

        row = []
        for cname in concept_names:
            members = concepts[cname]
            vals = []
            for m in members:
                if m in symbol_map:
                    vals.extend(symbol_map[m])
            if len(vals) >= MIN_SAMPLES:
                var = statistics.pvariance(vals)
            else:
                var = None
            row.append(var if var is not None else np.nan)
        heatmap_data.append(row)

    # Convert -> NumPy matrix
    matrix = np.array(heatmap_data).T
    if matrix.size == 0:
        print("⚠️  No sufficient RSI data for heatmap.")
        return

    # Normalize / clamp
    vmin = np.nanmin(matrix)
    vmax = np.nanmax(matrix)
    matrix = np.nan_to_num(matrix, nan=vmax)

    # ── Enhanced Visualization ───────────────────────────
    plt.figure(figsize=(14, 9))

    # Sort by overall mean variance (most dynamic concepts at top)
    row_means = np.nanmean(matrix, axis=1)
    sort_idx = np.argsort(-row_means)
    matrix = matrix[sort_idx, :]
    concept_names_sorted = [concept_names[i] for i in sort_idx]

    # Show only top N most dynamic concepts
    if len(concept_names_sorted) > TOP_N:
        concept_names_sorted = concept_names_sorted[:TOP_N]
        matrix = matrix[:TOP_N, :]

    im = plt.imshow(
        matrix,
        aspect="auto",
        cmap=COLORMAP,
        origin="lower",
        interpolation="nearest"
    )
    plt.colorbar(im, label="RSI Variance (Drift Intensity)")
    plt.yticks(
        range(len(concept_names_sorted)),
        concept_names_sorted,
        fontsize=8
    )
    plt.xticks(
        range(0, len(windows), max(1, len(windows)//10)),
        [datetime.fromtimestamp(w[0]).strftime("%H:%M:%S") for w in windows[::max(1, len(windows)//10)]],
        rotation=45,
        ha="right",
        fontsize=7
    )
    plt.title("Aion Cognitive Stability Heatmap - Top 30 Concept Fields (Phase 35.6.1)")
    plt.xlabel("Time Windows")
    plt.ylabel("Concept Fields")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(OUTPUT, dpi=200)
    plt.close()
    print(f"✅  Stability heatmap (Top 30) saved -> {OUTPUT}")

# ────────────────────────────────────────────────────────
if __name__ == "__main__":
    build_heatmap()