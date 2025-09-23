# symatics/operators/project.py
from __future__ import annotations
from typing import Optional

from backend.symatics.signature import Signature
from backend.symatics.operators import Operator
from backend.symatics.operators.superpose import _merge_meta


def _project(a: Signature, subspace: str, ctx: Optional["Context"] = None) -> Signature:
    """
    π Projection:
    - Allowed: H, V, RHC, LHC
    - If forcing change, attenuate ×0.9
    - Metadata records projection + attenuation

    TODO v0.2+: Extend with Jones calculus and full complex rotation
    """
    allowed = ("H", "V", "RHC", "LHC")
    if subspace not in allowed:
        return a

    atten = 1.0 if a.polarization == subspace else 0.9
    meta = _merge_meta(a.meta, {"projected": subspace, "atten": atten})

    sig = Signature(
        amplitude=a.amplitude * atten,
        frequency=a.frequency,
        phase=a.phase,
        polarization=subspace,
        mode=a.mode,
        oam_l=a.oam_l,
        envelope=a.envelope,
        meta=meta,
    )
    return ctx.canonical_signature(sig) if ctx else sig


project_op = Operator("π", 2, _project)


# ---------------------------------------------------------------------------
# Roadmap (π Projection v0.2+)
# ---------------------------------------------------------------------------
# - Replace attenuation heuristic with full Jones calculus.
# - Add arbitrary complex vector rotation support.
# - Support chained subspace projections with cumulative attenuation.
# - Context-based enforcement of polarization basis sets.