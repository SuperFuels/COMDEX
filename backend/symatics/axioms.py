from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, Dict, Any, Optional, Tuple
from .terms import Var, Sym, App, Term
from .operators import OPS
from .signature import Signature
from .wave import canonical_signature

@dataclass(frozen=True)
class Law:
    name: str
    lhs: Term
    rhs: Term
    guard: Optional[Callable[[Dict[str, Any]], bool]] = None  # optional side condition

def S(name: str) -> Sym: return Sym(name)
def V(name: str) -> Var: return Var(name)
def A(head: str | Sym, *args: Term) -> App:
    return App(S(head) if isinstance(head,str) else head, list(args))

# Laws (schemata)
AXIOMS: List[Law] = [
    # Associativity of ⊕: (x⊕y)⊕z → x⊕(y⊕z)
    Law("⊕-assoc",
        lhs=A("⊕", A("⊕", V("x"), V("y")), V("z")),
        rhs=A("⊕", V("x"), A("⊕", V("y"), V("z")))
    ),
    # Commutativity of ⊕: x⊕y → y⊕x
    Law("⊕-comm",
        lhs=A("⊕", V("x"), V("y")),
        rhs=A("⊕", V("y"), V("x"))
    ),
    # Idempotent μ: μ(μ(x)) → μ(x)
    Law("μ-idem",
        lhs=A("μ", A("μ", V("x"))),
        rhs=A("μ", V("x"))
    ),
    # Distribution ↔ over ⊕: (x⊕y)↔z → (x↔z) ⊕ (y↔z)
    Law("↔-dist-⊕",
        lhs=A("↔", A("⊕", V("x"), V("y")), V("z")),
        rhs=A("⊕", A("↔", V("x"), V("z")), A("↔", V("y"), V("z")))
    ),
]