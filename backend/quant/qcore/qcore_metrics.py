# ===============================
# 📁 backend/quant/qcore/qcore_metrics.py
# ===============================
"""
📊 QCoreMetrics - Aggregation & Telemetry Layer
------------------------------------------------
Collects and aggregates symbolic-photonic metrics produced by
QCoreExecutor runs.  Provides both numerical summaries and
telemetry-ready payloads for CodexTrace / GHX / AION systems.
"""

from __future__ import annotations
from typing import Any, Dict, List
from datetime import datetime
import math
import statistics
import uuid


class QCoreMetrics:
    """
    🧩 Aggregates Φ, ψ, κ, coherence, entropy, harmony, novelty, and SQI.
    """

    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.last_summary: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    def aggregate(self, qcells: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        """
        Aggregate resonance and symbolic cognition metrics from all QSheetCells.

        Args:
            qcells: mapping of id -> QSheetCell
            run_id: identifier for the QQC execution batch

        Returns:
            Dict summary of averages and coherence statistics.
        """
        Φ, ψ, κ, coh, sqi = [], [], [], [], []
        entropy, harmony, novelty = [], [], []

        for qc in qcells.values():
            Φ.append(qc.Φ_mean)
            ψ.append(qc.ψ_mean)
            κ.append(qc.κ)
            coh.append(qc.coherence_energy)
            sqi.append(qc.sqi_score)
            entropy.append(qc.entropy)
            harmony.append(qc.harmony)
            novelty.append(qc.novelty)

        def mean_safe(values: List[float], default: float = 0.0) -> float:
            vals = [v for v in values if v is not None]
            return float(statistics.mean(vals)) if vals else default

        summary = {
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "Φ_mean": mean_safe(Φ, 1.0),
            "ψ_mean": mean_safe(ψ, 1.0),
            "κ_mean": mean_safe(κ, 0.0),
            "coherence_mean": mean_safe(coh, 1.0),
            "sqi_mean": mean_safe(sqi, 1.0),
            "entropy_mean": mean_safe(entropy, 0.0),
            "harmony_mean": mean_safe(harmony, 1.0),
            "novelty_mean": mean_safe(novelty, 0.0),
            "cell_count": len(qcells),
        }

        # Derived coherence index
        summary["coherence_index"] = round(
            summary["Φ_mean"] * summary["ψ_mean"] * summary["coherence_mean"], 6
        )

        self.last_summary = summary
        self.history.append(summary)
        return summary

    # ------------------------------------------------------------------
    def export_packet(self, mode: str = "telemetry") -> Dict[str, Any]:
        """
        Produce a telemetry or archival packet for GHX or CodexTrace.
        """
        s = self.last_summary or {}
        return {
            "packet_id": f"qqc_metrics_{uuid.uuid4().hex[:8]}",
            "type": "qcore_metrics",
            "mode": mode,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "summary": s,
        }

    # ------------------------------------------------------------------
    def rolling_average(self, key: str, window: int = 5) -> float:
        """
        Compute rolling average of a metric over the last N runs.
        """
        if not self.history:
            return 0.0
        vals = [h.get(key, 0.0) for h in self.history[-window:]]
        return float(statistics.mean(vals)) if vals else 0.0

    # ------------------------------------------------------------------
    def clear_history(self) -> None:
        self.history.clear()
        self.last_summary = {}

    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        if not self.last_summary:
            return "QCoreMetrics(<empty>)"
        ci = self.last_summary.get("coherence_index", 0)
        Φ = self.last_summary.get("Φ_mean", 0)
        ψ = self.last_summary.get("ψ_mean", 0)
        return f"QCoreMetrics(Φ={Φ:.3f}, ψ={ψ:.3f}, coherence_index={ci:.3f})"