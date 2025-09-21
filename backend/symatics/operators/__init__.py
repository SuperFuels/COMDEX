# symatics/operators/__init__.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from symatics.signature import Signature


# ---------------------------------------------------------------------------
# Operator Base
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Operator:
    name: str
    arity: int
    impl: Callable[..., Any]  # semantic action


# ---------------------------------------------------------------------------
# Import individual operators
# ---------------------------------------------------------------------------

from .superpose import superpose_op
from .entangle import entangle_op
from .resonance import resonance_op
from .measure import measure_op
from .project import project_op

OPS: Dict[str, Operator] = {
    "⊕": superpose_op,
    "↔": entangle_op,
    "⟲": resonance_op,
    "μ": measure_op,
    "π": project_op,
    # 𝔽, 𝔼, τ, ⊖ → v0.2+
}


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def apply_operator(symbol: str, *args: Any, ctx: Optional["Context"] = None) -> Any:
    """
    Apply a Symatics operator by symbol.
    Handles context injection, arity checks, and safe dispatch.
    """
    if symbol not in OPS:
        raise ValueError(f"Unknown operator: {symbol}")

    op = OPS[symbol]
    if len(args) != op.arity:
        raise ValueError(
            f"Operator {symbol} expects {op.arity} args, got {len(args)}"
        )

    try:
        return op.impl(*args, ctx=ctx) if "ctx" in op.impl.__code__.co_varnames else op.impl(*args)
    except Exception as e:
        raise RuntimeError(f"Operator {symbol} failed: {e}") from e


# ---------------------------------------------------------------------------
# Roadmap (v0.2+)
# ---------------------------------------------------------------------------
# - Add extended operators: 𝔽, 𝔼, τ, ⊖
# - Standardize Context-aware operator injection
# - Add symbolic operator composition (macros)
# - Formalize operator error handling and recovery