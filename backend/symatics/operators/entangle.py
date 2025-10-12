"""
[Tessaris v0.2] — Legacy COMDEX Operator Stub (↔ Entanglement)
───────────────────────────────────────────────────────────────
This file is inactive. The active entanglement logic resides in:
backend/symatics/quantum_ops.py  (`entangle` function)
"""
import warnings
from backend.symatics.operators.base import Operator

warnings.warn(
    "backend.symatics.operators.entangle is deprecated. "
    "Use backend.symatics.quantum_ops.entangle instead.",
    DeprecationWarning,
    stacklevel=2,
)

entangle_op = Operator(
    name="entangle_op",
    arity=2,
    impl=lambda *a, **kw: {"deprecated": True, "op": "↔", "args": a},
)

__all__ = ["entangle_op"]