"""
===========================================
📁 photon_algebra.py
===========================================
Photon Algebra — successor to Boolean Algebra.

This module defines the algebraic operators over photon states,
where:
  - Boolean {0,1} ⊂ PhotonStates
  - SQI (Semantic Quality Index) replaces probability
  - Symatics provides the resonance structures
  - Photon Algebra provides the calculus
"""

import logging
import random
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)

# -------------------------------------------
# Types
# -------------------------------------------

PhotonState = Union[str, Dict[str, Any]]  # a glyph ID or structured state
SQIMap = Dict[str, float]  # glyph_id → quality weight


# -------------------------------------------
# Core Axioms
# -------------------------------------------

def identity(a: PhotonState) -> PhotonState:
    """a ⊕ ∅ = a"""
    return a


def superpose(*states: PhotonState) -> Dict[str, Any]:
    """⊕ — place states into superposition"""
    return {"op": "⊕", "states": list(states)}


def entangle(a: PhotonState, b: PhotonState) -> Dict[str, Any]:
    """↔ — entangle two states (symmetric)"""
    return {"op": "↔", "states": [a, b]}


def fuse(a: PhotonState, b: PhotonState) -> Dict[str, Any]:
    """⊗ — resonance amplification (reinforce alignment)"""
    return {"op": "⊗", "states": [a, b]}


def cancel(a: PhotonState, b: PhotonState) -> Dict[str, Any]:
    """⊖ — destructive cancellation of states"""
    return {"op": "⊖", "states": [a, b]}


def negate(a: PhotonState) -> Dict[str, Any]:
    """¬ — invert photon resonance"""
    return {"op": "¬", "state": a}


def collapse(state: Dict[str, Any], sqi: SQIMap) -> PhotonState:
    """
    ∇ — collapse superposition into a classical outcome,
    weighted by SQI distribution.
    """
    if not state or "states" not in state:
        return state

    states = state["states"]
    weights = [sqi.get(str(s), 1.0) for s in states]
    chosen = random.choices(states, weights=weights, k=1)[0]

    logger.info(f"[PhotonAlgebra] ∇ collapse {states} → {chosen} (weights={weights})")
    return chosen


def score(state: PhotonState, sqi: SQIMap) -> Dict[str, Any]:
    """★ — project SQI drift score"""
    return {
        "op": "★",
        "state": state,
        "score": sqi.get(str(state), 0.0)
    }


def broadcast(state: PhotonState, container_id: str) -> Dict[str, Any]:
    """☄ — broadcast photon state across containers"""
    return {
        "op": "☄",
        "state": state,
        "container": container_id
    }


# -------------------------------------------
# Boolean Subset
# -------------------------------------------

def to_boolean(state: PhotonState, sqi: SQIMap, threshold: float = 0.5) -> int:
    """
    Map photon state to Boolean 0/1 by SQI threshold.
    (Shows that Boolean ⊂ Photon Algebra)
    """
    return 1 if sqi.get(str(state), 0.0) >= threshold else 0


# -------------------------------------------
# Evaluation Engine
# -------------------------------------------

def evaluate(expr: Dict[str, Any], sqi: SQIMap) -> PhotonState:
    """
    Evaluate a Photon Algebra expression against an SQI map.
    """
    op = expr.get("op")

    if op == "⊕":
        return superpose(*expr["states"])
    elif op == "↔":
        a, b = expr["states"]
        return entangle(a, b)
    elif op == "⊗":
        a, b = expr["states"]
        return fuse(a, b)
    elif op == "⊖":
        a, b = expr["states"]
        return cancel(a, b)
    elif op == "¬":
        return negate(expr["state"])
    elif op == "∇":
        return collapse(expr, sqi)
    elif op == "★":
        return score(expr["state"], sqi)
    elif op == "☄":
        return broadcast(expr["state"], expr.get("container", "unknown"))
    else:
        return expr  # passthrough


# -------------------------------------------
# Trace Capsule Hook
# -------------------------------------------

def trace(expr: Dict[str, Any], sqi: SQIMap) -> Dict[str, Any]:
    """
    Return a Photon Capsule trace (for .dc.json replay).
    """
    return {
        "expr": expr,
        "sqi": sqi,
        "result": evaluate(expr, sqi)
    }


# -------------------------------------------
# Debug Harness
# -------------------------------------------
if __name__ == "__main__":
    # Example SQI map
    sqi = {"a": 0.8, "b": 0.2, "c": 0.5}

    expr = superpose("a", "b")
    ent = entangle(expr, "c")
    result = collapse(ent, sqi)

    print("Superposed:", expr)
    print("Entangled:", ent)
    print("Collapsed:", result)
    print("Score(a):", score("a", sqi))
    print("Boolean(a):", to_boolean("a", sqi))