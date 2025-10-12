# backend/symatics/operators/project.py
from __future__ import annotations
from typing import Optional, Union

from backend.symatics.signature import Signature
from backend.symatics.operators.base import Operator   # ✅ fixed import (no circular import)
from backend.symatics.operators.helpers import _merge_meta


def _project(a: Signature, subspace: Union[str, "Context"] = "H", ctx: Optional["Context"] = None) -> Signature:
    """
    π Projection to subspace (v0.1):
    - Supported: H, V, RHC, LHC
    - If forcing change, apply gentle attenuation (×0.9)
    - Metadata includes projection target + attenuation factor

    Defensive: supports legacy call forms where the second arg is a string ("H"/"V")
               or a Context passed as second positional parameter.
    """
    # Handle legacy form where 2nd arg is Context
    if ctx is None and not isinstance(subspace, str):
        ctx = subspace
        subspace = "H"

    allowed = ("H", "V", "RHC", "LHC")
    if subspace not in allowed:
        subspace = "H"

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


# Export unary operator
project_op = Operator("π", 1, _project)

# ---------------------------------------------------------------------------
# Roadmap (π Projection v0.2+)
# ---------------------------------------------------------------------------
# - Replace attenuation heuristic with full Jones calculus.
# - Add arbitrary complex vector rotation support.
# - Support chained subspace projections with cumulative attenuation.
# - Context-based enforcement of polarization basis sets.