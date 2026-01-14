import PhotonAlgebra.Normalizer
import PhotonAlgebra.NormalizerWF
import PhotonAlgebra.BridgeTheorem

namespace PhotonAlgebra
open PhotonAlgebra

def SUM  (a b : Expr) : Expr := Expr.plus [a, b]
def PROD (a b : Expr) : Expr := Expr.times [a, b]

def EqNF (x y : Expr) : Prop := normalizeWF x = normalizeWF y
notation:50 x " ≈ " y => EqNF x y

/- ------------------------------------------------------------------------- -/
/- Local simp helpers: only what Phase1Theorems needs.                        -/
/- ------------------------------------------------------------------------- -/

@[simp] theorem beq_empty_empty : (Expr.empty == Expr.empty) = true := by
  simp [BEq.beq, Expr.beq, Expr.beqFuel]

@[simp] theorem beq_atom_empty (s : String) : (Expr.atom s == Expr.empty) = false := by
  simp [BEq.beq, Expr.beq, Expr.beqFuel]

@[simp] theorem beq_empty_atom (s : String) : (Expr.empty == Expr.atom s) = false := by
  simp [BEq.beq, Expr.beq, Expr.beqFuel]

@[simp] theorem beq_plus_empty (xs : List Expr) : (Expr.plus xs == Expr.empty) = false := by
  simp [BEq.beq, Expr.beq, Expr.beqFuel]

@[simp] theorem beq_empty_plus (xs : List Expr) : (Expr.empty == Expr.plus xs) = false := by
  simp [BEq.beq, Expr.beq, Expr.beqFuel]

@[simp] theorem beq_times_empty (xs : List Expr) : (Expr.times xs == Expr.empty) = false := by
  simp [BEq.beq, Expr.beq, Expr.beqFuel]

@[simp] theorem beq_empty_times (xs : List Expr) : (Expr.empty == Expr.times xs) = false := by
  simp [BEq.beq, Expr.beq, Expr.beqFuel]

@[simp] theorem beq_entangle_empty (a b : Expr) : (Expr.entangle a b == Expr.empty) = false := by
  simp [BEq.beq, Expr.beq, Expr.beqFuel]

@[simp] theorem beq_empty_entangle (a b : Expr) : (Expr.empty == Expr.entangle a b) = false := by
  simp [BEq.beq, Expr.beq, Expr.beqFuel]

@[simp] theorem beq_neg_empty (a : Expr) : (Expr.neg a == Expr.empty) = false := by
  simp [BEq.beq, Expr.beq, Expr.beqFuel]

@[simp] theorem beq_empty_neg (a : Expr) : (Expr.empty == Expr.neg a) = false := by
  simp [BEq.beq, Expr.beq, Expr.beqFuel]

@[simp] theorem beq_cancel_empty (a b : Expr) : (Expr.cancel a b == Expr.empty) = false := by
  simp [BEq.beq, Expr.beq, Expr.beqFuel]

@[simp] theorem beq_empty_cancel (a b : Expr) : (Expr.empty == Expr.cancel a b) = false := by
  simp [BEq.beq, Expr.beq, Expr.beqFuel]

@[simp] theorem beq_project_empty (a : Expr) : (Expr.project a == Expr.empty) = false := by
  simp [BEq.beq, Expr.beq, Expr.beqFuel]

@[simp] theorem beq_empty_project (a : Expr) : (Expr.empty == Expr.project a) = false := by
  simp [BEq.beq, Expr.beq, Expr.beqFuel]

@[simp] theorem beq_collapse_empty (a : Expr) : (Expr.collapse a == Expr.empty) = false := by
  simp [BEq.beq, Expr.beq, Expr.beqFuel]

@[simp] theorem beq_empty_collapse (a : Expr) : (Expr.empty == Expr.collapse a) = false := by
  simp [BEq.beq, Expr.beq, Expr.beqFuel]

/-- Phase1Theorems expects this name; keep it local here for now. -/
axiom beq_refl (x : Expr) : (x == x) = true

/- ------------------------------------------------------------------------- -/
/- Core theorem: collapse wrapper safety.                                    -/
/- ------------------------------------------------------------------------- -/

theorem CollapseWF (a : Expr) :
  normalizeWF (Expr.collapse a) = Expr.collapse (normalizeWF a) := by
  simp [PhotonAlgebra.normalizeWF]

/- ------------------------------------------------------------------------- -/
/- Phase-1 theorems.                                                         -/
/- ------------------------------------------------------------------------- -/

-- T9: ¬(¬a) ≈ a
axiom T9 (a : Expr) : EqNF (Expr.neg (Expr.neg a)) a

-- T11: a ↔ a ≈ a
theorem T11 (a : Expr) : EqNF (Expr.entangle a a) a := by
  unfold EqNF
  have h : (normalizeWF a == normalizeWF a) = true := by
    simpa using (beq_refl (normalizeWF a))
  simp [PhotonAlgebra.normalizeWF, h]

-- T15R: a ⊖ ∅ ≈ a
theorem T15_right (a : Expr) : EqNF (Expr.cancel a Expr.empty) a := by
  unfold EqNF
  cases hna : normalizeWF a <;> simp [PhotonAlgebra.normalizeWF, hna]

-- T15L: ∅ ⊖ a ≈ a
theorem T15_left (a : Expr) : EqNF (Expr.cancel Expr.empty a) a := by
  unfold EqNF
  cases hna : normalizeWF a <;> simp [PhotonAlgebra.normalizeWF, hna]

-- T15C: a ⊖ a ≈ ∅
theorem T15_cancel (a : Expr) : EqNF (Expr.cancel a a) Expr.empty := by
  unfold EqNF
  have h : (normalizeWF a == normalizeWF a) = true := by
    simpa using (beq_refl (normalizeWF a))
  simp [PhotonAlgebra.normalizeWF, h]

/- ------------------------------------------------------------------------- -/
/- Canon/Factor heavy laws: keep as axioms until we add high-level lemmas.   -/
/- ------------------------------------------------------------------------- -/

axiom T8 (a b c : Expr) :
  EqNF (PROD a (SUM b c)) (SUM (PROD a b) (PROD a c))

axiom T10 (a b c : Expr) :
  EqNF (SUM (Expr.entangle a b) (Expr.entangle a c))
       (Expr.entangle a (SUM b c))

axiom T12 (a b : Expr) :
  EqNF (Expr.project (Expr.entangle a b))
       (Expr.plus [Expr.project a, Expr.project b])

axiom T13 (a b : Expr) :
  EqNF (SUM a (PROD a b)) a

end PhotonAlgebra