# ===============================
# 📁 backend/quant/qsheets/qsheets_runtime.py
# ===============================
"""
📜 QSheetsRuntime - Unified Q-Series Orchestrator
-------------------------------------------------
Coordinates the entire Q-Series workflow:
    ▸ execute QPy/QQC symbolic computations
    ▸ log metrics via QDataPipeline
    ▸ adapt parameters using QLearnEngine
    ▸ visualize through QPlotMetrics

Acts as a live runtime environment for running multi-sheet symbolic
sessions and exporting coherent summaries to Tessaris or AION layers.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
import asyncio
import os
from datetime import datetime

# Core dependencies
from backend.quant.qpy.qpy_module import QPyModule
from backend.quant.qdata.qdata_pipeline import QDataPipeline
from backend.quant.qlearn.qlearn_engine import QLearnEngine
from backend.quant.qplot.qplot_metrics import export_all_plots


class QSheetsRuntime:
    """
    🧩 Runtime controller for Q-Series sheets.
    """

    def __init__(self, base_dir: str = "backend/qsheets/session"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
        self.pipeline = QDataPipeline(os.path.join(base_dir, "qdata"))
        self.learner = QLearnEngine(os.path.join(base_dir, "qlearn"))
        self.qpy = QPyModule()
        self.history: List[Dict[str, Any]] = []
        self.session_id = f"qsession_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    # ------------------------------------------------------------------
    async def run_sheet(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute one full symbolic-resonance cycle.
        """
        context = context or {}
        result = self.qpy.run_test()
        summary = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "session": self.session_id,
            "Φ_mean": result.get("ΔΦ", 0.0),
            "ψ_mean": result.get("Δε", 0.0),
            "κ": result.get("κ", 0.0),
            "μ": result.get("μ", 0.0),
            "status": result.get("status", "ok"),
        }

        # Learn from and persist results
        self.learner.learn_from_summary(summary)
        self.pipeline.append_metrics(summary)
        self.history.append(summary)

        return summary

    # ------------------------------------------------------------------
    async def run_batch(self, n: int = 5, delay: float = 0.0):
        """
        Run a batch of symbolic executions sequentially.
        """
        for _ in range(n):
            s = await self.run_sheet()
            print(f"[QSheets] {s}")
            if delay > 0:
                await asyncio.sleep(delay)
        self.pipeline.export_parquet()
        export_all_plots(self.pipeline)
        return self.history

    # ------------------------------------------------------------------
    def summarize_session(self) -> Dict[str, Any]:
        """
        Generate a consolidated summary of the session's resonance performance.
        """
        if not self.history:
            return {"count": 0}
        coh_vals = [abs(h.get("κ", 0.0)) for h in self.history]
        mean_coh = sum(coh_vals) / len(coh_vals)
        state = self.learner.export_state_packet()
        return {
            "session": self.session_id,
            "count": len(self.history),
            "mean_κ": mean_coh,
            "weights": state["weights"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    # ------------------------------------------------------------------
    def clear_session(self):
        """
        Reset all logs, metrics, and learner state.
        """
        self.pipeline.clear_logs()
        self.history.clear()
        print(f"[QSheets] Session {self.session_id} cleared.")

    # ------------------------------------------------------------------
    def __repr__(self):
        return f"QSheetsRuntime(session='{self.session_id}', runs={len(self.history)})"


# ----------------------------------------------------------------------
# Convenience entry point for manual tests
# ----------------------------------------------------------------------
if __name__ == "__main__":
    async def main():
        qs = QSheetsRuntime()
        await qs.run_batch(n=3, delay=0.2)
        summary = qs.summarize_session()
        print(json.dumps(summary, indent=2))

    import json, asyncio
    asyncio.run(main())