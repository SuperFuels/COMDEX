# symatics/operators/measure.py
from __future__ import annotations
from typing import Optional

from symatics.signature import Signature
from symatics.operators import Operator
from symatics.wave import canonical_signature
from symatics.operators.superpose import _merge_meta


def _measure(a: Signature, ctx: Optional["Context"] = None) -> Signature:
    """
    μ Measurement:
    - Collapse to canonical lattice
    - Preserve metadata with 'measured' tag

    TODO v0.2+: Verify quantization of amplitude/frequency
    TODO v0.2+: Assert amplitude != original amplitude after quantization
    """
    c = canonical_signature(a) if ctx is None else ctx.canonical_signature(a)
    meta = _merge_meta(a.meta, c.meta, {"measured": True})
    sig = Signature(
        amplitude=c.amplitude,
        frequency=c.frequency,
        phase=c.phase,
        polarization=c.polarization,
        mode=c.mode,
        oam_l=c.oam_l,
        envelope=c.envelope,
        meta=meta,
    )
    return ctx.canonical_signature(sig) if ctx else sig


measure_op = Operator("μ", 1, _measure)

# ---------------------------------------------------------------------------
# Roadmap (μ Measurement v0.2+)
# ---------------------------------------------------------------------------
# - Enforce amplitude/frequency quantization to lattice.
# - Add stochastic collapse distributions (probabilistic branching).
# - Support multiple measurement bases (polarization, phase).
# - Track collapse lineage in metadata for replay.