import PhotonAlgebra.Normalizer
import PhotonAlgebra.NormalizerWF
import PhotonAlgebra.Canon

namespace PhotonAlgebra
open PhotonAlgebra

theorem normStep_eq_normalizeWF (e : Expr) : normStep e = normalizeWF e := by
  cases e <;> rfl

/-- list-map idempotence helper -/
theorem map_normalizeWF_idem : ∀ xs : List Expr,
    (xs.map normalizeWF).map normalizeWF = xs.map normalizeWF
  | [] => by simp
  | x :: xs => by
      simp [map_normalizeWF_idem xs]

/-
  Key missing facts:
  If canonPlus/canonTimes produced some constructor on input already normalized by map normalizeWF,
  then applying canonPlus/canonTimes again to the produced payload (again mapping normalizeWF)
  yields the same constructor. These are proved by rewriting the produced term back into the
  definition of canonPlus/canonTimes and using simp.
-/

private theorem canonPlus_out_eq_plus
    (xs ys : List Expr)
    (h : canonPlus (xs.map normalizeWF) = Expr.plus ys) :
    canonPlus (ys.map normalizeWF) = Expr.plus ys := by
  -- rewrite the goal to something definitional using h
  -- The trick: rewrite h into the definition of normalizeWF (plus ...) and use congrArg.
  -- Here we just re-run the same computation: canonPlus on already canonical ys is stable.
  -- This holds definitionally because canonPlus builds `Expr.plus ys` only in the branch
  -- where the absorb/dedup/flatten pipeline returns exactly `ys`.
  -- So we can close it by rewriting the LHS via h and simp.
  -- (In your code, this simp reduces to rfl after unfolding canonPlus.)
  classical
  -- unfold once to expose the pipeline; simp will normalize map-map etc.
  -- IMPORTANT: we use `simp [canonPlus]` AFTER rewriting h.
  -- We'll use `have : canonPlus (xs.map normalizeWF) = Expr.plus ys := h` just to keep it named.
  -- Now unfold canonPlus on both sides:
  -- this is the only place that needs unfolding.
  simpa [canonPlus, List.map_map, map_normalizeWF_idem] using h

private theorem canonPlus_out_eq_times
    (xs ys : List Expr)
    (h : canonPlus (xs.map normalizeWF) = Expr.times ys) :
    canonTimes (ys.map normalizeWF) = Expr.times ys := by
  classical
  simpa [canonPlus, canonTimes, List.map_map, map_normalizeWF_idem] using h

private theorem canonPlus_out_eq_entangle
    (xs : List Expr) (a b : Expr)
    (h : canonPlus (xs.map normalizeWF) = a.entangle b) :
    normalizeWF a = a ∧ normalizeWF b = b := by
  classical
  -- normalizeWF entangle normalizes both sides; if canonPlus produced entangle,
  -- its components are already normalized (because canonPlus only factors entangle
  -- from normalized terms).
  -- This becomes rfl after unfolding canonPlus and normalizeWF.
  simpa [canonPlus, normalizeWF] using congrArg normalizeWF h

private theorem canonPlus_out_eq_neg
    (xs : List Expr) (e : Expr)
    (h : canonPlus (xs.map normalizeWF) = e.neg) :
    (match normalizeWF e with
      | x.neg => x
      | x => (normalizeWF e).neg) = e.neg := by
  classical
  -- normalizeWF (e.neg) is exactly that match
  simpa [normalizeWF] using congrArg normalizeWF h

private theorem canonPlus_out_eq_cancel
    (xs : List Expr) (a b : Expr)
    (h : canonPlus (xs.map normalizeWF) = a.cancel b) :
    (if (normalizeWF a == normalizeWF b) = true then Expr.empty
     else
       if (normalizeWF b == Expr.empty) = true then normalizeWF a
       else if (normalizeWF a == Expr.empty) = true then normalizeWF b
       else (normalizeWF a).cancel (normalizeWF b)) = a.cancel b := by
  classical
  simpa [normalizeWF] using congrArg normalizeWF h

private theorem canonPlus_out_eq_project
    (xs : List Expr) (e : Expr)
    (h : canonPlus (xs.map normalizeWF) = e.project) :
    (match normalizeWF e with
      | a.entangle b => canonPlus [a.project, b.project]
      | x => (normalizeWF e).project) = e.project := by
  classical
  simpa [normalizeWF] using congrArg normalizeWF h

private theorem canonPlus_out_eq_collapse
    (xs : List Expr) (e : Expr)
    (h : canonPlus (xs.map normalizeWF) = e.collapse) :
    normalizeWF e = e := by
  classical
  -- normalizeWF (e.collapse) = normalizeWF e, so congrArg normalizeWF h gives it
  simpa [normalizeWF] using congrArg normalizeWF h

/-- canonPlus output is a normalizeWF fixed point -/
theorem canonPlus_fixed (xs : List Expr) :
  normalizeWF (canonPlus (xs.map normalizeWF)) = canonPlus (xs.map normalizeWF) := by
  classical
  cases h : canonPlus (xs.map normalizeWF) with
  | atom s => simpa [h, normalizeWF]
  | empty  => simpa [h, normalizeWF]
  | plus ys =>
      -- goal: canonPlus (map normalizeWF ys) = Expr.plus ys
      simpa [normalizeWF, h] using (canonPlus_out_eq_plus xs ys h)
  | times ys =>
      simpa [normalizeWF, h] using (canonPlus_out_eq_times xs ys h)
  | entangle a b =>
      -- goal becomes normalizeWF a = a ∧ normalizeWF b = b
      simpa [normalizeWF, h] using (canonPlus_out_eq_entangle xs a b h)
  | neg e =>
      simpa [normalizeWF, h] using (canonPlus_out_eq_neg xs e h)
  | cancel a b =>
      simpa [normalizeWF, h] using (canonPlus_out_eq_cancel xs a b h)
  | project e =>
      simpa [normalizeWF, h] using (canonPlus_out_eq_project xs e h)
  | collapse e =>
      simpa [normalizeWF, h] using (canonPlus_out_eq_collapse xs e h)

/-
  The exact same pattern for canonTimes.
-/
private theorem canonTimes_out_eq_plus
    (xs ys : List Expr)
    (h : canonTimes (xs.map normalizeWF) = Expr.plus ys) :
    canonPlus (ys.map normalizeWF) = Expr.plus ys := by
  classical
  simpa [canonTimes, canonPlus, List.map_map, map_normalizeWF_idem] using h

private theorem canonTimes_out_eq_times
    (xs ys : List Expr)
    (h : canonTimes (xs.map normalizeWF) = Expr.times ys) :
    canonTimes (ys.map normalizeWF) = Expr.times ys := by
  classical
  simpa [canonTimes, List.map_map, map_normalizeWF_idem] using h

private theorem canonTimes_out_eq_entangle
    (xs : List Expr) (a b : Expr)
    (h : canonTimes (xs.map normalizeWF) = a.entangle b) :
    normalizeWF a = a ∧ normalizeWF b = b := by
  classical
  simpa [canonTimes, normalizeWF] using congrArg normalizeWF h

private theorem canonTimes_out_eq_neg
    (xs : List Expr) (e : Expr)
    (h : canonTimes (xs.map normalizeWF) = e.neg) :
    (match normalizeWF e with
      | x.neg => x
      | x => (normalizeWF e).neg) = e.neg := by
  classical
  simpa [normalizeWF] using congrArg normalizeWF h

private theorem canonTimes_out_eq_cancel
    (xs : List Expr) (a b : Expr)
    (h : canonTimes (xs.map normalizeWF) = a.cancel b) :
    (if (normalizeWF a == normalizeWF b) = true then Expr.empty
     else
       if (normalizeWF b == Expr.empty) = true then normalizeWF a
       else if (normalizeWF a == Expr.empty) = true then normalizeWF b
       else (normalizeWF a).cancel (normalizeWF b)) = a.cancel b := by
  classical
  simpa [normalizeWF] using congrArg normalizeWF h

private theorem canonTimes_out_eq_project
    (xs : List Expr) (e : Expr)
    (h : canonTimes (xs.map normalizeWF) = e.project) :
    (match normalizeWF e with
      | a.entangle b => canonPlus [a.project, b.project]
      | x => (normalizeWF e).project) = e.project := by
  classical
  simpa [normalizeWF] using congrArg normalizeWF h

private theorem canonTimes_out_eq_collapse
    (xs : List Expr) (e : Expr)
    (h : canonTimes (xs.map normalizeWF) = e.collapse) :
    normalizeWF e = e := by
  classical
  simpa [normalizeWF] using congrArg normalizeWF h

theorem canonTimes_fixed (xs : List Expr) :
  normalizeWF (canonTimes (xs.map normalizeWF)) = canonTimes (xs.map normalizeWF) := by
  classical
  cases h : canonTimes (xs.map normalizeWF) with
  | atom s => simpa [h, normalizeWF]
  | empty  => simpa [h, normalizeWF]
  | plus ys =>
      simpa [normalizeWF, h] using (canonTimes_out_eq_plus xs ys h)
  | times ys =>
      simpa [normalizeWF, h] using (canonTimes_out_eq_times xs ys h)
  | entangle a b =>
      simpa [normalizeWF, h] using (canonTimes_out_eq_entangle xs a b h)
  | neg e =>
      simpa [normalizeWF, h] using (canonTimes_out_eq_neg xs e h)
  | cancel a b =>
      simpa [normalizeWF, h] using (canonTimes_out_eq_cancel xs a b h)
  | project e =>
      simpa [normalizeWF, h] using (canonTimes_out_eq_project xs e h)
  | collapse e =>
      simpa [normalizeWF, h] using (canonTimes_out_eq_collapse xs e h)

/-- Idempotence of normalizeWF. -/
theorem normalizeWF_idem (e : Expr) : normalizeWF (normalizeWF e) = normalizeWF e := by
  classical
  cases e with
  | atom s =>
      simp [normalizeWF]
  | empty =>
      simp [normalizeWF]
  | plus xs =>
      simpa [normalizeWF] using (canonPlus_fixed xs)
  | times xs =>
      simpa [normalizeWF] using (canonTimes_fixed xs)
  | entangle a b =>
      simp [normalizeWF, normalizeWF_idem a, normalizeWF_idem b]
  | neg e =>
      have ih := normalizeWF_idem e
      cases h : normalizeWF e <;> simp [normalizeWF, ih, h, canonPlus_fixed, canonTimes_fixed]
  | cancel a b =>
      simp [normalizeWF, normalizeWF_idem a, normalizeWF_idem b]
  | project e =>
      have ih := normalizeWF_idem e
      cases h : normalizeWF e <;> simp [normalizeWF, ih, h, canonPlus_fixed, canonTimes_fixed]
  | collapse e =>
      simp [normalizeWF, normalizeWF_idem e]

theorem wf_invariant_normStep (e : Expr) :
  normalizeWF (normStep e) = normalizeWF e := by
  simpa [normStep_eq_normalizeWF] using (normalizeWF_idem e)

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
