# backend/symatics/operators/superpose.py
from __future__ import annotations
from typing import Optional

from backend.symatics.signature import Signature
from backend.symatics.operators.base import Operator
from backend.symatics.operators.helpers import (
    _merge_meta,
    _pol_blend,
    _complex_from_amp_phase,
    _amp_phase_from_complex,
    _freq_blend,
)

# ---------------------------------------------------------------------------
# Operator
# ---------------------------------------------------------------------------

def _superpose(a: Signature, b: Signature, ctx: Optional["Context"] = None) -> Signature:
    """
    ⊕ Superposition (context-aware):
    - Complex vector add for amplitude/phase
    - Soft frequency/polarization blending
    - Metadata merged with 'superposed': True
    - Canonicalized if ctx is provided

    TODO v0.2+: Add phasor-based destructive interference
    TODO v0.2+: Enforce associativity within tolerance bands
    """
    za = _complex_from_amp_phase(a.amplitude, a.phase)
    zb = _complex_from_amp_phase(b.amplitude, b.phase)
    zc = za + zb
    A, phi = _amp_phase_from_complex(zc)

    f = _freq_blend(a.frequency, b.frequency)
    pol = _pol_blend(a.polarization, b.polarization)

    mode = a.mode if a.mode is not None else b.mode
    oam_l = a.oam_l if a.oam_l is not None else b.oam_l
    envelope = a.envelope if a.envelope is not None else b.envelope

    meta = _merge_meta(a.meta, b.meta, {"superposed": True})

    sig = Signature(
        amplitude=A,
        frequency=f,
        phase=phi,
        polarization=pol,
        mode=mode,
        oam_l=oam_l,
        envelope=envelope,
        meta=meta,
    )
    return ctx.canonical_signature(sig) if ctx else sig


superpose_op = Operator("⊕", 2, _superpose)


# ---------------------------------------------------------------------------
# Roadmap (⊕ Superposition v0.2+)
# ---------------------------------------------------------------------------
# - Add phasor-based destructive interference (amplitude reduction).
# - Enforce associativity within tolerance bands (phase-sensitive).
# - Context-aware frequency lattice snapping during superposition.
# - Polarization blending: upgrade from bias to vector-space calculus.