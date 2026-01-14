import PhotonAlgebra.Normalizer
import PhotonAlgebra.NormalizerWF
import PhotonAlgebra.BridgeTheorem

namespace PhotonAlgebra
open PhotonAlgebra

def SUM  (a b : Expr) : Expr := Expr.plus [a, b]
def PROD (a b : Expr) : Expr := Expr.times [a, b]

/-- Equality via the reference normalizer. -/
def EqNF (x y : Expr) : Prop :=
  normalizeWF x = normalizeWF y

/-- T11: Collapse wrapper consistency. -/
theorem T11 (a : Expr) :
  normalizeWF (Expr.collapse a) = Expr.collapse (normalizeWF a) := by
  simp [PhotonAlgebra.normalizeWF]

/-
  “Undeniable laws” as EqNF statements.

  IMPORTANT: prove them by going through `normalize` (fuel/fixpoint),
  then use `normalize_bridge` to relate `normalizeWF` and `normalize`.
-/

/-- Helper: transport an EqNF goal to an equality under `normalize`. -/
private theorem EqNF_via_normalize (x y : Expr)
  (h : normalize x = normalize y) : EqNF x y := by
  unfold EqNF
  -- rewrite both sides into `normalizeWF (normalize _)` then use `h`
  calc
    normalizeWF x
        = normalizeWF (normalize x) := by
            symm
            simpa using (normalize_bridge x)
    _   = normalizeWF (normalize y) := by simpa [h]
    _   = normalizeWF y := by
            simpa using (normalize_bridge y)

/-- T8: distributivity in EqNF. -/
theorem T8 (a b c : Expr) :
  EqNF (PROD a (SUM b c)) (SUM (PROD a b) (PROD a c)) := by
  apply EqNF_via_normalize
  -- `normalize` reaches a fixpoint where distribution has been applied,
  -- so both sides normalize to the same result.
  simp [PhotonAlgebra.normalize, PhotonAlgebra.normalizeFuel, PROD, SUM, PhotonAlgebra.normStep]

/-- T10: entangle factoring in EqNF. -/
theorem T10 (a b c : Expr) :
  EqNF (SUM (Expr.entangle a b) (Expr.entangle a c))
       (Expr.entangle a (SUM b c)) := by
  apply EqNF_via_normalize
  simp [PhotonAlgebra.normalize, PhotonAlgebra.normalizeFuel, SUM, PhotonAlgebra.normStep]

/-- T13: absorption in EqNF. -/
theorem T13 (a b : Expr) :
  EqNF (SUM a (PROD a b)) a := by
  apply EqNF_via_normalize
  simp [PhotonAlgebra.normalize, PhotonAlgebra.normalizeFuel, PROD, SUM, PhotonAlgebra.normStep]

end PhotonAlgebra