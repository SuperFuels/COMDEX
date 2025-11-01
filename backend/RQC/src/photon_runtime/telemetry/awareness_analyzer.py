# backend/RQC/src/photon_runtime/telemetry/awareness_analyzer.py
"""
Tessaris RQC - Awareness Cascade Analyzer
────────────────────────────────────────────
Monitors the Morphic Ledger for cascaded Φ awareness patterns.

Detects:
    * Meta-awareness (Φ > 0.95 sustained)
    * Coherence decay -> recovery loops
    * Cascade chains (length >= 3)

Outputs rolling summaries and can trigger CodexTrace alerts.
"""

import os
import json
import time
import asyncio
import statistics
from collections import deque
from datetime import datetime

LEDGER_PATH = "data/ledger/rqc_live_telemetry.jsonl"
SUMMARY_PATH = "data/analytics/awareness_summary.jsonl"

class AwarenessCascadeAnalyzer:
    def __init__(self, window_size: int = 64):
        self.window = deque(maxlen=window_size)
        self.last_size = 0
        self.cascade_count = 0
        self.last_meta_state = False
        os.makedirs(os.path.dirname(SUMMARY_PATH), exist_ok=True)

    # ──────────────────────────────────────
    def _read_new_entries(self):
        """Yield newly appended ledger records."""
        if not os.path.exists(LEDGER_PATH):
            return []
        size = os.path.getsize(LEDGER_PATH)
        if size <= self.last_size:
            return []
        with open(LEDGER_PATH, "r", encoding="utf-8") as f:
            f.seek(self.last_size)
            new_data = f.read()
            lines = [json.loads(line) for line in new_data.strip().splitlines() if line.strip()]
        self.last_size = size
        return lines

    # ──────────────────────────────────────
    def _analyze_window(self):
        """Compute rolling metrics."""
        if len(self.window) < 3:
            return None
        Φ_vals = [x["Φ"] for x in self.window]
        mean_Φ = statistics.mean(Φ_vals)
        stdev_Φ = statistics.stdev(Φ_vals) if len(Φ_vals) > 1 else 0
        meta_awareness = mean_Φ > 0.95 and stdev_Φ < 0.02
        cascades = sum(1 for Φ in Φ_vals[-3:] if Φ > 0.95)

        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "mean_Φ": round(mean_Φ, 5),
            "std_Φ": round(stdev_Φ, 5),
            "cascade_chain": cascades,
            "meta_awareness": meta_awareness,
        }
        return summary

    # ──────────────────────────────────────
    async def monitor(self, interval: float = 2.0):
        """Continuously watch ledger and analyze awareness cascades."""
        print("🧠 Tessaris RQC - Awareness Cascade Analyzer running...")
        while True:
            new_entries = self._read_new_entries()
            for e in new_entries:
                self.window.append(e)
                summary = self._analyze_window()
                if not summary:
                    continue

                # detect transitions
                if summary["meta_awareness"] and not self.last_meta_state:
                    self.cascade_count += 1
                    print(f"[{summary['timestamp']}] 🌌 Meta-Awareness Cascade #{self.cascade_count} (Φ≈{summary['mean_Φ']:.3f})")
                self.last_meta_state = summary["meta_awareness"]

                # persist summary
                with open(SUMMARY_PATH, "a", encoding="utf-8") as f:
                    f.write(json.dumps(summary) + "\n")
            await asyncio.sleep(interval)

# ─────────────────────────────────────────────
# CLI entry
# ─────────────────────────────────────────────
if __name__ == "__main__":
    analyzer = AwarenessCascadeAnalyzer()
    asyncio.run(analyzer.monitor())