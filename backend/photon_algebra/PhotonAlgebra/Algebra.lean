import PhotonAlgebra.Basic
import PhotonAlgebra.NormalizerWF
import PhotonAlgebra.NormalizerBridge
import PhotonAlgebra.Theorems

namespace PhotonAlgebra

/-- Canonical equality (your algebraic equality). -/
def EqNF (x y : Expr) : Prop := normalizeWF x = normalizeWF y

notation:50 x " ≈ " y => EqNF x y

-- Equivalence
theorem EqNF_refl (x) : x ≈ x := rfl
theorem EqNF_symm {x y} : x ≈ y → y ≈ x := by intro h; simpa [EqNF] using h.symm
theorem EqNF_trans {x y z} : x ≈ y → y ≈ z → x ≈ z := by intro h1 h2; exact Eq.trans h1 h2

-- Congruence examples (you can add all ops)
theorem EqNF_plus {x x' y y'} :
  x ≈ x' → y ≈ y' → (Expr.plus [x,y]) ≈ (Expr.plus [x',y']) := by
  intro hx hy; simp [EqNF, PhotonAlgebra.normalizeWF, hx, hy]

-- Headline laws (imported or restated)
-- T8, T10, T13, ...

end PhotonAlgebra