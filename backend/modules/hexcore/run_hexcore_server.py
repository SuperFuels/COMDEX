#!/usr/bin/env python3
"""
HexCore (HTTP) — minimal Symatics evaluator + metrics

Key semantics (LOCKED):
- μ is the measurement/collapse operator.
- ∇ is RESERVED for math:∇ (gradient) and MUST NOT be treated as collapse.

Metrics:
- ρ  : coherence   (0..1)
- Ī  : entropy     (0..1)
- ⟲  : equilibrium (0..1)   = (ρ + (1-Ī))/2
- SQI: checkpoint score      = sqrt(ρ * (1-Ī))
"""

from __future__ import annotations

import math
import os
import re
import statistics
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="HexCore", version="0.1")

# ─────────────────────────────────────────────
# Request model
# ─────────────────────────────────────────────
class QuantumRequest(BaseModel):
    expr: str = ""


# ─────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────
def safe_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def compute_superposition(a: float, b: float) -> float:
    return (a + b) / 2.0


def compute_entanglement(a: float, b: float) -> float:
    return a * b


def compute_resonance_value(a: float, b: float) -> float:
    """
    Keep the existing numeric "resonance value" behavior (not normalized).
    Normalized equilibrium metric is emitted separately as ⟲.
    """
    if (a + b) == 0:
        return 0.0
    return 2.0 * a * b / (a + b)


def compute_measurement(a: float, b: float) -> float:
    # simple stable collapse/measurement heuristic (mean)
    return (a + b) / 2.0


def coherence_metric(values: List[float]) -> float:
    """Simple coherence = 1 - variance normalized."""
    if len(values) < 2:
        return 1.0
    var = statistics.pvariance(values)
    return max(0.0, 1.0 - var / (1.0 + var))


def entropy_metric(values: List[float]) -> float:
    """Pseudo-entropy = normalized log dispersion."""
    vals = [abs(v) for v in values if v != 0]
    if not vals:
        return 0.0
    avg = sum(vals) / len(vals)
    dispersion = sum(abs(v - avg) for v in vals) / len(vals)
    return float(round(min(1.0, math.log(1.0 + dispersion)), 3))


def equilibrium_metric(rho: float, iota: float) -> float:
    """⟲ equilibrium score in [0,1]."""
    return max(0.0, min(1.0, (rho + (1.0 - iota)) / 2.0))


def sqi_metric(rho: float, iota: float) -> float:
    """SQI checkpoint score (penalizes imbalance)."""
    return max(0.0, min(1.0, math.sqrt(max(0.0, rho) * max(0.0, 1.0 - iota))))


# ─────────────────────────────────────────────
# Symatics Evaluator
# ─────────────────────────────────────────────
_OP_RE = re.compile(r"(⊕|↔|⟲|μ|->|∇)\s*\(([^)]*)\)")

def evaluate_symatic_expr(expr: str) -> Dict[str, Any]:
    """
    Evaluate numeric + symbolic Symatics expressions.

    Operators:
      ⊕(a,b)  -> superposition
      ↔(a,b)  -> entanglement
      ⟲(a,b)  -> resonance VALUE (non-normalized) (see note)
      μ(a,b)  -> measurement/collapse
      ->(x)   -> trigger = exp(x)
      ∇(...)  -> RESERVED (gradient). Returns status=skipped.

    Emits metrics:
      ρ, Ī, ⟲ (equilibrium), SQI
    """
    expr = (expr or "").strip()

    # 0) Reserved operator hard-block
    if "∇" in expr:
        # If user explicitly tries ∇(...), treat as reserved.
        if _OP_RE.search(expr) and "∇" in expr:
            return {
                "status": "skipped",
                "result": None,
                "ρ": 0.5,
                "Ī": 0.5,
                "⟲": 0.5,
                "SQI": 0.5,
                "type": "reserved",
                "note": "∇ is reserved for math:∇ (gradient). Use μ for measurement/collapse.",
            }

    # 1) Numeric math (very restricted)
    if re.fullmatch(r"[0-9\+\-\*\/\(\)\.\sxX]+", expr):
        e2 = expr.replace("x", "*").replace("X", "*")
        try:
            result = eval(e2, {"__builtins__": None, "math": math})
            result_f = float(result)
            rho = float(round(coherence_metric([result_f]), 3))
            iota = float(round(entropy_metric([result_f]), 3))
            eq = float(round(equilibrium_metric(rho, iota), 3))
            sqi = float(round(sqi_metric(rho, iota), 3))
            return {
                "result": result,
                "ρ": rho,
                "Ī": iota,
                "⟲": eq,
                "SQI": sqi,
                "type": "numeric",
            }
        except Exception as e:
            return {"error": f"Math eval error: {e}"}

    # 2) Operator forms
    m = _OP_RE.search(expr)
    if m:
        op = m.group(1)
        raw_args = (m.group(2) or "").strip()
        args = [a.strip() for a in raw_args.split(",") if a.strip()]

        if op != "->" and len(args) < 2:
            return {"error": f"Operator {op} requires two arguments."}
        if op == "->" and len(args) < 1:
            return {"error": "Operator -> requires one argument."}

        # reserved
        if op == "∇":
            return {
                "status": "skipped",
                "result": None,
                "ρ": 0.5,
                "Ī": 0.5,
                "⟲": 0.5,
                "SQI": 0.5,
                "type": "reserved",
                "note": "∇ is reserved for math:∇ (gradient). Use μ for measurement/collapse.",
            }

        a = safe_float(args[0]) if args else None
        b = safe_float(args[1]) if len(args) > 1 else None

        # numeric operands
        if a is not None and (b is not None or op == "->"):
            if op == "⊕":
                val = compute_superposition(a, float(b))
            elif op == "↔":
                val = compute_entanglement(a, float(b))
            elif op == "⟲":
                val = compute_resonance_value(a, float(b))
            elif op == "μ":
                val = compute_measurement(a, float(b))
            elif op == "->":
                val = math.exp(a)
            else:
                val = None

            vals = [v for v in [a, b, val] if isinstance(v, (int, float)) and v is not None]
            rho = float(round(coherence_metric([float(v) for v in vals]) if vals else 0.5, 3))
            iota = float(round(entropy_metric([float(v) for v in vals]) if vals else 0.5, 3))
            eq = float(round(equilibrium_metric(rho, iota), 3))
            sqi = float(round(sqi_metric(rho, iota), 3))

            return {
                "result": val,
                "ρ": rho,
                "Ī": iota,
                "⟲": eq,
                "SQI": sqi,
                "type": "numeric_symatic",
            }

        # symbolic operands
        meaning = {
            "⊕": "superposition",
            "↔": "entanglement",
            "⟲": "resonance",
            "μ": "measure",
            "->": "trigger",
        }.get(op, "unknown")

        # default symbolic metrics (stable placeholders)
        rho = 1.0
        iota = 0.5
        eq = float(round(equilibrium_metric(rho, iota), 3))
        sqi = float(round(sqi_metric(rho, iota), 3))

        return {
            "result": f"Ψ = {meaning}({', '.join(args)})",
            "ρ": rho,
            "Ī": iota,
            "⟲": eq,
            "SQI": sqi,
            "type": "symbolic",
        }

    # 3) Default symbolic interpretation
    if "photon" in expr and "wave" in expr:
        rho, iota = 0.92, 0.12
        return {"result": "Ψ = coherent(superposition(photon, wave))", "ρ": rho, "Ī": iota, "⟲": equilibrium_metric(rho, iota), "SQI": sqi_metric(rho, iota), "type": "symbolic"}
    if "resonance" in expr:
        rho, iota = 0.85, 0.25
        return {"result": "ρ⊕Ī -> balanced field state", "ρ": rho, "Ī": iota, "⟲": equilibrium_metric(rho, iota), "SQI": sqi_metric(rho, iota), "type": "symbolic"}
    if "entanglement" in expr:
        rho, iota = 0.78, 0.30
        return {"result": "↔ -> dual-phase coupling", "ρ": rho, "Ī": iota, "⟲": equilibrium_metric(rho, iota), "SQI": sqi_metric(rho, iota), "type": "symbolic"}

    rho, iota = 0.5, 0.5
    return {"result": f"[QQC symbolic] evaluated {expr}", "ρ": rho, "Ī": iota, "⟲": equilibrium_metric(rho, iota), "SQI": sqi_metric(rho, iota), "type": "symbolic"}


# ─────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────
@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "module": "HexCore", "qqc": True}


@app.post("/quantum")
def quantum_op(payload: QuantumRequest) -> Dict[str, Any]:
    return evaluate_symatic_expr(payload.expr)


# ─────────────────────────────────────────────
# Launch
# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("HEXCORE_PORT", "8500"))
    uvicorn.run(app, host="0.0.0.0", port=port)