# backend/modules/codex/ops/execute_trigger.py
from typing import Any

def execute_trigger(source=None, target=None, context=None, **kwargs):
    print(f"[CodexOp] execute_trigger {source} → {target}")
    return {"op": "trigger", "source": source, "target": target}