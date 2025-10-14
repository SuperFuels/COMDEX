"""
⚛ Photon–Symatics Bridge — SRK-15 Task 1
Bidirectional interface between the Symatic Algebra Core and the Photon Algebra Runtime.

Enables symbolic operators (⊕, ↔, ⟲, ∇, μ) to be executed as physical photon
transformations, while maintaining symbolic traceability and coherence continuity.
"""

import asyncio
from typing import Any, Dict

from backend.modules.photon.photon_algebra_runtime import PhotonAlgebraRuntime
from backend.symatics.operators import OPS


class _SymaticOperatorProxy:
    """
    Shim to wrap the OPS registry dictionary into a unified `.apply()` interface,
    providing compatibility with the PhotonAlgebraRuntime operator dispatch model.
    """

    def __init__(self, ops_dict):
        self.ops = ops_dict

    def apply(self, op_symbol: str, *args, **kwargs):
        op = self.ops.get(op_symbol)
        if not op:
            raise ValueError(f"Unknown symbolic operator: {op_symbol}")
        if hasattr(op, "impl"):
            return op.impl(*args, **kwargs)
        elif callable(op):
            return op(*args, **kwargs)
        raise TypeError(f"Operator {op_symbol} is not callable")


class PhotonSymaticsBridge:
    """
    Acts as the connective layer between the symbolic (Symatics) and photonic (Photon)
    computational domains. Routes algebraic operations to the appropriate backend
    based on coherence context and operator semantics.
    """

    def __init__(self):
        self.photon_runtime = PhotonAlgebraRuntime()

    # ────────────────────────────────────────────────────────────────
    async def sym_to_photon(self, symbolic_expr: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert and execute a symbolic algebra expression in the photonic domain.
        The resulting photon capsule executes entirely in light-space.
        """
        capsule = {
            "name": symbolic_expr.get("name", "bridge_capsule"),
            "glyphs": symbolic_expr.get("glyphs", []),
        }
        return await self.photon_runtime.execute(capsule)

    # ────────────────────────────────────────────────────────────────
    async def photon_to_sym(self, photon_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map a photonic computation result back into symbolic algebraic form.
        """
        wave = photon_state.get("final_wave", [])
        return {
            "symbol": "Ψ",
            "amplitude_vector": wave,
            "measurement_trace": photon_state.get("trace", []),
            "timestamp": photon_state.get("timestamp"),
        }

    # ────────────────────────────────────────────────────────────────
    def resolve_operator(self, op_symbol: str):
        """
        Route operator to the correct execution domain (Symatic vs Photon).
        Photonic operators map to PhotonAlgebraRuntime;
        all others map to Symatic OPS via proxy adapter.
        """
        if op_symbol in {"⊕", "↔", "⟲", "∇", "μ"}:
            return self.photon_runtime
        return _SymaticOperatorProxy(OPS)