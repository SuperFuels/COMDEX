import PhotonAlgebra.Normalizer
import PhotonAlgebra.NormalizerWF

namespace PhotonAlgebra
open PhotonAlgebra

/-- One step preserves the WF normal form (trivial because `normStep = normalizeWF`). -/
@[simp] theorem wf_invariant_normStep (e : Expr) :
    normalizeWF (normStep e) = normalizeWF e := by
  simp [PhotonAlgebra.normStep]

/-- Fuel normalization preserves WF normal form. -/
theorem wf_invariant_normalizeFuel : ∀ k (e : Expr),
    normalizeWF (normalizeFuel k e) = normalizeWF e
  | 0, e => by
      simp [PhotonAlgebra.normalizeFuel]
  | Nat.succ k, e => by
      classical
      by_cases h : (normStep e == e) = true
      · simp [PhotonAlgebra.normalizeFuel, h]
      · simp [PhotonAlgebra.normalizeFuel, h]
        calc
          normalizeWF (normalizeFuel k (normStep e))
              = normalizeWF (normStep e) := wf_invariant_normalizeFuel k (normStep e)
          _   = normalizeWF e := by simp [wf_invariant_normStep]

/-- Bridge: normalize agrees with normalizeWF. -/
@[simp] theorem normalize_bridge (e : Expr) :
    normalizeWF (normalize e) = normalizeWF e := by
  simp [PhotonAlgebra.normalize, wf_invariant_normalizeFuel]

end PhotonAlgebra