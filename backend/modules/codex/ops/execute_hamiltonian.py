# backend/modules/codex/ops/execute_hamiltonian.py
from typing import Any

def execute_hamiltonian(name=None, context=None, **kwargs):
    print(f"[CodexOp] execute_hamiltonian H({name})")
    return {"op": "hamiltonian", "name": name}