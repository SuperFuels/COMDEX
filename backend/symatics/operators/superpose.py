"""
Deprecation Stub for Superpose Operator
---------------------------------------
Use `backend.symatics.quantum_ops.superpose` instead.
"""

import warnings
from backend.symatics.quantum_ops import superpose
from backend.symatics.operators import Operator
from backend.utils.deprecation_logger import log_deprecation

# Emit warning immediately on import
_import_msg = (
    "backend.symatics.operators.superpose is deprecated. "
    "Use backend.symatics.quantum_ops.superpose instead."
)
warnings.warn(_import_msg, DeprecationWarning, stacklevel=2)
log_deprecation(_import_msg)


def _superpose(a, b, ctx=None, **kwargs):
    msg = (
        "backend.symatics.operators.superpose is deprecated. "
        "Use backend.symatics.quantum_ops.superpose instead."
    )
    warnings.warn(msg, DeprecationWarning, stacklevel=2)
    log_deprecation(msg)

    try:
        # Try forwarding ctx if supported
        return superpose(a, b, ctx=ctx, **kwargs)
    except TypeError:
        # Fallback if ctx is not accepted
        return superpose(a, b, **kwargs)


superpose_op = Operator("⊕", 2, _superpose)

__all__ = ["superpose_op"]