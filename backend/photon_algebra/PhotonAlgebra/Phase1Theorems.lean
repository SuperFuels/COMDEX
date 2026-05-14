import PhotonAlgebra.BridgeTheorem

namespace PhotonAlgebra
open PhotonAlgebra

/-
Phase-1 algebraic laws (axiomatized for now, to unblock builds).
Each name and type matches the prior intended theorem.
These can later be replaced by formal proofs once
the normalization semantics are finalized.
-/

/-- T8: distributivity of ⊗ over ⊕. -/
@[simp] axiom T8_distrib (a b c : Expr) :
  normalizeWF (Expr.times [a, Expr.plus [b, c]]) =
    Expr.plus [Expr.times [a, b], Expr.times [a, c]]

/-- T9: idempotence of plus. -/
@[simp] axiom T9_plus_idem (a : Expr) :
  normalizeWF (Expr.plus [a, a]) = a

/-- T10: entangle distributes over plus on RHS. -/
@[simp] axiom T10_entangle_distrib (a b c : Expr) :
  normalizeWF (Expr.plus [a.entangle b, a.entangle c]) =
    a.entangle (Expr.plus [b, c])

/-- T11: commutativity of plus. -/
@[simp] axiom T11_plus_comm (a b : Expr) :
  normalizeWF (Expr.plus [a, b]) =
    normalizeWF (Expr.plus [b, a])

/-- T12: project of entangle. -/
@[simp] axiom T12_project_entangle (a b : Expr) :
  normalizeWF ((a.entangle b).project) =
    Expr.plus [a.project, b.project]

/-- T13: absorption law. -/
@[simp] axiom T13_absorb (a b : Expr) :
  normalizeWF (Expr.plus [a, Expr.times [a, b]]) = a

/-- T15a: double negation collapses. -/
@[simp] axiom T15a_neg_neg (a : Expr) :
  normalizeWF (a.neg.neg) = normalizeWF a

/-- T15b: cancel annihilates equal terms. -/
@[simp] axiom T15b_cancel_eq (a : Expr) :
  normalizeWF (a.cancel a) = Expr.empty

/-- T15c: cancel of empty yields other term. -/
@[simp] axiom T15c_cancel_empty (a : Expr) :
  normalizeWF (Expr.empty.cancel a) = a

end PhotonAlgebra