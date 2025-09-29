"""
Deprecation Stub for Entangle Operator
--------------------------------------
Use `backend.symatics.quantum_ops.entangle` instead.
"""

import warnings
from backend.symatics.quantum_ops import entangle
from backend.symatics.operators import Operator
from backend.utils.deprecation_logger import log_deprecation

# Emit warning immediately on import
_import_msg = (
    "backend.symatics.operators.entangle is deprecated. "
    "Use backend.symatics.quantum_ops.entangle instead."
)
warnings.warn(_import_msg, DeprecationWarning, stacklevel=2)
log_deprecation(_import_msg)


def _entangle(a, b, ctx=None, **kwargs):
    msg = (
        "backend.symatics.operators.entangle is deprecated. "
        "Use backend.symatics.quantum_ops.entangle instead."
    )
    warnings.warn(msg, DeprecationWarning, stacklevel=2)
    log_deprecation(msg)

    try:
        # Try forwarding ctx in case supported
        return entangle(a, b, ctx=ctx, **kwargs)
    except TypeError:
        # Fallback if entangle() does not accept ctx
        return entangle(a, b, **kwargs)


entangle_op = Operator("↔", 2, _entangle)

__all__ = ["entangle_op"]