from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, Any, Optional

# ---------------------------------------------------------------------------
# Operator Base
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Operator:
    """Core operator definition for Symatics algebra."""
    name: str
    arity: int
    impl: Callable[..., Any]


# ---------------------------------------------------------------------------
# Individual operator imports (⚠ legacy paths via stubs to emit warnings)
# ---------------------------------------------------------------------------
import warnings

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
from backend.symatics.operators.superpose import superpose_op   # deprecated → warns
from backend.symatics.operators.entangle import entangle_op     # deprecated → warns
from backend.symatics.operators.measure import measure_op       # deprecated → warns

from backend.symatics.operators.resonance import resonance_op
from backend.symatics.operators.fuse import fuse_op
from backend.symatics.operators.damping import damping_op
from backend.symatics.operators.project import project_op
from backend.symatics.operators.cancel import cancel_op  


# ---------------------------------------------------------------------------
# Operator Registry
# ---------------------------------------------------------------------------

OPS: Dict[str, Operator] = {
    "⊕": superpose_op,
    "↔": entangle_op,
    "⟲": resonance_op,
    "μ": measure_op,
    "π": project_op,
    "⋈": fuse_op,
    "↯": damping_op,
    "⊖": cancel_op,
    # --- v0.2+ stubs ---
    "⊗": Operator("⊗", 2, lambda a, b, ctx=None, **kwargs: ("⊗", (a, b))),
    "≡": Operator("≡", 2, lambda a, b, ctx=None, **kwargs: ("≡", (a, b))),
    "¬": Operator("¬", 1, lambda a, ctx=None, **kwargs: ("¬", a)),
}


# ---------------------------------------------------------------------------
# Operator Dispatcher
# ---------------------------------------------------------------------------

def apply_operator(
    symbol: str,
    *args: Any,
    ctx: Optional["Context"] = None,
    **kwargs: Any
) -> Any:
    """Apply a Symatics operator by symbol with arity checks + safe dispatch."""
    if symbol not in OPS:
        raise ValueError(f"Unknown operator: {symbol}")

    op = OPS[symbol]
    if len(args) != op.arity:
        raise ValueError(
            f"Operator {symbol} expects {op.arity} args, got {len(args)}"
        )

    try:
        return op.impl(*args, ctx=ctx, **kwargs)
    except TypeError:
        return op.impl(*args)
    except Exception as e:
        raise RuntimeError(f"Operator {symbol} failed: {e}") from e


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "Operator",
    "OPS",
    "apply_operator",
]