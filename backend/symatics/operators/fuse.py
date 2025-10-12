from __future__ import annotations
import cmath
from typing import Optional

from backend.symatics.signature import Signature
from backend.symatics.operators.base import Operator  # ✅ fixed import (no circular reference)
from backend.symatics.operators.helpers import (
    _complex_from_amp_phase,
    _amp_phase_from_complex,
    _freq_blend,
    _pol_blend,
    _merge_meta,
)


def _fuse(a: Signature, b: Signature, *, phi: float = 0.0, ctx: Optional["Context"] = None) -> Signature:
    """
    ⋈ Interference/Fusion operator (v0.3):
    - Combines two signatures with explicit phase offset φ
    - Uses amplitude norm + phase averaging consistent with axioms A7–A8
    - Metadata includes φ for traceability.
    """
    z1 = _complex_from_amp_phase(a.amplitude, a.phase)
    z2 = _complex_from_amp_phase(b.amplitude, b.phase)
    zc = z1 + cmath.exp(1j * phi) * z2  # phase-shifted interference

    A, phi_eff = _amp_phase_from_complex(zc)
    f = _freq_blend(a.frequency, b.frequency)
    pol = _pol_blend(a.polarization, b.polarization)
    meta = _merge_meta(a.meta, b.meta, {"op": "⋈", "phi": phi})

    sig = Signature(
        amplitude=A,
        frequency=f,
        phase=phi_eff,
        polarization=pol,
        mode=a.mode if a.mode else b.mode,
        oam_l=a.oam_l if a.oam_l else b.oam_l,
        envelope=a.envelope if a.envelope else b.envelope,
        meta=meta,
    )
    return ctx.canonical_signature(sig) if ctx else sig


fuse_op = Operator("⋈", 2, _fuse)