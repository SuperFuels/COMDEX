import RiemannLab.Tasks.AdmissibleHeights

namespace RiemannLab

set_option maxHeartbeats 3000000

open Filter Set
open scoped Topology Interval

/-!
The exact quantitative input required on the zero-free heights.  The
downstream contour estimates are proved here; only the classical uniform
growth assertion for `ζ'/ζ` remains as a target.
-/

/-- On every fixed strip `-1 ≤ re(s) ≤ c`, the selected upper and lower
horizontal lines admit a common logarithmic-derivative bound `B n` satisfying
`B n / T n → 0`.  Classically one obtains `B n = O(log(T n)^2)`.
-/
def ZetaAdmissibleHeightGrowthTarget : Prop :=
  ∀ c : ℝ, 1 < c →
    ∃ B : ℕ → ℝ,
      (∀ n, 0 ≤ B n) ∧
      Tendsto (fun n ↦ B n / admissibleZetaHeight n) atTop (𝓝 0) ∧
      ∀ n σ, σ ∈ [[(-1 : ℝ), c]] →
        ‖logDeriv riemannZeta
          (σ + admissibleZetaHeight n * Complex.I)‖ ≤ B n ∧
        ‖logDeriv riemannZeta
          (σ - admissibleZetaHeight n * Complex.I)‖ ≤ B n

private theorem rpow_le_rpow_right_endpoint
    {x a b σ : ℝ} (hx : 1 < x) (hab : a ≤ b) (hσ : σ ∈ [[a, b]]) :
    x ^ σ ≤ x ^ b := by
  have hσb : σ ≤ b := by
    have hmem : σ ∈ Icc a b := by
      simpa only [uIcc_of_le hab] using hσ
    exact hmem.2
  exact Real.rpow_le_rpow_of_exponent_le hx.le hσb

/-- The quantitative admissible-height estimate makes the upper horizontal
segment from `-1` to `c` vanish. -/
theorem tendsto_upper_horizontal_segment_zero
    (hgrowth : ZetaAdmissibleHeightGrowthTarget)
    {x c : ℝ} (hx : 1 < x) (hc : 1 < c) :
    Tendsto (fun n ↦ ∫ σ in (-1 : ℝ)..c,
      explicitFormulaContourKernel x
        (σ + admissibleZetaHeight n * Complex.I)) atTop (𝓝 0) := by
  obtain ⟨B, hBnonneg, hBratio, hB⟩ := hgrowth c hc
  let bound : ℕ → ℝ := fun n ↦ B n * x ^ c / admissibleZetaHeight n
  apply tendsto_horizontal_explicitFormulaContourKernel_integral_zero
    (height := admissibleZetaHeight) (bound := bound)
  · intro n σ hσ
    have hσ' : σ ∈ [[(-1 : ℝ), c]] := uIoc_subset_uIcc hσ
    have hheight : 0 < admissibleZetaHeight n :=
      lt_trans (by positivity) (admissibleZetaHeight_lower n)
    have him : admissibleZetaHeight n ≤
        ‖(σ : ℂ) + admissibleZetaHeight n * Complex.I‖ := by
      have := Complex.abs_im_le_norm
        ((σ : ℂ) + admissibleZetaHeight n * Complex.I)
      simpa [abs_of_pos hheight] using this
    calc
      ‖explicitFormulaContourKernel x
          (σ + admissibleZetaHeight n * Complex.I)‖ ≤
          B n * x ^ σ / admissibleZetaHeight n := by
        simpa using norm_explicitFormulaContourKernel_le (zero_lt_one.trans hx)
          (hB n σ hσ').1 him hheight
      _ ≤ B n * x ^ c / admissibleZetaHeight n := by
        exact div_le_div_of_nonneg_right
          (mul_le_mul_of_nonneg_left
            (rpow_le_rpow_right_endpoint hx (by linarith) hσ') (hBnonneg n))
          hheight.le
  · have hconst : Tendsto (fun _ : ℕ ↦ x ^ c * |c - (-1 : ℝ)|) atTop
        (𝓝 (x ^ c * |c - (-1 : ℝ)|)) := tendsto_const_nhds
    have hmul := hBratio.mul hconst
    have hfun : (fun n ↦ bound n * |c - (-1 : ℝ)|) =
        (fun n ↦ (B n / admissibleZetaHeight n) *
          (x ^ c * |c - (-1 : ℝ)|)) := by
      funext n
      dsimp [bound]
      ring
    rw [hfun]
    simpa using hmul

/-- The same quantitative estimate makes the lower horizontal segment vanish.
The lower edge is parametrized with height `-T`. -/
theorem tendsto_lower_horizontal_segment_zero
    (hgrowth : ZetaAdmissibleHeightGrowthTarget)
    {x c : ℝ} (hx : 1 < x) (hc : 1 < c) :
    Tendsto (fun n ↦ ∫ σ in (-1 : ℝ)..c,
      explicitFormulaContourKernel x
        (σ - admissibleZetaHeight n * Complex.I)) atTop (𝓝 0) := by
  obtain ⟨B, hBnonneg, hBratio, hB⟩ := hgrowth c hc
  let bound : ℕ → ℝ := fun n ↦ B n * x ^ c / admissibleZetaHeight n
  have hbound : ∀ n σ, σ ∈ Ι (-1 : ℝ) c →
      ‖explicitFormulaContourKernel x
        (σ + (-admissibleZetaHeight n) * Complex.I)‖ ≤ bound n := by
    intro n σ hσ
    have hσ' : σ ∈ [[(-1 : ℝ), c]] := uIoc_subset_uIcc hσ
    have hheight : 0 < admissibleZetaHeight n :=
      lt_trans (by positivity) (admissibleZetaHeight_lower n)
    have him : admissibleZetaHeight n ≤
        ‖(σ : ℂ) - admissibleZetaHeight n * Complex.I‖ := by
      have := Complex.abs_im_le_norm
        ((σ : ℂ) - admissibleZetaHeight n * Complex.I)
      simpa [abs_of_pos hheight] using this
    have hkernel :
        ‖explicitFormulaContourKernel x
          (σ - admissibleZetaHeight n * Complex.I)‖ ≤
          B n * x ^ σ / admissibleZetaHeight n := by
      simpa using norm_explicitFormulaContourKernel_le (zero_lt_one.trans hx)
        (hB n σ hσ').2 him hheight
    have hkernel' :
        ‖explicitFormulaContourKernel x
          (σ - admissibleZetaHeight n * Complex.I)‖ ≤ bound n :=
      hkernel.trans (div_le_div_of_nonneg_right
        (mul_le_mul_of_nonneg_left
          (rpow_le_rpow_right_endpoint hx (by linarith) hσ') (hBnonneg n))
        hheight.le)
    convert hkernel' using 1 <;> push_cast <;> ring
  have hzero : Tendsto (fun n ↦ bound n * |c - (-1 : ℝ)|) atTop (𝓝 0) := by
    have hconst : Tendsto (fun _ : ℕ ↦ x ^ c * |c - (-1 : ℝ)|) atTop
        (𝓝 (x ^ c * |c - (-1 : ℝ)|)) := tendsto_const_nhds
    have hmul := hBratio.mul hconst
    have hfun : (fun n ↦ bound n * |c - (-1 : ℝ)|) =
        (fun n ↦ (B n / admissibleZetaHeight n) *
          (x ^ c * |c - (-1 : ℝ)|)) := by
      funext n
      dsimp [bound]
      ring
    rw [hfun]
    simpa using hmul
  have hbound' : ∀ n σ, σ ∈ Ι (-1 : ℝ) c →
      ‖explicitFormulaContourKernel x
        (σ + ((-admissibleZetaHeight n : ℝ) : ℂ) * Complex.I)‖ ≤ bound n := by
    intro n σ hσ
    convert hbound n σ hσ using 1 <;> push_cast <;> ring
  have htend := tendsto_horizontal_explicitFormulaContourKernel_integral_zero
    (x := x) (a := (-1 : ℝ)) (b := c)
    (height := fun n ↦ -admissibleZetaHeight n) (bound := bound) hbound' hzero
  have heq :
      (fun n ↦ ∫ σ in (-1 : ℝ)..c, explicitFormulaContourKernel x
        (σ - admissibleZetaHeight n * Complex.I)) =
      (fun n ↦ ∫ σ in (-1 : ℝ)..c, explicitFormulaContourKernel x
        (σ + ((-admissibleZetaHeight n : ℝ) : ℂ) * Complex.I)) := by
    funext n
    apply intervalIntegral.integral_congr
    intro σ hσ
    congr 2 <;> push_cast <;> ring
  rw [heq]
  exact htend

end RiemannLab
