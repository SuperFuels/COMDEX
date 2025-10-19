# ===============================
# 📁 backend/quant/qtools/qtools_utils.py
# ===============================
"""
🧰 QTools — Core Symbolic Utility Library
-----------------------------------------
Shared mathematical and symbolic helpers for the Q-Series stack.

Includes:
    • Glyph ⇄ Operator mappings
    • Resonance + coherence validators
    • Numeric normalization utilities
    • Serialization and pretty-print tools
    • Random state initializers for quantum sheets

All components are lightweight and dependency-safe.
"""

from __future__ import annotations
import math
import json
import cmath
import numpy as np
from typing import Any, Dict, List, Tuple, Union


# ----------------------------------------------------------------------
# Glyph ↔ Operator Mappings
# ----------------------------------------------------------------------
GLYPH_TO_OP = {
    "⊕": "superpose",
    "↔": "entangle",
    "⟲": "resonate",
    "∇": "collapse",
    "μ": "measure",
    "π": "project",
}
OP_TO_GLYPH = {v: k for k, v in GLYPH_TO_OP.items()}


def glyph_to_op(symbol: str) -> str:
    """Convert symbolic glyph to operation name."""
    return GLYPH_TO_OP.get(symbol, "unknown")


def op_to_glyph(op: str) -> str:
    """Convert operation name back to symbolic glyph."""
    return OP_TO_GLYPH.get(op, "?")


# ----------------------------------------------------------------------
# Resonance & Coherence Helpers
# ----------------------------------------------------------------------
def compute_resonance(a: np.ndarray, b: np.ndarray) -> Dict[str, float]:
    """
    Compute Φ–ψ resonance between two wavefields.

    Returns:
        {
          'correlation': float,
          'phase_shift': float,
          'coherence': float
        }
    """
    a_flat, b_flat = a.flatten(), b.flatten()
    correlation = float(np.vdot(a_flat, b_flat).real / (np.linalg.norm(a_flat) * np.linalg.norm(b_flat) + 1e-9))
    phase_shift = float(np.angle(np.vdot(a_flat, b_flat)))
    coherence = float(abs(correlation) * (1 - abs(phase_shift) / math.pi))
    return {
        "correlation": correlation,
        "phase_shift": phase_shift,
        "coherence": coherence,
    }


def validate_resonance_index(value: float) -> bool:
    """Return True if resonance index is within [0,1]."""
    return 0.0 <= value <= 1.0


def normalize_field(field: np.ndarray) -> np.ndarray:
    """Normalize a field to unit amplitude."""
    norm = np.linalg.norm(field)
    return field / (norm + 1e-9)


# ----------------------------------------------------------------------
# Symbolic Serialization
# ----------------------------------------------------------------------
def serialize_qtensor(tensor: np.ndarray) -> Dict[str, Any]:
    """Compact JSON-safe serializer for complex tensor fields."""
    return {
        "shape": tensor.shape,
        "real": tensor.real.tolist(),
        "imag": tensor.imag.tolist(),
    }


def deserialize_qtensor(payload: Dict[str, Any]) -> np.ndarray:
    """Reconstruct complex tensor from serialized form."""
    re = np.array(payload.get("real", []))
    im = np.array(payload.get("imag", []))
    return re + 1j * im


# ----------------------------------------------------------------------
# Pretty Print Utilities
# ----------------------------------------------------------------------
def format_complex(z: complex, precision: int = 4) -> str:
    """Format a complex number as readable Φ∠ψ string."""
    r, φ = abs(z), cmath.phase(z)
    return f"{r:.{precision}f}∠{φ:.{precision}f}"


def summarize_tensor(t: np.ndarray, name: str = "ψ") -> str:
    """Return a symbolic summary line for a tensor field."""
    mean = np.mean(np.abs(t))
    std = np.std(np.abs(t))
    return f"{name}: |Φ|≈{mean:.4f} σ={std:.4f}"


# ----------------------------------------------------------------------
# Random Initializers
# ----------------------------------------------------------------------
def random_unit_field(shape: Tuple[int, int]) -> np.ndarray:
    """Generate a random complex field with unit normalization."""
    data = np.random.randn(*shape) + 1j * np.random.randn(*shape)
    return normalize_field(data)


def random_resonant_pair(shape: Tuple[int, int]) -> Tuple[np.ndarray, np.ndarray]:
    """Generate two weakly correlated random fields for test simulations."""
    ψ1 = random_unit_field(shape)
    ψ2 = normalize_field(ψ1 + 0.05 * random_unit_field(shape))
    return ψ1, ψ2


# ----------------------------------------------------------------------
# Diagnostic Runner
# ----------------------------------------------------------------------
def run_test() -> Dict[str, Any]:
    """Quick self-test for QTools utilities."""
    ψ1, ψ2 = random_resonant_pair((4, 4))
    res = compute_resonance(ψ1, ψ2)
    return {
        "Φ_mean": float(np.mean(np.abs(ψ1))),
        "ψ_mean": float(np.mean(np.abs(ψ2))),
        "coherence": res["coherence"],
        "status": "ok" if validate_resonance_index(abs(res["correlation"])) else "warn",
    }


# ----------------------------------------------------------------------
# Self-test
# ----------------------------------------------------------------------
if __name__ == "__main__":
    from pprint import pprint
    pprint(run_test())