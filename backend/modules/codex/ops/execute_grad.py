# backend/modules/codex/ops/execute_grad.py

from typing import Any

def execute_grad(field, coords=None, context=None, **kwargs):
    print(f"[CodexOp] execute_grad ∇{field}")
    return {"op": "grad", "field": field, "coords": coords}