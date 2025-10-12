# backend/symatics/operators/damping.py
from __future__ import annotations
import math
from typing import Optional

from backend.symatics.signature import Signature
from backend.symatics.operators.base import Operator  # ✅ fixed import — no circular import


def _damp(
    a: Signature,
    *,
    gamma: float = 0.1,
    steps: int = 1,
    ctx: Optional["Context"] = None,
) -> Signature:
    """
    ↯ Damping operator (v0.1):
    - Exponential amplitude decay: A' = A * exp(-γ·steps)
    - Phase, frequency, and polarization unchanged
    - Metadata records damping parameters

    TODO v0.2+: Add frequency-dependent damping (dispersion).
    TODO v0.2+: Model coupling with resonance envelopes.
    """
    new_amp = a.amplitude * math.exp(-gamma * steps)

    sig = Signature(
        amplitude=new_amp,
        frequency=a.frequency,
        phase=a.phase,
        polarization=a.polarization,
        mode=a.mode,
        oam_l=a.oam_l,
        envelope=a.envelope,
        meta={**(a.meta or {}), "damped": True, "gamma": gamma, "steps": steps},
    )
    return ctx.canonical_signature(sig) if ctx else sig


# Export operator as unary
damping_op = Operator("↯", 1, _damp)