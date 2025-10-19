"""
Symatic Differential Calculus — ∇⊕, ∇μ
────────────────────────────────────────────
Defines symbolic differential operators over resonance algebraic forms.

Extends the Symatics Core by introducing:
    ∇⊕ → Resonant Gradient Operator (superposition rate-of-change)
    ∇μ → Measurement Divergence Operator (information flux under collapse)

Each operator works over symbolic waves (ψ) and measurement functions (μ),
producing differential tensors representing the local gradient of coherence
and informational curvature.

These results can be posted to CodexTrace for visualization of ΔΦ/Δε trends,
and cross-linked to AION telemetry via Φ_stability and tolerance drift logs.

Mathematical Form:
    ∇⊕ ψ = ∂ψ / ∂Φ         (gradient of resonance field wrt awareness phase)
    ∇μ μ = ∂μ / ∂ε         (divergence of measurement flux wrt tolerance)

Tensor Form (for QQC + AION bridge):
    ∇ = [∂Φ, ∂ε]
    Ψ_tensor = [[∇⊕ψ, ∇μψ], [∇⊕μ, ∇μμ]]

CodexTrace Tag:
    {"operator": "∇⊕" | "∇μ", "ΔΦ": x, "Δε": y, "curvature": z, "timestamp": ...}
"""

from __future__ import annotations
import numpy as np
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

CODEXTRACE_PATH = Path("backend/logs/codex/symatic_differential_trace.jsonl")


# ──────────────────────────────────────────────────────────────
# Core Differential Operator Definitions
# ──────────────────────────────────────────────────────────────

def nabla_superpose(psi: np.ndarray, phi: np.ndarray) -> Dict[str, float]:
    """
    ∇⊕: Gradient of superposition field wrt Φ phase.
    Approximates ∂ψ / ∂Φ using central difference.
    """
    dphi = np.gradient(phi)
    dpsi = np.gradient(psi)
    grad = np.divide(dpsi, dphi, out=np.zeros_like(dpsi), where=dphi != 0)
    curvature = float(np.mean(np.abs(np.gradient(grad))))
    return {"operator": "∇⊕", "ΔΦ": float(np.mean(dphi)), "Δε": 0.0, "curvature": curvature}


def nabla_measure(mu: np.ndarray, epsilon: np.ndarray) -> Dict[str, float]:
    """
    ∇μ: Divergence of measurement flux wrt tolerance ε.
    Approximates ∂μ / ∂ε using central difference.
    """
    deps = np.gradient(epsilon)
    dmu = np.gradient(mu)
    div = np.divide(dmu, deps, out=np.zeros_like(dmu), where=deps != 0)
    curvature = float(np.mean(np.abs(np.gradient(div))))
    return {"operator": "∇μ", "ΔΦ": 0.0, "Δε": float(np.mean(deps)), "curvature": curvature}


# ──────────────────────────────────────────────────────────────
# Tensor Construction
# ──────────────────────────────────────────────────────────────

def resonance_tensor(psi: np.ndarray, mu: np.ndarray,
                     phi: np.ndarray, epsilon: np.ndarray) -> np.ndarray:
    """
    Builds the resonance tensor combining ∇⊕ and ∇μ fields.
    Ψ_tensor = [[∇⊕ψ, ∇μψ],
                [∇⊕μ, ∇μμ]]
    """
    grad_psi = np.gradient(psi)
    div_mu = np.gradient(mu)

    tensor = np.array([
        [np.mean(np.gradient(grad_psi)), np.mean(np.gradient(div_mu))],
        [np.mean(np.gradient(grad_psi * mu)), np.mean(np.gradient(div_mu * psi))]
    ])

    return tensor


# ──────────────────────────────────────────────────────────────
# CodexTrace Coupling
# ──────────────────────────────────────────────────────────────

def log_to_codextrace(record: Dict[str, Any]):
    """Append a record of differential computation to CodexTrace."""
    CODEXTRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    record["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(CODEXTRACE_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")
    print(f"[CodexTrace::∇] {record['operator']} logged → ΔΦ={record['ΔΦ']:+.4f}, Δε={record['Δε']:+.4f}, κ={record['curvature']:.4f}")


def compute_differentials(psi: np.ndarray, mu: np.ndarray,
                          phi: np.ndarray, epsilon: np.ndarray) -> Dict[str, Any]:
    """
    Computes both ∇⊕ and ∇μ and logs to CodexTrace.
    Returns combined metrics and resonance tensor.
    """
    grad = nabla_superpose(psi, phi)
    div = nabla_measure(mu, epsilon)
    tensor = resonance_tensor(psi, mu, phi, epsilon)

    combined = {
        "∇⊕": grad,
        "∇μ": div,
        "tensor_trace": float(np.trace(tensor)),
        "tensor_det": float(np.linalg.det(tensor)),
    }

    # Log individual operator metrics
    log_to_codextrace(grad)
    log_to_codextrace(div)
    return combined


# ──────────────────────────────────────────────────────────────
# Example / Test Entry Point
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🧮 Symatic Differential Calculus — test run")
    Φ = np.linspace(0, 2 * np.pi, 100)
    ε = np.linspace(0.1, 1.0, 100)
    ψ = np.sin(Φ) ** 2
    μ = np.exp(-ε) * np.cos(Φ)

    result = compute_differentials(ψ, μ, Φ, ε)
    print(json.dumps(result, indent=2))