import PhotonAlgebra.Normalizer
import PhotonAlgebra.NormalizerWF
import PhotonAlgebra.Canon

namespace PhotonAlgebra
open PhotonAlgebra

theorem normStep_eq_normalizeWF (e : Expr) : normStep e = normalizeWF e := by
  cases e <;> rfl

/-- Idempotence of `normalizeWF`. -/
theorem normalizeWF_idem : ∀ e : Expr, normalizeWF (normalizeWF e) = normalizeWF e
  | Expr.atom s => by simp [normalizeWF]
  | Expr.empty  => by simp [normalizeWF]
  | Expr.plus xs => by
      -- normalizeWF (plus xs) = canonPlus (map normalizeWF xs)
      -- second pass = normalizeWF (canonPlus ...) which is exactly the goal of this case;
      -- unfold one layer of normalizeWF on the outer call and it becomes definitional.
      simp [normalizeWF]
  | Expr.times xs => by
      simp [normalizeWF]
  | Expr.entangle a b => by
      simp [normalizeWF, normalizeWF_idem a, normalizeWF_idem b]
  | Expr.neg e => by
      -- normalizeWF (neg e) is a match on normalizeWF e; second pass is fixed by IH on e
      -- plus the constructor-specific fixed lemma below (proved by rewriting via IH).
      have ih := normalizeWF_idem e
      -- reduce `normalizeWF (normalizeWF (neg e))` using definitional equation once
      simp [normalizeWF, ih]
  | Expr.cancel a b => by
      have ha := normalizeWF_idem a
      have hb := normalizeWF_idem b
      simp [normalizeWF, ha, hb]
  | Expr.project e => by
      have ih := normalizeWF_idem e
      simp [normalizeWF, ih]
  | Expr.collapse e => by
      have ih := normalizeWF_idem e
      simp [normalizeWF, ih]

/-
  Small “fixed-point” lemmas for the exact normal-form shapes that show up
  in your remaining failing goals.
-/

theorem normalizeWF_fixed_plus (xs : List Expr) :
  normalizeWF (canonPlus (xs.map normalizeWF)) = canonPlus (xs.map normalizeWF) := by
  -- This is exactly idempotence applied to (Expr.plus xs).
  simpa [normalizeWF] using (normalizeWF_idem (Expr.plus xs))

theorem normalizeWF_fixed_times (xs : List Expr) :
  normalizeWF (canonTimes (xs.map normalizeWF)) = canonTimes (xs.map normalizeWF) := by
  simpa [normalizeWF] using (normalizeWF_idem (Expr.times xs))

theorem normalizeWF_fixed_neg (e : Expr) :
  normalizeWF
      (match normalizeWF e with
      | x.neg => x
      | x => (normalizeWF e).neg) =
    (match normalizeWF e with
      | x.neg => x
      | x => (normalizeWF e).neg) := by
  -- This term is *definitionally* `normalizeWF (Expr.neg e)`.
  simpa [normalizeWF] using (normalizeWF_idem (Expr.neg e))

theorem normalizeWF_fixed_cancel (a b : Expr) :
  normalizeWF
      (if (normalizeWF a == normalizeWF b) = true then Expr.empty
      else
        if (normalizeWF b == Expr.empty) = true then normalizeWF a
        else if (normalizeWF a == Expr.empty) = true then normalizeWF b
        else (normalizeWF a).cancel (normalizeWF b)) =
    (if (normalizeWF a == normalizeWF b) = true then Expr.empty
    else
      if (normalizeWF b == Expr.empty) = true then normalizeWF a
      else if (normalizeWF a == Expr.empty) = true then normalizeWF b
      else (normalizeWF a).cancel (normalizeWF b) ) := by
  simpa [normalizeWF] using (normalizeWF_idem (Expr.cancel a b))

theorem normalizeWF_fixed_project (e : Expr) :
  normalizeWF
      (match normalizeWF e with
      | a.entangle b => canonPlus [a.project, b.project]
      | x => (normalizeWF e).project) =
    (match normalizeWF e with
    | a.entangle b => canonPlus [a.project, b.project]
    | x => (normalizeWF e).project) := by
  simpa [normalizeWF] using (normalizeWF_idem (Expr.project e))

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

theorem normalize_bridge (e : Expr) :
    normalizeWF (normalize e) = normalizeWF e := by
  simpa [normalize] using
    wf_invariant_normalizeFuel (e.size * e.size + 50) e

end PhotonAlgebra
