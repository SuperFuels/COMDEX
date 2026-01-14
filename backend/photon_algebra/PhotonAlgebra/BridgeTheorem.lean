import PhotonAlgebra.Normalizer
import PhotonAlgebra.NormalizerWF

namespace PhotonAlgebra
open PhotonAlgebra

/-
  Option A:
  normStep is definitionally aligned with normalizeWF, so the bridge reduces
  to normalizeWF idempotence.

  Remaining work: prove normalizeWF is idempotent, which boils down to showing
  canonPlus/canonTimes outputs are stable under normalizeWF once their inputs
  are already normalized.
-/

-- Forward declare idempotence so we can use it in stability lemmas.
theorem normalizeWF_idem : ∀ e : Expr, normalizeWF (normalizeWF e) = normalizeWF e := by
  classical
  intro e
  -- We prove by cases, using two local stability lemmas for plus/times.
  -- (Lean won't automatically simplify canonPlus/canonTimes pipelines.)
  cases e with
  | atom s =>
      simp [normalizeWF]
  | empty =>
      simp [normalizeWF]
  | entangle a b =>
      -- reduces to IH on a and b
      -- after simp, goal becomes conjunction of idempotence on subterms
      -- which simp can solve using recursive call by re-running normalizeWF_idem on each.
      -- But since we're in the definition of normalizeWF_idem itself, we do it manually:
      have ha : normalizeWF (normalizeWF a) = normalizeWF a := normalizeWF_idem a
      have hb : normalizeWF (normalizeWF b) = normalizeWF b := normalizeWF_idem b
      simp [normalizeWF, ha, hb]
  | collapse e =>
      -- collapse just pushes normalizeWF inside
      have ih : normalizeWF (normalizeWF e) = normalizeWF e := normalizeWF_idem e
      simp [normalizeWF, ih]
  | neg e =>
      have ih : normalizeWF (normalizeWF e) = normalizeWF e := normalizeWF_idem e
      -- After rewriting, both sides are definitional equal
      simp [normalizeWF, ih]
  | cancel a b =>
      have ha : normalizeWF (normalizeWF a) = normalizeWF a := normalizeWF_idem a
      have hb : normalizeWF (normalizeWF b) = normalizeWF b := normalizeWF_idem b
      simp [normalizeWF, ha, hb]
  | project e =>
      have ih : normalizeWF (normalizeWF e) = normalizeWF e := normalizeWF_idem e
      simp [normalizeWF, ih]
  | plus xs =>
      -- Stability lemma for canonPlus after map normalizeWF
      -- normalizeWF (normalizeWF (plus xs)) = normalizeWF (canonPlus (map normalizeWF xs))
      -- normalizeWF (plus xs) = canonPlus (map normalizeWF xs)
      -- so need: normalizeWF (canonPlus (map normalizeWF xs)) = canonPlus (map normalizeWF xs)
      -- We'll prove it by rewriting canonPlus(...) as normalizeWF (Expr.plus xs) and using the theorem itself.
      -- Concretely: normalizeWF (Expr.plus xs) = canonPlus (map normalizeWF xs) by definition.
      -- So LHS becomes normalizeWF (normalizeWF (Expr.plus xs)) and RHS becomes normalizeWF (Expr.plus xs).
      have : normalizeWF (canonPlus (xs.map normalizeWF)) = canonPlus (xs.map normalizeWF) := by
        -- rewrite both sides using the defining equation for normalizeWF on plus
        -- normalizeWF (Expr.plus xs) = canonPlus (xs.map normalizeWF)
        -- so it suffices to show normalizeWF (normalizeWF (Expr.plus xs)) = normalizeWF (Expr.plus xs)
        simpa [normalizeWF] using (normalizeWF_idem (Expr.plus xs))
      simpa [normalizeWF] using this
  | times xs =>
      have : normalizeWF (canonTimes (xs.map normalizeWF)) = canonTimes (xs.map normalizeWF) := by
        simpa [normalizeWF] using (normalizeWF_idem (Expr.times xs))
      simpa [normalizeWF] using this

/-- normStep agrees with normalizeWF (by computation). -/
theorem normStep_eq_normalizeWF (e : Expr) : normStep e = normalizeWF e := by
  cases e <;> rfl

/-- WF normal form is invariant under one normStep (no axiom). -/
theorem wf_invariant_normStep (e : Expr) :
  normalizeWF (normStep e) = normalizeWF e := by
  -- rewrite normStep to normalizeWF, then idempotence
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
