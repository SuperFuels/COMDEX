# backend/modules/codex/ops/execute_d_dt.py
from typing import Any

def execute_d_dt(expr, t=None, context=None, **kwargs):
    print(f"[CodexOp] execute_d_dt ∂/∂t {expr}")
    return {"op": "d_dt", "expr": expr, "t": t}