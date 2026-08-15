import RiemannLab.Tasks.NormalizedXiThreeLines
import Mathlib.NumberTheory.ZetaValues

namespace RiemannLab

open Complex Set Filter Topology ArithmeticFunction
open scoped LSeries.notation Moebius

/-!
Quantitative centre estimates for the local Jensen argument.  The key point
is that the moving centre `2+iT` admits a uniform zeta lower bound: the
Möbius L-series is the reciprocal of zeta and is dominated by `ζ(2)`.
-/

/-- The Möbius L-series on `Re(s)=2` is bounded by the classical value
`ζ(2)=π²/6`. -/
theorem norm_LSeries_moebius_le_pi_sq_div_six
    {s : ℂ} (hs : s.re = 2) :
    ‖L (fun n : ℕ ↦ (μ n : ℂ)) s‖ ≤ Real.pi ^ 2 / 6 := by
  unfold LSeries
  have hsum : Summable (fun n : ℕ ↦
      ‖LSeries.term (fun n : ℕ ↦ (μ n : ℂ)) s n‖) := by
    exact (LSeriesSummable_moebius_iff.mpr (by rw [hs]; norm_num)).norm
  refine (norm_tsum_le_tsum_norm hsum).trans ?_
  have hmajor : ∀ n : ℕ,
      ‖LSeries.term (fun n : ℕ ↦ (μ n : ℂ)) s n‖ ≤
        (1 : ℝ) / (n : ℝ) ^ 2 := by
    intro n
    rw [LSeries.norm_term_eq, hs]
    split_ifs with hn
    · subst n
      norm_num
    · have hμ : ‖(μ n : ℂ)‖ ≤ 1 := by
        rw [norm_intCast]
        exact_mod_cast abs_moebius_le_one (n := n)
      have hpow : (n : ℝ) ^ (2 : ℝ) = (n : ℝ) ^ (2 : ℕ) :=
        Real.rpow_natCast _ _
      rw [hpow]
      exact div_le_div_of_nonneg_right hμ (sq_nonneg (n : ℝ))
  exact (hsum.tsum_mono hasSum_zeta_two.summable hmajor).trans_eq
    hasSum_zeta_two.tsum_eq

/-- Uniform reciprocal-Euler-product lower bound for zeta on `Re(s)=2`. -/
theorem pi_sq_div_six_mul_norm_riemannZeta_ge_one
    {s : ℂ} (hs : s.re = 2) :
    1 ≤ (Real.pi ^ 2 / 6) * ‖riemannZeta s‖ := by
  have hre : 1 < s.re := by rw [hs]; norm_num
  have hinv := LSeries_one_mul_Lseries_moebius hre
  rw [LSeries_one_eq_riemannZeta hre] at hinv
  have hnorm : ‖riemannZeta s‖ *
      ‖L (fun n : ℕ ↦ (μ n : ℂ)) s‖ = 1 := by
    simpa [norm_mul] using congrArg norm hinv
  calc
    1 = ‖riemannZeta s‖ *
        ‖L (fun n : ℕ ↦ (μ n : ℂ)) s‖ := hnorm.symm
    _ ≤ ‖riemannZeta s‖ * (Real.pi ^ 2 / 6) := by
      gcongr
      exact norm_LSeries_moebius_le_pi_sq_div_six hs
    _ = (Real.pi ^ 2 / 6) * ‖riemannZeta s‖ := mul_comm _ _

/-- Exact Gamma-factor norm at the moving Jensen centre `2+2it`. -/
theorem norm_GammaR_two_add_two_mul_I_sq
    {t : ℝ} (ht : 0 < t) :
    ‖Gammaℝ (2 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2 =
      (Real.pi ^ (-1 : ℝ)) ^ 2 *
        (Real.pi * t / Real.sinh (Real.pi * t)) := by
  rw [Gammaℝ_def, norm_mul, mul_pow]
  rw [Complex.norm_cpow_eq_rpow_re_of_pos Real.pi_pos]
  have hre : (-(2 + ((2 * t : ℝ) : ℂ) * I) / 2).re = -1 := by
    norm_num
  rw [hre]
  have harg : (2 + ((2 * t : ℝ) : ℂ) * I) / 2 =
      1 + (t : ℂ) * I := by
    apply Complex.ext <;> simp <;> ring
  rw [harg, norm_Gamma_one_add_mul_I_sq ht]

theorem sinh_le_exp_div_two (x : ℝ) :
    Real.sinh x ≤ Real.exp x / 2 := by
  rw [Real.sinh_eq]
  linarith [Real.exp_pos (-x)]

/-- A matching exponential lower bound at the Jensen centre.  Together with
the strip upper bound, this is what cancels the archimedean exponential in
the Jensen quotient. -/
theorem GammaR_jensenCenter_sq_lower
    {t : ℝ} (ht : 0 < t) :
    (Real.pi ^ (-1 : ℝ)) ^ 2 *
        (Real.pi * t / (Real.exp (Real.pi * t) / 2)) ≤
      ‖Gammaℝ (2 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2 := by
  rw [norm_GammaR_two_add_two_mul_I_sq ht]
  apply mul_le_mul_of_nonneg_left
  · apply div_le_div_of_nonneg_left
    · exact mul_nonneg Real.pi_pos.le ht.le
    · exact Real.sinh_pos_iff.mpr (mul_pos Real.pi_pos ht)
    · exact sinh_le_exp_div_two _
  · exact sq_nonneg _

/-- One further Gamma recurrence, needed on the widened right boundary
`Re(s)=6` containing the complete Jensen circle. -/
theorem norm_Gamma_three_add_mul_I_sq
    {t : ℝ} (ht : 0 < t) :
    ‖Complex.Gamma (3 + (t : ℂ) * I)‖ ^ 2 =
      (4 + t ^ 2) * (1 + t ^ 2) *
        (Real.pi * t / Real.sinh (Real.pi * t)) := by
  have hs : (2 : ℂ) + (t : ℂ) * I ≠ 0 := by
    intro h
    have := congrArg Complex.re h
    norm_num at this
  have hrec : Complex.Gamma (3 + (t : ℂ) * I) =
      (2 + (t : ℂ) * I) * Complex.Gamma (2 + (t : ℂ) * I) := by
    convert Complex.Gamma_add_one (2 + (t : ℂ) * I) hs using 1 <;> ring
  have hnorm : ‖(2 : ℂ) + (t : ℂ) * I‖ ^ 2 = 4 + t ^ 2 := by
    rw [Complex.sq_norm]
    simp [Complex.normSq_apply]
    ring
  rw [hrec, norm_mul, mul_pow, hnorm,
    norm_Gamma_two_add_mul_I_sq ht]
  ring

theorem norm_GammaR_six_add_two_mul_I_sq
    {t : ℝ} (ht : 0 < t) :
    ‖Gammaℝ (6 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2 =
      (Real.pi ^ (-3 : ℝ)) ^ 2 *
        ((4 + t ^ 2) * (1 + t ^ 2) *
          (Real.pi * t / Real.sinh (Real.pi * t))) := by
  rw [Gammaℝ_def, norm_mul, mul_pow]
  rw [Complex.norm_cpow_eq_rpow_re_of_pos Real.pi_pos]
  have hre : (-(6 + ((2 * t : ℝ) : ℂ) * I) / 2).re = -3 := by
    norm_num
  rw [hre]
  have harg : (6 + ((2 * t : ℝ) : ℂ) * I) / 2 =
      3 + (t : ℂ) * I := by
    apply Complex.ext <;> norm_num <;> ring
  rw [harg, norm_Gamma_three_add_mul_I_sq ht]

/-- Exact product decomposition of xi at the moving Jensen centre. -/
theorem norm_riemannXiEntire_jensenCenter
    (T : ℝ) :
    ‖riemannXiEntire (riemannXiJensenCenter T)‖ =
      ‖riemannXiJensenCenter T‖ *
        ‖riemannXiJensenCenter T - 1‖ *
        ‖Gammaℝ (riemannXiJensenCenter T)‖ *
        ‖riemannZeta (riemannXiJensenCenter T)‖ := by
  have hs0 : riemannXiJensenCenter T ≠ 0 := by
    intro h
    have := congrArg Complex.re h
    simp at this
  have hs1 : riemannXiJensenCenter T ≠ 1 := by
    intro h
    have := congrArg Complex.re h
    simp at this
  rw [riemannXiEntire_eq_mul_GammaR_riemannZeta hs0 hs1 (by simp)]
  simp only [norm_mul]

end RiemannLab
