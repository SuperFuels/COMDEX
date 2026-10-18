import RiemannLab.Tasks.ScalarPerron
import Mathlib.MeasureTheory.Integral.IntervalIntegral.IntegrationByParts

namespace RiemannLab

open Filter MeasureTheory Complex
open scoped ComplexConjugate Interval Topology

/-!
Integration-by-parts infrastructure for the only remaining conditional limit
inside the scalar Perron kernel.
-/

/-- A vertical line with nonzero real part avoids the origin. -/
theorem verticalLine_ne_zero_of_re_ne_zero {c : ℝ} (hc : c ≠ 0) (t : ℝ) :
    (c + t * Complex.I : ℂ) ≠ 0 := by
  intro h
  have hRe := congrArg Complex.re h
  simp only [Complex.add_re, Complex.ofReal_re, Complex.mul_re, Complex.I_re,
    Complex.I_im, mul_zero, Complex.ofReal_im, zero_mul, sub_zero, Complex.zero_re] at hRe
  exact hc (by simpa using hRe)

/-- Derivative of the reciprocal vertical-line parameter. -/
theorem hasDerivAt_verticalLine_inv {c x : ℝ} (hc : 0 < c) :
    HasDerivAt (fun t : ℝ ↦ (c + t * Complex.I : ℂ)⁻¹)
      (-Complex.I / (c + x * Complex.I : ℂ) ^ 2) x := by
  have hlin : HasDerivAt (fun z : ℂ ↦ c + z * Complex.I) Complex.I (x : ℂ) := by
    simpa only [id_eq, one_mul] using
      ((hasDerivAt_id (x : ℂ)).mul_const Complex.I).const_add (c : ℂ)
  have hinv := hlin.inv (scalarPerron_vertical_ne_zero hc x)
  convert hinv.comp_ofReal using 1
  funext t
  congr 2

/-- A normalized primitive of the pure oscillation `exp(i*a*t)`. -/
noncomputable def oscillatoryPrimitive (a t : ℝ) : ℂ :=
  Complex.exp ((a * t : ℝ) * Complex.I) / ((a : ℂ) * Complex.I)

/-- The normalized primitive differentiates back to the oscillation whenever
the frequency is nonzero. -/
theorem hasDerivAt_oscillatoryPrimitive {a x : ℝ} (ha : a ≠ 0) :
    HasDerivAt (oscillatoryPrimitive a)
      (Complex.exp ((a * x : ℝ) * Complex.I)) x := by
  unfold oscillatoryPrimitive
  have harg : HasDerivAt (fun z : ℂ ↦ (a : ℂ) * z * Complex.I)
      ((a : ℂ) * Complex.I) (x : ℂ) := by
    simpa using (hasDerivAt_id (x : ℂ)).const_mul (a : ℂ) |>.mul_const Complex.I
  have h := harg.cexp.div_const ((a : ℂ) * Complex.I)
  convert h.comp_ofReal using 1
  · funext t
    congr 3
    push_cast
    ring
  · have haC : (a : ℂ) ≠ 0 := Complex.ofReal_ne_zero.mpr ha
    rw [mul_div_cancel_right₀ _ (mul_ne_zero haC I_ne_zero)]
    congr 1
    push_cast
    ring

/-- The oscillatory primitive has constant norm `|a|⁻¹`. -/
theorem norm_oscillatoryPrimitive (a t : ℝ) :
    ‖oscillatoryPrimitive a t‖ = |a|⁻¹ := by
  rw [oscillatoryPrimitive, norm_div, Complex.norm_exp_ofReal_mul_I, norm_mul,
    norm_real, norm_I, mul_one]
  rw [Real.norm_eq_abs, one_div]

/-- On a nonzero height, the reciprocal vertical parameter is bounded by
`|t|⁻¹`; this is the endpoint term in the Dirichlet tail estimate. -/
theorem norm_verticalLine_inv_le_abs_inv {c t : ℝ} (hc : 0 < c) (ht : t ≠ 0) :
    ‖(c + t * Complex.I : ℂ)⁻¹‖ ≤ |t|⁻¹ := by
  have hz : (c + t * Complex.I : ℂ) ≠ 0 := scalarPerron_vertical_ne_zero hc t
  have him : |t| ≤ ‖(c + t * Complex.I : ℂ)‖ := by
    simpa using RCLike.abs_im_le_norm (c + t * Complex.I : ℂ)
  rw [norm_inv]
  exact (inv_le_inv₀ (norm_pos_iff.mpr hz) (abs_pos.mpr ht)).mpr him

/-- Exact norm of the absolutely integrable remainder produced by integration
by parts. -/
theorem norm_oscillatoryCauchy_remainder (c a t : ℝ) :
    ‖(-Complex.I / (c + t * Complex.I : ℂ) ^ 2) * oscillatoryPrimitive a t‖ =
      |a|⁻¹ * (c ^ 2 + t ^ 2)⁻¹ := by
  rw [norm_mul, norm_div, norm_neg, norm_I, one_div, norm_pow,
    norm_oscillatoryPrimitive, Complex.sq_norm, Complex.normSq_add_mul_I]
  ring

/-- The rational majorant of the integration-by-parts remainder is integrable
on the real line whenever `c ≠ 0`. -/
theorem integrable_inv_sq_add_sq {c : ℝ} (hc : c ≠ 0) :
    Integrable (fun t : ℝ ↦ (c ^ 2 + t ^ 2)⁻¹) := by
  have h := integrable_inv_one_add_sq.comp_div hc
  have h' := h.const_mul (c ^ 2)⁻¹
  convert h' using 1 with t
  field_simp

/-- Hence the remainder term is absolutely integrable; only the explicit
endpoint term carries conditional convergence. -/
theorem integrable_oscillatoryCauchy_remainder {c a : ℝ} (hc : c ≠ 0) :
    Integrable (fun t : ℝ ↦
      (-Complex.I / (c + t * Complex.I : ℂ) ^ 2) * oscillatoryPrimitive a t) := by
  have hmeas : AEStronglyMeasurable (fun t : ℝ ↦
      (-Complex.I / (c + t * Complex.I : ℂ) ^ 2) * oscillatoryPrimitive a t) volume := by
    have hden : Continuous (fun t : ℝ ↦ (c + t * Complex.I : ℂ) ^ 2) := by fun_prop
    have hquot : Continuous (fun t : ℝ ↦ -Complex.I / (c + t * Complex.I : ℂ) ^ 2) :=
      continuous_const.div hden
        (fun t ↦ pow_ne_zero 2 (verticalLine_ne_zero_of_re_ne_zero hc t))
    have hprim : Continuous (oscillatoryPrimitive a) := by
      unfold oscillatoryPrimitive
      fun_prop
    exact (hquot.mul hprim).aestronglyMeasurable
  rw [← integrable_norm_iff hmeas]
  simp_rw [norm_oscillatoryCauchy_remainder]
  exact (integrable_inv_sq_add_sq hc).const_mul |a|⁻¹

/-- The boundary term in integration by parts vanishes at positive infinity. -/
theorem tendsto_vertical_inv_mul_oscillatoryPrimitive_atTop_zero
    {c a : ℝ} (hc : 0 < c) :
    Tendsto (fun T : ℝ ↦
      (c + T * Complex.I : ℂ)⁻¹ * oscillatoryPrimitive a T) atTop (𝓝 0) := by
  rw [tendsto_zero_iff_norm_tendsto_zero]
  apply squeeze_zero' (g := fun T : ℝ ↦ T⁻¹ * |a|⁻¹)
  · exact Eventually.of_forall (fun T ↦ norm_nonneg _)
  · filter_upwards [eventually_gt_atTop (0 : ℝ)] with T hT
    rw [norm_mul, norm_oscillatoryPrimitive]
    calc
      ‖(c + T * Complex.I : ℂ)⁻¹‖ * |a|⁻¹
          ≤ |T|⁻¹ * |a|⁻¹ := by
            gcongr
            exact norm_verticalLine_inv_le_abs_inv hc hT.ne'
      _ = T⁻¹ * |a|⁻¹ := by rw [abs_of_pos hT]
  · simpa using tendsto_inv_atTop_zero.mul_const |a|⁻¹

/-- Exact finite-interval integration-by-parts identity. This identity is the
source of the eventual `O(1 / (|a| A))` tail estimate. -/
theorem oscillatoryCauchy_integrationByParts {c a A B : ℝ}
    (hc : 0 < c) (ha : a ≠ 0) :
    (∫ t in A..B,
        (c + t * Complex.I : ℂ)⁻¹ * Complex.exp ((a * t : ℝ) * Complex.I)) =
      (c + B * Complex.I : ℂ)⁻¹ * oscillatoryPrimitive a B -
      (c + A * Complex.I : ℂ)⁻¹ * oscillatoryPrimitive a A -
      ∫ t in A..B,
        (-Complex.I / (c + t * Complex.I : ℂ) ^ 2) * oscillatoryPrimitive a t := by
  apply intervalIntegral.integral_mul_deriv_eq_deriv_mul
  · intro x _
    exact hasDerivAt_verticalLine_inv hc
  · intro x _
    exact hasDerivAt_oscillatoryPrimitive ha
  · exact (by
      have hden : Continuous (fun t : ℝ ↦ (c + t * Complex.I : ℂ)) := by fun_prop
      have hsq : Continuous (fun t : ℝ ↦ (c + t * Complex.I : ℂ) ^ 2) := hden.pow 2
      exact (continuous_const.div hsq
        (fun t ↦ pow_ne_zero 2 (scalarPerron_vertical_ne_zero hc t))).intervalIntegrable A B)
  · exact (by
      have h : Continuous (fun t : ℝ ↦ Complex.exp ((a * t : ℝ) * Complex.I)) := by fun_prop
      exact h.intervalIntegrable A B)

/-- The one-sided sharp oscillatory integral converges for every nonzero
frequency. Its value is expressed by an absolutely convergent remainder; no
contour-value claim is hidden in this existence theorem. -/
theorem tendsto_oneSidedOscillatoryCauchyIntegral {c a : ℝ}
    (hc : 0 < c) (ha : a ≠ 0) :
    Tendsto (fun T : ℝ ↦ ∫ t in 0..T, oscillatoryCauchyKernel c a t) atTop
      (𝓝 (-((c : ℂ)⁻¹ * oscillatoryPrimitive a 0) -
        ∫ t : ℝ in Set.Ioi 0,
          (-Complex.I / (c + t * Complex.I : ℂ) ^ 2) * oscillatoryPrimitive a t)) := by
  let r : ℝ → ℂ := fun t ↦
    (-Complex.I / (c + t * Complex.I : ℂ) ^ 2) * oscillatoryPrimitive a t
  have hr : Integrable r := integrable_oscillatoryCauchy_remainder hc.ne'
  have hR : Tendsto (fun T : ℝ ↦ ∫ t in 0..T, r t) atTop
      (𝓝 (∫ t in Set.Ioi 0, r t)) :=
    intervalIntegral_tendsto_integral_Ioi 0 hr.integrableOn tendsto_id
  have hE := tendsto_vertical_inv_mul_oscillatoryPrimitive_atTop_zero (c := c) (a := a) hc
  have hCombined := (hE.sub_const ((c : ℂ)⁻¹ * oscillatoryPrimitive a 0)).sub hR
  rw [show -((c : ℂ)⁻¹ * oscillatoryPrimitive a 0) -
      (∫ t : ℝ in Set.Ioi 0, r t) =
      0 - (c : ℂ)⁻¹ * oscillatoryPrimitive a 0 -
      (∫ t : ℝ in Set.Ioi 0, r t) by ring]
  apply hCombined.congr'
  filter_upwards with T
  symm
  calc
    (∫ t in 0..T, oscillatoryCauchyKernel c a t) =
        ∫ t in 0..T,
          (c + t * Complex.I : ℂ)⁻¹ * Complex.exp ((a * t : ℝ) * Complex.I) := by
      apply intervalIntegral.integral_congr
      intro t _
      unfold oscillatoryCauchyKernel
      field_simp
    _ = (c + T * Complex.I : ℂ)⁻¹ * oscillatoryPrimitive a T -
        (c : ℂ)⁻¹ * oscillatoryPrimitive a 0 - ∫ t in 0..T, r t := by
      simpa only [r, ofReal_zero, zero_mul, add_zero] using
        oscillatoryCauchy_integrationByParts (A := 0) (B := T) hc ha

/-- The explicit absolutely-convergent expression reached by the one-sided
sharp integral. -/
noncomputable def oneSidedOscillatoryCauchyLimit (c a : ℝ) : ℂ :=
  -((c : ℂ)⁻¹ * oscillatoryPrimitive a 0) -
    ∫ t : ℝ in Set.Ioi 0,
      (-Complex.I / (c + t * Complex.I : ℂ) ^ 2) * oscillatoryPrimitive a t

theorem tendsto_oneSidedOscillatoryCauchyIntegral' {c a : ℝ}
    (hc : 0 < c) (ha : a ≠ 0) :
    Tendsto (fun T : ℝ ↦ ∫ t in 0..T, oscillatoryCauchyKernel c a t) atTop
      (𝓝 (oneSidedOscillatoryCauchyLimit c a)) := by
  simpa only [oneSidedOscillatoryCauchyLimit] using
    tendsto_oneSidedOscillatoryCauchyIntegral hc ha

/-- Reflection in the height variable conjugates the oscillatory kernel. -/
theorem oscillatoryCauchyKernel_neg (c a t : ℝ) :
    oscillatoryCauchyKernel c a (-t) = conj (oscillatoryCauchyKernel c a t) := by
  unfold oscillatoryCauchyKernel
  rw [map_div₀, ← Complex.exp_conj]
  simp only [mul_neg, ofReal_neg, neg_mul, map_add, map_mul, conj_ofReal, conj_I]

/-- The oscillatory Cauchy kernel is continuous on every positive vertical
line. -/
theorem continuous_oscillatoryCauchyKernel {c a : ℝ} (hc : 0 < c) :
    Continuous (oscillatoryCauchyKernel c a) := by
  unfold oscillatoryCauchyKernel
  have hnum : Continuous (fun t : ℝ ↦ Complex.exp ((a * t : ℝ) * Complex.I)) := by fun_prop
  have hden : Continuous (fun t : ℝ ↦ (c + t * Complex.I : ℂ)) := by fun_prop
  exact hnum.div hden (fun t ↦ scalarPerron_vertical_ne_zero hc t)

/-- A symmetric truncation is twice the real part of its positive-height
half, expressed algebraically as `J + conj J`. -/
theorem integral_oscillatoryCauchyKernel_neg_add_pos {c a T : ℝ} (hc : 0 < c) :
    (∫ t in -T..T, oscillatoryCauchyKernel c a t) =
      (∫ t in 0..T, oscillatoryCauchyKernel c a t) +
        conj (∫ t in 0..T, oscillatoryCauchyKernel c a t) := by
  have hcont := continuous_oscillatoryCauchyKernel (c := c) (a := a) hc
  have hneg : IntervalIntegrable (oscillatoryCauchyKernel c a) volume (-T) 0 :=
    hcont.intervalIntegrable (-T) 0
  have hpos : IntervalIntegrable (oscillatoryCauchyKernel c a) volume 0 T :=
    hcont.intervalIntegrable 0 T
  calc
    (∫ t in -T..T, oscillatoryCauchyKernel c a t) =
        (∫ t in -T..0, oscillatoryCauchyKernel c a t) +
          ∫ t in 0..T, oscillatoryCauchyKernel c a t :=
      (intervalIntegral.integral_add_adjacent_intervals hneg hpos).symm
    _ = (∫ t in 0..T, oscillatoryCauchyKernel c a (-t)) +
          ∫ t in 0..T, oscillatoryCauchyKernel c a t := by
      rw [intervalIntegral.integral_comp_neg]
      simp
    _ = (∫ t in 0..T, conj (oscillatoryCauchyKernel c a t)) +
          ∫ t in 0..T, oscillatoryCauchyKernel c a t := by
      congr 2
      funext t
      exact oscillatoryCauchyKernel_neg c a t
    _ = conj (∫ t in 0..T, oscillatoryCauchyKernel c a t) +
          ∫ t in 0..T, oscillatoryCauchyKernel c a t := by
      rw [intervalIntegral.intervalIntegral_conj]
    _ = _ := add_comm _ _

/-- The symmetric sharp truncations genuinely converge for every nonzero
frequency. What remains open is identifying this absolutely-convergent
expression with the classical piecewise value. -/
theorem tendsto_oscillatoryTruncatedCauchyIntegral_exists {c a : ℝ}
    (hc : 0 < c) (ha : a ≠ 0) :
    Tendsto (fun T : ℝ ↦ oscillatoryTruncatedCauchyIntegral c a T) atTop
      (𝓝 ((1 / (2 * (Real.pi : ℂ))) *
        (oneSidedOscillatoryCauchyLimit c a + conj (oneSidedOscillatoryCauchyLimit c a)))) := by
  have H := tendsto_oneSidedOscillatoryCauchyIntegral' hc ha
  have Hconj := RCLike.continuous_conj.continuousAt.tendsto.comp H
  have Hsum := H.add Hconj
  have Hnorm := Hsum.const_mul (1 / (2 * (Real.pi : ℂ)))
  apply Hnorm.congr'
  filter_upwards with T
  simp only [Function.comp_apply]
  rw [← integral_oscillatoryCauchyKernel_neg_add_pos hc]
  rfl

/-- The concrete value of the sharp symmetric limit obtained without any
contour evaluation. -/
noncomputable def oscillatoryCauchyLimitValue (c a : ℝ) : ℂ :=
  (1 / (2 * (Real.pi : ℂ))) *
    (oneSidedOscillatoryCauchyLimit c a + conj (oneSidedOscillatoryCauchyLimit c a))

theorem tendsto_oscillatoryTruncatedCauchyIntegral_value {c a : ℝ}
    (hc : 0 < c) (ha : a ≠ 0) :
    Tendsto (fun T : ℝ ↦ oscillatoryTruncatedCauchyIntegral c a T) atTop
      (𝓝 (oscillatoryCauchyLimitValue c a)) := by
  simpa only [oscillatoryCauchyLimitValue] using
    tendsto_oscillatoryTruncatedCauchyIntegral_exists hc ha

/-- Since convergence is now proved, the original open target is equivalent
to one explicit value-identification theorem. -/
theorem oscillatoryCauchyLimitTarget_iff_value :
    OscillatoryCauchyLimitTarget ↔
      ∀ c a : ℝ, 0 < c → a ≠ 0 →
        oscillatoryCauchyLimitValue c a =
          if 0 < a then (Real.exp (-a * c) : ℂ) else 0 := by
  constructor
  · intro h c a hc ha
    exact tendsto_nhds_unique
      (tendsto_oscillatoryTruncatedCauchyIntegral_value hc ha)
      (h c a hc ha)
  · intro h c a hc ha
    rw [← h c a hc ha]
    exact tendsto_oscillatoryTruncatedCauchyIntegral_value hc ha

/-! A Laplace representation for the remaining value calculation. -/

/-- The reciprocal Cauchy denominator is the Laplace transform of a decaying
complex exponential. -/
theorem integral_exp_neg_verticalLine_mul_Ioi {c t : ℝ} (hc : 0 < c) :
    (∫ u : ℝ in Set.Ioi 0,
      Complex.exp (-(c + t * Complex.I : ℂ) * u)) =
        (c + t * Complex.I : ℂ)⁻¹ := by
  have hre : (-(c + t * Complex.I : ℂ)).re < 0 := by simpa using hc
  rw [integral_exp_mul_complex_Ioi hre 0]
  norm_num
  rw [show (-((t : ℂ) * Complex.I) + -(c : ℂ)) =
      -(c + t * Complex.I : ℂ) by ring]
  rw [neg_div_neg_eq]
  exact one_div _

/-- Consequently the oscillatory Cauchy kernel has an exact source-closed
Laplace representation, ready for a regularized Fubini calculation. -/
theorem oscillatoryCauchyKernel_eq_laplace {c a t : ℝ} (hc : 0 < c) :
    oscillatoryCauchyKernel c a t =
      Complex.exp ((a * t : ℝ) * Complex.I) *
        ∫ u : ℝ in Set.Ioi 0,
          Complex.exp (-(c + t * Complex.I : ℂ) * u) := by
  rw [integral_exp_neg_verticalLine_mul_Ioi hc]
  unfold oscillatoryCauchyKernel
  field_simp

/-! Reduction of the remaining value theorem to an absolutely convergent
Fourier integral. -/

/-- The squared-denominator kernel left after integration by parts. -/
noncomputable def squaredOscillatoryCauchyKernel (c a t : ℝ) : ℂ :=
  Complex.exp ((a * t : ℝ) * Complex.I) / (c + t * Complex.I : ℂ) ^ 2

theorem norm_squaredOscillatoryCauchyKernel (c a t : ℝ) :
    ‖squaredOscillatoryCauchyKernel c a t‖ = (c ^ 2 + t ^ 2)⁻¹ := by
  unfold squaredOscillatoryCauchyKernel
  rw [norm_div, Complex.norm_exp_ofReal_mul_I, norm_pow, Complex.sq_norm,
    Complex.normSq_add_mul_I]
  simp only [one_div]

/-- Unlike the original Cauchy kernel, the squared-denominator kernel is
absolutely integrable on the whole real line. -/
theorem integrable_squaredOscillatoryCauchyKernel {c a : ℝ} (hc : c ≠ 0) :
    Integrable (squaredOscillatoryCauchyKernel c a) := by
  have hmeas : AEStronglyMeasurable (squaredOscillatoryCauchyKernel c a) volume := by
    have hnum : Continuous (fun t : ℝ ↦
        Complex.exp ((a * t : ℝ) * Complex.I)) := by fun_prop
    have hden : Continuous (fun t : ℝ ↦ (c + t * Complex.I : ℂ) ^ 2) := by fun_prop
    exact (hnum.div hden (fun t ↦
      pow_ne_zero 2 (verticalLine_ne_zero_of_re_ne_zero hc t))).aestronglyMeasurable
  rw [← integrable_norm_iff hmeas]
  simp_rw [norm_squaredOscillatoryCauchyKernel]
  exact integrable_inv_sq_add_sq hc

/-- Uniform finite-height bound for the absolutely integrable squared kernel. -/
theorem norm_integral_squaredOscillatoryCauchyKernel_le
    {c a T : ℝ} (hc : 0 < c) :
    ‖∫ t in -T..T, squaredOscillatoryCauchyKernel c a t‖ ≤ c⁻¹ * Real.pi := by
  calc
    ‖∫ t in -T..T, squaredOscillatoryCauchyKernel c a t‖ ≤
        |∫ t in -T..T, ‖squaredOscillatoryCauchyKernel c a t‖| :=
      intervalIntegral.norm_integral_le_abs_integral_norm
    _ = |c⁻¹ * (Real.arctan (T / c) - Real.arctan (-T / c))| := by
      congr 1
      simp_rw [norm_squaredOscillatoryCauchyKernel]
      exact integral_inv_sq_add_sq hc.ne'
    _ ≤ c⁻¹ * Real.pi := by
      rw [show -T / c = -(T / c) by ring, Real.arctan_neg, sub_neg_eq_add,
        ← two_mul, abs_mul, abs_of_pos (inv_pos.mpr hc)]
      rw [abs_mul, abs_of_pos (by norm_num : (0 : ℝ) < 2)]
      have hatan : |Real.arctan (T / c)| ≤ Real.pi / 2 := by
        rw [abs_le]
        constructor <;> linarith [Real.neg_pi_div_two_lt_arctan (T / c),
          Real.arctan_lt_pi_div_two (T / c)]
      calc
        c⁻¹ * (2 * |Real.arctan (T / c)|) ≤
            c⁻¹ * (2 * (Real.pi / 2)) := by gcongr
        _ = c⁻¹ * Real.pi := by ring

theorem norm_verticalLine_inv_le_inv {c : ℝ} (hc : 0 < c) (t : ℝ) :
    ‖(c + t * Complex.I : ℂ)⁻¹‖ ≤ c⁻¹ := by
  rw [norm_inv]
  apply (inv_le_inv₀
    (norm_pos_iff.mpr (scalarPerron_vertical_ne_zero hc t)) hc).2
  simpa using Complex.re_le_norm (c + t * Complex.I)

/-- Symmetric integration by parts removes the conditional kernel in favour
of the absolutely integrable squared-denominator kernel. -/
theorem oscillatoryCauchy_symmetric_integrationByParts {c a T : ℝ}
    (hc : 0 < c) (ha : a ≠ 0) :
    (∫ t in -T..T, oscillatoryCauchyKernel c a t) =
      (c + T * Complex.I : ℂ)⁻¹ * oscillatoryPrimitive a T -
      (c + (-T) * Complex.I : ℂ)⁻¹ * oscillatoryPrimitive a (-T) +
      (a : ℂ)⁻¹ * ∫ t in -T..T, squaredOscillatoryCauchyKernel c a t := by
  calc
    (∫ t in -T..T, oscillatoryCauchyKernel c a t) =
        ∫ t in -T..T,
          (c + t * Complex.I : ℂ)⁻¹ * Complex.exp ((a * t : ℝ) * Complex.I) := by
      apply intervalIntegral.integral_congr
      intro t _
      unfold oscillatoryCauchyKernel
      field_simp
    _ = (c + T * Complex.I : ℂ)⁻¹ * oscillatoryPrimitive a T -
        (c + (-T) * Complex.I : ℂ)⁻¹ * oscillatoryPrimitive a (-T) -
        ∫ t in -T..T,
          (-Complex.I / (c + t * Complex.I : ℂ) ^ 2) *
            oscillatoryPrimitive a t :=
      by simpa only [Complex.ofReal_neg] using
        oscillatoryCauchy_integrationByParts (A := -T) (B := T) hc ha
    _ = _ := by
      have hint :
          -(∫ t in -T..T,
              (-Complex.I / (c + t * Complex.I : ℂ) ^ 2) *
                oscillatoryPrimitive a t) =
            (a : ℂ)⁻¹ * ∫ t in -T..T, squaredOscillatoryCauchyKernel c a t := by
        rw [← intervalIntegral.integral_neg, ← intervalIntegral.integral_const_mul]
        apply intervalIntegral.integral_congr
        intro t _
        unfold squaredOscillatoryCauchyKernel oscillatoryPrimitive
        have haC : (a : ℂ) ≠ 0 := Complex.ofReal_ne_zero.mpr ha
        field_simp
      rw [sub_eq_add_neg, hint]

/-- A height-independent Dirichlet bound for the symmetric oscillatory Cauchy
integral. -/
theorem norm_integral_oscillatoryCauchyKernel_le
    {c a T : ℝ} (hc : 0 < c) (ha : a ≠ 0) :
    ‖∫ t in -T..T, oscillatoryCauchyKernel c a t‖ ≤
      |a|⁻¹ * (2 * c⁻¹ + c⁻¹ * Real.pi) := by
  rw [oscillatoryCauchy_symmetric_integrationByParts hc ha]
  let e₁ : ℂ := (c + T * Complex.I : ℂ)⁻¹ * oscillatoryPrimitive a T
  let e₂ : ℂ := (c + (-T) * Complex.I : ℂ)⁻¹ * oscillatoryPrimitive a (-T)
  let r : ℂ := (a : ℂ)⁻¹ *
    ∫ t in -T..T, squaredOscillatoryCauchyKernel c a t
  have htri : ‖e₁ - e₂ + r‖ ≤ ‖e₁‖ + ‖e₂‖ + ‖r‖ := by
    calc
      ‖e₁ - e₂ + r‖ ≤ ‖e₁ - e₂‖ + ‖r‖ := norm_add_le _ _
      _ ≤ (‖e₁‖ + ‖e₂‖) + ‖r‖ :=
        by simpa [add_comm, add_left_comm, add_assoc] using
          add_le_add_right (norm_sub_le e₁ e₂) ‖r‖
      _ = ‖e₁‖ + ‖e₂‖ + ‖r‖ := rfl
  apply htri.trans
  have he₁ : ‖e₁‖ ≤ c⁻¹ * |a|⁻¹ := by
    unfold e₁
    rw [norm_mul, norm_oscillatoryPrimitive]
    gcongr
    exact norm_verticalLine_inv_le_inv hc T
  have he₂ : ‖e₂‖ ≤ c⁻¹ * |a|⁻¹ := by
    unfold e₂
    rw [norm_mul, norm_oscillatoryPrimitive]
    gcongr
    simpa only [Complex.ofReal_neg] using norm_verticalLine_inv_le_inv hc (-T)
  have hr : ‖r‖ ≤ |a|⁻¹ * (c⁻¹ * Real.pi) := by
    unfold r
    rw [norm_mul, norm_inv, norm_real, Real.norm_eq_abs]
    gcongr
    exact norm_integral_squaredOscillatoryCauchyKernel_le hc
  calc
    ‖e₁‖ + ‖e₂‖ + ‖r‖ ≤
        c⁻¹ * |a|⁻¹ + c⁻¹ * |a|⁻¹ +
          |a|⁻¹ * (c⁻¹ * Real.pi) := by gcongr
    _ = |a|⁻¹ * (2 * c⁻¹ + c⁻¹ * Real.pi) := by ring

/-- The negative-height endpoint in the symmetric integration-by-parts
formula also vanishes. -/
theorem tendsto_negative_vertical_inv_mul_oscillatoryPrimitive_atTop_zero
    {c a : ℝ} (hc : 0 < c) :
    Tendsto (fun T : ℝ ↦
      (c + (-T) * Complex.I : ℂ)⁻¹ * oscillatoryPrimitive a (-T)) atTop (𝓝 0) := by
  rw [tendsto_zero_iff_norm_tendsto_zero]
  apply squeeze_zero' (g := fun T : ℝ ↦ T⁻¹ * |a|⁻¹)
  · exact Eventually.of_forall (fun T ↦ norm_nonneg _)
  · filter_upwards [eventually_gt_atTop (0 : ℝ)] with T hT
    rw [norm_mul, norm_oscillatoryPrimitive]
    calc
      ‖(c + (-T) * Complex.I : ℂ)⁻¹‖ * |a|⁻¹
          ≤ |-T|⁻¹ * |a|⁻¹ := by
            gcongr
            have hb := norm_verticalLine_inv_le_abs_inv (c := c) (t := -T) hc
              (neg_ne_zero.mpr hT.ne')
            simpa only [Complex.ofReal_neg] using hb
      _ = T⁻¹ * |a|⁻¹ := by rw [abs_neg, abs_of_pos hT]
  · simpa using tendsto_inv_atTop_zero.mul_const |a|⁻¹

/-- The already-constructed sharp limit is exactly a normalized, absolutely
convergent Fourier integral. This isolates the remaining value computation. -/
theorem oscillatoryCauchyLimitValue_eq_integral_squared {c a : ℝ}
    (hc : 0 < c) (ha : a ≠ 0) :
    oscillatoryCauchyLimitValue c a =
      (1 / (2 * (Real.pi : ℂ))) * (a : ℂ)⁻¹ *
        ∫ t : ℝ, squaredOscillatoryCauchyKernel c a t := by
  have hInt := intervalIntegral_tendsto_integral
    (l := atTop) (a := fun T : ℝ ↦ -T) (b := fun T : ℝ ↦ T)
    (integrable_squaredOscillatoryCauchyKernel (a := a) hc.ne')
    tendsto_neg_atTop_atBot (tendsto_id : Tendsto (fun T : ℝ ↦ T) atTop atTop)
  have hPos := tendsto_vertical_inv_mul_oscillatoryPrimitive_atTop_zero
    (c := c) (a := a) hc
  have hNeg := tendsto_negative_vertical_inv_mul_oscillatoryPrimitive_atTop_zero
    (c := c) (a := a) hc
  have hRhs := ((hPos.sub hNeg).add
    (hInt.const_mul (a : ℂ)⁻¹)).const_mul (1 / (2 * (Real.pi : ℂ)))
  have hSharp := tendsto_oscillatoryTruncatedCauchyIntegral_value hc ha
  have hRhs' : Tendsto
      (fun T : ℝ ↦ oscillatoryTruncatedCauchyIntegral c a T) atTop
      (𝓝 ((1 / (2 * (Real.pi : ℂ))) * (a : ℂ)⁻¹ *
        ∫ t : ℝ, squaredOscillatoryCauchyKernel c a t)) := by
    convert hRhs using 1
    · funext T
      unfold oscillatoryTruncatedCauchyIntegral
      rw [oscillatoryCauchy_symmetric_integrationByParts hc ha]
    · ring_nf
  exact tendsto_nhds_unique hSharp hRhs'

/-- The remaining absolutely convergent Fourier-transform evaluation. Its
normalization is chosen so that it closes the original scalar Perron gate
without any further conditional-limit argument. -/
def SquaredCauchyFourierValueTarget : Prop :=
  ∀ c a : ℝ, 0 < c → a ≠ 0 →
    (∫ t : ℝ, squaredOscillatoryCauchyKernel c a t) =
      if 0 < a then
        (2 * (Real.pi : ℂ)) * (a : ℂ) * Real.exp (-a * c)
      else 0

/-- The absolutely convergent Fourier value is sufficient for the complete
oscillatory Cauchy limit, hence (through `ScalarPerron.lean`) for the scalar
Perron limit away from its jump. -/
theorem oscillatoryCauchyLimitTarget_of_squaredCauchyFourierValueTarget
    (h : SquaredCauchyFourierValueTarget) : OscillatoryCauchyLimitTarget := by
  rw [oscillatoryCauchyLimitTarget_iff_value]
  intro c a hc ha
  rw [oscillatoryCauchyLimitValue_eq_integral_squared hc ha, h c a hc ha]
  by_cases hapos : 0 < a
  · simp only [if_pos hapos]
    have haC : (a : ℂ) ≠ 0 := Complex.ofReal_ne_zero.mpr ha
    have hpiC : (Real.pi : ℂ) ≠ 0 := Complex.ofReal_ne_zero.mpr Real.pi_ne_zero
    field_simp
  · simp only [if_neg hapos, mul_zero]

end RiemannLab
