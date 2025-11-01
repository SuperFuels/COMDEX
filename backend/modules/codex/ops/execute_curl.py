# backend/modules/codex/ops/execute_curl.py
from typing import Any

def execute_curl(vector, coords=None, context=None, **kwargs):
    print(f"[CodexOp] execute_curl ∇*{vector}")
    return {"op": "curl", "vector": vector, "coords": coords}