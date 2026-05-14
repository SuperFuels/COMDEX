# backend/modules/codex/ops/execute_operator.py
from typing import Any

def execute_operator(name, arg=None, context=None, **kwargs):
    print(f"[CodexOp] execute_operator {name}[{arg}]")
    return f"Â[{name}]({arg})"