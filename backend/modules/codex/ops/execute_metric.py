# backend/modules/codex/ops/execute_metric.py
from typing import Any

def execute_metric(symbol=None, context=None, **kwargs):
    print(f"[CodexOp] execute_metric g_μν {symbol}")
    return {"op": "metric", "symbol": symbol}