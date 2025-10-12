"""
Quantum Ops (dict-backed for registry + tests)
──────────────────────────────────────────────
Unified quantum operator primitives for Tessaris Symatics.

Exports:
  - dict-based quantum ops ({"op": "...", "args": [...]})
  - INSTRUCTION_REGISTRY mapping symbols to callables
  - LAW_REGISTRY["quantum"] hooks (lazy-injected to avoid circular import)

Implements:
  - ⊕  Superposition
  - ↔  Entanglement
  - μ  Measurement
  - ε  Noisy Measurement
  - ⊗  Tensor Fusion
  - ≡  Equivalence / Coherence Check
  - ¬  Negation / Phase Inversion
"""

import random
import logging

logger = logging.getLogger(__name__)

# -----------------
# Dict-based Quantum Operators
# -----------------

def entangle(a, b):
    """Entanglement ↔ (dict form)."""
    return {"op": "↔", "args": [a, b]}


def superpose(a, b):
    """Superposition ⊕ (dict form)."""
    return {"op": "⊕", "args": [a, b]}


def measure(a):
    """Measurement μ (dict form). Collapses superpositions if present."""
    if isinstance(a, dict) and a.get("op") == "⊕":
        collapsed = random.choice(a.get("args", []))
        logger.debug(f"[Quantum μ] Collapsed superposition → {collapsed}")
        return {"op": "μ", "args": [a], "collapsed": collapsed}
    return {"op": "μ", "args": [a], "collapsed": a}


def measurement_noisy(a, eps: float):
    """Noisy measurement ε (dict form)."""
    return {"op": "ε", "args": [a, eps], "value": a}


# -----------------
# Phase 1 — Extended Quantum Operators
# -----------------

def tensor(a, b):
    """Tensor Fusion ⊗ — combines two waves into a single tensor product."""
    return {"op": "⊗", "args": [a, b], "fused": True}


def equivalence(a, b):
    """Equivalence ≡ — symbolic coherence or equality operator."""
    equal = a == b
    return {"op": "≡", "args": [a, b], "coherent": equal}


def negation(a):
    """Negation ¬ — flips phase or symbolic sense of the argument."""
    return {"op": "¬", "args": [a], "inverted": True}


# -----------------
# Instruction Registry
# -----------------

INSTRUCTION_REGISTRY = {
    "⊕": superpose,
    "↔": entangle,
    "μ": measure,
    "ε": measurement_noisy,
    "⊗": tensor,
    "≡": equivalence,
    "¬": negation,
}


# -----------------
# LAW_REGISTRY Wiring (lazy)
# -----------------

def inject_into_law_registry():
    """
    Safely injects quantum ops into LAW_REGISTRY["quantum"].
    Should be called by symatics_rulebook after initialization.
    """
    try:
        from backend.symatics.symatics_rulebook import LAW_REGISTRY
        LAW_REGISTRY.setdefault("quantum", [])
        for fn in (
            entangle,
            superpose,
            measure,
            measurement_noisy,
            tensor,
            equivalence,
            negation,
        ):
            if fn not in LAW_REGISTRY["quantum"]:
                LAW_REGISTRY["quantum"].append(fn)
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            f"[QuantumOps] Could not inject into LAW_REGISTRY (lazy): {e}"
        )
        return False


# NOTE: ⚠️ No automatic injection here — must be called explicitly