import PhotonAlgebra.NormalizerWF

namespace PhotonAlgebra
open PhotonAlgebra

-- Minimal helper: map congruence is usually all you want.
@[simp] theorem map_normalizeWF_congr {xs ys : List Expr}
  (h : xs.map normalizeWF = ys.map normalizeWF) :
  canonPlus (xs.map normalizeWF) = canonPlus (ys.map normalizeWF) := by
  simpa [h]

end PhotonAlgebra