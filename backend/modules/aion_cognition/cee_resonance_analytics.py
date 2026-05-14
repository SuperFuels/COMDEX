#!/usr/bin/env python3
# ================================================================
# 📊 CEE Resonance Analytics - Cross-Session Drift Tracker (v2)
# ================================================================
"""
Logs and visualizes LexMemory resonance dynamics over time.

✔ v2 schema aware (LexMemory JSON: {"version":2, "entries":[...]} )
✔ DATA_ROOT aware (all paths resolve under ${DATA_ROOT:-data})
✔ Safe for missing/corrupt files (LexMemory auto-recovery handles it)
✔ Writes:
    - ${DATA_ROOT}/telemetry/resonance_history.csv
    - ${DATA_ROOT}/telemetry/resonance_trends.png

Each snapshot row:
  ts, tag, key, SQI, count
where "key" is the normalized prompt (stable id).
"""

from __future__ import annotations

import csv
import logging
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt

from backend.modules.aion_cognition.cee_lex_memory import LexMemory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ---------------------------
# DATA_ROOT + paths (single source of truth)
# ---------------------------
def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))


def _paths() -> tuple[Path, Path, Path]:
    root = _data_root()
    lex_path = root / "memory" / "lex_memory.json"
    hist_path = root / "telemetry" / "resonance_history.csv"
    img_path = root / "telemetry" / "resonance_trends.png"
    return lex_path, hist_path, img_path


# ---------------------------
# LexMemory loader (defensive)
# ---------------------------
def _make_lex() -> LexMemory:
    lex_path, _, _ = _paths()
    try:
        return LexMemory(path=lex_path)
    except TypeError:
        # ultra-back-compat if constructor signature differs
        return LexMemory()


def snapshot_memory(tag: str = "run") -> None:
    """Append current LexMemory state to the historical log and auto-plot drift."""
    lex = _make_lex()
    entries = list(lex.entries.values())

    _, hist_path, _ = _paths()
    hist_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not hist_path.exists()

    ts = int(time.time())
    with open(hist_path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["ts", "tag", "key", "SQI", "count"])
        for e in entries:
            key = getattr(e, "prompt", "") or ""
            sqi = float(getattr(e, "sqi", 0.0) or 0.0)
            cnt = int(getattr(e, "count", 0) or 0)
            w.writerow([ts, tag, key, sqi, cnt])

    logger.info(f"[ResonanceAnalytics] Snapshot logged for tag={tag}, entries={len(entries)}")

    # Auto-plot after each snapshot (safe)
    try:
        plot_concept_trends()
        logger.info("[ResonanceAnalytics] Auto-generated resonance trend plot.")
    except Exception as e:
        logger.warning(f"[ResonanceAnalytics] Could not plot trends automatically: {e}")


def plot_concept_trends(top_n: int = 10) -> None:
    """Plot SQI drift across time for top_n most-frequently seen prompts."""
    _, hist_path, img_path = _paths()

    if not hist_path.exists():
        logger.warning("[ResonanceAnalytics] No history found.")
        return

    with open(hist_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        logger.warning("[ResonanceAnalytics] History file empty.")
        return

    series: Dict[str, List[Tuple[int, float]]] = defaultdict(list)
    for r in rows:
        try:
            k = (r.get("key") or "").strip()
            ts = int(float(r.get("ts") or 0))
            sqi = float(r.get("SQI") or 0.0)
            if k:
                series[k].append((ts, sqi))
        except Exception:
            continue

    if not series:
        logger.warning("[ResonanceAnalytics] No valid series data.")
        return

    top = sorted(series.items(), key=lambda kv: len(kv[1]), reverse=True)[: max(1, int(top_n))]

    plt.figure(figsize=(10, 6))
    for key, vals in top:
        vals.sort(key=lambda t: t[0])
        x, y = zip(*vals)
        label = key[:24]  # trim for readability
        plt.plot(x, y, label=label)

    plt.legend(loc="best")
    plt.title("Resonance Drift Over Sessions")
    plt.xlabel("Timestamp")
    plt.ylabel("SQI")
    plt.tight_layout()

    img_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(img_path, dpi=150)
    logger.info(f"[ResonanceAnalytics] Saved trend plot -> {img_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    snapshot_memory("manual")
    plot_concept_trends()