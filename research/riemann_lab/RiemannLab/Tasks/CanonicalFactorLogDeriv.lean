import RiemannLab.Tasks.LocalXiCanonicalDecomp

namespace RiemannLab

open Complex ComplexConjugate Set MeromorphicOn

/-! Quantitative denominator bounds for the finite canonical factors in the
translated xi decomposition. -/

/-- The reflected numerator of a radius-`R` canonical factor stays uniformly
away from zero on every smaller radius-`r` disk. -/
theorem canonicalFactor_reflected_denom_norm_lower
    {R r : ℝ} {w z : ℂ} (hR : 0 < R) (hr : 0 ≤ r) (hrR : r < R)
    (hw : w ∈ Metric.ball (0 : ℂ) R)
    (hz : z ∈ Metric.closedBall (0 : ℂ) r) :
    R * (R - r) ≤ ‖(R : ℂ) ^ 2 - conj w * z‖ := by
  have hwR : ‖w‖ ≤ R := (by
    have := (show ‖w‖ < R by simpa [Metric.mem_ball] using hw)
    exact this.le)
  have hzr : ‖z‖ ≤ r := by simpa [Metric.mem_closedBall] using hz
  have hmul : ‖conj w * z‖ ≤ R * r := by
    rw [norm_mul, norm_conj]
    exact mul_le_mul hwR hzr (norm_nonneg _) hR.le
  have hrev := norm_sub_norm_le ((R : ℂ) ^ 2) (conj w * z)
  have hRnorm : ‖((R : ℂ) ^ 2)‖ = R ^ 2 := by
    rw [norm_pow, norm_real, Real.norm_eq_abs, abs_of_pos hR]
  rw [hRnorm] at hrev
  calc
    R * (R - r) = R ^ 2 - R * r := by ring
    _ ≤ R ^ 2 - ‖conj w * z‖ := sub_le_sub_left hmul _
    _ ≤ ‖(R : ℂ) ^ 2 - conj w * z‖ := by linarith

theorem canonicalFactor_seven_halves_reflected_denom_norm_ge
    {w z : ℂ} (hw : w ∈ Metric.ball (0 : ℂ) (7 / 2 : ℝ))
    (hz : z ∈ Metric.closedBall (0 : ℂ) (13 / 4 : ℝ)) :
    7 / 8 ≤ ‖((7 / 2 : ℝ) : ℂ) ^ 2 - conj w * z‖ := by
  have h := canonicalFactor_reflected_denom_norm_lower
    (R := (7 / 2 : ℝ)) (r := (13 / 4 : ℝ)) (w := w) (z := z)
    (by norm_num) (by norm_num) (by norm_num) hw hz
  norm_num at h ⊢
  exact h

theorem canonicalFactor_seven_halves_reflected_denom_ne_zero
    {w z : ℂ} (hw : w ∈ Metric.ball (0 : ℂ) (7 / 2 : ℝ))
    (hz : z ∈ Metric.closedBall (0 : ℂ) (13 / 4 : ℝ)) :
    ((7 / 2 : ℝ) : ℂ) ^ 2 - conj w * z ≠ 0 := by
  intro hzero
  have h := canonicalFactor_seven_halves_reflected_denom_norm_ge hw hz
  rw [hzero, norm_zero] at h
  norm_num at h

/-- Exact logarithmic derivative of one radius-seven-halves canonical factor,
away from its zero. -/
theorem logDeriv_canonicalFactor_seven_halves
    {w z : ℂ} (hw : w ∈ Metric.ball (0 : ℂ) (7 / 2 : ℝ))
    (hz : z ∈ Metric.closedBall (0 : ℂ) (13 / 4 : ℝ))
    (hzw : z ≠ w) :
    logDeriv (canonicalFactor (7 / 2 : ℝ) w) z =
      -(conj w) / (((7 / 2 : ℝ) : ℂ) ^ 2 - conj w * z) - 1 / (z - w) := by
  rw [canonicalFactor_def]
  have hnum : ((7 / 2 : ℝ) : ℂ) ^ 2 - conj w * z ≠ 0 :=
    canonicalFactor_seven_halves_reflected_denom_ne_zero hw hz
  have hden : ((7 / 2 : ℝ) : ℂ) * (z - w) ≠ 0 :=
    mul_ne_zero (by norm_num) (sub_ne_zero.mpr hzw)
  have hdnum : DifferentiableAt ℂ
      (fun z : ℂ => ((7 / 2 : ℝ) : ℂ) ^ 2 - conj w * z) z :=
    DifferentiableAt.const_sub (differentiableAt_id.const_mul (conj w)) _
  have hdden : DifferentiableAt ℂ
      (fun z : ℂ => ((7 / 2 : ℝ) : ℂ) * (z - w)) z :=
    (differentiableAt_id.sub_const w).const_mul _
  rw [logDeriv_div z hnum hden hdnum hdden]
  simp only [logDeriv_apply]
  have hR : ((7 / 2 : ℝ) : ℂ) ≠ 0 := by norm_num
  have hdnum' : HasDerivAt
      (fun z : ℂ => ((7 / 2 : ℝ) : ℂ) ^ 2 - conj w * z) (-(conj w)) z := by
    simpa only [id_eq, mul_one] using
      ((hasDerivAt_id z).const_mul (conj w)).const_sub
        (((7 / 2 : ℝ) : ℂ) ^ 2)
  have hdden' : HasDerivAt
      (fun z : ℂ => ((7 / 2 : ℝ) : ℂ) * (z - w)) ((7 / 2 : ℝ) : ℂ) z := by
    simpa only [id_eq, mul_one] using
      ((hasDerivAt_id z).sub_const w).const_mul (((7 / 2 : ℝ) : ℂ))
  rw [hdnum'.deriv, hdden'.deriv]
  field_simp

theorem norm_canonicalFactor_reflected_term_le_four
    {w z : ℂ} (hw : w ∈ Metric.ball (0 : ℂ) (7 / 2 : ℝ))
    (hz : z ∈ Metric.closedBall (0 : ℂ) (13 / 4 : ℝ)) :
    ‖conj w / (((7 / 2 : ℝ) : ℂ) ^ 2 - conj w * z)‖ ≤ 4 := by
  have hwR : ‖w‖ ≤ 7 / 2 := by
    exact (show ‖w‖ < 7 / 2 by simpa [Metric.mem_ball] using hw).le
  have hden := canonicalFactor_seven_halves_reflected_denom_norm_ge hw hz
  have hdenpos : 0 < ‖((7 / 2 : ℝ) : ℂ) ^ 2 - conj w * z‖ := by linarith
  rw [norm_div, norm_conj]
  exact (div_le_iff₀ hdenpos).2 (by nlinarith)

/-- Separation of ordinates supplies the singular reciprocal bound needed
for every local zero factor. -/
theorem norm_inv_sub_le_of_im_separation
    {z w : ℂ} {δ : ℝ} (hδ : 0 < δ) (hsep : δ ≤ |z.im - w.im|) :
    ‖(z - w)⁻¹‖ ≤ 1 / δ := by
  have hdist : δ ≤ ‖z - w‖ := by
    exact hsep.trans (by
      simpa using Complex.abs_im_le_norm (z - w))
  have hnormpos : 0 < ‖z - w‖ := lt_of_lt_of_le hδ hdist
  rw [norm_inv]
  simpa [one_div] using one_div_le_one_div_of_le hδ hdist

theorem norm_canonicalFactor_log_kernel_le
    {w z : ℂ} {δ : ℝ} (hδ : 0 < δ)
    (hw : w ∈ Metric.ball (0 : ℂ) (7 / 2 : ℝ))
    (hz : z ∈ Metric.closedBall (0 : ℂ) (13 / 4 : ℝ))
    (hsep : δ ≤ |z.im - w.im|) :
    ‖-(conj w) / (((7 / 2 : ℝ) : ℂ) ^ 2 - conj w * z) - 1 / (z - w)‖ ≤
      4 + 1 / δ := by
  have href := norm_canonicalFactor_reflected_term_le_four hw hz
  have hsing := norm_inv_sub_le_of_im_separation hδ hsep
  calc
    ‖-(conj w) / (((7 / 2 : ℝ) : ℂ) ^ 2 - conj w * z) - 1 / (z - w)‖ ≤
        ‖-(conj w) / (((7 / 2 : ℝ) : ℂ) ^ 2 - conj w * z)‖ + ‖1 / (z - w)‖ :=
      norm_sub_le _ _
    _ = ‖conj w / (((7 / 2 : ℝ) : ℂ) ^ 2 - conj w * z)‖ + ‖(z - w)⁻¹‖ := by
      simp only [norm_div, norm_neg, norm_one, one_div]
    _ ≤ 4 + 1 / δ := add_le_add href hsing

end RiemannLab
