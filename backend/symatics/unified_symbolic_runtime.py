"""
⚛ Unified Symbolic Runtime (USR) — SRK-15 Task 3 + 15.5
Bridges symbolic algebra (Symatics) and photonic computation (Photon Algebra Runtime)
through adaptive operator dispatch and coherence-aware routing.

New in SRK-15.5:
────────────────
• Telemetry integration from OperatorOverloadingLayer.
• Coherence analytics (average, trend, and mode ratios).
• get_status() endpoint for GHX and monitoring export.
"""

import asyncio
import time
from statistics import mean
from typing import Any, Dict, Union, List

from backend.symatics.operator_overloading_layer import OperatorOverloadingLayer
from backend.symatics.photon_symatics_bridge import PhotonSymaticsBridge


class UnifiedSymbolicRuntime:
    """Central orchestration layer for hybrid symbolic–photonic computation."""

    def __init__(self, coherence_threshold: float = 0.6):
        self.coherence_threshold = coherence_threshold
        self._coherence_context = 1.0
        self._lock = asyncio.Lock()

        # Subsystems
        self.bridge = PhotonSymaticsBridge()
        self.overlayer = OperatorOverloadingLayer(coherence_threshold=coherence_threshold)

        # Telemetry buffers
        self._history: List[Dict[str, Any]] = []
        self._max_history = 50

    # ────────────────────────────────────────────────────────────────
    def set_context(self, coherence: float):
        """Set current coherence level for runtime decision-making."""
        self._coherence_context = max(0.0, min(1.0, coherence))
        self.overlayer.set_context(self._coherence_context)

    def get_context(self) -> float:
        """Return active coherence level."""
        return self._coherence_context

    # ────────────────────────────────────────────────────────────────
    async def execute(
        self, expression: Union[Dict[str, Any], str], *args, **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a symbolic expression (dict or operator symbol) with coherence-aware routing.
        Returns a unified trace with both symbolic + photonic data if applicable.
        """
        async with self._lock:
            start = time.time()
            coherence = self._coherence_context
            trace = {"start": start, "coherence": coherence, "mode": None}

            # Case 1 – Symbolic expression capsule (Symatic Core)
            if isinstance(expression, dict) and "glyphs" in expression:
                trace["mode"] = "photonic"
                result = await self.bridge.sym_to_photon(expression)
                trace.update(
                    {
                        "final_wave": result.get("final_wave"),
                        "trace": result.get("trace", []),
                        "duration": time.time() - start,
                    }
                )
                self._record_trace(trace)
                return trace

            # Case 2 – Direct operator symbol
            if isinstance(expression, str):
                trace["mode"] = (
                    "photon" if coherence >= self.coherence_threshold else "symbolic"
                )
                result = await self.overlayer.apply(expression, *args, **kwargs)
                trace["result"] = result
                trace["duration"] = time.time() - start
                self._record_trace(trace)
                return trace

            raise TypeError(
                "Unsupported expression type for UnifiedSymbolicRuntime.execute()"
            )

    # ────────────────────────────────────────────────────────────────
    async def evaluate_sequence(self, seq: list[tuple[str, Any]]):
        """
        Execute a sequence of (operator, args) tuples in temporal order.
        Useful for chained symbolic expressions or temporal resonance updates.
        """
        results = []
        for op, arg in seq:
            res = await self.execute(op, arg)
            results.append(res)
        return {
            "sequence_results": results,
            "timestamp": time.time(),
            "coherence": self._coherence_context,
            "telemetry": self.overlayer.get_trace(),
        }

    # ────────────────────────────────────────────────────────────────
    def _record_trace(self, trace: Dict[str, Any]):
        """Internal helper to store bounded telemetry history."""
        self._history.append(trace)
        if len(self._history) > self._max_history:
            self._history.pop(0)

    # ────────────────────────────────────────────────────────────────
    def get_status(self) -> Dict[str, Any]:
        """
        Return aggregated runtime status including coherence metrics,
        dispatch statistics, and historical telemetry.
        """
        telemetry = self.overlayer.get_trace()
        if not telemetry:
            return {
                "coherence": self._coherence_context,
                "avg_coherence": self._coherence_context,
                "mode_ratio": {"photon": 0, "symbolic": 0},
                "telemetry_count": 0,
            }

        coherences = [t["coherence"] for t in telemetry]
        modes = [t["domain"] for t in telemetry]
        photon_count = modes.count("photon")
        symbolic_count = modes.count("symbolic")
        total = max(1, len(modes))

        return {
            "coherence": self._coherence_context,
            "avg_coherence": round(mean(coherences), 4),
            "mode_ratio": {
                "photon": photon_count / total,
                "symbolic": symbolic_count / total,
            },
            "telemetry_count": len(telemetry),
            "recent": telemetry[-3:],  # last 3 dispatch decisions
            "runtime_age": len(self._history),
        }

    def export_telemetry(self) -> dict:
        """
        🔹 SRK-17 Update — Export symbolic runtime telemetry for GHX bundle.
        Captures basic Symatics operator statistics and state metrics.
        """
        try:
            stats = getattr(self, "stats", {})
            active_ops = getattr(self, "active_ops", [])
        except Exception:
            stats, active_ops = {}, []

        return {
            "timestamp": time.time(),
            "runtime_id": getattr(self, "runtime_id", "USR-core"),
            "active_ops": active_ops,
            "operator_count": len(active_ops),
            "stats": stats,
        }