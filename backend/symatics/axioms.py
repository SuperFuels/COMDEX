# =====================================================
# File: backend/symatics/axioms.py
# =====================================================
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, Dict, Any, Optional

from .terms import Var, Sym, App, Term
from backend.symatics.operators import OPS as SymOps
from .signature import Signature
from .wave import canonical_signature

# =====================================================
# Clean up legacy operator aliases (Tessaris v0.3+)
# =====================================================
# Removes deprecated aliases such as superpose_op, entangle_op, and measure_op
# to silence warnings and enforce the modern operator namespace.
for legacy_alias in ("superpose_op", "entangle_op", "measure_op"):
    if legacy_alias in SymOps:
        del SymOps[legacy_alias]

# === Added imports for v2.0 Meta-Axiom Integration ===
from backend.symatics.core.meta_axioms_v02 import META_AXIOMS
from backend.symatics.core.validators.pi_s_closure import validate_pi_s_closure

# =====================================================
# LAW SCHEMA
# =====================================================
import warnings
warnings.filterwarnings(
    "ignore",
    message=r"\[Tessaris\] Legacy operator aliases",
    category=DeprecationWarning,
)

@dataclass(frozen=True)
class Law:
    """
    Represents a formal rewrite rule or invariant in Symatics Algebra.
    Optionally includes a guard (side condition) for context-sensitive rules.
    """
    name: str
    lhs: Term
    rhs: Term
    guard: Optional[Callable[[Dict[str, Any]], bool]] = None  # optional side condition


def S(name: str) -> Sym:
    """Shortcut for creating a symbolic constant."""
    return Sym(name)

def V(name: str) -> Var:
    """Shortcut for creating a variable symbol."""
    return Var(name)

def A(head: str | Sym, *args: Term) -> App:
    """Application node: builds an operator expression."""
    return App(S(head) if isinstance(head, str) else head, list(args))

# =====================================================
# BASE AXIOMS - OPERATOR LAWS (⊕, μ, ↔, ⋈)
# =====================================================

AXIOMS: List[Law] = [

    # -----------------
    # ⊕, μ, ↔ fragment
    # -----------------

    # Associativity of ⊕: (x⊕y)⊕z -> x⊕(y⊕z)
    Law("⊕-assoc",
        lhs=A("⊕", A("⊕", V("x"), V("y")), V("z")),
        rhs=A("⊕", V("x"), A("⊕", V("y"), V("z")))
    ),

    # Commutativity of ⊕: x⊕y -> y⊕x
    Law("⊕-comm",
        lhs=A("⊕", V("x"), V("y")),
        rhs=A("⊕", V("y"), V("x"))
    ),

    # Idempotence of μ: μ(μ(x)) -> μ(x)
    Law("μ-idem",
        lhs=A("μ", A("μ", V("x"))),
        rhs=A("μ", V("x"))
    ),

    # Distribution of ↔ over ⊕: (x⊕y)↔z -> (x↔z) ⊕ (y↔z)
    Law("↔-dist-⊕",
        lhs=A("↔", A("⊕", V("x"), V("y")), V("z")),
        rhs=A("⊕", A("↔", V("x"), V("z")), A("↔", V("y"), V("z")))
    ),

    # -----------------
    # ⋈ interference fragment
    # -----------------

    # Commutativity with phase inversion:
    # (x ⋈[φ] y) -> (y ⋈[-φ] x)
    Law("⋈-comm_phi",
        lhs=A("⋈", V("x"), V("y"), V("φ")),
        rhs=A("⋈", V("y"), V("x"), A("neg", V("φ")))
    ),

    # Self-interference at zero phase: (x ⋈[0] x) -> x
    Law("⋈-self_zero",
        lhs=A("⋈", V("x"), V("x"), S("0")),
        rhs=V("x")
    ),

    # Self-interference at π phase: (x ⋈[π] x) -> ⊥
    Law("⋈-self_pi",
        lhs=A("⋈", V("x"), V("x"), S("π")),
        rhs=S("⊥")
    ),

    # Neutrality of ⊥: (x ⋈[φ] ⊥) -> x
    Law("⋈-neutral_phi",
        lhs=A("⋈", V("x"), S("⊥"), V("φ")),
        rhs=V("x")
    ),

    # Phase composition associativity:
    # ((x ⋈[φ] y) ⋈[ψ] z) -> (x ⋈[φ+ψ] (y ⋈[ψ] z))
    Law("⋈-assoc_phase",
        lhs=A("⋈", A("⋈", V("x"), V("y"), V("φ")), V("z"), V("ψ")),
        rhs=A("⋈", V("x"), A("⋈", V("y"), V("z"), V("ψ")), A("add", V("φ"), V("ψ")))
    ),

    # Phase cancellation:
    # (x ⋈[φ] (x ⋈[-φ] y)) -> y
    Law("⋈-inv_phase",
        lhs=A("⋈", V("x"), A("⋈", V("x"), V("y"), A("neg", V("φ"))), V("φ")),
        rhs=V("y")
    ),
]

# =====================================================
# META-AXIOMS (v2.0+) - GEOMETRY -> COMPUTATION
# =====================================================

def load_axioms(version: str = "v02") -> List[Dict[str, Any]]:
    """
    Loads both classical operator laws (⊕, μ, ↔, ⋈)
    and the v2.0+ meta-axioms (G-L-E-I-C-X) used by
    the symbolic and photonic runtime.

    Returns
    -------
    list[dict]
        Unified rulebook combining symbolic laws and meta-axioms.
    """
    axioms = []
    # Convert internal Laws -> dicts for uniformity
    for law in AXIOMS:
        axioms.append({
            "id": law.name,
            "domain": "Operator",
            "lhs": str(law.lhs),
            "rhs": str(law.rhs),
            "guard": law.guard.__name__ if law.guard else None,
        })

    # Extend with high-level foundational laws (meta-axioms)
    axioms.extend(META_AXIOMS)
    return axioms


def verify_axioms(state: Any) -> List[Dict[str, Any]]:
    """
    Runtime verifier for πs closure and meta-law coherence.

    Parameters
    ----------
    state : object or dict
        Must include `phase` or `field['phase']` (array-like).

    Returns
    -------
    list[dict]
        Validation results for all applicable meta-axioms.
    """
    results = []
    for ax in META_AXIOMS:
        if "validated_by" in ax and "validate_pi_s_closure" in ax["validated_by"]:
            check = validate_pi_s_closure(state)
            results.append({
                "axiom_id": ax["id"],
                "domain": ax["domain"],
                "passed": check["passed"],
                "deviation": check["deviation"],
                "n": check["n"],
            })
        else:
            results.append({
                "axiom_id": ax["id"],
                "domain": ax["domain"],
                "passed": True,
                "note": "Symbolic-only axiom; no numerical check applied."
            })

    return results


# =====================================================
# DEBUG/UTILITY ENTRYPOINTS
# =====================================================

def summarize_axioms() -> None:
    """
    Prints a concise summary of all loaded axioms and meta-axioms.
    Useful for diagnostics and export pipelines.
    """
    all_axioms = load_axioms()
    print(f"\n[Symatics::Axioms] Loaded {len(all_axioms)} total laws:")
    for ax in all_axioms:
        tag = "META" if ax.get("domain") != "Operator" else "CORE"
        print(f"  - [{tag}] {ax['id']} -> {ax['domain']}")


def test_axioms_runtime(state: Dict[str, Any]) -> None:
    """
    Quick runtime check that validates πs closure and prints summary.
    """
    print("\n[Symatics::Verify] Running πs closure verification...")
    results = verify_axioms(state)
    passed = sum(1 for r in results if r.get("passed"))
    failed = len(results) - passed
    print(f"  -> {passed} passed, {failed} failed")
    for r in results:
        if not r.get("passed"):
            print(f"    ❌ {r['axiom_id']} ({r['domain']}) -> deviation={r.get('deviation')}")