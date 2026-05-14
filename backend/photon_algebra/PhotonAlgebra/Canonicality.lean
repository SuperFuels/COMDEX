import PhotonAlgebra.NormalizerWF
import PhotonAlgebra.CanonWF

namespace PhotonAlgebra
open PhotonAlgebra

/-- `normalizeWF` is idempotent. -/
theorem normalizeWF_idem : ∀ e : Expr, normalizeWF (normalizeWF e) = normalizeWF e
  | Expr.atom s => by
      simp [PhotonAlgebra.normalizeWF]

  | Expr.empty => by
      simp [PhotonAlgebra.normalizeWF]

  | Expr.plus xs => by
      simpa [PhotonAlgebra.normalizeWF] using (canonPlus_stable xs)

  | Expr.times xs => by
      simpa [PhotonAlgebra.normalizeWF] using (canonTimes_stable xs)

  | Expr.entangle a b => by
      -- goal reduces to the entangle-stability lemma after unfolding normalizeWF once
      simpa [PhotonAlgebra.normalizeWF] using (entangle_stable a b)

  | Expr.cancel a b => by
      simpa [PhotonAlgebra.normalizeWF] using (cancel_stable a b)

  | Expr.collapse a => by
      have ha := normalizeWF_idem a
      simp [PhotonAlgebra.normalizeWF, ha]

  | Expr.neg a => by
      -- IMPORTANT: unfold normalizeWF on `.neg` so the goal becomes the same "match" form
      -- as `neg_stable`.
      simpa [PhotonAlgebra.normalizeWF] using (neg_stable a)

  | Expr.project a => by
      -- IMPORTANT: unfold normalizeWF on `.project` so the goal becomes the same "match" form
      -- as `project_stable`.
      simpa [PhotonAlgebra.normalizeWF] using (project_stable a)

end PhotonAlgebra