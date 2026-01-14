import PhotonAlgebra.Normalizer
import PhotonAlgebra.NormalizerWF

namespace PhotonAlgebra
open PhotonAlgebra

/-- WF normal form is invariant under one `normStep` (now definitional). -/
theorem wf_invariant_normStep (e : Expr) :
  normalizeWF (normStep e) = normalizeWF e := by
  rfl

/-- WF normal form is invariant under the whole fuel loop. -/
theorem wf_invariant_normalizeFuel (k : Nat) (e : Expr) :
    normalizeWF (normalizeFuel k e) = normalizeWF e := by
  induction k generalizing e with
  | zero =>
      simp [normalizeFuel]
  | succ k ih =>
      by_cases hfix : (normStep e == e) = true
      · simp [normalizeFuel, hfix]
      ·
        have hstep : normalizeWF (normStep e) = normalizeWF e :=
          wf_invariant_normStep e
        simp [normalizeFuel, hfix, ih (e := normStep e), hstep]

/-- The operational normalizer preserves WF semantics (canonical form). -/
theorem normalize_bridge (e : Expr) :
    normalizeWF (normalize e) = normalizeWF e := by
  simpa [normalize] using
    wf_invariant_normalizeFuel (e.size * e.size + 50) e

end PhotonAlgebra
