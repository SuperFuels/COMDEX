import RiemannLab.Tasks.ZetaQuadraticSummability
import Mathlib.Analysis.Normed.Module.MultipliableUniformlyOn

namespace RiemannLab

open Complex

/-!
# The genus-one primary factor

This file supplies the local analytic and quantitative facts used to turn the
quadratically summable zeta divisor into a locally uniform canonical product.
-/

/-- The genus-one Weierstrass primary factor attached to a nonzero point
`ρ`. -/
noncomputable def zetaGenusOneFactor (ρ z : ℂ) : ℂ :=
  (1 - z / ρ) * Complex.exp (z / ρ)

@[simp] theorem zetaGenusOneFactor_zero (ρ : ℂ) :
    zetaGenusOneFactor ρ 0 = 1 := by
  simp [zetaGenusOneFactor]

theorem zetaGenusOneFactor_analytic (ρ : ℂ) :
    ∀ z, AnalyticAt ℂ (zetaGenusOneFactor ρ) z := by
  intro z
  unfold zetaGenusOneFactor
  fun_prop

/-- Away from the forbidden denominator `ρ=0`, the primary factor has its
only zero at `z=ρ`. -/
theorem zetaGenusOneFactor_eq_zero_iff {ρ z : ℂ} (hρ : ρ ≠ 0) :
    zetaGenusOneFactor ρ z = 0 ↔ z = ρ := by
  rw [zetaGenusOneFactor, mul_eq_zero]
  simp only [Complex.exp_ne_zero, or_false]
  constructor
  · intro h
    have : z / ρ = 1 := (sub_eq_zero.mp h).symm
    exact (div_eq_one_iff_eq hρ).mp this
  · rintro rfl
    simp [hρ]

/-- Exact derivative of one genus-one factor. -/
theorem hasDerivAt_zetaGenusOneFactor {ρ z : ℂ} (hρ : ρ ≠ 0) :
    HasDerivAt (zetaGenusOneFactor ρ)
      (-(z / ρ ^ 2) * Complex.exp (z / ρ)) z := by
  have hdiv : HasDerivAt (fun x : ℂ ↦ x / ρ) (1 / ρ) z := by
    simpa using (hasDerivAt_id z).div_const ρ
  have hone : HasDerivAt
      ((fun _ : ℂ ↦ (1 : ℂ)) - fun x : ℂ ↦ x / ρ) (-(1 / ρ)) z := by
    simpa only [zero_sub] using
      (hasDerivAt_const z (1 : ℂ)).sub hdiv
  have hexp : HasDerivAt (fun x : ℂ ↦ Complex.exp (x / ρ))
      (Complex.exp (z / ρ) * (1 / ρ)) z :=
    (Complex.hasDerivAt_exp (z / ρ)).comp z hdiv
  have hmul := hone.mul hexp
  have hfun : ((fun _ : ℂ ↦ (1 : ℂ)) - fun x : ℂ ↦ x / ρ) =
      (fun x : ℂ ↦ 1 - x / ρ) := by rfl
  rw [hfun] at hmul
  have heq : -(z / ρ ^ 2) * Complex.exp (z / ρ) =
      -(1 / ρ) * Complex.exp (z / ρ) +
        (1 - z / ρ) * (Complex.exp (z / ρ) * (1 / ρ)) := by
    field_simp [hρ]
    ring
  unfold zetaGenusOneFactor
  rw [heq]
  exact hmul

/-- Exact logarithmic derivative of the primary factor away from its zero. -/
theorem logDeriv_zetaGenusOneFactor {ρ z : ℂ} (hρ : ρ ≠ 0) (hz : z ≠ ρ) :
    logDeriv (zetaGenusOneFactor ρ) z = 1 / ρ + 1 / (z - ρ) := by
  rw [logDeriv_apply, (hasDerivAt_zetaGenusOneFactor hρ).deriv]
  have hfactor : zetaGenusOneFactor ρ z ≠ 0 :=
    (zetaGenusOneFactor_eq_zero_iff hρ).not.mpr hz
  unfold zetaGenusOneFactor at hfactor ⊢
  field_simp
  ring

/-- Cancellation of the linear exponential term makes the genus-one factor
quadratically close to one on the unit disk. -/
theorem norm_zetaGenusOneFactor_sub_one_le {ρ z : ℂ} (hρ : ρ ≠ 0)
    (hsmall : ‖z / ρ‖ ≤ 1) :
    ‖zetaGenusOneFactor ρ z - 1‖ ≤ 3 * ‖z / ρ‖ ^ 2 := by
  let w : ℂ := z / ρ
  have hexp1 : ‖Complex.exp w - 1‖ ≤ 2 * ‖w‖ :=
    Complex.norm_exp_sub_one_le hsmall
  have hexp2 : ‖Complex.exp w - 1 - w‖ ≤ ‖w‖ ^ 2 :=
    Complex.norm_exp_sub_one_sub_id_le hsmall
  have hid : (1 - w) * Complex.exp w - 1 =
      (Complex.exp w - 1 - w) + w * (1 - Complex.exp w) := by ring
  unfold zetaGenusOneFactor
  change ‖(1 - w) * Complex.exp w - 1‖ ≤ 3 * ‖w‖ ^ 2
  rw [hid]
  calc
    ‖(Complex.exp w - 1 - w) + w * (1 - Complex.exp w)‖ ≤
        ‖Complex.exp w - 1 - w‖ + ‖w * (1 - Complex.exp w)‖ :=
      norm_add_le _ _
    _ ≤ ‖w‖ ^ 2 + ‖w‖ * (2 * ‖w‖) := by
      apply add_le_add hexp2
      rw [norm_mul]
      apply mul_le_mul_of_nonneg_left _ (norm_nonneg w)
      have hnorm : ‖1 - Complex.exp w‖ = ‖Complex.exp w - 1‖ := by
        rw [← norm_neg]
        congr 1
        ring
      rw [hnorm]
      exact hexp1
    _ = 3 * ‖w‖ ^ 2 := by ring

/-- A global quadratic-exponential primary-factor estimate.  Unlike the
unit-disk estimate, this version has no smallness hypothesis and is therefore
suited to uniform products on an arbitrary fixed compact disk. -/
theorem norm_zetaGenusOneFactor_sub_one_le_global {ρ z : ℂ} :
    ‖zetaGenusOneFactor ρ z - 1‖ ≤
      2 * ‖z / ρ‖ ^ 2 * Real.exp ‖z / ρ‖ := by
  let w : ℂ := z / ρ
  have hexp2 : ‖Complex.exp w - 1 - w‖ ≤
      ‖w‖ ^ 2 * Real.exp ‖w‖ := by
    have h := Complex.norm_exp_sub_sum_le_norm_mul_exp w 2
    simp [Finset.sum_range_succ] at h
    convert h using 1
    ring
  have hexp1 : ‖Complex.exp w - 1‖ ≤
      ‖w‖ * Real.exp ‖w‖ := by
    simpa using Complex.norm_exp_sub_sum_le_norm_mul_exp w 1
  have hid : (1 - w) * Complex.exp w - 1 =
      (Complex.exp w - 1 - w) + w * (1 - Complex.exp w) := by ring
  unfold zetaGenusOneFactor
  change ‖(1 - w) * Complex.exp w - 1‖ ≤
    2 * ‖w‖ ^ 2 * Real.exp ‖w‖
  rw [hid]
  calc
    ‖(Complex.exp w - 1 - w) + w * (1 - Complex.exp w)‖ ≤
        ‖Complex.exp w - 1 - w‖ + ‖w * (1 - Complex.exp w)‖ :=
      norm_add_le _ _
    _ ≤ ‖w‖ ^ 2 * Real.exp ‖w‖ +
        ‖w‖ * (‖w‖ * Real.exp ‖w‖) := by
      apply add_le_add hexp2
      rw [norm_mul]
      apply mul_le_mul_of_nonneg_left _ (norm_nonneg w)
      have hnorm : ‖1 - Complex.exp w‖ = ‖Complex.exp w - 1‖ := by
        rw [← norm_neg]
        congr 1
        ring
      rw [hnorm]
      exact hexp1
    _ = 2 * ‖w‖ ^ 2 * Real.exp ‖w‖ := by ring

end RiemannLab
