# File: backend/symatics/quantum_ops.py
"""
Quantum Ops (dict-backed for registry + tests)
──────────────────────────────────────────────
Unifies entangle, superpose, and measure operators.

Exports:
  - dict-based quantum ops ({"op": "...", "args": [...]})
  - INSTRUCTION_REGISTRY mapping symbols to callables
  - LAW_REGISTRY["quantum"] hooks
"""

import random
from backend.symatics.symatics_rulebook import LAW_REGISTRY


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
        # collapse nondeterministically (here: random branch)
        collapsed = random.choice(a.get("args", []))
        return {"op": "μ", "args": [a], "collapsed": collapsed}
    return {"op": "μ", "args": [a], "collapsed": a}


def measurement_noisy(a, eps: float):
    """Noisy measurement ε (dict form)."""
    return {"op": "ε", "args": [a, eps], "value": a}


# -----------------
# Instruction Registry
# -----------------

INSTRUCTION_REGISTRY = {
    "⊕": superpose,
    "↔": entangle,
    "μ": measure,
    "ε": measurement_noisy,
}


# -----------------
# LAW_REGISTRY Wiring
# -----------------

LAW_REGISTRY.setdefault("quantum", [])
LAW_REGISTRY["quantum"].extend([
    entangle,
    superpose,
    measure,
    measurement_noisy,
])