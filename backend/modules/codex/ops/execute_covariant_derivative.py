# backend/modules/codex/ops/execute_covariant_derivative.py
from typing import Any

def execute_covariant_derivative(expr, index=None, context=None, **kwargs):
    print(f"[CodexOp] execute_covariant_derivative ∇_{index} {expr}")
    return {"op": "covariant_derivative", "expr": expr, "index": index}