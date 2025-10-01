"""
Photon Algebra (Phase 1) — Successor to Boolean Algebra.
--------------------------------------------------------

Defines the foundational axioms (P1–P8), the collapse operator,
and a rewriter for normalization.

Boolean {0,1} ⊂ PhotonStates
Symatics ↔ Codex ↔ Photon are unified here.
"""

from typing import Any, Dict, List, Union, Optional
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

# E2: Meta-ops bounds (inert for now)
TOP: Dict[str, Any] = {"op": "⊤"}
BOTTOM: Dict[str, Any] = {"op": "⊥"}

__all__ = [
    "PhotonState",
    "SQIMap",
    "EMPTY",
    "TOP",
    "BOTTOM",
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
    # E2 constructors
    "similar",
    "contains",
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

def collapse(state: PhotonState, sqi: Optional[SQIMap] = None) -> PhotonState:
    """
    P7: Collapse — ∇ selects a state based on SQI weights.
    If `sqi` is None, return symbolic collapse operator instead of sampling.
    """
    if not isinstance(state, dict) or state.get("op") != "⊕":
        # Nothing to collapse, return as-is
        return state

    states = state.get("states", [])
    if not states:
        return EMPTY

    if sqi is None:
        # symbolic collapse
        return {"op": "∇", "state": state}

    # probabilistic collapse by SQI
    weights = [sqi.get(str(s), 1.0) for s in states]
    chosen = random.choices(states, weights=weights, k=1)[0]
    logger.info(f"[PhotonAlgebra] ∇ collapse {states} → {chosen} (weights={weights})")
    return chosen

def project(state: PhotonState, sqi: Optional[SQIMap] = None) -> Dict[str, Any]:
    """
    P8: Projection — ★ returns SQI drift score.
    If `sqi` is None, return symbolic ★(state).
    """
    if sqi is None:
        return {"op": "★", "state": state}
    return {"op": "★", "state": state, "score": sqi.get(str(state), 0.0)}

# -------------------------------
# E2: Meta-ops (inert constructors)
# -------------------------------

def similar(a: PhotonState, b: PhotonState) -> Dict[str, Any]:
    """E2: Similarity operator — a ≈ b (inert in Phase 1)"""
    return {"op": "≈", "states": [a, b]}

def contains(a: PhotonState, b: PhotonState) -> Dict[str, Any]:
    """E2: Containment operator — a ⊂ b (inert in Phase 1)"""
    return {"op": "⊂", "states": [a, b]}

# -------------------------------
# Boolean Subset
# -------------------------------

def to_boolean(state: PhotonState, sqi: SQIMap, threshold: float = 0.5) -> int:
    """Boolean ⊂ Photon — map state → {0,1} by SQI threshold."""
    return 1 if sqi.get(str(state), 0.0) >= threshold else 0

# -------------------------------
# Rewriter
# -------------------------------

def rewrite(expr: Dict[str, Any]) -> PhotonState:
    """
    Normalize expressions (flatten ⊕, eliminate neutral ops).
    Phase 1: very simple rules; expand later.
    """
    if expr is EMPTY:
        return EMPTY

    op = expr.get("op")

    if op == "⊕":
        # flatten nested superpositions
        flat_states: List[PhotonState] = []
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

    # E2: inert pass-through for ≈, ⊂, ⊤, ⊥ (no rewrites yet)
    # Any other op just passes through untouched in Phase 1.
    return expr

# -------------------------------
# Debug Harness
# -------------------------------

if __name__ == "__main__":
    sqi = {"a": 0.8, "b": 0.2, "c": 0.5}
    expr = superpose("a", "b")
    ent = entangle(expr, "c")
    collapsed = collapse(expr, sqi)
    projected = project("a", sqi)
    sim = similar("a", "b")
    cont = contains("a", "b")

    print("Expr:", expr)
    print("Entangled:", ent)
    print("Collapsed:", collapsed)
    print("Boolean(a):", to_boolean("a", sqi))
    print("Projection(a):", projected)
    print("Similar(a,b):", sim)
    print("Contains(a,b):", cont)
    print("TOP:", TOP, "BOTTOM:", BOTTOM)