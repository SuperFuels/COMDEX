# backend/symatics/operators/cancel.py
from __future__ import annotations
from typing import Optional
import cmath

from backend.symatics.signature import Signature
from backend.symatics.operators.base import Operator  # ✅ fixed import (no circular import)
from backend.symatics.operators.helpers import (
    _complex_from_amp_phase,
    _amp_phase_from_complex,
    _merge_meta,
    _freq_blend,
    _pol_blend,
)


def _cancel(a: Signature, b: Signature, ctx: Optional["Context"] = None) -> Signature:
    """
    ⊖ Cancellation operator:
    - Represents destructive interference (phase difference = π).
    - Equivalent to vector subtraction in the phasor plane.
    - Metadata tagged with "cancel": True
    """
    z1 = _complex_from_amp_phase(a.amplitude, a.phase)
    z2 = _complex_from_amp_phase(b.amplitude, b.phase)
    zc = z1 - z2  # destructive interference

    A, phi_eff = _amp_phase_from_complex(zc)
    f = _freq_blend(a.frequency, b.frequency)
    pol = _pol_blend(a.polarization, b.polarization)
    meta = _merge_meta(a.meta, b.meta, {"op": "⊖", "cancel": True})

    sig = Signature(
        amplitude=A,
        frequency=f,
        phase=phi_eff,
        polarization=pol,
        mode=a.mode or b.mode,
        oam_l=a.oam_l or b.oam_l,
        envelope=a.envelope or b.envelope,
        meta=meta,
    )
    return ctx.canonical_signature(sig) if ctx else sig


# Export operator
cancel_op = Operator("⊖", 2, _cancel)