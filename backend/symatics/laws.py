# symatics/laws.py
from __future__ import annotations
import math, random

from .signature import Signature
from .engine import SymNode, eval_expr
from .normalize import canonical_signature


# ---------------------------------------------------------------------------
# Random Signature Generator
# ---------------------------------------------------------------------------

def random_sig() -> Signature:
    """Generate a random Signature for law checks."""
    return Signature(
        amplitude=random.uniform(0.5, 2.0),
        frequency=random.uniform(1.0, 10.0),
        phase=random.uniform(0.0, 2 * math.pi),
        polarization=random.choice(["H", "V"]),
        meta={}
    )


# ---------------------------------------------------------------------------
# Algebraic Laws
# ---------------------------------------------------------------------------

def law_associativity(ctx=None, trials: int = 10) -> bool:
    """
    Check associativity of ⊕ under canonicalization.

    v0.1: Exact equality of amplitudes.
    TODO v0.2+: Relax equality into tolerance band to allow destructive interference.
    """
    for _ in range(trials):
        a, b, c = random_sig(), random_sig(), random_sig()

        left = eval_expr(SymNode(op="⊕", args=[
            SymNode(op="⊕", args=[SymNode(value=a), SymNode(value=b)]),
            SymNode(value=c)
        ]), ctx)

        right = eval_expr(SymNode(op="⊕", args=[
            SymNode(value=a),
            SymNode(op="⊕", args=[SymNode(value=b), SymNode(value=c)])
        ]), ctx)

        if abs(left.amplitude - right.amplitude) > 1e-6:
            return False

    return True

# ---------------------------------------------------------------------------
# Roadmap (Laws v0.2+)
# ---------------------------------------------------------------------------
# Associativity:
#   - Relax equality to tolerance bands (allow destructive interference).
#   - Add randomized destructive interference cases in tests.
#
# Commutativity:
#   - Introduce tolerance-based checks across polarization and phase.
#
# Resonance Laws:
#   - Add Q-factor models and temporal decay verification.
#
# Entanglement Laws:
#   - Nonlocal correlation propagation tests across multiple Contexts.
#
# Measurement Laws:
#   - Assert quantization lattice enforcement (freq/amp snap).
#   - Introduce stochastic collapse distributions.