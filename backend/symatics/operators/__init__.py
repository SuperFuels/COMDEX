# backend/symatics/operators/__init__.py
from __future__ import annotations
from typing import Callable, Dict, Any, Optional
import warnings

from backend.symatics.signature import Signature
from backend.symatics.operators.base import Operator
from backend.symatics.quantum_ops import superpose, entangle, measure
from backend.symatics.operators.resonance import resonance_op
from backend.symatics.operators.fuse import fuse_op
from backend.symatics.operators.damping import damping_op
from backend.symatics.operators.project import project_op
from backend.symatics.operators.cancel import cancel_op
from backend.symatics.operators.collapse import collapse_op

# ---------------------------------------------------------------------------
# Helper: normalize output into Signature
# ---------------------------------------------------------------------------

def _ensure_signature(result: Any) -> Any:
    """Ensure any operator result is normalized to a Signature."""
    if isinstance(result, Signature):
        return result
    if isinstance(result, dict) and "op" in result:
        args = result.get("args", [])
        sigs = [a for a in args if isinstance(a, Signature)]
        if sigs:
            amp = sum(s.amplitude for s in sigs)
            freq = sum(s.frequency for s in sigs) / len(sigs)
        else:
            amp = result.get("amplitude", 1.0)
            freq = result.get("frequency", 1.0)
        return Signature(
            amplitude=amp,
            frequency=freq,
            phase=0.0,
            polarization="H",
            meta={"synthetic": True, "expr": result},
        )
    return result


# ---------------------------------------------------------------------------
# Adapter builder
# ---------------------------------------------------------------------------

def _adapter(func: Callable[..., Any], symbol: str, arity: int) -> Operator:
    """Wrap a quantum op to conform to the Operator interface."""

    def impl(*a, ctx=None, **kw):
        # -------------------------------------------------------------
        # Special handling for entanglement ↔
        # -------------------------------------------------------------
        if symbol == "↔":
            raw = func(*a, ctx=ctx, **kw) if "ctx" in func.__code__.co_varnames else func(*a, **kw)
            if isinstance(raw, dict) and "args" in raw:
                left, right = raw.get("args", [None, None])
                return {
                    "left": left,
                    "right": right,
                    "meta": {
                        "entangled": True,
                        "link_id": f"link_{id(left) ^ id(right):x}",
                        "corr": {
                            "phase": 1.0,
                            "spin": 1.0,
                            "pol": "coherent",
                        },
                    },
                }
            return raw

        # -------------------------------------------------------------
        # Normal operator execution
        # -------------------------------------------------------------
        if "ctx" in func.__code__.co_varnames:
            res = func(*a, ctx=ctx, **kw)
        else:
            res = func(*a, **kw)

        if isinstance(res, Signature):
            return res

        # -------------------------------------------------------------
        # Handle symbolic dicts (⊕, μ)
        # -------------------------------------------------------------
        if isinstance(res, dict):
            meta = {"synthetic": True, "expr": res}

            # --- SUPERPOSE (⊕) ---
            if symbol == "⊕":
                meta["superposed"] = True
                args = res.get("args", [])
                sigs = [x for x in args if isinstance(x, Signature)]
                if sigs:
                    amp = sum(s.amplitude for s in sigs)
                    freq = sum(s.frequency for s in sigs) / len(sigs)
                else:
                    amp = res.get("amplitude", 1.0)
                    freq = res.get("frequency", 1.0)
                return Signature(amplitude=amp, frequency=freq, phase=0.0, polarization="H", meta=meta)

            # --- MEASURE (μ) ---
            elif symbol == "μ":
                meta["measured"] = True

                # Deep recursive detection of superposition
                def _has_superposed(node):
                    if isinstance(node, dict):
                        if node.get("superposed") is True:
                            return True
                        return any(_has_superposed(v) for v in node.values())
                    elif isinstance(node, list):
                        return any(_has_superposed(v) for v in node)
                    return False

                detected = (
                    _has_superposed(res)
                    or _has_superposed(meta.get("expr"))
                    or (
                        isinstance(meta.get("expr"), dict)
                        and _has_superposed(meta["expr"].get("args"))
                    )
                )
                if detected:
                    meta["superposed"] = True

                # Preserve numeric values
                if isinstance(a[0], Signature):
                    amp = a[0].amplitude
                    freq = a[0].frequency
                else:
                    amp = res.get("amplitude", 1.0)
                    freq = res.get("frequency", 1.0)

                sig = Signature(
                    amplitude=amp,
                    frequency=freq,
                    phase=0.0,
                    polarization="H",
                    meta=meta,
                )

                # Promote any inner superposed flag upward
                def _promote_superposed(meta_dict):
                    if not isinstance(meta_dict, dict):
                        return False
                    if meta_dict.get("superposed") is True:
                        return True
                    if "expr" in meta_dict and _promote_superposed(meta_dict["expr"]):
                        return True
                    if "args" in meta_dict and any(
                        _promote_superposed(x) for x in meta_dict["args"]
                    ):
                        return True
                    return False

                if _promote_superposed(sig.meta):
                    sig.meta["superposed"] = True

                return sig

            # --- Default ---
            return Signature(
                amplitude=res.get("amplitude", 1.0),
                frequency=res.get("frequency", 1.0),
                phase=0.0,
                polarization="H",
                meta=meta,
            )

        # -------------------------------------------------------------
        # Fallback normalization
        # -------------------------------------------------------------
        return _ensure_signature(res)

    return Operator(symbol, arity, impl)


# ---------------------------------------------------------------------------
# Operator Registry (authoritative set)
# ---------------------------------------------------------------------------

OPS: Dict[str, Operator] = {
    "⊕": _adapter(superpose, "⊕", 2),
    "↔": _adapter(entangle, "↔", 2),
    "μ": _adapter(measure, "μ", 1),
    "∇": collapse_op,
    "⟲": resonance_op,
    "π": project_op,
    "⋈": fuse_op,
    "↯": damping_op,
    "⊖": cancel_op,
    "⊗": Operator("⊗", 2, lambda a, b, ctx=None, **kw: ("⊗", (a, b))),
    "≡": Operator("≡", 2, lambda a, b, ctx=None, **kw: ("≡", (a, b))),
    "¬": Operator("¬", 1, lambda a, ctx=None, **kw: ("¬", a)),
}

from .collapse_wave import collapse_wave

# after OPS = {...}
OPS["∇"] = collapse_wave

# ---------------------------------------------------------------------------
# Legacy COMDEX compatibility (for test_operator_registry.py)
# ---------------------------------------------------------------------------

warnings.warn(
    "[Tessaris] Legacy operator aliases (superpose_op, entangle_op, measure_op) "
    "are provided for backward compatibility only.",
    DeprecationWarning,
    stacklevel=2,
)

# Bridge aliases to quantum_ops implementations so legacy tests pass
OPS["superpose_op"] = OPS["⊕"]
OPS["entangle_op"] = OPS["↔"]
OPS["measure_op"]  = OPS["μ"]


# ---------------------------------------------------------------------------
# Operator Dispatcher
# ---------------------------------------------------------------------------

def apply_operator(symbol: str, *args: Any, ctx: Optional["Context"] = None, **kwargs: Any) -> Any:
    """Apply a Symatics operator by symbol with arity checks + safe dispatch."""
    if symbol not in OPS:
        raise ValueError(f"Unknown operator: {symbol}")

    op = OPS[symbol]
    if len(args) != op.arity:
        raise ValueError(f"Operator {symbol} expects {op.arity} args, got {len(args)}")

    try:
        res = op.impl(*args, ctx=ctx, **kwargs)
    except TypeError:
        res = op.impl(*args)

    return _ensure_signature(res)


__all__ = ["Operator", "OPS", "apply_operator"]