"""
Symatics Operators Package
--------------------------
This package defines symbolic operators used in COMDEX Symatics.

- Each operator is implemented in its own module (superpose, fuse, etc.).
- The registry of all operators and the dispatcher live here in
  `backend/symatics/operators/__init__.py`.
- Import from this package to get the registry and dispatcher.

Example:
    from backend.symatics.operators import apply_operator, OPS
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, Any, Optional

# ---------------------------------------------------------------------------
# Operator Base
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Operator:
    """
    Core operator definition for Symatics algebra.
    - name: Unicode symbol of the operator (⊕, ⋈, ↯, …)
    - arity: Number of required arguments
    - impl: Callable implementing the operator’s semantics
    """
    name: str
    arity: int
    impl: Callable[..., Any]


# ---------------------------------------------------------------------------
# Individual operator imports
# ---------------------------------------------------------------------------

from backend.symatics.operators.superpose import superpose_op
from backend.symatics.operators.entangle import entangle_op
from backend.symatics.operators.resonance import resonance_op
from backend.symatics.operators.fuse import fuse_op
from backend.symatics.operators.damping import damping_op
from backend.symatics.operators.project import project_op
from backend.symatics.operators.measure import measure_op
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
    "⋈": fuse_op,       # interference/fusion operator
    "↯": damping_op,    # damping operator
    "⊖": cancel_op,     # cancellation / destructive interference
    # --- v0.2+ / stub operators ---
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
    """
    Apply a Symatics operator by symbol.
    Handles context injection, arity checks, and safe dispatch.
    Extra keyword args (e.g. phi, steps) are passed through to the operator.
    """
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
        # fallback if impl doesn’t accept ctx/kwargs
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
# ---------------------------------------------------------------------------
# Roadmap (v0.2+)
# ---------------------------------------------------------------------------
# - Add extended operators: 𝔽, 𝔼, τ
# - Replace stubs with full implementations
# - Standardize Context-aware operator injection
# - Add symbolic operator composition (macros)
# - Formalize operator error handling and recovery