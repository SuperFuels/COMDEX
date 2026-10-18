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

/-- The Möbius ratio occurring in Li's coefficients is contractive exactly
to the right of the critical line. -/
theorem norm_one_sub_inv_lt_one_iff {ρ : ℂ} (hρ0 : ρ ≠ 0) :
    ‖1 - ρ⁻¹‖ < 1 ↔ 1 / 2 < ρ.re := by
  have hratio : 1 - ρ⁻¹ = (ρ - 1) / ρ := by
    field_simp
  rw [hratio, norm_div, div_lt_one (norm_pos_iff.mpr hρ0)]
  rw [← sq_lt_sq₀ (norm_nonneg (ρ - 1)) (norm_nonneg ρ),
    Complex.sq_norm, Complex.sq_norm]
  simp [Complex.normSq_apply]
  constructor <;> intro h <;> nlinarith

/-- Dually, the Li ratio is expansive exactly to the left of the critical
line.  This growing mode is what the numerical quartet detector measures. -/
theorem one_lt_norm_one_sub_inv_iff {ρ : ℂ} (hρ0 : ρ ≠ 0) :
    1 < ‖1 - ρ⁻¹‖ ↔ ρ.re < 1 / 2 := by
  have hratio : 1 - ρ⁻¹ = (ρ - 1) / ρ := by
    field_simp
  rw [hratio, norm_div, one_lt_div (norm_pos_iff.mpr hρ0)]
  rw [← sq_lt_sq₀ (norm_nonneg ρ) (norm_nonneg (ρ - 1)),
    Complex.sq_norm, Complex.sq_norm]
  simp [Complex.normSq_apply]
  constructor <;> intro h <;> nlinarith

/-- A right-hand counterexample therefore supplies an expansive Li mode at
its reflected zero. -/
theorem IsRightOffCriticalZero.reflection_has_expansive_li_ratio
    {ρ : ℂ} (hρ : IsRightOffCriticalZero ρ) :
    1 < ‖1 - (1 - ρ)⁻¹‖ := by
  apply (one_lt_norm_one_sub_inv_iff ?_).2
  · rw [one_sub_re]
    linarith [hρ.2]
  · intro hzero
    have hre := congrArg Complex.re hzero
    simp at hre
    linarith [hρ.1.re_lt_one]

end RiemannLab
