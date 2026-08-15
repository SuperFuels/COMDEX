import RiemannLab.Tasks.PerronFormula
import Mathlib.Analysis.Complex.CauchyIntegral

namespace RiemannLab

open Filter Set
open Asymptotics
open scoped Interval Topology

/-!
Oriented rectangular-contour infrastructure for the Chebyshev explicit
formula.  The definitions follow Mathlib's Cauchy--Goursat orientation exactly,
so later pole excision cannot silently reverse a horizontal or vertical side.
-/

/-- The positively oriented integral around the rectangle with opposite
corners `z` and `w`, in Mathlib's explicit four-side parametrization. -/
noncomputable def rectangleBoundaryIntegral (f : ℂ → ℂ) (z w : ℂ) : ℂ :=
  (∫ x : ℝ in z.re..w.re, f (x + z.im * Complex.I)) -
    (∫ x : ℝ in z.re..w.re, f (x + w.im * Complex.I)) +
    Complex.I * (∫ y : ℝ in z.im..w.im, f (w.re + y * Complex.I)) -
    Complex.I * (∫ y : ℝ in z.im..w.im, f (z.re + y * Complex.I))

/-- Cauchy--Goursat in the exact rectangle representation used by the RH
programme. -/
theorem rectangleBoundaryIntegral_eq_zero
    (f : ℂ → ℂ) (z w : ℂ)
    (hcont : ContinuousOn f ([[z.re, w.re]] ×ℂ [[z.im, w.im]]))
    (hdiff : DifferentiableOn ℂ f
      (Ioo (min z.re w.re) (max z.re w.re) ×ℂ
        Ioo (min z.im w.im) (max z.im w.im))) :
    rectangleBoundaryIntegral f z w = 0 := by
  simpa [rectangleBoundaryIntegral, smul_eq_mul] using
    Complex.integral_boundary_rect_eq_zero_of_continuousOn_of_differentiableOn
      f z w hcont hdiff

/-- The contour-shift kernel is definitionally the same logarithmic-derivative
kernel already used in the proved Perron inversion. -/
theorem explicitFormulaContourKernel_eq_zetaPerronKernel (x : ℝ) (s : ℂ) :
    explicitFormulaContourKernel x s = zetaPerronKernel x s := by
  simp [explicitFormulaContourKernel, zetaPerronKernel, logDeriv_apply]
  ring

/-- The oriented vertical contour integral along `Re(s)=c`, from height `a`
to height `b`.  The leading `i` is `ds/dt`. -/
noncomputable def verticalExplicitFormulaContourIntegral
    (x c a b : ℝ) : ℂ :=
  Complex.I * ∫ t in a..b, explicitFormulaContourKernel x (c + t * Complex.I)

/-- The right edge of the contour, after division by `2πi`, is exactly the
finite-height Perron integral already proved to converge to `ψ(x)`. -/
theorem normalized_verticalExplicitFormulaContourIntegral_eq_perron
    (x c T : ℝ) :
    (1 / (2 * (Real.pi : ℂ) * Complex.I)) *
        verticalExplicitFormulaContourIntegral x c (-T) T =
      truncatedZetaPerronIntegral c T x := by
  rw [verticalExplicitFormulaContourIntegral, truncatedZetaPerronIntegral]
  simp_rw [explicitFormulaContourKernel_eq_zetaPerronKernel]
  have hpi : (Real.pi : ℂ) ≠ 0 := by exact_mod_cast Real.pi_ne_zero
  field_simp [hpi, Complex.I_ne_zero]

/-- The logarithmic derivative of zeta has residue `-1` at zeta's simple
pole `s=1`.  This packages Mathlib's Laurent asymptotic in the exact form used
by contour shifting. -/
theorem tendsto_mul_zetaLogDeriv_at_one :
    Tendsto (fun s : ℂ ↦ (s - 1) * logDeriv riemannZeta s) (𝓝[≠] 1) (𝓝 (-1)) := by
  have hrem : Tendsto
      (fun s : ℂ ↦ logDeriv riemannZeta s + (s - 1)⁻¹ - Real.eulerMascheroniConstant)
      (𝓝[≠] 1) (𝓝 0) := by
    simpa [logDeriv_apply] using
      ((isLittleO_one_iff ℂ).mp log_deriv_riemannZeta_add_inv_sub_sub_isLittleO)
  have hregular : Tendsto
      (fun s : ℂ ↦ logDeriv riemannZeta s + (s - 1)⁻¹)
      (𝓝[≠] 1) (𝓝 (Real.eulerMascheroniConstant : ℂ)) := by
    convert hrem.add tendsto_const_nhds using 1 <;> ring
  have hsmall : Tendsto
      (fun s : ℂ ↦ (s - 1) * (logDeriv riemannZeta s + (s - 1)⁻¹))
      (𝓝[≠] 1) (𝓝 0) := by
    have hshift : Tendsto (fun s : ℂ ↦ s - 1) (𝓝[≠] 1) (𝓝 0) := by
      have hc : ContinuousAt (fun s : ℂ ↦ s - 1) 1 := by fun_prop
      simpa using hc.continuousWithinAt.tendsto
    simpa using hshift.mul hregular
  have hmodel : Tendsto
      (fun s : ℂ ↦ (s - 1) * (logDeriv riemannZeta s + (s - 1)⁻¹) - 1)
      (𝓝[≠] 1) (𝓝 (-1)) := by
    simpa using hsmall.sub tendsto_const_nhds
  apply hmodel.congr'
  filter_upwards [self_mem_nhdsWithin] with s hs
  have hs1 : s - 1 ≠ 0 := sub_ne_zero.mpr hs
  field_simp [hs1]
  ring

/-- The pole at `s=1` contributes the main term `x` to the Chebyshev explicit
formula. -/
theorem tendsto_mul_explicitFormulaContourKernel_at_one {x : ℝ} (hx : 0 < x) :
    Tendsto (fun s : ℂ ↦ (s - 1) * explicitFormulaContourKernel x s)
      (𝓝[≠] 1) (𝓝 (x : ℂ)) := by
  have hweight : Tendsto (fun s : ℂ ↦ (x : ℂ) ^ s / s) (𝓝[≠] 1) (𝓝 (x : ℂ)) := by
    have hcontinuous : ContinuousAt (fun s : ℂ ↦ (x : ℂ) ^ s / s) 1 :=
      (continuousAt_const_cpow (Complex.ofReal_ne_zero.mpr hx.ne')).div continuousAt_id one_ne_zero
    simpa using hcontinuous.tendsto.mono_left nhdsWithin_le_nhds
  have hproduct := tendsto_mul_zetaLogDeriv_at_one.neg.mul hweight
  simpa [explicitFormulaContourKernel, Complex.cpow_one, mul_assoc] using hproduct

/-- The pole introduced by the Perron factor `1/s` at `s=0` contributes
`-log(2π)`. -/
theorem tendsto_mul_explicitFormulaContourKernel_at_zero {x : ℝ} (hx : 0 < x) :
    Tendsto (fun s : ℂ ↦ s * explicitFormulaContourKernel x s)
      (𝓝[≠] 0) (𝓝 (-Complex.log (2 * Real.pi))) := by
  have hzetaAnalytic : AnalyticAt ℂ riemannZeta 0 := by
    exact analyticOn_riemannZeta 0 (by norm_num)
  have hzeta0 : riemannZeta 0 ≠ 0 := by rw [riemannZeta_zero]; norm_num
  have hlog : Tendsto (fun s : ℂ ↦ -logDeriv riemannZeta s)
      (𝓝[≠] 0) (𝓝 (-Complex.log (2 * Real.pi))) := by
    have hc : ContinuousAt (fun s : ℂ ↦ -logDeriv riemannZeta s) 0 :=
      (hzetaAnalytic.deriv.continuousAt.div hzetaAnalytic.continuousAt hzeta0).neg
    have hvalue : -logDeriv riemannZeta 0 = -Complex.log (2 * Real.pi) := by
      rw [logDeriv_apply, deriv_riemannZeta_zero, riemannZeta_zero]
      ring
    rw [← hvalue]
    exact hc.tendsto.mono_left nhdsWithin_le_nhds
  have hpow : Tendsto (fun s : ℂ ↦ (x : ℂ) ^ s) (𝓝[≠] 0) (𝓝 1) := by
    have hc : ContinuousAt (fun s : ℂ ↦ (x : ℂ) ^ s) 0 :=
      continuousAt_const_cpow (Complex.ofReal_ne_zero.mpr hx.ne')
    simpa using hc.tendsto.mono_left nhdsWithin_le_nhds
  have hproduct : Tendsto (fun s : ℂ ↦ -logDeriv riemannZeta s * (x : ℂ) ^ s)
      (𝓝[≠] 0) (𝓝 (-Complex.log (2 * Real.pi))) := by
    simpa using hlog.mul hpow
  apply hproduct.congr'
  filter_upwards [self_mem_nhdsWithin] with s hs
  have hs0 : s ≠ 0 := by simpa using hs
  unfold explicitFormulaContourKernel
  field_simp [hs0]

end RiemannLab
