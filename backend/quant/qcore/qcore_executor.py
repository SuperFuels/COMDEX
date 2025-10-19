# ===============================
# 📁 backend/quant/qcore/qcore_executor.py
# ===============================
"""
⚙️  QCoreExecutor — Q-Series Symbolic Execution Engine
-------------------------------------------------------

The QCoreExecutor coordinates symbolic computation, resonance propagation,
and metric aggregation for a full QSheet.

It operates as the runtime driver behind QPy/QTensor/QLearn,
executing 4-D AtomSheets transformed through the QSeriesBridge.

Execution Flow:
    1.  Initialize bridge and convert AtomSheet → QSheetCells
    2.  Compute Φ–ψ resonance for each cell
    3.  Propagate resonance and update metrics (entropy, harmony, novelty)
    4.  Aggregate run-level metrics into QCoreMetrics
    5.  Sync results back into AtomSheet for Codex/AION layers
"""

from __future__ import annotations
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

from backend.quant.qcore.qseries_bridge import QSeriesBridge
from backend.quant.qcore.qsheet_cell import QSheetCell
from backend.quant.qcore.qcore_metrics import QCoreMetrics

# ---------------------------------------------------------------------------

class QCoreExecutor:
    """
    🧠 QCoreExecutor — central runtime orchestrator for Q-Series.
    """

    def __init__(self):
        self.metrics = QCoreMetrics()
        self.run_id = f"qqc_run_{uuid.uuid4().hex[:8]}"
        self.results: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    async def execute_atomsheet(self, sheet) -> Dict[str, Any]:
        """
        🔄 Execute a full AtomSheet under Q-Series symbolic resonance.

        Args:
            sheet: AtomSheet instance (or compatible)
        Returns:
            Dict summary with metrics and per-cell resonance data.
        """
        start_time = datetime.utcnow()
        bridge = QSeriesBridge(sheet)
        bridge.initialize_qsheet()

        # Phase 1 — Compute per-cell Φ–ψ resonance
        resonance_data = bridge.compute_all_resonances()

        # Phase 2 — Relational (entropy / harmony / novelty)
        bridge.compute_relational_metrics()

        # Phase 3 — Aggregate metrics
        agg = self.metrics.aggregate(bridge.qcells, run_id=self.run_id)

        # Phase 4 — Sync results back to AtomSheet
        bridge.sync_back_to_atomsheet()

        # Finalize
        elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000.0
        result = {
            "ok": True,
            "run_id": self.run_id,
            "elapsed_ms": elapsed_ms,
            "cell_count": len(bridge.qcells),
            "resonance_data": resonance_data,
            "aggregates": agg,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        self.results = result
        return result

    # ------------------------------------------------------------------
    async def execute_async_batch(self, sheets: List[Any]) -> List[Dict[str, Any]]:
        """
        🚀 Run multiple AtomSheets asynchronously (for multi-core QQC).
        """
        coros = [self.execute_atomsheet(s) for s in sheets]
        return await asyncio.gather(*coros)

    # ------------------------------------------------------------------
    def quick_run(self, sheet) -> Dict[str, Any]:
        """
        ⚡ Synchronous convenience wrapper for single-sheet execution.
        """
        return asyncio.run(self.execute_atomsheet(sheet))

    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"QCoreExecutor(run_id={self.run_id}, metrics={self.metrics})"