import RiemannLab.Tasks.ZetaContourPrincipalParts

namespace RiemannLab

open Filter Set
open scoped Topology Interval

/-!
Quantitative reduction of the displaced contour edges.  These lemmas contain
no number-theoretic estimate: they turn a bound for `ζ'/ζ` into the exact
kernel and interval-integral bounds required by the explicit-formula contour.
-/

/-- Exact norm of the zeta Perron kernel.  This exposes the three factors that
the admissible-height argument must control: `ζ'/ζ`, `x ^ re(s)`, and `1/|s|`. -/
theorem norm_explicitFormulaContourKernel
    {x : ℝ} (hx : 0 < x) (s : ℂ) :
    ‖explicitFormulaContourKernel x s‖ =
      ‖logDeriv riemannZeta s‖ * x ^ s.re / ‖s‖ := by
  unfold explicitFormulaContourKernel
  rw [norm_mul, norm_neg, norm_div,
    Complex.norm_cpow_eq_rpow_re_of_pos hx]
  ring

/-- A pointwise logarithmic-derivative bound immediately gives the
corresponding pointwise contour-kernel bound. -/
theorem norm_explicitFormulaContourKernel_le
    {x L R : ℝ} (hx : 0 < x) {s : ℂ}
    (hlog : ‖logDeriv riemannZeta s‖ ≤ L) (hR : R ≤ ‖s‖) (hR0 : 0 < R) :
    ‖explicitFormulaContourKernel x s‖ ≤ L * x ^ s.re / R := by
  rw [norm_explicitFormulaContourKernel hx]
  have hxpow : 0 ≤ x ^ s.re := Real.rpow_nonneg hx.le _
  have hL : 0 ≤ L := le_trans (norm_nonneg _) hlog
  calc
    ‖logDeriv riemannZeta s‖ * x ^ s.re / ‖s‖ ≤
        ‖logDeriv riemannZeta s‖ * x ^ s.re / R :=
      div_le_div_of_nonneg_left (mul_nonneg (norm_nonneg _) hxpow) hR0 hR
    _ ≤ L * x ^ s.re / R :=
      div_le_div_of_nonneg_right (mul_le_mul_of_nonneg_right hlog hxpow) hR0.le

/-- Uniform control of a horizontal parametrization bounds its integral by
the width of the rectangle. -/
theorem norm_horizontal_explicitFormulaContourKernel_integral_le
    {x a b T C : ℝ}
    (hbound : ∀ σ ∈ Ι a b,
      ‖explicitFormulaContourKernel x (σ + T * Complex.I)‖ ≤ C) :
    ‖∫ σ in a..b, explicitFormulaContourKernel x
        (σ + T * Complex.I)‖ ≤ C * |b - a| :=
  intervalIntegral.norm_integral_le_of_norm_le_const hbound

/-- Uniform control of a vertical parametrization bounds its integral by its
height.  The prefactor `i` in a contour parametrization has norm one. -/
theorem norm_vertical_explicitFormulaContourKernel_integral_le
    {x a U V C : ℝ}
    (hbound : ∀ t ∈ Ι U V,
      ‖explicitFormulaContourKernel x (a + t * Complex.I)‖ ≤ C) :
    ‖Complex.I * (∫ t in U..V, explicitFormulaContourKernel x
        (a + t * Complex.I))‖ ≤ C * |V - U| := by
  rw [norm_mul, Complex.norm_I, one_mul]
  exact intervalIntegral.norm_integral_le_of_norm_le_const hbound

/-- A sequence of uniform horizontal-edge bounds tending to zero forces the
actual horizontal contour integrals to vanish. -/
theorem tendsto_horizontal_explicitFormulaContourKernel_integral_zero
    {x a b : ℝ} {height bound : ℕ → ℝ}
    (hbound : ∀ n σ, σ ∈ Ι a b →
      ‖explicitFormulaContourKernel x
        (σ + height n * Complex.I)‖ ≤ bound n)
    (hzero : Tendsto (fun n ↦ bound n * |b - a|) atTop (𝓝 0)) :
    Tendsto (fun n ↦ ∫ σ in a..b, explicitFormulaContourKernel x
      (σ + height n * Complex.I)) atTop (𝓝 0) := by
  rw [tendsto_zero_iff_norm_tendsto_zero]
  refine squeeze_zero' (Eventually.of_forall (fun n : ℕ ↦ norm_nonneg
    (∫ σ in a..b, explicitFormulaContourKernel x
      (σ + height n * Complex.I)))) ?_ hzero
  filter_upwards with n
  exact norm_horizontal_explicitFormulaContourKernel_integral_le
    (fun σ hσ ↦ hbound n σ hσ)

/-- A sequence of uniform vertical-edge bounds tending to zero after
multiplication by the edge length forces the vertical contour integrals to
vanish. -/
theorem tendsto_vertical_explicitFormulaContourKernel_integral_zero
    {x : ℝ} {realPart lower upper bound : ℕ → ℝ}
    (hbound : ∀ n t, t ∈ Ι (lower n) (upper n) →
      ‖explicitFormulaContourKernel x
        (realPart n + t * Complex.I)‖ ≤ bound n)
    (hzero : Tendsto (fun n ↦ bound n * |upper n - lower n|) atTop (𝓝 0)) :
    Tendsto (fun n ↦ Complex.I *
      (∫ t in lower n..upper n, explicitFormulaContourKernel x
        (realPart n + t * Complex.I))) atTop (𝓝 0) := by
  rw [tendsto_zero_iff_norm_tendsto_zero]
  refine squeeze_zero' (Eventually.of_forall (fun n : ℕ ↦ norm_nonneg
    (Complex.I * (∫ t in lower n..upper n,
      explicitFormulaContourKernel x
        (realPart n + t * Complex.I))))) ?_ hzero
  filter_upwards with n
  exact norm_vertical_explicitFormulaContourKernel_integral_le
    (fun t ht ↦ hbound n t ht)

end RiemannLab
