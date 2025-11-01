from __future__ import annotations
from typing import Any, Dict
from .terms import Term, Sym, App
from .operators import OPS
from .signature import Signature

def evaluate(t: Term, env: Dict[str, Any]) -> Any:
    """
    v0.1 evaluator: if term is App with primitive operator head and arguments
    evaluate to concrete semantics (Signatures-in -> Signature/Dict out).
    """
    if isinstance(t, Sym):
        return env.get(t.name, t)
    if isinstance(t, App):
        head = t.head.name if isinstance(t.head, Sym) else None
        if head in OPS:
            op = OPS[head]
            if len(t.args) != op.arity:
                raise ValueError(f"Arity mismatch for {head}")
            vals = [evaluate(a, env) for a in t.args]
            return op.impl(*vals)
        # Non-primitive application: interpret as data structure
        return {"head": evaluate(t.head, env), "args": [evaluate(a, env) for a in t.args]}
    return env.get(str(t), t)