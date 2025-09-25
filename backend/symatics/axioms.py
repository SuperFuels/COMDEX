# backend/symatics/axioms.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, Dict, Any, Optional
from .terms import Var, Sym, App, Term
from .operators import OPS
from .signature import Signature
from .wave import canonical_signature

# -----------------
# Law schema
# -----------------

@dataclass(frozen=True)
class Law:
    name: str
    lhs: Term
    rhs: Term
    guard: Optional[Callable[[Dict[str, Any]], bool]] = None  # optional side condition

def S(name: str) -> Sym: 
    return Sym(name)

def V(name: str) -> Var: 
    return Var(name)

def A(head: str | Sym, *args: Term) -> App:
    return App(S(head) if isinstance(head, str) else head, list(args))

# -----------------
# Axioms (⊕, μ, ↔, ⋈)
# -----------------

AXIOMS: List[Law] = [

    # -----------------
    # ⊕, μ, ↔ fragment
    # -----------------

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

    # Idempotence of μ: μ(μ(x)) → μ(x)
    Law("μ-idem",
        lhs=A("μ", A("μ", V("x"))),
        rhs=A("μ", V("x"))
    ),

    # Distribution of ↔ over ⊕: (x⊕y)↔z → (x↔z) ⊕ (y↔z)
    Law("↔-dist-⊕",
        lhs=A("↔", A("⊕", V("x"), V("y")), V("z")),
        rhs=A("⊕", A("↔", V("x"), V("z")), A("↔", V("y"), V("z")))
    ),

    # -----------------
    # ⋈ interference fragment
    # -----------------

    # Commutativity with phase inversion:
    # (x ⋈[φ] y) → (y ⋈[−φ] x)
    Law("⋈-comm_phi",
        lhs=A("⋈", V("x"), V("y"), V("φ")),
        rhs=A("⋈", V("y"), V("x"), A("neg", V("φ")))
    ),

    # Self-interference at zero phase: (x ⋈[0] x) → x
    Law("⋈-self_zero",
        lhs=A("⋈", V("x"), V("x"), S("0")),
        rhs=V("x")
    ),

    # Self-interference at π phase: (x ⋈[π] x) → ⊥
    Law("⋈-self_pi",
        lhs=A("⋈", V("x"), V("x"), S("π")),
        rhs=S("⊥")
    ),

    # Neutrality of ⊥: (x ⋈[φ] ⊥) → x
    Law("⋈-neutral_phi",
        lhs=A("⋈", V("x"), S("⊥"), V("φ")),
        rhs=V("x")
    ),

    # Phase composition associativity:
    # ((x ⋈[φ] y) ⋈[ψ] z) → (x ⋈[φ+ψ] (y ⋈[ψ] z))
    Law("⋈-assoc_phase",
        lhs=A("⋈", A("⋈", V("x"), V("y"), V("φ")), V("z"), V("ψ")),
        rhs=A("⋈", V("x"), A("⋈", V("y"), V("z"), V("ψ")), A("add", V("φ"), V("ψ")))
    ),

    # Phase cancellation:
    # (x ⋈[φ] (x ⋈[−φ] y)) → y
    Law("⋈-inv_phase",
        lhs=A("⋈", V("x"), A("⋈", V("x"), V("y"), A("neg", V("φ"))), V("φ")),
        rhs=V("y")
    ),
]