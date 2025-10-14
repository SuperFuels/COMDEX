from __future__ import annotations
from typing import Optional, Union

from backend.symatics.signature import Signature
from backend.symatics.operators.base import Operator
from backend.symatics.operators.helpers import _merge_meta


def _project(a: Signature, subspace: Union[str, "Context"] = "H", ctx: Optional["Context"] = None) -> Signature:
    """
    π Projection to subspace (v0.1):
    - Supported: H, V, RHC, LHC
    - If forcing change, apply gentle attenuation (×0.9)
    - Metadata includes projection target + attenuation factor

    Defensive features:
    • Automatically wraps primitive (float/int) inputs into a minimal Signature.
    • Supports legacy form where the second arg is Context instead of subspace string.
    • Gracefully handles missing attributes with sensible defaults.
    """
    # ────────────────────────────────────────────────────────────────
    # Defensive normalization
    if isinstance(a, (float, int)):
        a = Signature(
            amplitude=float(a),
            frequency=1.0,
            phase=0.0,
            polarization="H",
            mode="default",
            oam_l=0,
            envelope=None,
            meta={},
        )

    # Handle legacy form where 2nd arg is Context
    if ctx is None and not isinstance(subspace, str):
        ctx = subspace
        subspace = "H"

    allowed = ("H", "V", "RHC", "LHC")
    if subspace not in allowed:
        subspace = "H"

    # Safe attribute resolution
    polarization = getattr(a, "polarization", "H")
    meta = getattr(a, "meta", {})

    atten = 1.0 if polarization == subspace else 0.9
    merged_meta = _merge_meta(meta, {"projected": subspace, "atten": atten})

    sig = Signature(
        amplitude=getattr(a, "amplitude", 1.0) * atten,
        frequency=getattr(a, "frequency", 1.0),
        phase=getattr(a, "phase", 0.0),
        polarization=subspace,
        mode=getattr(a, "mode", "default"),
        oam_l=getattr(a, "oam_l", 0),
        envelope=getattr(a, "envelope", None),
        meta=merged_meta,
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