from __future__ import annotations
from .terms import Term, Sym, App

def typecheck(t: Term) -> bool:
    # v0.1 lightweight: ensure operator heads are symbols
    if isinstance(t, App):
        if not isinstance(t.head, Sym):
            return False
        return all(typecheck(a) for a in t.args)
    return True