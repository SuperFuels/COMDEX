import PhotonAlgebra.Normalizer
import PhotonAlgebra.NormalizerWF
import PhotonAlgebra.Canon

namespace PhotonAlgebra
open PhotonAlgebra

/-- `normStep` is definitionally the same computation as `normalizeWF`. -/
theorem normStep_eq_normalizeWF (e : Expr) : normStep e = normalizeWF e := by
  cases e <;> rfl

/-- Canon sum is stable under normalizeWF when inputs are already normalized. -/
theorem canonPlus_fixed (xs : List Expr) :
  normalizeWF (canonPlus (xs.map normalizeWF)) = canonPlus (xs.map normalizeWF) := by
  classical
  -- split on the *output* of canonPlus
  cases h : canonPlus (xs.map normalizeWF) with
  | atom s =>
      simp [normalizeWF, h]
  | empty =>
      simp [normalizeWF, h]
  | plus ys =>
      -- normalizeWF (plus ys) = canonPlus (ys.map normalizeWF)
      -- goal becomes canonPlus (ys.map normalizeWF) = plus ys, and h is exactly that
      simp [normalizeWF, h]
  | times ys =>
      simp [normalizeWF, h]
  | entangle a b =>
      simp [normalizeWF, h]
  | neg e =>
      simp [normalizeWF, h]
  | cancel a b =>
      simp [normalizeWF, h]
  | project e =>
      simp [normalizeWF, h]
  | collapse e =>
      simp [normalizeWF, h]

/-- Canon product is stable under normalizeWF when inputs are already normalized. -/
theorem canonTimes_fixed (xs : List Expr) :
  normalizeWF (canonTimes (xs.map normalizeWF)) = canonTimes (xs.map normalizeWF) := by
  classical
  cases h : canonTimes (xs.map normalizeWF) with
  | atom s =>
      simp [normalizeWF, h]
  | empty =>
      simp [normalizeWF, h]
  | plus ys =>
      -- normalizeWF (plus ys) = canonPlus (ys.map normalizeWF)
      -- but h already pins canonTimes (...) = plus ys
      simp [normalizeWF, h]
  | times ys =>
      simp [normalizeWF, h]
  | entangle a b =>
      simp [normalizeWF, h]
  | neg e =>
      simp [normalizeWF, h]
  | cancel a b =>
      simp [normalizeWF, h]
  | project e =>
      simp [normalizeWF, h]
  | collapse e =>
      simp [normalizeWF, h]

/-- Idempotence of normalizeWF (now follows from canonPlus_fixed/canonTimes_fixed). -/
theorem normalizeWF_idem (e : Expr) : normalizeWF (normalizeWF e) = normalizeWF e := by
  classical
  cases e with
  | atom s =>
      simp [normalizeWF]
  | empty =>
      simp [normalizeWF]
  | plus xs =>
      -- normalizeWF (plus xs) = canonPlus (xs.map normalizeWF)
      simpa [normalizeWF] using (canonPlus_fixed xs)
  | times xs =>
      simpa [normalizeWF] using (canonTimes_fixed xs)
  | entangle a b =>
      have ha := normalizeWF_idem a
      have hb := normalizeWF_idem b
      simp [normalizeWF, ha, hb]
  | neg e =>
      have ih := normalizeWF_idem e
      -- normalizeWF (neg e) matches on normalizeWF e; split on that value
      cases h : normalizeWF e <;> simp [normalizeWF, ih, h, canonPlus_fixed, canonTimes_fixed]
  | cancel a b =>
      have ha := normalizeWF_idem a
      have hb := normalizeWF_idem b
      simp [normalizeWF, ha, hb]
  | project e =>
      have ih := normalizeWF_idem e
      cases h : normalizeWF e <;> simp [normalizeWF, ih, h, canonPlus_fixed, canonTimes_fixed]
  | collapse e =>
      have ih := normalizeWF_idem e
      simp [normalizeWF, ih]

/-- WF normal form is invariant under one `normStep`. -/
theorem wf_invariant_normStep (e : Expr) :
  normalizeWF (normStep e) = normalizeWF e := by
  simpa [normStep_eq_normalizeWF] using (normalizeWF_idem e)

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
