# backend/modules/codex/ops/execute_einstein_tensor.py
def execute_einstein_tensor(context=None, **kwargs):
    print("[CodexOp] execute_einstein_tensor G_{μν}")
    return {"op": "einstein_tensor"}