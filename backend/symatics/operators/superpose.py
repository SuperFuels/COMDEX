# symatics/operators/superpose.py
from __future__ import annotations
import math
from typing import Optional

from backend.symatics.signature import Signature
from backend.symatics.operators import Operator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _merge_meta(a: Optional[dict], b: Optional[dict], extra: Optional[dict] = None) -> dict:
    """
    Merge metadata dictionaries with right-precedence, then apply extras.
    """
    m: dict = {}
    if isinstance(a, dict):
        m.update(a)
    if isinstance(b, dict):
        m.update(b)  # right side wins on collision
    if isinstance(extra, dict):
        m.update(extra)
    return m


def _pol_blend(pa: str, pb: str) -> str:
    """
    Polarization blending (v0.1):
    - Identical → keep
    - Otherwise → gentle bias toward the first operand
    """
    return pa if pa == pb else pa


def _complex_from_amp_phase(A: float, phi: float) -> complex:
    """Convert amplitude + phase into a complex phasor."""
    return complex(A * math.cos(phi), A * math.sin(phi))


def _amp_phase_from_complex(z: complex) -> tuple[float, float]:
    """Convert complex phasor into (amplitude, phase)."""
    A = abs(z)
    phi = (math.atan2(z.imag, z.real) + math.tau) % math.tau
    return A, phi


def _freq_blend(fa: float, fb: float) -> float:
    """
    Frequency blending (v0.1):
    - If nearly equal → average
    - Else prefer the closer-to-dominant
    """
    if abs(fa - fb) < 1e-9:
        return (fa + fb) / 2.0
    return fa if abs(fa - fb) < abs(fb - fa) else fb


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