# backend/modules/codex/ops/execute_ricci_scalar.py
def execute_ricci_scalar(context=None, **kwargs):
    print("[CodexOp] execute_ricci_scalar R")
    return {"op": "ricci_scalar"}