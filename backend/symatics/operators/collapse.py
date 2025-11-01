# backend/symatics/operators/collapse.py
# ---------------------------------------------------------------------
# Tessaris v0.2a: ∇ Collapse Operator
# ---------------------------------------------------------------------
# Represents wavefunction collapse with directional bias.
# Converts a superposed Signature (⊕) into a singular measured state (μ),
# possibly applying probabilistic weighting or normalization.
# ---------------------------------------------------------------------

from __future__ import annotations
from typing import Any, Dict
from backend.symatics.signature import Signature

def collapse_op(a: Signature, ctx: Dict[str, Any] | None = None, **kw) -> Signature:
    """
    Collapse (∇) operator.
    Converts a possibly superposed Signature into a canonicalized single state.

    Rules:
      * If a.meta['superposed'] -> mark as collapsed + measured
      * Optional ctx['bias'] shifts amplitude weighting
      * Always returns a normalized Signature (amplitude ∈ [0, 1])
    """
    amp = a.amplitude
    bias = kw.get("bias", 1.0)
    norm_amp = min(1.0, amp * bias)

    new_meta = dict(a.meta)
    new_meta.update({
        "collapsed": True,
        "measured": True,
    })
    if a.meta.get("superposed"):
        new_meta["superposed"] = True

    return Signature(
        amplitude=norm_amp,
        frequency=a.frequency,
        phase=a.phase,
        polarization=a.polarization,
        meta=new_meta,
    )

__all__ = ["collapse_op"]