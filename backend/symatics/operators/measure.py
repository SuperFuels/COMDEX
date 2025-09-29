"""
Deprecation Stub for Measure Operator
-------------------------------------
Use `backend.symatics.quantum_ops.measure` instead.
"""

import warnings
from backend.symatics.quantum_ops import measure
from backend.symatics.operators import Operator
from backend.utils.deprecation_logger import log_deprecation

# Emit warning immediately on import
_import_msg = (
    "backend.symatics.operators.measure is deprecated. "
    "Use backend.symatics.quantum_ops.measure instead."
)
warnings.warn(_import_msg, DeprecationWarning, stacklevel=2)
log_deprecation(_import_msg)


def _measure(a, ctx=None, **kwargs):
    msg = (
        "backend.symatics.operators.measure is deprecated. "
        "Use backend.symatics.quantum_ops.measure instead."
    )
    warnings.warn(msg, DeprecationWarning, stacklevel=2)
    log_deprecation(msg)

    try:
        # Try forwarding ctx if supported
        return measure(a, ctx=ctx, **kwargs)
    except TypeError:
        # Fallback if ctx is not accepted
        return measure(a, **kwargs)


measure_op = Operator("μ", 1, _measure)

__all__ = ["measure_op"]