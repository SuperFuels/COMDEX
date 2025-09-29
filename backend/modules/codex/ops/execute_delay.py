# backend/modules/codex/ops/execute_delay.py
import time
from typing import Any

def execute_delay(symbol, seconds=1, context=None, **kwargs):
    print(f"[CodexOp] execute_delay {symbol} for {seconds}s")
    time.sleep(seconds)
    return f"Delayed: {symbol} by {seconds}s"