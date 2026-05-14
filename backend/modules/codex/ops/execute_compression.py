# backend/modules/codex/ops/execute_compression.py
from typing import Any

def execute_compression(*symbols, context=None, **kwargs):
    print(f"[CodexOp] execute_compression {symbols}")
    return f"∇({', '.join(map(str, symbols))})"