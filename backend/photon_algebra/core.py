"""
Photon Algebra (Phase 1) — Successor to Boolean Algebra.
--------------------------------------------------------

Defines the foundational axioms (P1–P8), the collapse operator,
and a rewriter for normalization.

Boolean {0,1} ⊂ PhotonStates
Symatics ↔ Codex ↔ Photon are unified here.
"""

from typing import Any, Dict, List, Union
import random
import logging

logger = logging.getLogger(__name__)

# -------------------------------
# Types
# -------------------------------

PhotonState = Union[str, Dict[str, Any]]  # atomic glyph ID or structured op
SQIMap = Dict[str, float]  # glyph_id → Semantic Quality Index

# -------------------------------
# Constants
# -------------------------------

# Canonical representation of the empty photon state
EMPTY: Dict[str, Any] = {"op": "∅"}

__all__ = [
    "PhotonState",
    "SQIMap",
    "EMPTY",
    "identity",
    "superpose",
    "entangle",
    "fuse",
    "cancel",
    "negate",
    "collapse",
    "project",
    "to_boolean",
    "rewrite",
]

# -------------------------------
# Core Axioms (P1–P8)
# -------------------------------

def identity(a: PhotonState) -> PhotonState:
    """P1: Identity — a ⊕ ∅ = a"""
    return a

def superpose(*states: PhotonState) -> Dict[str, Any]:
    """P2: Superposition — combine states into ⊕"""
    if not states:
        return EMPTY
    return {"op": "⊕", "states": list(states)}

def entangle(a: PhotonState, b: PhotonState) -> Dict[str, Any]:
    """P3: Entanglement — symmetric ↔"""
    return {"op": "↔", "states": [a, b]}

def fuse(a: PhotonState, b: PhotonState) -> Dict[str, Any]:
    """P4: Resonance / Amplification — ⊗"""
    return {"op": "⊗", "states": [a, b]}

def cancel(a: PhotonState, b: PhotonState) -> Dict[str, Any]:
    """P5: Cancellation — ⊖"""
    if a == b:
        return EMPTY
    return {"op": "⊖", "states": [a, b]}

def negate(a: PhotonState) -> Dict[str, Any]:
    """P6: Negation — ¬"""
    # Double negation elimination
    if isinstance(a, dict) and a.get("op") == "¬":
        return a.get("state", EMPTY)
    return {"op": "¬", "state": a}

def collapse(state: Dict[str, Any], sqi: SQIMap) -> PhotonState:
    """
    P7: Collapse — ∇ selects a state based on SQI weights.
    """
    if not state or "states" not in state:
        return state

    states = state["states"]
    if not states:
        return EMPTY

    weights = [sqi.get(str(s), 1.0) for s in states]
    chosen = random.choices(states, weights=weights, k=1)[0]

    logger.info(f"[PhotonAlgebra] ∇ collapse {states} → {chosen} (weights={weights})")
    return chosen

def project(state: PhotonState, sqi: SQIMap) -> Dict[str, Any]:
    """P8: Projection — ★ returns SQI drift score."""
    return {"op": "★", "state": state, "score": sqi.get(str(state), 0.0)}

# -------------------------------
# Boolean Subset
# -------------------------------

def to_boolean(state: PhotonState, sqi: SQIMap, threshold: float = 0.5) -> int:
    """Boolean ⊂ Photon — map state → {0,1} by SQI threshold."""
    return 1 if sqi.get(str(state), 0.0) >= threshold else 0

# -------------------------------
# Rewriter
# -------------------------------

def rewrite(expr: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize expressions (flatten ⊕, eliminate neutral ops).
    Phase 1: very simple rules; expand later.
    """
    if expr is EMPTY:
        return EMPTY

    op = expr.get("op")

    if op == "⊕":
        # flatten nested superpositions
        flat_states = []
        for s in expr.get("states", []):
            if isinstance(s, dict) and s.get("op") == "⊕":
                flat_states.extend(s.get("states", []))
            else:
                flat_states.append(s)

        # Remove ∅ since a ⊕ ∅ = a
        flat_states = [s for s in flat_states if s != EMPTY]

        if not flat_states:
            return EMPTY
        if len(flat_states) == 1:
            return flat_states[0]
        return {"op": "⊕", "states": flat_states}

    return expr  # passthrough

# -------------------------------
# Debug Harness
# -------------------------------

if __name__ == "__main__":
    sqi = {"a": 0.8, "b": 0.2, "c": 0.5}
    expr = superpose("a", "b")
    ent = entangle(expr, "c")
    collapsed = collapse(expr, sqi)

    print("Expr:", expr)
    print("Entangled:", ent)
    print("Collapsed:", collapsed)
    print("Boolean(a):", to_boolean("a", sqi))
    print("Projection(a):", project("a", sqi))