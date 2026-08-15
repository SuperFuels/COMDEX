import RiemannLab.Tasks.NontrivialZeros

namespace RiemannLab

/-!
# The counterexample normal form for the RH frontier programme

This file contains no assumption that RH is false.  It proves that if RH is
false, reflection supplies a nontrivial zero strictly to the right of the
critical line.  That is the canonical adversarial witness used by the
positivity experiments.
-/

/-- A nontrivial zero on the right-hand side of the critical strip. -/
def IsRightOffCriticalZero (ρ : ℂ) : Prop :=
  IsNontrivialZetaZero ρ ∧ 1 / 2 < ρ.re

/-- Reflection changes the real part from `β` to `1-β`. -/
theorem one_sub_re (ρ : ℂ) : (1 - ρ).re = 1 - ρ.re := by
  simp

/-- A zero off the critical line and not already on its right has a reflected
right-hand representative. -/
theorem IsNontrivialZetaZero.right_offCritical_of_re_ne_half
    {ρ : ℂ} (hρ : IsNontrivialZetaZero ρ) (hne : ρ.re ≠ 1 / 2) :
    ∃ ω : ℂ, IsRightOffCriticalZero ω := by
  by_cases hright : 1 / 2 < ρ.re
  · exact ⟨ρ, hρ, hright⟩
  · refine ⟨1 - ρ, hρ.one_sub, ?_⟩
    rw [one_sub_re]
    have hle : ρ.re ≤ 1 / 2 := le_of_not_gt hright
    have hlt : ρ.re < 1 / 2 := lt_of_le_of_ne hle hne
    linarith

/-- RH is false exactly when there is a nontrivial zero strictly to the right
of the critical line.  This turns an arbitrary counterexample into one
canonical search region. -/
theorem not_riemannHypothesis_iff_exists_right_offCriticalZero :
    ¬RiemannHypothesis ↔ ∃ ρ : ℂ, IsRightOffCriticalZero ρ := by
  constructor
  · intro hRH
    rw [riemannHypothesis_iff_nontrivial_zeros] at hRH
    push Not at hRH
    obtain ⟨ρ, hρ, hne⟩ := hRH
    exact hρ.right_offCritical_of_re_ne_half hne
  · rintro ⟨ρ, hρ, hright⟩ hRH
    have hline := (riemannHypothesis_iff_nontrivial_zeros.mp hRH) ρ hρ
    linarith

/-- A right-hand counterexample is distinct from its functional-equation
reflection. -/
theorem IsRightOffCriticalZero.ne_one_sub {ρ : ℂ}
    (hρ : IsRightOffCriticalZero ρ) : ρ ≠ 1 - ρ := by
  intro heq
  have hre := congrArg Complex.re heq
  simp at hre
  linarith [hρ.2]

/-- The complete verified symmetry orbit attached to a right-hand
counterexample. -/
theorem IsRightOffCriticalZero.symmetry_quartet {ρ : ℂ}
    (hρ : IsRightOffCriticalZero ρ) :
    IsNontrivialZetaZero ρ ∧
      IsNontrivialZetaZero (starRingEnd ℂ ρ) ∧
      IsNontrivialZetaZero (1 - ρ) ∧
      IsNontrivialZetaZero (1 - starRingEnd ℂ ρ) :=
  hρ.1.symmetry_orbit

end RiemannLab
