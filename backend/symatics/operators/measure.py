"""
[Tessaris v0.2] — Legacy COMDEX Operator Stub (μ Measurement)
──────────────────────────────────────────────────────────────
Inactive archival operator stub. Use quantum_ops.measure instead.
"""
import warnings
from backend.symatics.operators.base import Operator

warnings.warn(
    "backend.symatics.operators.measure is deprecated. "
    "Use backend.symatics.quantum_ops.measure instead.",
    DeprecationWarning,
    stacklevel=2,
)

measure_op = Operator(
    name="measure_op",
    arity=1,
    impl=lambda *a, **kw: {"deprecated": True, "op": "μ", "args": a},
)

__all__ = ["measure_op"]