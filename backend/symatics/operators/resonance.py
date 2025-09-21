# symatics/operators/resonance.py
from __future__ import annotations
import math
from typing import Optional

from symatics.signature import Signature
from symatics.operators import Operator
from symatics.operators.superpose import _merge_meta, _pol_blend


def _resonance(a: Signature, b: Signature, ctx: Optional["Context"] = None) -> Signature:
    """
    ⟲ Resonance:
    - If frequencies nearly match → amplify (1.25× of max amplitude)
    - Else softly select closer-to-reference frequency with mild damping
    - Metadata includes `resonant` flag and frequency delta `df`

    TODO v0.2+: Include Q-factor models and decay times
    TODO v0.2+: Model resonance envelope growth/decay physics
    """
    df = abs(a.frequency - b.frequency)

    if df < 1e-6:
        amp = max(a.amplitude, b.amplitude) * 1.25
        phase = (a.phase + b.phase) / 2.0
        pol = _pol_blend(a.polarization, b.polarization)
        meta = _merge_meta(a.meta, b.meta, {"resonant": True, "df": df})

        sig = Signature(
            amplitude=amp,
            frequency=(a.frequency + b.frequency) / 2.0,
            phase=phase,
            polarization=pol,
            mode=a.mode or b.mode,
            oam_l=a.oam_l or b.oam_l,
            envelope=a.envelope or b.envelope,
            meta=meta,
        )
        return ctx.canonical_signature(sig) if ctx else sig

    # Off-resonance: select the closer frequency and damp
    pick = a if abs(a.frequency - b.frequency) < abs(b.frequency - a.frequency) else b
    meta = _merge_meta(pick.meta, {"resonant": False, "df": df})

    sig = Signature(
        amplitude=pick.amplitude * 0.98,
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


# ---------------------------------------------------------------------------
# Roadmap (⟲ Resonance v0.2+)
# ---------------------------------------------------------------------------
# - Introduce Q-factor models (bandwidth, sharpness).
# - Simulate resonance decay/envelope over time.
# - Extend to multimode resonance interactions.
# - Add stochastic detuning noise injection.