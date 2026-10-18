import RiemannLab.Tasks.LiFiniteSpectralIsolation
import RiemannLab.Tasks.CriticalStripFoundation
import RiemannLab.Tasks.OffCriticalQuartet

namespace RiemannLab

/-!
# Compactness of dominant expansive Li modes

An off-critical reflected zero produces a Li ratio of norm greater than one.
This file proves the quantitative fact needed by spectral isolation: for any
fixed threshold `R>1`, a mode with norm at least `R` must have bounded height.
Hence only a finite compact cluster can compete at that exponential scale.
-/

/-- Exact squared norm of the Li ratio in Cartesian coordinates. -/
theorem norm_one_sub_inv_sq_eq_cartesian
    {ρ : ℂ} (hρ0 : ρ ≠ 0) :
    ‖1 - ρ⁻¹‖ ^ 2 =
      ((ρ.re - 1) ^ 2 + ρ.im ^ 2) /
        (ρ.re ^ 2 + ρ.im ^ 2) := by
  have hratio : 1 - ρ⁻¹ = (ρ - 1) / ρ := by
    field_simp
  rw [hratio, norm_div, div_pow, Complex.sq_norm, Complex.sq_norm]
  simp [Complex.normSq_apply]
  ring

/-- Pure coordinate height bound.  Once the Li ratio is separated from the
unit circle by `R>1`, its ordinate is bounded by `1/sqrt(R²-1)`. -/
theorem expansive_coordinate_im_sq_le
    {β γ R : ℝ} (hden : 0 < β ^ 2 + γ ^ 2)
    (hβ : 0 ≤ β) (hR : 1 < R)
    (hlarge : R ^ 2 ≤ ((β - 1) ^ 2 + γ ^ 2) / (β ^ 2 + γ ^ 2)) :
    γ ^ 2 ≤ 1 / (R ^ 2 - 1) := by
  have hfac : 0 < R ^ 2 - 1 := by nlinarith
  have hcross : R ^ 2 * (β ^ 2 + γ ^ 2) ≤
      (β - 1) ^ 2 + γ ^ 2 := by
    exact (le_div_iff₀ hden).mp hlarge
  apply (le_div_iff₀ hfac).mpr
  nlinarith [sq_nonneg β]

/-- Coordinate-free form for an actual complex mode. -/
theorem expansive_liRatio_im_sq_le
    {ρ : ℂ} {R : ℝ} (hρ0 : ρ ≠ 0) (hre : 0 ≤ ρ.re)
    (hR : 1 < R) (hlarge : R ≤ ‖1 - ρ⁻¹‖) :
    ρ.im ^ 2 ≤ 1 / (R ^ 2 - 1) := by
  apply expansive_coordinate_im_sq_le
  · have hnormSq : 0 < Complex.normSq ρ := Complex.normSq_pos.mpr hρ0
    simpa [Complex.normSq_apply, pow_two] using hnormSq
  · exact hre
  · exact hR
  · rw [← norm_one_sub_inv_sq_eq_cartesian hρ0]
    exact (sq_le_sq₀ (by linarith) (norm_nonneg _)).mpr hlarge

/-- A nontrivial zeta zero whose Li ratio exceeds a fixed threshold lies in
an explicit closed ball. -/
theorem nontrivialZero_mem_expansive_closedBall
    {ρ : ℂ} {R : ℝ} (hρ : IsNontrivialZetaZero ρ)
    (hR : 1 < R) (hlarge : R ≤ ‖1 - ρ⁻¹‖) :
    ρ ∈ Metric.closedBall (0 : ℂ)
      (Real.sqrt (1 + 1 / (R ^ 2 - 1))) := by
  have hρ0 : ρ ≠ 0 := by
    intro hzero
    have hre := congrArg Complex.re hzero
    simp at hre
    linarith [hρ.re_pos]
  have him := expansive_liRatio_im_sq_le hρ0 hρ.re_pos.le hR hlarge
  have hreSq : ρ.re ^ 2 ≤ 1 := by
    nlinarith [hρ.re_pos, hρ.re_lt_one]
  have htotal : ρ.re ^ 2 + ρ.im ^ 2 ≤
      1 + 1 / (R ^ 2 - 1) := by linarith
  have hrhs : 0 ≤ 1 + 1 / (R ^ 2 - 1) := by
    have : 0 < R ^ 2 - 1 := by nlinarith
    positivity
  rw [Metric.mem_closedBall, dist_zero_right]
  apply (Real.le_sqrt (norm_nonneg ρ) hrhs).mpr
  rw [Complex.sq_norm]
  simpa [Complex.normSq_apply, pow_two] using htotal

/-- At every fixed expansive threshold, the set of competing nontrivial zeta
zeros is finite.  This is the compactness input required by the exact finite
annihilator. -/
theorem finite_nontrivialZeros_with_large_liRatio
    {R : ℝ} (hR : 1 < R) :
    {ρ : ℂ | IsNontrivialZetaZero ρ ∧ R ≤ ‖1 - ρ⁻¹‖}.Finite := by
  let K : Set ℂ := Metric.closedBall (0 : ℂ)
    (Real.sqrt (1 + 1 / (R ^ 2 - 1)))
  have hK : IsCompact K := isCompact_closedBall 0 _
  apply (compact_inter_zeta_zeros_finite hK).subset
  intro ρ hρ
  refine ⟨?_, ?_⟩
  · exact nontrivialZero_mem_expansive_closedBall hρ.1 hR hρ.2
  · exact hρ.1.1

/-- RH failure supplies an actual expansive target together with a strictly
smaller threshold above one whose complete competing zeta cluster is finite.
This closes the extremal-selection and finite-dominant-cluster step without
assuming that only one off-line quartet exists. -/
theorem not_riemannHypothesis_exists_expansive_target_finite_cluster
    (hRH : ¬RiemannHypothesis) :
    ∃ ρ : ℂ, ∃ R : ℝ,
      IsNontrivialZetaZero ρ ∧
      1 < R ∧
      R < ‖1 - ρ⁻¹‖ ∧
      {z : ℂ | IsNontrivialZetaZero z ∧ R ≤ ‖1 - z⁻¹‖}.Finite := by
  obtain ⟨ω, hω⟩ :=
    not_riemannHypothesis_iff_exists_right_offCriticalZero.mp hRH
  let ρ : ℂ := 1 - ω
  have hρ : IsNontrivialZetaZero ρ := hω.1.one_sub
  have hexp : 1 < ‖1 - ρ⁻¹‖ := by
    simpa [ρ] using hω.reflection_has_expansive_li_ratio
  let R : ℝ := (1 + ‖1 - ρ⁻¹‖) / 2
  have hR : 1 < R := by
    dsimp [R]
    linarith
  have hRtarget : R < ‖1 - ρ⁻¹‖ := by
    dsimp [R]
    linarith
  exact ⟨ρ, R, hρ, hR, hRtarget,
    finite_nontrivialZeros_with_large_liRatio hR⟩

end RiemannLab
