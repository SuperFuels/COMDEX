import PhotonAlgebra.Basic
import PhotonAlgebra.Normalizer

namespace PhotonAlgebra

open Expr

/-- Theorem checkers in the repo style:
    theorem_Ti(...) returns true iff norm(lhs) == norm(rhs).

These are PA-core equivalences under the directed normalizer.
-/

private def eqNorm (a b : Expr) : Bool := decide (norm a = norm b)

/-- T8: Distributivity (expansion) — a ⊗ (b ⊕ c) == (a ⊗ b) ⊕ (a ⊗ c). -/
def theorem_T8 (a b c : Expr) : Bool :=
  let lhs := times [a, plus [b, c]]
  let rhs := plus [times [a, b], times [a, c]]
  eqNorm lhs rhs

/-- T9: Double negation — ¬(¬a) == a. -/
def theorem_T9 (a : Expr) : Bool :=
  let lhs := neg (neg a)
  eqNorm lhs a

/-- T10: Entanglement distributivity — (a↔b) ⊕ (a↔c) == a↔(b⊕c). -/
def theorem_T10 (a b c : Expr) : Bool :=
  let lhs := plus [entangle a b, entangle a c]
  let rhs := entangle a (plus [b, c])
  eqNorm lhs rhs

/-- T11: Collapse wrapper consistency (symbolic): ∇(NF(a)) == NF(∇(a)). -/
def theorem_T11 (a : Expr) : Bool :=
  let lhs := collapse (norm a)
  let rhs := norm (collapse a)
  eqNorm lhs rhs

/-- T12: Projection fidelity (structural): ★(a↔b) == (★a) ⊕ (★b). -/
def theorem_T12 (a b : Expr) : Bool :=
  let lhs := project (entangle a b)
  let rhs := plus [project a, project b]
  eqNorm lhs rhs

/-- T13: Absorption — a ⊕ (a ⊗ b) == a. -/
def theorem_T13 (a b : Expr) : Bool :=
  let lhs := plus [a, times [a, b]]
  eqNorm lhs a

/-- T14: Dual distributivity factoring is intentionally NOT a PA-core theorem.

Returns true iff the equivalence happens to hold under this normalizer,
but callers MUST NOT rely on it.
-/
def theorem_T14 (a b c : Expr) : Bool :=
  let lhs := plus [a, times [b, c]]
  let rhs := times [plus [a, b], plus [a, c]]
  eqNorm lhs rhs

/-- T15: Falsification / cancellation identities — a ⊖ ∅ == a and ∅ ⊖ a == a. -/
def theorem_T15 (a : Expr) : Bool :=
  let lhs1 := cancel a empty
  let lhs2 := cancel empty a
  (eqNorm lhs1 a) && (eqNorm lhs2 a)

end PhotonAlgebra
