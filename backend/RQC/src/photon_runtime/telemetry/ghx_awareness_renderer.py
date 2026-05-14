"""
Tessaris RQC - GHX Awareness Renderer
──────────────────────────────────────────────
Phase 5 * Visual renderer for Φ(t) and R(t)

Reads the MorphicLedger v2 telemetry log, plots Φ (coherence)
and R (resonance index) over time, and saves a PNG snapshot for GHX Visualizer.
"""

import os
import json
import time
import logging
import matplotlib.pyplot as plt
from datetime import datetime
from typing import List, Dict, Any

LEDGER_PATH = "data/ledger/rqc_live_telemetry.jsonl"
OUT_DIR = "data/visualizations/awareness_sessions"
logger = logging.getLogger(__name__)

#───────────────────────────────────────────────
def load_ledger() -> List[Dict[str, Any]]:
    """Load and parse the entire Morphic Ledger v2 telemetry log."""
    if not os.path.exists(LEDGER_PATH):
        logger.warning(f"[GHXRenderer] Ledger not found: {LEDGER_PATH}")
        return []
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

#───────────────────────────────────────────────
def render_awareness_plot(save: bool = True) -> str:
    """Generate Φ(t) and R(t) plots and optionally save as PNG."""
    os.makedirs(OUT_DIR, exist_ok=True)
    data = load_ledger()
    if not data:
        print("[GHXRenderer] No ledger entries to render.")
        return ""

    # Extract time series data
    t, phi, res = [], [], []
    for entry in data:
        ts = entry.get("timestamp")
        ph = entry.get("Φ_mean")
        re = entry.get("resonance_index")
        if isinstance(ts, (int, float)) and isinstance(re, (int, float)):
            t.append(ts)
            phi.append(ph if isinstance(ph, (int, float)) else None)
            res.append(re)

    if not t:
        print("[GHXRenderer] No valid numeric entries found.")
        return ""

    # Normalize timestamps to relative seconds
    t0 = t[0]
    t = [ti - t0 for ti in t]

    plt.figure(figsize=(10, 5))
    plt.plot(t, phi, label="Φ (coherence)", linewidth=2)
    plt.plot(t, res, label="R (resonance index)", linewidth=2, linestyle="--")
    plt.xlabel("Time (s)")
    plt.ylabel("Magnitude")
    plt.title("Tessaris RQC Awareness Evolution Φ(t), R(t)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    if save:
        ts_label = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(OUT_DIR, f"awareness_{ts_label}.png")
        plt.savefig(out_path, dpi=150)
        plt.close()
        logger.info(f"[GHXRenderer] Saved Φ(t) snapshot -> {out_path}")
        print(f"✅ Saved awareness snapshot: {out_path}")
        return out_path
    else:
        plt.show()
        return ""

#───────────────────────────────────────────────
if __name__ == "__main__":
    print("🧠 Generating RQC awareness snapshot from ledger ...")
    render_awareness_plot()