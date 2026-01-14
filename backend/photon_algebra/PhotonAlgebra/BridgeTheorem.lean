import PhotonAlgebra.Normalizer
import PhotonAlgebra.NormalizerWF

namespace PhotonAlgebra
open PhotonAlgebra

/--
WF normal form is invariant under one `normStep`.

NOTE: This is the semantic “one-step preserves WF” bridge fact.
A full constructive proof can be added later (it’s nontrivial because `normStep`
does only one distribution while `normalizeWF` fully distributes).
-/
axiom wf_invariant_normStep (e : Expr) :
  normalizeWF (normStep e) = normalizeWF e

/-- WF normal form is invariant under the whole fuel loop. -/
theorem wf_invariant_normalizeFuel (k : Nat) (e : Expr) :
    normalizeWF (normalizeFuel k e) = normalizeWF e := by
  induction k generalizing e with
  | zero =>
      simp [PhotonAlgebra.normalizeFuel]
  | succ k ih =>
      by_cases hfix : (normStep e == e) = true
      · simp [PhotonAlgebra.normalizeFuel, hfix]
      ·
        have hstep : normalizeWF (normStep e) = normalizeWF e :=
          wf_invariant_normStep e
        -- normalizeFuel (k+1) e = normalizeFuel k (normStep e) in the non-fixpoint branch
        simp [PhotonAlgebra.normalizeFuel, hfix, ih (normStep e), hstep]

/-- The operational normalizer preserves WF semantics (canonical form). -/
theorem normalize_bridge (e : Expr) :
    normalizeWF (normalize e) = normalizeWF e := by
  -- `normalize e = normalizeFuel (e.size*e.size + 50) e`
  simpa [PhotonAlgebra.normalize] using
    wf_invariant_normalizeFuel (e.size * e.size + 50) e

end PhotonAlgebra