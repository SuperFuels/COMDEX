# backend/modules/codex/ops/execute_negation.py
from typing import Any

def execute_negation(symbol, context=None, **kwargs):
    print(f"[CodexOp] execute_negation ⊗{symbol}")
    return {"op": "negation", "symbol": symbol, "result": f"¬{symbol}"}