# backend/modules/codex/ops/execute_tensor_product.py
from typing import Any

def execute_tensor_product(A, B, context=None, **kwargs):
    print(f"[CodexOp] execute_tensor_product {A} ⊗ {B}")
    return {"op": "tensor_product", "A": A, "B": B, "result": f"{A}⊗{B}"}