import RiemannLab.Tasks.QuantitativeJensen

namespace RiemannLab

open Complex Set Filter Topology

/-! Boundary data for extending the sharp xi estimate far enough to contain
the complete radius-four Jensen circle centred at `2+iT`. -/

noncomputable def extendedWeightedXi (s : ℂ) : ℂ :=
  Complex.exp ((-I * (Real.pi : ℂ) / 4) * s) *
    (riemannXiEntire s / (s + 4) ^ 6)

theorem norm_extendedWeightedXi_six_sq {t : ℝ} (ht : 0 < t) :
    ‖extendedWeightedXi (6 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2 =
      Real.exp (Real.pi * t) *
        ((36 + 4 * t ^ 2) * (25 + 4 * t ^ 2) *
          ((Real.pi ^ (-3 : ℝ)) ^ 2 *
            ((4 + t ^ 2) * (1 + t ^ 2) *
              (Real.pi * t / Real.sinh (Real.pi * t)))) *
          ‖riemannZeta (6 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2) /
        (100 + 4 * t ^ 2) ^ 6 := by
  let s : ℂ := 6 + ((2 * t : ℝ) : ℂ) * I
  have hsre : s.re = 6 := by simp [s]
  have hsim : s.im = 2 * t := by simp [s]
  have hs0 : s ≠ 0 := ne_zero_of_re_pos (by rw [hsre]; norm_num)
  have hs1 : s ≠ 1 := by
    intro h
    have := congrArg Complex.re h
    rw [hsre] at this
    norm_num at this
  have hexp : Real.exp (Real.pi * (2 * t) / 4) ^ 2 =
      Real.exp (Real.pi * t) := by
    rw [← Real.exp_nat_mul]
    congr 1
    norm_num
    ring
  have hnorms : ‖s‖ ^ 2 = 36 + 4 * t ^ 2 := by
    rw [Complex.sq_norm]
    simp [s, Complex.normSq_apply]
    ring
  have hnorms1 : ‖s - 1‖ ^ 2 = 25 + 4 * t ^ 2 := by
    rw [Complex.sq_norm]
    simp [s, Complex.normSq_apply]
    ring
  have hnorms4 : ‖s + 4‖ ^ 2 = 100 + 4 * t ^ 2 := by
    rw [Complex.sq_norm]
    simp [s, Complex.normSq_apply]
    ring
  have hden : (‖s + 4‖ ^ 6) ^ 2 = (100 + 4 * t ^ 2) ^ 6 := by
    calc
      (‖s + 4‖ ^ 6) ^ 2 = (‖s + 4‖ ^ 2) ^ 6 := by ring
      _ = (100 + 4 * t ^ 2) ^ 6 := by rw [hnorms4]
  have hgamma := norm_GammaR_six_add_two_mul_I_sq ht
  change ‖Gammaℝ s‖ ^ 2 = _ at hgamma
  unfold extendedWeightedXi
  rw [norm_mul, norm_div, norm_pow, mul_pow, div_pow, norm_upperWeight]
  rw [riemannXiEntire_eq_mul_GammaR_riemannZeta hs0 hs1
    (by rw [hsre]; norm_num)]
  simp only [norm_mul, mul_pow]
  rw [hsim, hexp, hnorms, hnorms1, hden, hgamma]
  ring

/-- Height-independent squared-norm bound on the positive high part of the
actual Jensen right boundary. -/
theorem norm_extendedWeightedXi_six_sq_le {t : ℝ} (ht : 1 ≤ t) :
    ‖extendedWeightedXi (6 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2 ≤
      46400 * (Real.pi ^ (-3 : ℝ)) ^ 2 * Real.pi *
        riemannZetaFourMajorant ^ 2 := by
  rw [norm_extendedWeightedXi_six_sq (zero_lt_one.trans_le ht)]
  have hsinh : Real.exp (Real.pi * t) / 4 ≤
      Real.sinh (Real.pi * t) := by
    apply exp_div_four_le_sinh
    nlinarith [Real.two_le_pi]
  have hsinhpos : 0 < Real.sinh (Real.pi * t) := by positivity
  have hcancel : Real.exp (Real.pi * t) *
      (Real.pi * t / Real.sinh (Real.pi * t)) ≤ 4 * Real.pi * t := by
    have hratio : Real.exp (Real.pi * t) /
        Real.sinh (Real.pi * t) ≤ 4 := by
      apply (div_le_iff₀ hsinhpos).2
      linarith
    calc
      Real.exp (Real.pi * t) *
          (Real.pi * t / Real.sinh (Real.pi * t)) =
          (Real.pi * t) *
            (Real.exp (Real.pi * t) / Real.sinh (Real.pi * t)) := by ring
      _ ≤ (Real.pi * t) * 4 := by gcongr
      _ = 4 * Real.pi * t := by ring
  have hzeta := norm_riemannZeta_le_fourMajorant
    (s := 6 + ((2 * t : ℝ) : ℂ) * I) (by norm_num)
  have hzetaSq : ‖riemannZeta
      (6 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2 ≤
      riemannZetaFourMajorant ^ 2 := by
    nlinarith [norm_nonneg (riemannZeta
      (6 + ((2 * t : ℝ) : ℂ) * I)), riemannZetaFourMajorant_nonneg]
  have h36 : 36 + 4 * t ^ 2 ≤ 40 * t ^ 2 := by nlinarith [sq_nonneg t]
  have h25 : 25 + 4 * t ^ 2 ≤ 29 * t ^ 2 := by nlinarith [sq_nonneg t]
  have h4 : 4 + t ^ 2 ≤ 5 * t ^ 2 := by nlinarith [sq_nonneg t]
  have h1 : 1 + t ^ 2 ≤ 2 * t ^ 2 := by nlinarith [sq_nonneg t]
  have hdenpos : 0 < (100 + 4 * t ^ 2) ^ 6 := by positivity
  have hden : t ^ 12 ≤ (100 + 4 * t ^ 2) ^ 6 := by
    have ht2 : t ^ 2 ≤ 100 + 4 * t ^ 2 := by nlinarith [sq_nonneg t]
    calc
      t ^ 12 = (t ^ 2) ^ 6 := by ring
      _ ≤ (100 + 4 * t ^ 2) ^ 6 := by gcongr
  have ht9 : t ^ 9 ≤ t ^ 12 := by
    have ht0 : 0 ≤ t := le_trans zero_le_one ht
    have ht3 : 1 ≤ t ^ 3 := by
      nlinarith [sq_nonneg t, mul_nonneg (sq_nonneg t) ht0]
    calc
      t ^ 9 = t ^ 9 * 1 := by ring
      _ ≤ t ^ 9 * t ^ 3 := by
        exact mul_le_mul_of_nonneg_left ht3 (by positivity)
      _ = t ^ 12 := by ring
  apply (div_le_iff₀ hdenpos).2
  calc
    Real.exp (Real.pi * t) *
        ((36 + 4 * t ^ 2) * (25 + 4 * t ^ 2) *
          ((Real.pi ^ (-3 : ℝ)) ^ 2 *
            ((4 + t ^ 2) * (1 + t ^ 2) *
              (Real.pi * t / Real.sinh (Real.pi * t)))) *
          ‖riemannZeta (6 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2) ≤
      (40 * t ^ 2) * (29 * t ^ 2) *
        (Real.pi ^ (-3 : ℝ)) ^ 2 * (5 * t ^ 2) * (2 * t ^ 2) *
        (4 * Real.pi * t) * riemannZetaFourMajorant ^ 2 := by
      calc
        _ = (36 + 4 * t ^ 2) * (25 + 4 * t ^ 2) *
            (Real.pi ^ (-3 : ℝ)) ^ 2 * (4 + t ^ 2) * (1 + t ^ 2) *
            (Real.exp (Real.pi * t) *
              (Real.pi * t / Real.sinh (Real.pi * t))) *
            ‖riemannZeta (6 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2 := by ring
        _ ≤ _ := by gcongr
    _ = 46400 * (Real.pi ^ (-3 : ℝ)) ^ 2 * Real.pi *
        riemannZetaFourMajorant ^ 2 * t ^ 9 := by ring
    _ ≤ 46400 * (Real.pi ^ (-3 : ℝ)) ^ 2 * Real.pi *
        riemannZetaFourMajorant ^ 2 * t ^ 12 := by gcongr
    _ ≤ (46400 * (Real.pi ^ (-3 : ℝ)) ^ 2 * Real.pi *
        riemannZetaFourMajorant ^ 2) * (100 + 4 * t ^ 2) ^ 6 := by gcongr

end RiemannLab
