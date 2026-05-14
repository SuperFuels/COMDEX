# backend/modules/codex/ops/execute_schrodinger.py
from typing import Any

def execute_schrodinger(psi, H, t=None, context=None, **kwargs):
    print(f"[CodexOp] execute_schrodinger iħ ∂|{psi}⟩/∂t = {H}|{psi}⟩")
    return {"op": "schrodinger", "psi": psi, "H": H, "t": t}