# backend/modules/codex/ops/execute_laplacian.py
from typing import Any

def execute_laplacian(field, coords=None, context=None, **kwargs):
    print(f"[CodexOp] execute_laplacian ∇²{field}")
    return {"op": "laplacian", "field": field, "coords": coords}