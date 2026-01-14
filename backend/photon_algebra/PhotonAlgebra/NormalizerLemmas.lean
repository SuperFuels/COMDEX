import PhotonAlgebra.Normalizer
import PhotonAlgebra.NormalizerWF

namespace PhotonAlgebra
open PhotonAlgebra

/-- All `normalizeWF` congruences aligned with full canonical `normStep`. -/

@[simp] theorem normalizeWF_congr_neg {e₁ e₂ : Expr}
  (h : normalizeWF e₁ = normalizeWF e₂) :
  normalizeWF (Expr.neg e₁) = normalizeWF (Expr.neg e₂) := by
  simp [PhotonAlgebra.normalizeWF, h]

@[simp] theorem normalizeWF_congr_cancel {a₁ a₂ b₁ b₂ : Expr}
  (ha : normalizeWF a₁ = normalizeWF a₂)
  (hb : normalizeWF b₁ = normalizeWF b₂) :
  normalizeWF (Expr.cancel a₁ b₁) = normalizeWF (Expr.cancel a₂ b₂) := by
  simp [PhotonAlgebra.normalizeWF, ha, hb]

@[simp] theorem normalizeWF_congr_entangle {a₁ a₂ b₁ b₂ : Expr}
  (ha : normalizeWF a₁ = normalizeWF a₂)
  (hb : normalizeWF b₁ = normalizeWF b₂) :
  normalizeWF (Expr.entangle a₁ b₁) = normalizeWF (Expr.entangle a₂ b₂) := by
  simp [PhotonAlgebra.normalizeWF, ha, hb]

@[simp] theorem normalizeWF_congr_collapse {e₁ e₂ : Expr}
  (h : normalizeWF e₁ = normalizeWF e₂) :
  normalizeWF (Expr.collapse e₁) = normalizeWF (Expr.collapse e₂) := by
  simp [PhotonAlgebra.normalizeWF, h]

@[simp] theorem normalizeWF_congr_plus {xs ys : List Expr}
  (hmap : xs.map normalizeWF = ys.map normalizeWF) :
  normalizeWF (Expr.plus xs) = normalizeWF (Expr.plus ys) := by
  simp [PhotonAlgebra.normalizeWF, hmap]

@[simp] theorem normalizeWF_congr_times {xs ys : List Expr}
  (hmap : xs.map normalizeWF = ys.map normalizeWF) :
  normalizeWF (Expr.times xs) = normalizeWF (Expr.times ys) := by
  simp [PhotonAlgebra.normalizeWF, hmap]

end PhotonAlgebra