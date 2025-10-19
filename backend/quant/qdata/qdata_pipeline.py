# ===============================
# 📁 backend/quant/qdata/qdata_pipeline.py
# ===============================
"""
🗂️  QDataPipeline — Resonant Data Ingestion & Persistence Layer
----------------------------------------------------------------
Captures, normalizes, and persists Q-Series runtime data
(Φ, ψ, κ, entropy, harmony, novelty, SQI, coherence) from
executions managed by QCoreExecutor and QCoreMetrics.

Supported backends:
    • JSONL (stream append)
    • CSV (batch summary)
    • Parquet (if pyarrow available)

Intended for telemetry persistence and offline analytics.
"""

from __future__ import annotations
import os
import json
import csv
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import pandas as pd
except ImportError:
    pd = None


class QDataPipeline:
    """
    🔄 Persistent data manager for Q-Series metrics.
    """

    def __init__(self, base_dir: str = "backend/qdata/logs"):
        self.base_dir = base_dir
        self.jsonl_path = os.path.join(base_dir, "qmetrics.jsonl")
        self.csv_path = os.path.join(base_dir, "qmetrics.csv")
        os.makedirs(base_dir, exist_ok=True)

    # ------------------------------------------------------------------
    def append_metrics(self, summary: Dict[str, Any]) -> None:
        """
        Append a metrics summary to the JSONL log and update CSV snapshot.
        """
        # JSONL append
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(summary, ensure_ascii=False) + "\n")

        # CSV write/append
        write_header = not os.path.exists(self.csv_path)
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
            if write_header:
                writer.writeheader()
            writer.writerow(summary)

    # ------------------------------------------------------------------
    def load_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load metrics history from JSONL (most recent first if limit specified).
        """
        if not os.path.exists(self.jsonl_path):
            return []
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        data = [json.loads(l) for l in lines if l.strip()]
        if limit:
            data = data[-limit:]
        return data

    # ------------------------------------------------------------------
    def export_parquet(self, out_path: Optional[str] = None) -> Optional[str]:
        """
        Export JSONL → Parquet if pandas/pyarrow available.
        """
        if pd is None:
            return None
        out_path = out_path or os.path.join(self.base_dir, "qmetrics.parquet")
        data = self.load_history()
        if not data:
            return None
        df = pd.DataFrame(data)
        df.to_parquet(out_path, index=False)
        return out_path

    # ------------------------------------------------------------------
    def summarize(self, key: str = "coherence_index") -> Dict[str, Any]:
        """
        Compute simple min/mean/max stats for a given metric key.
        """
        data = self.load_history()
        if not data:
            return {"count": 0}
        vals = [d.get(key, 0.0) for d in data if isinstance(d.get(key), (int, float))]
        if not vals:
            return {"count": 0}
        return {
            "count": len(vals),
            "min": min(vals),
            "max": max(vals),
            "mean": sum(vals) / len(vals),
        }

    # ------------------------------------------------------------------
    def filter_runs(self, start_time: Optional[str] = None, end_time: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve runs between two ISO timestamps (inclusive).
        """
        data = self.load_history()
        if not start_time and not end_time:
            return data

        def to_dt(ts: str):
            try:
                return datetime.fromisoformat(ts.replace("Z", ""))
            except Exception:
                return None

        start_dt = to_dt(start_time) if start_time else None
        end_dt = to_dt(end_time) if end_time else None
        filtered: List[Dict[str, Any]] = []

        for d in data:
            ts = to_dt(d.get("timestamp", ""))
            if ts is None:
                continue
            if (not start_dt or ts >= start_dt) and (not end_dt or ts <= end_dt):
                filtered.append(d)
        return filtered

    # ------------------------------------------------------------------
    def clear_logs(self) -> None:
        """
        Delete all stored log files.
        """
        for p in [self.jsonl_path, self.csv_path]:
            if os.path.exists(p):
                os.remove(p)

    # ------------------------------------------------------------------
    def __repr__(self):
        n = len(self.load_history())
        return f"QDataPipeline(base_dir='{self.base_dir}', entries={n})"