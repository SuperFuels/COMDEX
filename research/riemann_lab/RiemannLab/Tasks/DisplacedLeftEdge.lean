import RiemannLab.Tasks.AdmissibleHeightBounds

namespace RiemannLab

open Filter Set
open scoped Topology Interval

/-!
The deterministic displaced-left contour.  Negative odd real parts avoid all
trivial zeros, while every nontrivial zero lies in `0 < re(s) < 1`.
-/

/-- The `n`th displaced-left real part is the negative odd integer
`-(2n+1)`. -/
def displacedLeftRealPart (n : ℕ) : ℝ := -(2 * (n : ℝ) + 1)

theorem displacedLeftRealPart_neg (n : ℕ) : displacedLeftRealPart n < 0 := by
  have hn : 0 ≤ (n : ℝ) := Nat.cast_nonneg n
  dsimp [displacedLeftRealPart]
  linarith

theorem tendsto_displacedLeftRealPart_atBot :
    Tendsto displacedLeftRealPart atTop atBot := by
  refine tendsto_atBot.2 fun b ↦ ?_
  obtain ⟨N, hN⟩ := exists_nat_ge ((-b + 1) / 2)
  filter_upwards [eventually_ge_atTop N] with n hn
  dsimp [displacedLeftRealPart]
  have hn' : ((N : ℝ) : ℝ) ≤ n := by exact_mod_cast hn
  linarith

/-- No zeta zero lies on a negative-odd vertical line. -/
theorem riemannZeta_ne_zero_on_displacedLeftRealPart (n : ℕ) (t : ℝ) :
    riemannZeta (displacedLeftRealPart n + t * Complex.I) ≠ 0 := by
  intro hz
  have hre : (displacedLeftRealPart n + t * Complex.I : ℂ).re ≤ 0 := by
    have hn : 0 ≤ (n : ℝ) := Nat.cast_nonneg n
    dsimp [displacedLeftRealPart]
    simp
    linarith
  obtain ⟨k, hk⟩ := zeta_zero_of_re_nonpos_is_trivial hz hre
  have hreEq := congrArg Complex.re hk
  simp [displacedLeftRealPart] at hreEq
  have hparityReal : 2 * (n : ℝ) + 1 = 2 * ((k : ℝ) + 1) := by
    linarith [hreEq]
  have hparity : 2 * (n : ℤ) + 1 = 2 * ((k : ℤ) + 1) := by
    exact_mod_cast hparityReal
  omega

/-- Exact remaining decay statement for the displaced-left edge.  The
functional equation and gamma-factor estimates are expected to supply such a
bound. -/
def DisplacedLeftKernelDecayTarget (x : ℝ) : Prop :=
  ∃ C : ℕ → ℝ,
    (∀ n t, t ∈ Ι (-quantitativeAdmissibleZetaHeight n) (quantitativeAdmissibleZetaHeight n) →
      ‖explicitFormulaContourKernel x
        (displacedLeftRealPart n + t * Complex.I)‖ ≤ C n) ∧
    Tendsto (fun n ↦ C n *
      |quantitativeAdmissibleZetaHeight n - (-quantitativeAdmissibleZetaHeight n)|) atTop (𝓝 0)

/-- Once the displaced-left kernel decay estimate is supplied, the actual
oriented left-edge integrals vanish. -/
theorem tendsto_displacedLeft_edge_zero {x : ℝ}
    (hdecay : DisplacedLeftKernelDecayTarget x) :
    Tendsto (fun n ↦ Complex.I *
      (∫ t in (-quantitativeAdmissibleZetaHeight n)..quantitativeAdmissibleZetaHeight n,
        explicitFormulaContourKernel x
          (displacedLeftRealPart n + t * Complex.I))) atTop (𝓝 0) := by
  obtain ⟨C, hC, hzero⟩ := hdecay
  exact tendsto_vertical_explicitFormulaContourKernel_integral_zero hC hzero

end RiemannLab
