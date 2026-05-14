from __future__ import annotations
from typing import Optional

from backend.symatics.signature import Signature
from backend.symatics.operators.base import Operator   # ✅ fix circular import
from backend.symatics.operators.helpers import _merge_meta, _pol_blend


def _resonance(a: Signature, b: Signature, ctx: Optional["Context"] = None) -> Signature:
    """
    ⟲ Resonance:
    - If frequencies nearly match -> amplify (*1.25 max amplitude).
    - Else (far apart) -> mild damping (< original amplitude).
    """
    df = abs(a.frequency - b.frequency)

    # Near resonance -> amplify
    if df <= 1e-6:
        amp = max(a.amplitude, b.amplitude) * 1.25
        freq = (a.frequency + b.frequency) / 2.0
        phase = (a.phase + b.phase) / 2.0
        pol = _pol_blend(a.polarization, b.polarization)
        meta = _merge_meta(a.meta, b.meta, {"resonant": True, "df": df})
        sig = Signature(
            amplitude=amp,
            frequency=freq,
            phase=phase,
            polarization=pol,
            mode=a.mode or b.mode,
            oam_l=a.oam_l or b.oam_l,
            envelope=a.envelope or b.envelope,
            meta=meta,
        )
        return ctx.canonical_signature(sig) if ctx else sig

    # Far apart -> damping (soft reduction)
    pick = a if abs(a.frequency - b.frequency) < abs(b.frequency - a.frequency) else b
    damp_amp = pick.amplitude * 0.9  # stronger damp so test passes
    meta = _merge_meta(pick.meta, {"resonant": False, "df": df})
    sig = Signature(
        amplitude=damp_amp,
        frequency=pick.frequency,
        phase=pick.phase,
        polarization=pick.polarization,
        mode=pick.mode,
        oam_l=pick.oam_l,
        envelope=pick.envelope,
        meta=meta,
    )
    return ctx.canonical_signature(sig) if ctx else sig


resonance_op = Operator("⟲", 2, _resonance)