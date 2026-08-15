import RiemannLab.Tasks.OscillatoryCauchy
import Mathlib.Analysis.Fourier.Inversion
import Mathlib.Analysis.SpecialFunctions.Gamma.Basic

namespace RiemannLab

open Filter MeasureTheory Complex Set
open scoped FourierTransform Topology

/-!
Fourier-inversion route for the last absolutely convergent scalar Perron gate.
-/

/-- The continuous-at-nonzero one-sided exponential moment whose Fourier
transform is the squared Cauchy denominator. -/
noncomputable def oneSidedExpMoment (c x : ℝ) : ℂ :=
  if 0 < x then (x : ℂ) * Complex.exp (-(c * x : ℝ)) else 0

/-- The positive-half-line part of the one-sided exponential moment is
integrable. -/
theorem integrableOn_oneSidedExpMoment_Ioi {c : ℝ} (hc : 0 < c) :
    IntegrableOn (oneSidedExpMoment c) (Ioi 0) := by
  let g : ℝ → ℝ := fun x ↦ Real.exp (-x) * x ^ ((2 : ℝ) - 1)
  have hg : IntegrableOn g (Ioi 0) := by
    simpa only [g] using Real.GammaIntegral_convergent (s := (2 : ℝ)) (by norm_num)
  have hscaled : IntegrableOn (fun x : ℝ ↦ g (c * x)) (Ioi 0) := by
    apply (integrableOn_Ioi_comp_mul_left_iff g 0 hc).mpr
    simpa using hg
  have hreal : IntegrableOn (fun x : ℝ ↦ x * Real.exp (-(c * x))) (Ioi 0) := by
    have h := hscaled.const_mul c⁻¹
    apply h.congr
    filter_upwards [ae_restrict_mem measurableSet_Ioi] with x hx
    simp only [g]
    norm_num
    field_simp
  have hcomplex := hreal.ofReal (𝕜 := ℂ)
  apply hcomplex.congr
  filter_upwards [ae_restrict_mem measurableSet_Ioi] with x hx
  have hx' : 0 < x := hx
  rw [oneSidedExpMoment, if_pos hx']
  push_cast
  rw [show (-((c : ℂ) * (x : ℂ))) = ((-(c * x) : ℝ) : ℂ) by push_cast; rfl]
  rw [← ofReal_exp]
  rfl

/-- The one-sided exponential moment is integrable on the whole real line. -/
theorem integrable_oneSidedExpMoment {c : ℝ} (hc : 0 < c) :
    Integrable (oneSidedExpMoment c) := by
  rw [← integrableOn_univ, ← Iic_union_Ioi (a := (0 : ℝ))]
  apply IntegrableOn.union
  · have hz : IntegrableOn (fun _ : ℝ ↦ (0 : ℂ)) (Iic 0) := integrableOn_zero
    apply hz.congr_fun (s := Iic 0) _ measurableSet_Iic
    intro x hx
    rw [oneSidedExpMoment, if_neg (not_lt.mpr hx)]
  · exact integrableOn_oneSidedExpMoment_Ioi hc

/-- Away from the jump at zero, the one-sided moment has the expected value
and is continuous. -/
theorem oneSidedExpMoment_eq_of_ne {c a : ℝ} (_ha : a ≠ 0) :
    oneSidedExpMoment c a =
      if 0 < a then (a : ℂ) * Complex.exp (-(c * a : ℝ)) else 0 := rfl

theorem continuousAt_oneSidedExpMoment_of_ne {c a : ℝ} (ha : a ≠ 0) :
    ContinuousAt (oneSidedExpMoment c) a := by
  by_cases hapos : 0 < a
  · have hev : oneSidedExpMoment c =ᶠ[𝓝 a]
        (fun x : ℝ ↦ (x : ℂ) * Complex.exp (-(c * x : ℝ))) := by
      filter_upwards [Ioi_mem_nhds hapos] with x hx
      have hx' : 0 < x := hx
      rw [oneSidedExpMoment, if_pos hx']
    exact (by fun_prop : ContinuousAt
      (fun x : ℝ ↦ (x : ℂ) * Complex.exp (-(c * x : ℝ))) a).congr_of_eventuallyEq hev
  · have haneg : a < 0 := lt_of_le_of_ne (not_lt.mp hapos) ha
    have hev : oneSidedExpMoment c =ᶠ[𝓝 a] (fun _ : ℝ ↦ (0 : ℂ)) := by
      filter_upwards [Iio_mem_nhds haneg] with x hx
      rw [oneSidedExpMoment, if_neg (not_lt.mpr hx.le)]
    exact continuousAt_const.congr_of_eventuallyEq hev

/-- The positive-half-line kernel appearing when the Fourier transform of
`oneSidedExpMoment` is expanded. -/
noncomputable def expMomentFourierKernel (c w x : ℝ) : ℂ :=
  (x : ℂ) * Complex.exp
    (-((c : ℂ) + (2 * Real.pi * w : ℝ) * Complex.I) * x)

theorem norm_expMomentFourierKernel_of_pos {c w x : ℝ} (hx : 0 < x) :
    ‖expMomentFourierKernel c w x‖ = x * Real.exp (-(c * x)) := by
  unfold expMomentFourierKernel
  rw [norm_mul, norm_real, Real.norm_eq_abs, abs_of_pos hx, Complex.norm_exp]
  congr 1
  simp only [mul_re, neg_re, add_re, ofReal_re, ofReal_im, mul_zero, I_re, I_im,
    zero_mul, sub_zero]
  ring

theorem integrableOn_expMomentFourierKernel_Ioi {c w : ℝ} (hc : 0 < c) :
    IntegrableOn (expMomentFourierKernel c w) (Ioi 0) := by
  have hmeas : AEStronglyMeasurable (expMomentFourierKernel c w)
      (volume.restrict (Ioi 0)) := by
    apply Continuous.aestronglyMeasurable
    unfold expMomentFourierKernel
    fun_prop
  change Integrable (expMomentFourierKernel c w) (volume.restrict (Ioi 0))
  rw [← integrable_norm_iff hmeas]
  have hnorm := (integrableOn_oneSidedExpMoment_Ioi (c := c) hc).norm
  apply hnorm.congr
  filter_upwards [ae_restrict_mem measurableSet_Ioi] with x hx
  have hx' : 0 < x := hx
  rw [norm_expMomentFourierKernel_of_pos hx', oneSidedExpMoment, if_pos hx',
    norm_mul, norm_real, Real.norm_eq_abs, abs_of_pos hx', Complex.norm_exp]
  congr 1

theorem expMomentFourierParameter_ne_zero {c w : ℝ} (hc : 0 < c) :
    ((c : ℂ) + (2 * Real.pi * w : ℝ) * Complex.I) ≠ 0 := by
  apply verticalLine_ne_zero_of_re_ne_zero hc.ne'

/-- A primitive for the exponential factor in `expMomentFourierKernel`. -/
noncomputable def expMomentFourierPrimitive (c w x : ℝ) : ℂ :=
  Complex.exp
      (-((c : ℂ) + (2 * Real.pi * w : ℝ) * Complex.I) * x) /
    (-((c : ℂ) + (2 * Real.pi * w : ℝ) * Complex.I))

theorem hasDerivAt_expMomentFourierPrimitive {c w x : ℝ} (hc : 0 < c) :
    HasDerivAt (expMomentFourierPrimitive c w)
      (Complex.exp
        (-((c : ℂ) + (2 * Real.pi * w : ℝ) * Complex.I) * x)) x := by
  let d : ℂ := (c : ℂ) + (2 * Real.pi * w : ℝ) * Complex.I
  have hd : d ≠ 0 := expMomentFourierParameter_ne_zero hc
  have harg : HasDerivAt (fun z : ℂ ↦ -d * z) (-d) (x : ℂ) := by
    simpa using (hasDerivAt_id (x : ℂ)).const_mul (-d)
  have h := harg.cexp.div_const (-d)
  convert h.comp_ofReal using 1
  · funext t
    unfold expMomentFourierPrimitive d
    rfl
  · rw [mul_div_cancel_right₀ _ (neg_ne_zero.mpr hd)]

/-- Finite-height integration by parts for the exponential moment. -/
theorem integral_expMomentFourierKernel_zero_to {c w T : ℝ} (hc : 0 < c) :
    (∫ x in 0..T, expMomentFourierKernel c w x) =
      (T : ℂ) * expMomentFourierPrimitive c w T -
      ∫ x in 0..T, expMomentFourierPrimitive c w x := by
  have h := intervalIntegral.integral_mul_deriv_eq_deriv_mul
    (a := 0) (b := T)
    (u := fun x : ℝ ↦ (x : ℂ))
    (v := expMomentFourierPrimitive c w)
    (u' := fun _ : ℝ ↦ (1 : ℂ))
    (v' := fun x : ℝ ↦ Complex.exp
      (-((c : ℂ) + (2 * Real.pi * w : ℝ) * Complex.I) * x))
    (fun x _ ↦ by simpa using (hasDerivAt_id (x : ℂ)).comp_ofReal)
    (fun x _ ↦ hasDerivAt_expMomentFourierPrimitive hc)
    (continuous_const.intervalIntegrable 0 T)
    (by
      have hcont : Continuous (fun x : ℝ ↦ Complex.exp
        (-((c : ℂ) + (2 * Real.pi * w : ℝ) * Complex.I) * x)) := by fun_prop
      exact hcont.intervalIntegrable 0 T)
  simpa only [expMomentFourierKernel, ofReal_zero, zero_mul, sub_zero, one_mul] using h

theorem tendsto_expMomentFourier_boundary_zero {c w : ℝ} (hc : 0 < c) :
    Tendsto (fun T : ℝ ↦ (T : ℂ) * expMomentFourierPrimitive c w T)
      atTop (𝓝 0) := by
  let d : ℂ := (c : ℂ) + (2 * Real.pi * w : ℝ) * Complex.I
  rw [tendsto_zero_iff_norm_tendsto_zero]
  have hbase := tendsto_rpow_mul_exp_neg_mul_atTop_nhds_zero (1 : ℝ) c hc
  have h := hbase.mul_const ‖d‖⁻¹
  have h' : Tendsto (fun x : ℝ ↦ x ^ (1 : ℝ) * Real.exp (-c * x) * ‖d‖⁻¹)
      atTop (𝓝 0) := by simpa using h
  apply h'.congr'
  filter_upwards [eventually_gt_atTop (0 : ℝ)] with T hT
  unfold expMomentFourierPrimitive
  rw [norm_mul, norm_real, Real.norm_eq_abs, abs_of_pos hT, norm_div, norm_neg,
    Complex.norm_exp]
  simp only [mul_re, neg_re, add_re, ofReal_re, ofReal_im, mul_zero, I_re, I_im,
    zero_mul, sub_zero, Real.rpow_one]
  dsimp only [d]
  ring

theorem integrableOn_expMomentFourierPrimitive_Ioi {c w : ℝ} (hc : 0 < c) :
    IntegrableOn (expMomentFourierPrimitive c w) (Ioi 0) := by
  let d : ℂ := (c : ℂ) + (2 * Real.pi * w : ℝ) * Complex.I
  have hdre : (-d).re < 0 := by
    dsimp only [d]
    simpa using hc
  have h := (integrableOn_exp_mul_complex_Ioi hdre 0).div_const (-d)
  apply h.congr
  filter_upwards [ae_restrict_mem measurableSet_Ioi] with x hx
  unfold expMomentFourierPrimitive
  rfl

theorem integral_expMomentFourierPrimitive_Ioi {c w : ℝ} (hc : 0 < c) :
    (∫ x : ℝ in Ioi 0, expMomentFourierPrimitive c w x) =
      -(((c : ℂ) + (2 * Real.pi * w : ℝ) * Complex.I) ^ 2)⁻¹ := by
  let d : ℂ := (c : ℂ) + (2 * Real.pi * w : ℝ) * Complex.I
  have hd : d ≠ 0 := expMomentFourierParameter_ne_zero hc
  have hdre : (-d).re < 0 := by
    dsimp only [d]
    simpa using hc
  unfold expMomentFourierPrimitive
  rw [integral_div, integral_exp_mul_complex_Ioi hdre 0]
  change (-Complex.exp ((-d) * (0 : ℂ)) / (-d)) / (-d) = -(d ^ 2)⁻¹
  norm_num
  field_simp

/-- Exact half-line transform calculation. This is the analytic core that
turns the one-sided exponential moment into the squared Cauchy denominator. -/
theorem integral_expMomentFourierKernel_Ioi {c w : ℝ} (hc : 0 < c) :
    (∫ x : ℝ in Ioi 0, expMomentFourierKernel c w x) =
      (((c : ℂ) + (2 * Real.pi * w : ℝ) * Complex.I) ^ 2)⁻¹ := by
  have hL := intervalIntegral_tendsto_integral_Ioi (b := fun T : ℝ ↦ T) 0
    (integrableOn_expMomentFourierKernel_Ioi (w := w) hc)
    (tendsto_id : Tendsto (fun T : ℝ ↦ T) atTop atTop)
  have hB := tendsto_expMomentFourier_boundary_zero (w := w) hc
  have hP := intervalIntegral_tendsto_integral_Ioi (b := fun T : ℝ ↦ T) 0
    (integrableOn_expMomentFourierPrimitive_Ioi (w := w) hc)
    (tendsto_id : Tendsto (fun T : ℝ ↦ T) atTop atTop)
  rw [integral_expMomentFourierPrimitive_Ioi hc] at hP
  have hR := hB.sub hP
  have hR' : Tendsto (fun T : ℝ ↦
      ∫ x in 0..T, expMomentFourierKernel c w x) atTop
      (𝓝 ((((c : ℂ) + (2 * Real.pi * w : ℝ) * Complex.I) ^ 2)⁻¹)) := by
    convert hR using 1
    · funext T
      rw [integral_expMomentFourierKernel_zero_to hc]
    · ring
  exact tendsto_nhds_unique hL hR'

/-- The Fourier transform of the one-sided exponential moment is exactly the
squared Cauchy denominator, with Mathlib's `2*pi` convention. -/
theorem fourier_oneSidedExpMoment {c w : ℝ} (hc : 0 < c) :
    𝓕 (oneSidedExpMoment c) w =
      (((c : ℂ) + (2 * Real.pi * w : ℝ) * Complex.I) ^ 2)⁻¹ := by
  rw [Real.fourier_real_eq_integral_exp_smul]
  rw [← integral_expMomentFourierKernel_Ioi hc, ← integral_indicator measurableSet_Ioi]
  apply integral_congr_ae
  filter_upwards with x
  by_cases hx : 0 < x
  · simp only [Set.indicator, mem_Ioi, hx, if_pos, oneSidedExpMoment, smul_eq_mul]
    calc
      Complex.exp ((-2 * Real.pi * x * w : ℝ) * Complex.I) *
          ((x : ℂ) * Complex.exp (-(c * x : ℝ))) =
          (x : ℂ) * (Complex.exp ((-2 * Real.pi * x * w : ℝ) * Complex.I) *
            Complex.exp (-(c * x : ℝ))) := by ring
      _ = (x : ℂ) * Complex.exp
          (((-2 * Real.pi * x * w : ℝ) * Complex.I) + (-(c * x : ℝ) : ℂ)) := by
            rw [Complex.exp_add]
      _ = expMomentFourierKernel c w x := by
        unfold expMomentFourierKernel
        congr 2
        push_cast
        ring
  · simp [Set.indicator, oneSidedExpMoment, hx]

theorem integrable_fourier_oneSidedExpMoment {c : ℝ} (hc : 0 < c) :
    Integrable (𝓕 (oneSidedExpMoment c)) := by
  have hsq := integrable_squaredOscillatoryCauchyKernel (a := 0) hc.ne'
  have hscale : (2 * Real.pi : ℝ) ≠ 0 := mul_ne_zero two_ne_zero Real.pi_ne_zero
  have hcomp : Integrable (fun w : ℝ ↦
      squaredOscillatoryCauchyKernel c 0 ((2 * Real.pi) * w)) :=
    (integrable_comp_mul_left_iff (squaredOscillatoryCauchyKernel c 0) hscale).mpr hsq
  apply hcomp.congr
  filter_upwards with w
  rw [fourier_oneSidedExpMoment hc]
  unfold squaredOscillatoryCauchyKernel
  norm_num

/-- Fourier inversion evaluates the normalized squared-denominator integral
before the final linear change of variables. -/
theorem integral_fourier_scaled_squaredCauchy {c a : ℝ} (hc : 0 < c) (ha : a ≠ 0) :
    (∫ w : ℝ, Complex.exp ((2 * Real.pi * w * a : ℝ) * Complex.I) *
      (((c : ℂ) + (2 * Real.pi * w : ℝ) * Complex.I) ^ 2)⁻¹) =
        if 0 < a then (a : ℂ) * Complex.exp (-(c * a : ℝ)) else 0 := by
  have h := (integrable_oneSidedExpMoment (c := c) hc).fourierInv_fourier_eq
    (integrable_fourier_oneSidedExpMoment hc)
    (continuousAt_oneSidedExpMoment_of_ne (c := c) ha)
  rw [Real.fourierInv_eq'] at h
  simp_rw [smul_eq_mul, fourier_oneSidedExpMoment hc] at h
  simp only [oneSidedExpMoment, RCLike.inner_apply, conj_trivial] at h
  simpa only [mul_assoc, mul_left_comm, mul_comm] using h

/-- Undoing Mathlib's Fourier normalization gives the exact whole-line value
needed by `SquaredCauchyFourierValueTarget`. -/
theorem integral_squaredOscillatoryCauchyKernel {c a : ℝ}
    (hc : 0 < c) (ha : a ≠ 0) :
    (∫ t : ℝ, squaredOscillatoryCauchyKernel c a t) =
      if 0 < a then
        (2 * (Real.pi : ℂ)) * (a : ℂ) * Real.exp (-a * c)
      else 0 := by
  let R : ℝ := 2 * Real.pi
  have hRpos : 0 < R := mul_pos zero_lt_two Real.pi_pos
  have hscaled := integral_fourier_scaled_squaredCauchy hc ha
  have hcomp : (∫ w : ℝ, squaredOscillatoryCauchyKernel c a (R * w)) =
      if 0 < a then (a : ℂ) * Complex.exp (-(c * a : ℝ)) else 0 := by
    simpa only [R, squaredOscillatoryCauchyKernel, div_eq_mul_inv,
      mul_assoc, mul_left_comm, mul_comm]
      using hscaled
  have hchange := Measure.integral_comp_mul_left
    (squaredOscillatoryCauchyKernel c a) R
  rw [abs_of_pos (inv_pos.mpr hRpos)] at hchange
  rw [hcomp] at hchange
  by_cases hapos : 0 < a
  · simp only [if_pos hapos] at hchange ⊢
    rw [real_smul] at hchange
    have hRne : (R : ℂ) ≠ 0 := Complex.ofReal_ne_zero.mpr hRpos.ne'
    calc
      (∫ t : ℝ, squaredOscillatoryCauchyKernel c a t) =
          (R : ℂ) * ((R⁻¹ : ℝ) : ℂ) *
            ∫ t : ℝ, squaredOscillatoryCauchyKernel c a t := by
              rw [← ofReal_mul, mul_inv_cancel₀ hRpos.ne', ofReal_one, one_mul]
      _ = (R : ℂ) * (((R⁻¹ : ℝ) : ℂ) *
            ∫ t : ℝ, squaredOscillatoryCauchyKernel c a t) := by ring
      _ = (R : ℂ) * ((a : ℂ) * Complex.exp (-(c * a : ℝ))) := by rw [← hchange]
      _ = (2 * (Real.pi : ℂ)) * (a : ℂ) * Real.exp (-a * c) := by
        dsimp only [R]
        rw [show (-((c * a : ℝ) : ℂ)) = ((-a * c : ℝ) : ℂ) by push_cast; ring]
        rw [← ofReal_exp]
        push_cast
        ring
  · simp only [if_neg hapos] at hchange ⊢
    rw [real_smul] at hchange
    have hRinv : ((R⁻¹ : ℝ) : ℂ) ≠ 0 :=
      Complex.ofReal_ne_zero.mpr (inv_ne_zero hRpos.ne')
    exact (mul_eq_zero.mp hchange.symm).resolve_left hRinv

theorem squaredCauchyFourierValueTarget : SquaredCauchyFourierValueTarget := by
  intro c a hc ha
  exact integral_squaredOscillatoryCauchyKernel hc ha

theorem oscillatoryCauchyLimitTarget : OscillatoryCauchyLimitTarget :=
  oscillatoryCauchyLimitTarget_of_squaredCauchyFourierValueTarget
    squaredCauchyFourierValueTarget

theorem logarithmicScalarPerronLimitTarget : LogarithmicScalarPerronLimitTarget :=
  logarithmicScalarPerronLimitTarget_iff_oscillatory.mpr
    oscillatoryCauchyLimitTarget

/-- The scalar Perron discontinuity kernel is now fully proved away from its
jump at `y = 1`. -/
theorem scalarPerronLimitTarget : ScalarPerronLimitTarget :=
  scalarPerronLimitTarget_iff_logarithmic.mpr logarithmicScalarPerronLimitTarget



end RiemannLab
