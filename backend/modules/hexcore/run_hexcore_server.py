#!/usr/bin/env python3
from fastapi import FastAPI
import uvicorn
import math, re, statistics

app = FastAPI()

# ─────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────
def safe_float(x):
    """Convert to float if numeric, else None."""
    try:
        return float(x)
    except Exception:
        return None

def compute_superposition(a, b):
    return (a + b) / 2.0

def compute_entanglement(a, b):
    return a * b

def compute_resonance(a, b):
    if (a + b) == 0:
        return 0
    return 2 * a * b / (a + b)

def coherence_metric(values):
    """Simple coherence = 1 - variance normalized."""
    if len(values) < 2:
        return 1.0
    var = statistics.pvariance(values)
    return max(0.0, 1 - var / (1 + var))

def entropy_metric(values):
    """Pseudo-entropy = normalized log dispersion."""
    vals = [abs(v) for v in values if v != 0]
    if not vals:
        return 0.0
    avg = sum(vals) / len(vals)
    dispersion = sum(abs(v - avg) for v in vals) / len(vals)
    return round(min(1.0, math.log(1 + dispersion)), 3)


# ─────────────────────────────────────────────
# Symatics Evaluator
# ─────────────────────────────────────────────
def evaluate_symatic_expr(expr: str):
    """
    Evaluate numeric + symbolic Symatics expressions.
    Supports:
      ⊕(a,b)  → superposition = (a+b)/2
      ↔(a,b)  → entanglement = a*b
      ⟲(a,b)  → resonance = 2ab/(a+b)
      ∇(...)  → collapse = mean(...)
      ⇒(x)    → trigger = exp(x)
    Emits coherence (ρ) and entropy (Ī) metrics.
    """
    expr = expr.strip()

    # 1️⃣ Try numeric math first
    if re.fullmatch(r"[0-9\+\-\*\/\(\)\.\sxX]+", expr):
        expr = expr.replace("x", "*").replace("X", "*")
        try:
            result = eval(expr, {"__builtins__": None, "math": math})
            rho = coherence_metric([result])
            iota = entropy_metric([result])
            return {
                "result": result,
                "ρ": round(rho, 3),
                "Ī": round(iota, 3),
                "type": "numeric"
            }
        except Exception as e:
            return {"error": f"Math eval error: {e}"}

    # 2️⃣ Pattern match symbolic operators
    m = re.search(r"([\⊕↔⟲∇⇒])\s*\(([^)]+)\)", expr)
    if m:
        op = m.group(1)
        args = [a.strip() for a in m.group(2).split(",")]
        if len(args) < 2 and op != "⇒":
            return {"error": f"Operator {op} requires two arguments."}

        a = safe_float(args[0])
        b = safe_float(args[1]) if len(args) > 1 else None

        # handle numeric operands
        if a is not None and (b is not None or op == "⇒"):
            if op == "⊕":
                val = compute_superposition(a, b)
            elif op == "↔":
                val = compute_entanglement(a, b)
            elif op == "⟲":
                val = compute_resonance(a, b)
            elif op == "∇":
                val = (a + b) / 2.0
            elif op == "⇒":
                val = math.exp(a)
            else:
                val = None

            vals = [v for v in [a, b, val] if v is not None]
            rho = coherence_metric(vals)
            iota = entropy_metric(vals)

            return {
                "result": val,
                "ρ": round(rho, 3),
                "Ī": round(iota, 3),
                "type": "numeric_symatic"
            }

        # fallback: symbolic operands
        else:
            if op == "⊕":
                meaning = "superposition"
            elif op == "↔":
                meaning = "entanglement"
            elif op == "⟲":
                meaning = "resonance"
            elif op == "∇":
                meaning = "collapse"
            elif op == "⇒":
                meaning = "trigger"
            else:
                meaning = "unknown"
            return {
                "result": f"Ψ = {meaning}({', '.join(args)})",
                "ρ": 1.0,
                "Ī": 0.5,
                "type": "symbolic"
            }

    # 3️⃣ Default symbolic interpretation
    if "photon" in expr and "wave" in expr:
        return {"result": "Ψ = coherent(superposition(photon, wave))", "ρ": 0.92, "Ī": 0.12}
    if "resonance" in expr:
        return {"result": "ρ⊕Ī → balanced field state", "ρ": 0.85, "Ī": 0.25}
    if "entanglement" in expr:
        return {"result": "↔ → dual-phase coupling", "ρ": 0.78, "Ī": 0.30}

    return {"result": f"[QQC symbolic] evaluated {expr}", "ρ": 0.5, "Ī": 0.5}


# ─────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "module": "HexCore", "qqc": True}

@app.post("/quantum")
def quantum_op(payload: dict):
    expr = payload.get("expr", "")
    result = evaluate_symatic_expr(expr)
    return result


# ─────────────────────────────────────────────
# Launch
# ─────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8500)