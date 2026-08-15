import RiemannLab.Tasks.CompletedZetaGrowth
import Mathlib.Analysis.Complex.Hadamard
import Mathlib.Analysis.SpecialFunctions.Gamma.Beta
import Mathlib.Analysis.SpecialFunctions.Trigonometric.DerivHyp

namespace RiemannLab

open Complex

/-!
Exact vertical-line identities for the complex Gamma factor.  These are the
smallest classical inputs needed before applying a three-lines argument to a
polynomially normalized completed zeta function.
-/

theorem norm_sin_pi_mul_I_mul (t : ℝ) :
    ‖Complex.sin ((Real.pi : ℂ) * ((t : ℂ) * I))‖ =
      |Real.sinh (Real.pi * t)| := by
  rw [← mul_assoc, ← ofReal_mul, Complex.sin_mul_I,
    ← Complex.ofReal_sinh, norm_mul, norm_real, norm_I, mul_one]
  exact Real.norm_eq_abs _

/-- Deligne's real Gamma factor has conjugation-invariant norm. -/
theorem norm_GammaR_conj (s : ℂ) : ‖Gammaℝ (starRingEnd ℂ s)‖ = ‖Gammaℝ s‖ := by
  rw [Gammaℝ_def, Gammaℝ_def, norm_mul, norm_mul]
  rw [Complex.norm_cpow_eq_rpow_re_of_pos Real.pi_pos,
    Complex.norm_cpow_eq_rpow_re_of_pos Real.pi_pos]
  have hdiv : (starRingEnd ℂ s) / 2 = starRingEnd ℂ (s / 2) := by
    rw [map_div₀]
    congr 1
    apply Complex.ext <;> norm_num
  rw [hdiv, Complex.Gamma_conj, norm_conj]
  congr 2
  simp

theorem norm_sin_pi_mul_I_mul_of_pos {t : ℝ} (ht : 0 < t) :
    ‖Complex.sin ((Real.pi : ℂ) * ((t : ℂ) * I))‖ =
      Real.sinh (Real.pi * t) := by
  rw [norm_sin_pi_mul_I_mul, abs_of_pos]
  exact (Real.sinh_pos_iff).2 (mul_pos Real.pi_pos ht)

/-- A convenient explicit exponential lower bound for the hyperbolic sine.
It is deliberately coarse; unlike a full Stirling expansion, it is already
strong enough to expose Gamma's vertical exponential decay. -/
theorem exp_div_four_le_sinh {x : ℝ} (hx : 1 ≤ x) :
    Real.exp x / 4 ≤ Real.sinh x := by
  rw [Real.sinh_eq]
  have hneg : Real.exp (-x) ≤ 1 := Real.exp_le_one_iff.mpr (by linarith)
  have htwo : 2 ≤ Real.exp x := by
    calc
      2 ≤ x + 1 := by linarith
      _ ≤ Real.exp x := Real.add_one_le_exp x
  linarith

/-- Exact Gamma norm identity on the line `Re(s)=1`, in squared form. -/
theorem norm_Gamma_one_add_mul_I_sq {t : ℝ} (ht : 0 < t) :
    ‖Complex.Gamma (1 + (t : ℂ) * I)‖ ^ 2 =
      Real.pi * t / Real.sinh (Real.pi * t) := by
  have hit : (t : ℂ) * I ≠ 0 := mul_ne_zero (ofReal_ne_zero.mpr ht.ne') I_ne_zero
  have hnegit : -(t : ℂ) * I ≠ 0 := mul_ne_zero (neg_ne_zero.mpr (ofReal_ne_zero.mpr ht.ne')) I_ne_zero
  have href := Complex.Gamma_mul_Gamma_one_sub ((t : ℂ) * I)
  have hnorm := congrArg norm href
  have hconj : Complex.Gamma (-(t : ℂ) * I) =
      starRingEnd ℂ (Complex.Gamma ((t : ℂ) * I)) := by
    rw [← Complex.Gamma_conj]
    congr 2
    apply Complex.ext <;> simp
  have honeNeg : Complex.Gamma (1 - (t : ℂ) * I) =
      (-(t : ℂ) * I) * Complex.Gamma (-(t : ℂ) * I) := by
    convert Complex.Gamma_add_one (-(t : ℂ) * I) hnegit using 1 <;> ring
  have honePos : Complex.Gamma (1 + (t : ℂ) * I) =
      ((t : ℂ) * I) * Complex.Gamma ((t : ℂ) * I) := by
    convert Complex.Gamma_add_one ((t : ℂ) * I) hit using 1 <;> ring
  have hpi : ‖(Real.pi : ℂ)‖ = Real.pi := by
    simpa [Real.norm_eq_abs, abs_of_pos Real.pi_pos]
  rw [norm_mul, honeNeg, norm_mul, hconj, norm_conj, norm_div,
    norm_sin_pi_mul_I_mul_of_pos ht] at hnorm
  rw [norm_mul, norm_neg, norm_real, Real.norm_eq_abs, abs_of_pos ht,
    norm_I, mul_one, hpi] at hnorm
  rw [honePos, norm_mul, norm_mul, norm_real, Real.norm_eq_abs, abs_of_pos ht,
    norm_I, mul_one]
  have ht0 : t ≠ 0 := ht.ne'
  have hsinh0 : Real.sinh (Real.pi * t) ≠ 0 :=
    ((Real.sinh_pos_iff).2 (mul_pos Real.pi_pos ht)).ne'
  field_simp at hnorm ⊢
  nlinarith [norm_nonneg (Complex.Gamma ((t : ℂ) * I))]

/-- Explicit exponential upper bound extracted from the exact vertical-line
identity. -/
theorem norm_Gamma_one_add_mul_I_sq_le {t : ℝ} (ht : 1 ≤ t) :
    ‖Complex.Gamma (1 + (t : ℂ) * I)‖ ^ 2 ≤
      (Real.pi * t) / (Real.exp (Real.pi * t) / 4) := by
  rw [norm_Gamma_one_add_mul_I_sq (lt_of_lt_of_le zero_lt_one ht)]
  apply div_le_div_of_nonneg_left
  · positivity
  · positivity
  · apply exp_div_four_le_sinh
    nlinarith [Real.two_le_pi]

/-- Exact Gamma norm identity on the line `Re(s)=2`. -/
theorem norm_Gamma_two_add_mul_I_sq {t : ℝ} (ht : 0 < t) :
    ‖Complex.Gamma (2 + (t : ℂ) * I)‖ ^ 2 =
      (1 + t ^ 2) * (Real.pi * t / Real.sinh (Real.pi * t)) := by
  have hs : (1 : ℂ) + (t : ℂ) * I ≠ 0 := by
    intro h
    have := congrArg Complex.re h
    norm_num at this
  have hrec : Complex.Gamma (2 + (t : ℂ) * I) =
      (1 + (t : ℂ) * I) * Complex.Gamma (1 + (t : ℂ) * I) := by
    convert Complex.Gamma_add_one (1 + (t : ℂ) * I) hs using 1 <;> ring
  have hnorm : ‖(1 : ℂ) + (t : ℂ) * I‖ ^ 2 = 1 + t ^ 2 := by
    rw [Complex.sq_norm]
    simp [Complex.normSq_apply]
    ring
  rw [hrec, norm_mul, mul_pow]
  rw [hnorm]
  rw [norm_Gamma_one_add_mul_I_sq ht]

/-- Exact squared norm of Deligne's real Gamma factor on `Re(s)=4`.
The ordinate is written as `2t` so that the underlying complex Gamma
parameter is `2+it`. -/
theorem norm_GammaR_four_add_two_mul_I_sq {t : ℝ} (ht : 0 < t) :
    ‖Gammaℝ (4 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2 =
      (Real.pi ^ (-2 : ℝ)) ^ 2 *
        ((1 + t ^ 2) * (Real.pi * t / Real.sinh (Real.pi * t))) := by
  rw [Gammaℝ_def, norm_mul, mul_pow]
  rw [Complex.norm_cpow_eq_rpow_re_of_pos Real.pi_pos]
  have hre : (-(4 + ((2 * t : ℝ) : ℂ) * I) / 2).re = -2 := by
    norm_num
  rw [hre]
  have harg : (4 + ((2 * t : ℝ) : ℂ) * I) / 2 =
      2 + (t : ℂ) * I := by
    apply Complex.ext <;> simp <;> ring
  rw [harg, norm_Gamma_two_add_mul_I_sq ht]

end RiemannLab
