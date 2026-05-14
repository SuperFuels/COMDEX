# backend/modules/codex/ops/execute_ket.py
from typing import Any

def execute_ket(label, context=None, **kwargs):
    print(f"[CodexOp] execute_ket |{label}⟩")
    return {"op": "ket", "label": label}