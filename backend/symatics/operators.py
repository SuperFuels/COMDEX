from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, Any, Optional, Tuple
import math
import hashlib

from .signature import Signature
from .wave import canonical_signature


@dataclass(frozen=True)
class Operator:
    name: str
    arity: int
    impl: Callable[..., Any]  # semantic action in v0.1


def _merge_meta(a: Optional[dict], b: Optional[dict], extra: Optional[dict] = None) -> dict:
    m: dict = {}
    if isinstance(a, dict):
        m.update(a)
    if isinstance(b, dict):
        # right side wins on collision (latest-event-wins)
        m.update(b)
    if isinstance(extra, dict):
        m.update(extra)
    return m


def _pol_blend(pa: str, pb: str) -> str:
    """
    Simple polarization blending rule (v0.1):
    - identical → keep
    - H/V vs circular → prefer existing pa
    - H vs V mismatch → keep pa (stable bias)
    """
    if pa == pb:
        return pa
    return pa  # gentle bias toward first operand


def _complex_from_amp_phase(A: float, phi: float) -> complex:
    return complex(A * math.cos(phi), A * math.sin(phi))


def _amp_phase_from_complex(z: complex) -> Tuple[float, float]:
    A = abs(z)
    phi = (math.atan2(z.imag, z.real) + math.tau) % math.tau
    return A, phi


def _freq_blend(fa: float, fb: float) -> float:
    """
    Frequency blending (v0.1):
    - If nearly equal → average
    - Else prefer closer to dominant
    """
    if abs(fa - fb) < 1e-9:
        return (fa + fb) / 2.0
    return fa if abs(fa - fb) < abs(fb - fa) else fb


def _superpose(a: Signature, b: Signature, ctx: Optional["Context"] = None) -> Signature:
    """
    ⊕ Superposition (context-aware):
    - Complex vector add for amplitude/phase
    - Soft frequency/polarization blending
    - Metadata merged with 'superposed': True
    - Canonicalized if ctx is provided

    TODO v0.2+: Add phasor-based check where interference (phase difference)
                can reduce amplitude (destructive interference), not always sum.
    TODO v0.2+: Enforce associativity within tolerance bands when destructive
                interference is modeled (not exact equality).
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
        meta=meta
    )
    return ctx.canonical_signature(sig) if ctx else sig


def _entangle(a: Signature, b: Signature, ctx: Optional["Context"] = None) -> Dict[str, Any]:
    """
    ↔ Entanglement (API-compatible):
    - Represent as correlated pair with stable link_id
    - Add minimal correlation fingerprint for traceability

    TODO v0.2+: Add nonlocal correlation check across contexts,
                verifying that changes to left propagate to right.
    """
    key = f"{a.frequency:.12e}|{a.polarization}|{b.frequency:.12e}|{b.polarization}|{a.phase:.12e}|{b.phase:.12e}"
    link_id = "E:" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    corr_fp = {
        "dphi": float((a.phase - b.phase) % (2 * math.pi)),
        "df": float(a.frequency - b.frequency),
        "pol_pair": f"{a.polarization}-{b.polarization}",
    }

    meta = {"link_id": link_id, "corr": corr_fp}
    if ctx:
        meta["ctx_norm"] = ctx.id if hasattr(ctx, "id") else "ctx"

    return {"left": a, "right": b, "meta": meta}


def _resonance(a: Signature, b: Signature, ctx: Optional["Context"] = None) -> Signature:
    """
    ⟲ Resonance with reference (binary, preserves your arity=2):
    - If frequencies nearly match → amplify (1.25x of max amplitude)
    - Else soft-select closer-to-reference frequency with mild damping

    TODO v0.2+: Include Q-factor models and decay times;
                verify amplitude growth follows resonance envelope physics.
    """
    df = abs(a.frequency - b.frequency)

    if df < 1e-6:
        amp = max(a.amplitude, b.amplitude) * 1.25
        phase = (a.phase + b.phase) / 2.0
        pol = _pol_blend(a.polarization, b.polarization)
        mode = a.mode if a.mode is not None else b.mode
        oam_l = a.oam_l if a.oam_l is not None else b.oam_l
        envelope = a.envelope if a.envelope is not None else b.envelope
        meta = _merge_meta(a.meta, b.meta, {"resonant": True, "df": df})
        sig = Signature(
            amplitude=amp,
            frequency=(a.frequency + b.frequency) / 2.0,
            phase=phase,
            polarization=pol,
            mode=mode,
            oam_l=oam_l,
            envelope=envelope,
            meta=meta
        )
        return ctx.canonical_signature(sig) if ctx else sig

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
        meta=meta
    )
    return ctx.canonical_signature(sig) if ctx else sig


def _measure(a: Signature, ctx: Optional["Context"] = None) -> Signature:
    """
    μ Measurement/canonicalization (context-aware):
    - Collapse to canonical lattice via ctx if provided
    - Preserve prior metadata with a 'measured' tag

    TODO v0.2+: Verify quantization of amplitude/frequency to lattice
                instead of passthrough identity.
    TODO v0.2+: When canonical_signature() introduces quantization lattices,
                assert amplitude != original amplitude.
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
        meta=meta
    )
    return ctx.canonical_signature(sig) if ctx else sig


def _project(a: Signature, subspace: str, ctx: Optional["Context"] = None) -> Signature:
    """
    π Projection to subspace (v0.1):
    - Supported: H, V, RHC, LHC
    - If forcing change, apply gentle attenuation (×0.9)

    TODO v0.2+: Extend polarization projection with Jones calculus
                and full complex vector rotation, not just ×0.9 attenuation.
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
        meta=meta
    )
    return ctx.canonical_signature(sig) if ctx else sig


OPS: Dict[str, Operator] = {
    "⊕": Operator("⊕", 2, _superpose),
    "↔": Operator("↔", 2, _entangle),
    "⟲": Operator("⟲", 2, _resonance),
    "μ": Operator("μ", 1, _measure),
    "π": Operator("π", 2, _project),
    # 𝔽, 𝔼, τ, ⊖ → v0.2+
}

# ---------------------------------------------------------------------------
# Operator Dispatcher
# ---------------------------------------------------------------------------

def apply_operator(symbol: str, *args: Any, ctx: Optional["Context"] = None) -> Any:
    """
    Apply a Symatics operator by symbol.
    Handles context injection, arity checks, and safe dispatch.
    """
    if symbol not in OPS:
        raise ValueError(f"Unknown operator: {symbol}")

    op = OPS[symbol]
    if len(args) != op.arity:
        raise ValueError(
            f"Operator {symbol} expects {op.arity} args, got {len(args)}"
        )

    try:
        return op.impl(*args, ctx=ctx) if "ctx" in op.impl.__code__.co_varnames else op.impl(*args)
    except Exception as e:
        raise RuntimeError(f"Operator {symbol} failed: {e}") from e

# --- v0.3 operators (quantum set) ---

OPS["⊖"] = {
    "name": "Interference",
    "arity": 2,
    "canonical": lambda a, b: ("⊖", (a, b)),
    "laws": [
        # TODO: implement cancellation: ψ ⊖ ψ ≈ 𝟘
        # TODO: interference with ¬ψ gives collapse
    ],
    "status": "stub",
}

OPS["≡"] = {
    "name": "Equivalence",
    "arity": 2,
    "canonical": lambda a, b: ("≡", (a, b)),
    "laws": [
        # TODO: reflexivity: a ≡ a
        # TODO: symmetry: a ≡ b ⇒ b ≡ a
        # TODO: transitivity: a ≡ b, b ≡ c ⇒ a ≡ c
    ],
    "status": "stub",
}

OPS["¬"] = {
    "name": "Negation / Orthogonal dual",
    "arity": 1,
    "canonical": lambda a: ("¬", a),
    "laws": [
        # TODO: double negation: ¬(¬ψ) ≡ ψ
        # TODO: ψ ⊕ ¬ψ collapses
    ],
    "status": "stub",
}

OPS["⊗"] = {
    "name": "Entanglement",
    "arity": 2,
    "canonical": lambda a, b: ("⊗", (a, b)),
    "laws": [
        # TODO: associativity: (ψ1 ⊗ ψ2) ⊗ ψ3 ≡ ψ1 ⊗ (ψ2 ⊗ ψ3)
        # TODO: distributivity over ⊕
        # TODO: collapse consistency (e.g. GHZ, W)
    ],
    "status": "stub",
}

# --- placeholders for v0.4 / v0.5 operators (not implemented yet) ---
# OPS["σ"] = {...}   # Symmetry operator
# OPS["τ"] = {...}   # Time-fold
# OPS["ℙ"] = {...}   # Probability weight
# OPS["⇒"] = {...}   # Trigger
# OPS["δ"] = {...}   # Decoherence
# OPS["Tr"] = {...}  # Trace
# OPS["↯⟲"] = {...} # Coupling operator


# Example usage:
# sig_c = apply_operator("⊕", sig_a, sig_b, ctx=my_context)
# entangled = apply_operator("↔", sig_a, sig_b)
# measured = apply_operator("μ", sig_a, ctx=my_context)

# ---------------------------------------------------------------------------
# Roadmap (Operators v0.2+)
# ---------------------------------------------------------------------------
# ⊕ Superposition:
#   - Add phasor-based interference (constructive/destructive).
#   - Associativity checks within tolerance bands.
#
# ↔ Entanglement:
#   - Nonlocal correlation checks across Contexts.
#   - Propagation verification: left → right sync.
#
# ⟲ Resonance:
#   - Q-factor models, decay times, resonance envelope physics.
#   - Energy conservation validation during amplification.
#
# μ Measurement:
#   - Quantization lattice enforcement for amplitude/frequency.
#   - Assert canonicalization visibly alters values (no passthrough).
#
# π Projection:
#   - Replace attenuation model with Jones calculus / full vector rotation.
#   - Extend to arbitrary polarization subspaces.
#
# Shared:
#   - Replace polarization blending with Jones vector model.
#   - Frequency blending weighted by spectral density.
#   - Unified metadata lineage tracking for reproducible experiments.

# ---------------------------------------------------------------------------
# Developer Guidance (Symatics Operators v0.1, context-ready)
#
# • Determinism: Always pass a Context C (lattice, resonance, normalization).
# • Precision: Operators stay parametric in Context for swappable fidelity.
# • Benchmarks: Start with test vectors, add property-based law tests.
# • Interop: Collapse (μ) → GlyphNet events. Triggers (⇒) → CodexCore/Photon.
# • Evolution: This v0.1 is deterministic + safe. v0.2+ adds ⊖, τ, 𝔽, 𝔼.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Developer Guidance (Symatics Operators v0.1)
#
# • Determinism:
#   Always pass a Context C (frequency lattice, normalization rules, etc.)
#   and run CNF (canonical normalization) after each op. This ensures equality
#   checks and law-verification tests behave predictably.
#
# • Precision:
#   Keep operator implementations parametric in Context (lattice spacing,
#   resonance tolerance, noise floor). This allows swapping in higher-fidelity
#   physical models later (e.g. Jones calculus for polarization, full resonance
#   decay functions).
#
# • Benchmarks:
#   Start with basic test vectors (⊕, ↔, ⟲, μ, π).
#   Then add property-based tests (Hypothesis / QuickCheck style) to verify
#   algebraic laws (associativity, superposition consistency, resonance decay).
#
# • Interop:
#   Collapse signatures (μ) can map directly to GlyphNet events.
#   Trigger operators (⇒, deferred) should link to CodexCore actions or Photon
#   (.phn) capsule execution.
#
# • Evolution:
#   This v0.1 layer is safe, deterministic, and testable.
#   Future versions (v0.2+) will add: ⊖ (inversion), τ (transport),
#   𝔽 (Fourier fold), 𝔼 (entropic combine).

# • Context Integration:
#   All operator functions now accept an optional ctx: Context parameter.
#   If provided, results are snapped to the lattice / normalization rules
#   defined in ctx. If omitted, operators run in "free mode" (no snapping).
#
#   Example:
#       from symatics.context import Context
#       ctx = Context(lattice_spacing=1e-6, resonance_tolerance=1e-6)
#       result = OPS["⊕"].impl(sig1, sig2, ctx=ctx)
#
# Keep this block in sync with the Symatics Algebra Rulebook RFC.
# ---------------------------------------------------------------------------