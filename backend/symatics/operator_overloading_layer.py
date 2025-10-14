"""
⚛ Operator Overloading Layer — SRK-15 Task 2 + 15.4 (Finalized)
Adds per-operator coherence thresholds, adaptive dispatch, and telemetry.
Safe integration with all DynamicCoherenceOptimizer variants.
"""

import asyncio
from typing import Any, Callable, Dict

from backend.modules.photon.photon_algebra_runtime import PhotonAlgebraRuntime
from backend.symatics.operators import OPS
from backend.modules.glyphwave.core.coherence_optimizer import DynamicCoherenceOptimizer


class OperatorOverloadingLayer:
    """
    Adaptive dispatcher for symbolic and photonic operators.
    Decides execution path based on dynamic coherence, per-operator
    thresholds, and current system mode.
    """

    def __init__(self, coherence_threshold: float = 0.7):
        self.photon_runtime = PhotonAlgebraRuntime()
        self.sym_ops = OPS
        self.optimizer = DynamicCoherenceOptimizer()

        # Global + per-operator thresholds
        self.coherence_threshold = coherence_threshold
        self.operator_thresholds: Dict[str, float] = {
            "⊕": 0.6,  # superposition — moderate
            "↔": 0.75, # entanglement — high
            "⟲": 0.65, # resonance — moderate-high
            "∇": 0.5,  # collapse — tolerant
            "μ": 0.3,  # measurement — robust
            "π": 0.5,  # projection — hybrid symbolic
        }

        self._context_state: Dict[str, Any] = {"coherence": 1.0}
        self._dispatch_trace: list[Dict[str, Any]] = []

    # ────────────────────────────────────────────────────────────────
    def set_context(self, coherence: float):
        """Update coherence context for adaptive operator dispatch."""
        # Safely normalize using available optimizer method
        try:
            if hasattr(self.optimizer, "normalize_coherence"):
                coherence = self.optimizer.normalize_coherence(coherence)
            elif hasattr(self.optimizer, "optimize_coherence"):
                coherence = self.optimizer.optimize_coherence(coherence)
            elif hasattr(self.optimizer, "stabilize"):
                coherence = self.optimizer.stabilize(coherence)
            else:
                # fallback simple clamp
                coherence = max(0.0, min(1.0, coherence))
        except Exception:
            coherence = max(0.0, min(1.0, coherence))

        self._context_state["coherence"] = coherence

    # ────────────────────────────────────────────────────────────────
    def _resolve_threshold(self, op_symbol: str) -> float:
        """Fetch operator-specific threshold or default."""
        return self.operator_thresholds.get(op_symbol, self.coherence_threshold)

    # ────────────────────────────────────────────────────────────────
    def _should_use_photon(self, op_symbol: str) -> bool:
        """Determine if photonic backend should be used for given operator."""
        coherence = self._context_state.get("coherence", 1.0)
        threshold = self._resolve_threshold(op_symbol)
        return coherence >= threshold

    # ────────────────────────────────────────────────────────────────
    async def apply(self, op_symbol: str, *args, **kwargs) -> Any:
        """
        Apply an operator adaptively in either symbolic or photonic mode.
        Records telemetry for each decision.
        """
        coherence = self._context_state.get("coherence", 1.0)
        threshold = self._resolve_threshold(op_symbol)
        domain = "photon" if self._should_use_photon(op_symbol) else "symbolic"

        # Log decision
        self._dispatch_trace.append({
            "op": op_symbol,
            "coherence": coherence,
            "threshold": threshold,
            "domain": domain,
        })

        # Photonic path
        if op_symbol in {"⊕", "↔", "⟲", "∇", "μ"} and domain == "photon":
            capsule = {
                "name": f"auto_capsule_{op_symbol}",
                "glyphs": [{"operator": op_symbol, "args": list(args)}],
            }
            return await self.photon_runtime.execute(capsule)

        # Symbolic fallback
        op = self.sym_ops.get(op_symbol)
        if not op:
            raise ValueError(f"Unknown operator: {op_symbol}")

        if hasattr(op, "impl"):
            return op.impl(*args, **kwargs)
        return op(*args, **kwargs)

    # ────────────────────────────────────────────────────────────────
    def get_trace(self) -> list[Dict[str, Any]]:
        """Return recorded coherence-dispatch telemetry."""
        return list(self._dispatch_trace)


# ─────────────────────────────────────────────────────────────────────
# Global convenience layer (like OPS)
OVERLOAD: Dict[str, Callable[..., Any]] = {}


def initialize_overloads():
    """Populate OVERLOAD mapping with adaptive operator functions."""
    layer = OperatorOverloadingLayer()

    async def make_async(op_symbol):
        async def async_func(*args, **kwargs):
            return await layer.apply(op_symbol, *args, **kwargs)
        return async_func

    for symbol in {"⊕", "↔", "⟲", "∇", "μ"} | set(OPS.keys()):
        OVERLOAD[symbol] = asyncio.run(make_async(symbol))  # pre-bind async wrapper

    return layer


# Initialize at import
try:
    ADAPTIVE_LAYER = initialize_overloads()
except RuntimeError:
    # In event loop already — fallback silent init
    ADAPTIVE_LAYER = OperatorOverloadingLayer()