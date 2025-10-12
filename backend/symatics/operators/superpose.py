"""
[Tessaris v0.2] — Legacy COMDEX Operator Stub
──────────────────────────────────────────────
This module is **deprecated** and retained only for archival / backward
compatibility with legacy COMDEX tests or external tools.

It is no longer active in the operator registry — the canonical implementation
lives in:  backend/symatics/quantum_ops.py  (function: `superpose`).

DO NOT import or modify this file. It will be removed in v0.3.
"""

import warnings
from backend.symatics.operators.base import Operator

warnings.warn(
    "backend.symatics.operators.superpose is deprecated. "
    "Use backend.symatics.quantum_ops.superpose instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Inactive placeholder Operator
superpose_op = Operator(
    name="superpose_op",
    arity=2,
    impl=lambda *a, **kw: {"deprecated": True, "op": "⊕", "args": a},
)

__all__ = ["superpose_op"]