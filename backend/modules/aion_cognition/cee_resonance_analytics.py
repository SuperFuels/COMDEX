# ================================================================
# 📊 CEE Resonance Analytics - Cross-Session Drift Tracker
# ================================================================
"""
Logs and visualizes LexMemory resonance dynamics over time.
Each session snapshot records {timestamp, tag, key, SQI, count}.
"""

import csv, time, logging, json
from pathlib import Path
import matplotlib.pyplot as plt
from collections import defaultdict
from .cee_lex_memory import _load_memory

logger = logging.getLogger(__name__)
HIST_PATH = Path("data/telemetry/resonance_history.csv")
IMG_PATH = Path("data/telemetry/resonance_trends.png")

def snapshot_memory(tag: str = "run"):
    """Append the current memory state to the historical log and auto-plot drift."""
    mem = _load_memory()
    HIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    new = not HIST_PATH.exists()

    with open(HIST_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["ts", "tag", "key", "SQI", "count"])
        ts = int(time.time())
        for k, v in mem.items():
            w.writerow([ts, tag, k, v.get("SQI", 0.0), v.get("count", 0)])

    logger.info(f"[ResonanceAnalytics] Snapshot logged for tag={tag}, entries={len(mem)}")

    # ------------------------------------------------------------
    # 📈 Auto-plot after each snapshot (resonance drift visualization)
    try:
        plot_concept_trends()
        logger.info("[ResonanceAnalytics] Auto-generated resonance trend plot.")
    except Exception as e:
        logger.warning(f"[ResonanceAnalytics] Could not plot trends automatically: {e}")

def plot_concept_trends(top_n: int = 10):
    """Plot average SQI drift across sessions for top_n frequent concepts."""
    if not HIST_PATH.exists():
        logger.warning("[ResonanceAnalytics] No history found.")
        return
    rows = list(csv.DictReader(open(HIST_PATH, encoding="utf-8")))
    series = defaultdict(list)
    for r in rows:
        k = r["key"]
        series[k].append((int(r["ts"]), float(r["SQI"])))
    # sort by frequency and trim
    top = sorted(series.items(), key=lambda kv: len(kv[1]), reverse=True)[:top_n]

    plt.figure(figsize=(10,6))
    for key, vals in top:
        vals.sort()
        x, y = zip(*vals)
        plt.plot(x, y, label=key.split("↔")[-1][:15])
    plt.legend()
    plt.title("Resonance Drift Over Sessions")
    plt.xlabel("Timestamp")
    plt.ylabel("SQI")
    plt.tight_layout()
    IMG_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(IMG_PATH, dpi=150)
    logger.info(f"[ResonanceAnalytics] Saved trend plot -> {IMG_PATH}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    snapshot_memory("manual")
    plot_concept_trends()