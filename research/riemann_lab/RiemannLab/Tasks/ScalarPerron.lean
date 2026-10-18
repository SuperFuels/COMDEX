import Mathlib.Analysis.MellinInversion
import Mathlib.Analysis.SpecialFunctions.ImproperIntegrals

namespace RiemannLab

open Filter MeasureTheory
open scoped Interval Topology

/-!
The scalar discontinuous kernel underlying Perron's formula.

This module fixes the normalization and proves the algebraic and finite-interval
facts needed before the genuinely conditional limit is attacked.  The sharp
limit is represented as a proposition, never assumed as an axiom.
-/

/-- The scalar Perron integrand on the vertical line `Re(s) = c`. -/
noncomputable def scalarPerronKernel (c y t : ℝ) : ℂ :=
  (y : ℂ) ^ (c + t * Complex.I) / (c + t * Complex.I)

/-- The normalized symmetric truncation of the scalar Perron integral. -/
noncomputable def scalarTruncatedPerronIntegral (c y T : ℝ) : ℂ :=
  (1 / (2 * (Real.pi : ℂ))) * ∫ t in -T..T, scalarPerronKernel c y t

/-- The same kernel after the substitution `a = log y`. -/
noncomputable def logarithmicScalarPerronKernel (c a t : ℝ) : ℂ :=
  Complex.exp ((a : ℂ) * (c + t * Complex.I)) / (c + t * Complex.I)

/-- Symmetric truncation of the logarithmic/Fourier form. -/
noncomputable def logarithmicTruncatedPerronIntegral (c a T : ℝ) : ℂ :=
  (1 / (2 * (Real.pi : ℂ))) * ∫ t in -T..T, logarithmicScalarPerronKernel c a t

/-- The conditionally integrable oscillatory Cauchy kernel remaining after
factoring out the constant `exp (a*c)`. -/
noncomputable def oscillatoryCauchyKernel (c a t : ℝ) : ℂ :=
  Complex.exp ((a * t : ℝ) * Complex.I) / (c + t * Complex.I)

/-- Its normalized symmetric finite-height integral. -/
noncomputable def oscillatoryTruncatedCauchyIntegral (c a T : ℝ) : ℂ :=
  (1 / (2 * (Real.pi : ℂ))) * ∫ t in -T..T, oscillatoryCauchyKernel c a t

/-- A vertical parameter with positive real part never meets the pole at zero. -/
theorem scalarPerron_vertical_ne_zero {c : ℝ} (hc : 0 < c) (t : ℝ) :
    (c + t * Complex.I : ℂ) ≠ 0 := by
  intro h
  have hRe := congrArg Complex.re h
  simp only [Complex.add_re, Complex.ofReal_re, Complex.mul_re, Complex.I_re,
    Complex.I_im, mul_zero, Complex.ofReal_im, zero_mul, sub_zero, Complex.zero_re] at hRe
  exact hc.ne' (by simpa using hRe)

/-- For positive `y`, complex exponentiation in the scalar kernel has the
expected exponential/logarithmic form. -/
theorem scalarPerron_cpow_eq_exp {c y t : ℝ} (hy : 0 < y) :
    (y : ℂ) ^ (c + t * Complex.I) =
      Complex.exp ((Real.log y : ℂ) * (c + t * Complex.I)) := by
  rw [Complex.cpow_def_of_ne_zero (Complex.ofReal_ne_zero.mpr hy.ne')]
  rw [← Complex.ofReal_log hy.le]

/-- Substitution `a = log y` identifies the original and oscillatory kernels. -/
theorem scalarPerronKernel_eq_logarithmic {c y t : ℝ} (hy : 0 < y) :
    scalarPerronKernel c y t = logarithmicScalarPerronKernel c (Real.log y) t := by
  rw [scalarPerronKernel, logarithmicScalarPerronKernel, scalarPerron_cpow_eq_exp hy]

/-- The logarithmic reduction is exact at every finite truncation height. -/
theorem scalarTruncatedPerronIntegral_eq_logarithmic {c y T : ℝ} (hy : 0 < y) :
    scalarTruncatedPerronIntegral c y T =
      logarithmicTruncatedPerronIntegral c (Real.log y) T := by
  unfold scalarTruncatedPerronIntegral logarithmicTruncatedPerronIntegral
  congr 1
  apply intervalIntegral.integral_congr
  intro t _
  exact scalarPerronKernel_eq_logarithmic hy

/-- Exact separation of exponential growth/decay from the oscillation. -/
theorem logarithmicScalarPerronKernel_eq_exp_mul (c a t : ℝ) :
    logarithmicScalarPerronKernel c a t =
      (Real.exp (a * c) : ℂ) * oscillatoryCauchyKernel c a t := by
  rw [logarithmicScalarPerronKernel, oscillatoryCauchyKernel]
  rw [show (a : ℂ) * (c + t * Complex.I) =
      (a * c : ℝ) + (a * t : ℝ) * Complex.I by push_cast; ring]
  rw [Complex.exp_add]
  push_cast
  ring

/-- The same factorization commutes with every finite interval integral. -/
theorem logarithmicTruncatedPerronIntegral_eq_exp_mul (c a T : ℝ) :
    logarithmicTruncatedPerronIntegral c a T =
      (Real.exp (a * c) : ℂ) * oscillatoryTruncatedCauchyIntegral c a T := by
  unfold logarithmicTruncatedPerronIntegral oscillatoryTruncatedCauchyIntegral
  simp_rw [logarithmicScalarPerronKernel_eq_exp_mul]
  rw [intervalIntegral.integral_const_mul]
  ring

/-- The scalar kernel is continuous in the height variable away from the pole. -/
theorem continuous_scalarPerronKernel {c y : ℝ} (hc : 0 < c) (hy : 0 < y) :
    Continuous (scalarPerronKernel c y) := by
  unfold scalarPerronKernel
  simp_rw [scalarPerron_cpow_eq_exp hy]
  have hnum : Continuous (fun t : ℝ ↦
      Complex.exp ((Real.log y : ℂ) * (c + t * Complex.I))) := by fun_prop
  have hden : Continuous (fun t : ℝ ↦ (c + t * Complex.I : ℂ)) := by fun_prop
  exact hnum.div hden (fun t ↦ scalarPerron_vertical_ne_zero hc t)

/-- Consequently every finite scalar truncation is a legitimate interval
integral. -/
theorem intervalIntegrable_scalarPerronKernel {c y a b : ℝ} (hc : 0 < c) (hy : 0 < y) :
    IntervalIntegrable (scalarPerronKernel c y) volume a b :=
  (continuous_scalarPerronKernel hc hy).intervalIntegrable a b

/-- The reduced logarithmic kernel is continuous for positive `c`. -/
theorem continuous_logarithmicScalarPerronKernel {c a : ℝ} (hc : 0 < c) :
    Continuous (logarithmicScalarPerronKernel c a) := by
  unfold logarithmicScalarPerronKernel
  have hnum : Continuous (fun t : ℝ ↦
      Complex.exp ((a : ℂ) * (c + t * Complex.I))) := by fun_prop
  have hden : Continuous (fun t : ℝ ↦ (c + t * Complex.I : ℂ)) := by fun_prop
  exact hnum.div hden (fun t ↦ scalarPerron_vertical_ne_zero hc t)

@[simp]
theorem scalarTruncatedPerronIntegral_zero_height (c y : ℝ) :
    scalarTruncatedPerronIntegral c y 0 = 0 := by
  simp [scalarTruncatedPerronIntegral]

@[simp]
theorem logarithmicTruncatedPerronIntegral_zero_height (c a : ℝ) :
    logarithmicTruncatedPerronIntegral c a 0 = 0 := by
  simp [logarithmicTruncatedPerronIntegral]

@[simp]
theorem oscillatoryTruncatedCauchyIntegral_zero_height (c a : ℝ) :
    oscillatoryTruncatedCauchyIntegral c a 0 = 0 := by
  simp [oscillatoryTruncatedCauchyIntegral]

/-- The exact classical scalar Perron statement away from its jump. -/
def ScalarPerronLimitTarget : Prop :=
  ∀ c y : ℝ, 0 < c → 0 < y → y ≠ 1 →
    Tendsto (fun T : ℝ ↦ scalarTruncatedPerronIntegral c y T) atTop
      (𝓝 (if 1 < y then (1 : ℂ) else 0))

/-- Equivalent target shape after `a = log y`; the remaining analytic issue is
the sign-sensitive oscillatory limit at every nonzero frequency `a`. -/
def LogarithmicScalarPerronLimitTarget : Prop :=
  ∀ c a : ℝ, 0 < c → a ≠ 0 →
    Tendsto (fun T : ℝ ↦ logarithmicTruncatedPerronIntegral c a T) atTop
      (𝓝 (if 0 < a then (1 : ℂ) else 0))

/-- The final normalized oscillatory Cauchy-transform limit after removing the
constant factor `exp (a*c)`. -/
def OscillatoryCauchyLimitTarget : Prop :=
  ∀ c a : ℝ, 0 < c → a ≠ 0 →
    Tendsto (fun T : ℝ ↦ oscillatoryTruncatedCauchyIntegral c a T) atTop
      (𝓝 (if 0 < a then (Real.exp (-a * c) : ℂ) else 0))

/-- The `y`-form and the logarithmic oscillatory form of the open limit are
logically equivalent, with all changes of variables kernel-checked. -/
theorem scalarPerronLimitTarget_iff_logarithmic :
    ScalarPerronLimitTarget ↔ LogarithmicScalarPerronLimitTarget := by
  constructor
  · intro h c a hc ha
    have hExpNe : Real.exp a ≠ 1 := by
      rw [← Real.exp_zero]
      exact Real.exp_injective.ne ha
    have H := h c (Real.exp a) hc (Real.exp_pos a) hExpNe
    have hsign : (1 < Real.exp a) ↔ 0 < a := by
      simpa only [Real.exp_zero] using (Real.exp_lt_exp (x := 0) (y := a))
    simpa only [scalarTruncatedPerronIntegral_eq_logarithmic (Real.exp_pos a),
      Real.log_exp, hsign] using H
  · intro h c y hc hy hy1
    have hlog : Real.log y ≠ 0 := by
      rw [Real.log_ne_zero]
      exact ⟨hy.ne', hy1, by linarith⟩
    have H := h c (Real.log y) hc hlog
    have hsign : (0 < Real.log y) ↔ 1 < y := by
      rw [← Real.exp_lt_exp, Real.exp_zero, Real.exp_log hy]
    simpa only [scalarTruncatedPerronIntegral_eq_logarithmic hy, hsign] using H

/-- Removing the nonzero constant `exp (a*c)` loses no information: the
logarithmic scalar target is exactly the oscillatory Cauchy target. -/
theorem logarithmicScalarPerronLimitTarget_iff_oscillatory :
    LogarithmicScalarPerronLimitTarget ↔ OscillatoryCauchyLimitTarget := by
  constructor
  · intro h c a hc ha
    have H := h c a hc ha
    have Hmul := H.const_mul (Real.exp (-a * c) : ℂ)
    by_cases hpos : 0 < a
    · simp only [hpos, if_true, mul_one] at Hmul ⊢
      apply Hmul.congr'
      filter_upwards with T
      rw [logarithmicTruncatedPerronIntegral_eq_exp_mul]
      push_cast
      rw [← mul_assoc]
      rw [← Complex.exp_add]
      ring_nf
      simp
    · simp only [hpos, if_false, mul_zero] at Hmul ⊢
      apply Hmul.congr'
      filter_upwards with T
      rw [logarithmicTruncatedPerronIntegral_eq_exp_mul]
      push_cast
      rw [← mul_assoc]
      rw [← Complex.exp_add]
      ring_nf
      simp
  · intro h c a hc ha
    have H := h c a hc ha
    have Hmul := H.const_mul (Real.exp (a * c) : ℂ)
    by_cases hpos : 0 < a
    · simp only [hpos, if_true] at Hmul ⊢
      rw [show (Real.exp (a * c) : ℂ) * Real.exp (-a * c) = 1 by
        push_cast
        rw [← Complex.exp_add]
        ring_nf
        simp] at Hmul
      simpa only [one_mul, ← logarithmicTruncatedPerronIntegral_eq_exp_mul] using Hmul
    · simp only [hpos, if_false, mul_zero] at Hmul ⊢
      simpa only [← logarithmicTruncatedPerronIntegral_eq_exp_mul] using Hmul

/-- Positive `y ≠ 1` is equivalently on one of the two sides of the jump. -/
theorem scalarPerron_side_cases {y : ℝ} (_hy : 0 < y) (hy1 : y ≠ 1) :
    y < 1 ∨ 1 < y := by
  exact lt_or_gt_of_ne hy1

/-! The jump point is not part of `ScalarPerronLimitTarget`, but it is a
valuable normalization check: the symmetric truncation has half weight. -/

theorem scalarPerronKernel_one_re (c t : ℝ) :
    RCLike.re (scalarPerronKernel c 1 t) = c / (c ^ 2 + t ^ 2) := by
  simp [scalarPerronKernel, Complex.normSq_apply]
  ring

theorem scalarPerronKernel_one_im (c t : ℝ) :
    RCLike.im (scalarPerronKernel c 1 t) = -t / (c ^ 2 + t ^ 2) := by
  simp [scalarPerronKernel, Complex.normSq_apply]
  ring

theorem integral_scalarPerronKernel_one_re (c T : ℝ) :
    ∫ t in -T..T, RCLike.re (scalarPerronKernel c 1 t) =
      2 * Real.arctan (T / c) := by
  simp_rw [scalarPerronKernel_one_re]
  rw [integral_div_sq_add_sq]
  rw [show -T / c = -(T / c) by ring, Real.arctan_neg]
  ring

theorem integral_scalarPerronKernel_one_im (c T : ℝ) :
    ∫ t in -T..T, RCLike.im (scalarPerronKernel c 1 t) = 0 := by
  simp_rw [scalarPerronKernel_one_im]
  let f : ℝ → ℝ := fun t ↦ -t / (c ^ 2 + t ^ 2)
  have hodd : Function.Odd f := by
    intro t
    simp [f]
    ring
  have h := intervalIntegral.integral_comp_neg f (a := -T) (b := T)
  have hfun : (fun t : ℝ ↦ f (-t)) = fun t : ℝ ↦ -f t := by
    funext t
    exact hodd t
  rw [hfun, intervalIntegral.integral_neg] at h
  simp only [neg_neg] at h
  linarith

/-- Exact finite-height evaluation at the discontinuity `y = 1`. -/
theorem integral_scalarPerronKernel_one {c T : ℝ} (hc : 0 < c) :
    ∫ t in -T..T, scalarPerronKernel c 1 t =
      (2 * Real.arctan (T / c) : ℝ) := by
  have hInt := intervalIntegrable_scalarPerronKernel (a := -T) (b := T) hc zero_lt_one
  apply Complex.ext
  · change RCLike.re (∫ t in -T..T, scalarPerronKernel c 1 t) =
      2 * Real.arctan (T / c)
    rw [← intervalIntegral.intervalIntegral_re hInt]
    exact integral_scalarPerronKernel_one_re c T
  · change RCLike.im (∫ t in -T..T, scalarPerronKernel c 1 t) = 0
    rw [← intervalIntegral.intervalIntegral_im hInt]
    exact integral_scalarPerronKernel_one_im c T

/-- The normalized finite truncation at `y = 1` is an arctangent ratio. -/
theorem scalarTruncatedPerronIntegral_one {c T : ℝ} (hc : 0 < c) :
    scalarTruncatedPerronIntegral c 1 T =
      (Real.arctan (T / c) / Real.pi : ℝ) := by
  rw [scalarTruncatedPerronIntegral, integral_scalarPerronKernel_one hc]
  push_cast
  field_simp

/-- The symmetric convention gives the classical half weight at the jump. -/
theorem scalarTruncatedPerronIntegral_tendsto_half {c : ℝ} (hc : 0 < c) :
    Tendsto (fun T : ℝ ↦ scalarTruncatedPerronIntegral c 1 T) atTop
      (𝓝 (1 / 2 : ℂ)) := by
  have hTc : Tendsto (fun T : ℝ ↦ T / c) atTop atTop :=
    (tendsto_div_const_atTop_of_pos hc).2 tendsto_id
  have hA : Tendsto (fun T : ℝ ↦ Real.arctan (T / c)) atTop
      (𝓝 (Real.pi / 2)) :=
    tendsto_nhds_of_tendsto_nhdsWithin (Real.tendsto_arctan_atTop.comp hTc)
  have hR : Tendsto (fun T : ℝ ↦ Real.arctan (T / c) / Real.pi) atTop
      (𝓝 ((Real.pi / 2) / Real.pi)) := hA.div_const Real.pi
  have hC := Complex.continuous_ofReal.continuousAt.tendsto.comp hR
  rw [show ((Real.pi / 2) / Real.pi : ℝ) = 1 / 2 by field_simp] at hC
  change Tendsto (fun T : ℝ ↦ ((Real.arctan (T / c) / Real.pi : ℝ) : ℂ)) atTop
    (𝓝 ((1 / 2 : ℝ) : ℂ)) at hC
  simpa only [scalarTruncatedPerronIntegral_one hc, Complex.ofReal_div,
    Complex.ofReal_one, Complex.ofReal_ofNat] using hC

end RiemannLab
